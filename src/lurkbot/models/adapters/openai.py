"""OpenAI GPT model adapter."""

import json
from collections.abc import AsyncIterator
from typing import Any

from loguru import logger

from lurkbot.models.base import ModelAdapter
from lurkbot.models.types import (
    ModelConfig,
    ModelResponse,
    StreamChunk,
    ToolCall,
    ToolResult,
)


class OpenAIAdapter(ModelAdapter):
    """Adapter for OpenAI GPT models.

    Uses the native OpenAI SDK with format conversion for tools and messages.
    Converts Anthropic-style tool format to OpenAI function format.
    """

    @property
    def client(self) -> Any:
        """Lazy-load the OpenAI client."""
        if self._client is None:
            import openai

            self._client = openai.AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_results: list[ToolResult] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Send a chat completion request to OpenAI.

        Args:
            messages: Conversation messages
            tools: Available tools in Anthropic format (converted to OpenAI)
            tool_results: Results from previous tool executions
            **kwargs: Additional parameters (max_tokens, temperature, etc.)

        Returns:
            Unified model response
        """
        # Convert messages to OpenAI format
        api_messages = self._convert_messages(messages, tool_results)

        # Build request parameters
        request_params: dict[str, Any] = {
            "model": self.config.model_id,
            "max_tokens": self._get_max_tokens(**kwargs),
            "messages": api_messages,
        }

        # Convert and add tools if provided
        if tools:
            request_params["tools"] = self._convert_tools(tools)
            logger.debug(f"Providing {len(tools)} tools to OpenAI")

        # Add optional parameters
        if "temperature" in kwargs:
            request_params["temperature"] = kwargs["temperature"]

        # Call API
        response = await self.client.chat.completions.create(**request_params)

        return self._parse_response(response)

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_results: list[ToolResult] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a chat completion response from OpenAI.

        Args:
            messages: Conversation messages
            tools: Available tools in Anthropic format
            tool_results: Results from previous tool executions
            **kwargs: Additional parameters

        Yields:
            Stream chunks containing text or tool use deltas
        """
        # Convert messages to OpenAI format
        api_messages = self._convert_messages(messages, tool_results)

        # Build request parameters
        request_params: dict[str, Any] = {
            "model": self.config.model_id,
            "max_tokens": self._get_max_tokens(**kwargs),
            "messages": api_messages,
            "stream": True,
        }

        # Convert and add tools if provided
        if tools:
            request_params["tools"] = self._convert_tools(tools)

        # Add optional parameters
        if "temperature" in kwargs:
            request_params["temperature"] = kwargs["temperature"]

        # Stream response
        stream = await self.client.chat.completions.create(**request_params)

        current_tool_calls: dict[int, dict[str, Any]] = {}

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            finish_reason = chunk.choices[0].finish_reason if chunk.choices else None

            if delta:
                # Handle text content
                if delta.content:
                    yield StreamChunk(text=delta.content)

                # Handle tool calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in current_tool_calls:
                            current_tool_calls[idx] = {
                                "id": tc.id,
                                "name": tc.function.name if tc.function else None,
                                "arguments": "",
                            }
                            if tc.id and tc.function and tc.function.name:
                                yield StreamChunk(
                                    tool_use_id=tc.id,
                                    tool_name=tc.function.name,
                                )

                        if tc.function and tc.function.arguments:
                            current_tool_calls[idx]["arguments"] += tc.function.arguments
                            yield StreamChunk(
                                tool_use_id=current_tool_calls[idx]["id"],
                                tool_name=current_tool_calls[idx]["name"],
                                tool_input_delta=tc.function.arguments,
                            )

            if finish_reason:
                yield StreamChunk(finish_reason=finish_reason)

    def _convert_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert Anthropic tool format to OpenAI function format.

        Anthropic format:
            {"name": "...", "description": "...", "input_schema": {...}}

        OpenAI format:
            {"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}

        Args:
            tools: Tools in Anthropic format

        Returns:
            Tools in OpenAI format
        """
        if not tools:
            return []

        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {}),
                },
            }
            for tool in tools
        ]

    def _convert_messages(
        self,
        messages: list[dict[str, Any]],
        tool_results: list[ToolResult] | None = None,
    ) -> list[dict[str, Any]]:
        """Convert messages to OpenAI format.

        Handles conversion of:
        - Anthropic tool_result content blocks to OpenAI tool role messages
        - Assistant messages with tool_use blocks to function_call format

        Args:
            messages: Messages in provider-agnostic format
            tool_results: Results from tool executions

        Returns:
            Messages in OpenAI format
        """
        converted: list[dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")

            # Handle assistant messages with tool use (from conversation history)
            if role == "assistant" and isinstance(content, list):
                # Extract text and tool calls
                text_parts = []
                tool_calls = []

                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif block.get("type") == "tool_use":
                            tool_calls.append(
                                {
                                    "id": block.get("id"),
                                    "type": "function",
                                    "function": {
                                        "name": block.get("name"),
                                        "arguments": json.dumps(block.get("input", {})),
                                    },
                                }
                            )
                    elif hasattr(block, "type"):
                        # Handle Anthropic content block objects
                        if block.type == "text":
                            text_parts.append(block.text)
                        elif block.type == "tool_use":
                            tool_calls.append(
                                {
                                    "id": block.id,
                                    "type": "function",
                                    "function": {
                                        "name": block.name,
                                        "arguments": json.dumps(block.input),
                                    },
                                }
                            )

                converted_msg: dict[str, Any] = {"role": "assistant"}
                if text_parts:
                    converted_msg["content"] = "\n".join(text_parts)
                if tool_calls:
                    converted_msg["tool_calls"] = tool_calls
                    if "content" not in converted_msg:
                        converted_msg["content"] = None

                converted.append(converted_msg)

            # Handle user messages that might contain tool_result (from history)
            elif role == "user" and isinstance(content, list):
                # Check if this is a tool_result message
                if content and isinstance(content[0], dict) and content[0].get("type") == "tool_result":
                    # Convert each tool_result to a separate tool message
                    for result in content:
                        converted.append(
                            {
                                "role": "tool",
                                "tool_call_id": result.get("tool_use_id"),
                                "content": result.get("content", ""),
                            }
                        )
                else:
                    # Regular user message with content blocks (e.g., vision)
                    converted.append({"role": role, "content": content})

            else:
                # Standard message
                converted.append({"role": role, "content": content})

        # Append new tool results if any
        if tool_results:
            for result in tool_results:
                converted.append(
                    {
                        "role": "tool",
                        "tool_call_id": result.tool_use_id,
                        "content": result.content,
                    }
                )

        return converted

    def _parse_response(self, response: Any) -> ModelResponse:
        """Parse OpenAI response into unified format.

        Args:
            response: Raw OpenAI API response

        Returns:
            Unified ModelResponse
        """
        choice = response.choices[0]
        message = choice.message

        tool_calls: list[ToolCall] = []
        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    arguments = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    arguments = {"raw": tc.function.arguments}

                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=arguments,
                    )
                )

        usage = {}
        if response.usage:
            usage = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            }

        return ModelResponse(
            text=message.content,
            tool_calls=tool_calls,
            stop_reason=choice.finish_reason,
            usage=usage,
            raw=response,
        )
