"""Ollama local model adapter."""

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


class OllamaAdapter(ModelAdapter):
    """Adapter for Ollama local models.

    Uses Ollama's OpenAI-compatible API endpoint for chat completions.
    Supports tool use for models that implement function calling.
    """

    def __init__(
        self,
        config: ModelConfig,
        api_key: str | None = None,
        base_url: str = "http://localhost:11434",
        **kwargs: Any,
    ) -> None:
        """Initialize the Ollama adapter.

        Args:
            config: Model configuration
            api_key: Not used for Ollama (local)
            base_url: Ollama server URL (default: http://localhost:11434)
            **kwargs: Additional options
        """
        super().__init__(config, api_key, **kwargs)
        self.base_url = base_url.rstrip("/")

    @property
    def client(self) -> Any:
        """Lazy-load the httpx async client."""
        if self._client is None:
            import httpx

            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(120.0, connect=30.0),
            )
        return self._client

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_results: list[ToolResult] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Send a chat completion request to Ollama.

        Uses the OpenAI-compatible /v1/chat/completions endpoint.

        Args:
            messages: Conversation messages
            tools: Available tools in Anthropic format (converted to OpenAI)
            tool_results: Results from previous tool executions
            **kwargs: Additional parameters

        Returns:
            Unified model response
        """
        # Convert messages to OpenAI format (Ollama uses OpenAI-compatible API)
        api_messages = self._convert_messages(messages, tool_results)

        # Build request payload
        payload: dict[str, Any] = {
            "model": self.config.model_id,
            "messages": api_messages,
            "stream": False,
        }

        # Add max tokens if specified
        max_tokens = self._get_max_tokens(**kwargs)
        if max_tokens:
            payload["max_tokens"] = max_tokens

        # Convert and add tools if provided
        if tools:
            converted_tools = self._convert_tools(tools)
            if converted_tools:
                payload["tools"] = converted_tools
                logger.debug(f"Providing {len(tools)} tools to Ollama")

        # Add optional parameters
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]

        # Call API
        response = await self.client.post("/v1/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        return self._parse_response(data)

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_results: list[ToolResult] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a chat completion response from Ollama.

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

        # Build request payload
        payload: dict[str, Any] = {
            "model": self.config.model_id,
            "messages": api_messages,
            "stream": True,
        }

        # Add max tokens if specified
        max_tokens = self._get_max_tokens(**kwargs)
        if max_tokens:
            payload["max_tokens"] = max_tokens

        # Convert and add tools if provided
        if tools:
            converted_tools = self._convert_tools(tools)
            if converted_tools:
                payload["tools"] = converted_tools

        # Add optional parameters
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]

        # Stream response using SSE
        async with self.client.stream("POST", "/v1/chat/completions", json=payload) as response:
            response.raise_for_status()

            current_tool_calls: dict[int, dict[str, Any]] = {}

            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue

                data_str = line[6:]  # Remove "data: " prefix
                if data_str == "[DONE]":
                    break

                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                choices = chunk.get("choices", [])
                if not choices:
                    continue

                delta = choices[0].get("delta", {})
                finish_reason = choices[0].get("finish_reason")

                # Handle text content
                if delta.get("content"):
                    yield StreamChunk(text=delta["content"])

                # Handle tool calls
                if delta.get("tool_calls"):
                    for tc in delta["tool_calls"]:
                        idx = tc.get("index", 0)
                        if idx not in current_tool_calls:
                            current_tool_calls[idx] = {
                                "id": tc.get("id"),
                                "name": tc.get("function", {}).get("name"),
                                "arguments": "",
                            }
                            if tc.get("id"):
                                yield StreamChunk(
                                    tool_use_id=tc["id"],
                                    tool_name=tc.get("function", {}).get("name"),
                                )

                        func_args = tc.get("function", {}).get("arguments", "")
                        if func_args:
                            current_tool_calls[idx]["arguments"] += func_args
                            yield StreamChunk(
                                tool_use_id=current_tool_calls[idx]["id"],
                                tool_name=current_tool_calls[idx]["name"],
                                tool_input_delta=func_args,
                            )

                if finish_reason:
                    yield StreamChunk(finish_reason=finish_reason)

    def _convert_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert Anthropic tool format to OpenAI function format.

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

            # Handle assistant messages with tool use blocks
            if role == "assistant" and isinstance(content, list):
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

            # Handle user messages with tool_result content
            elif role == "user" and isinstance(content, list):
                if content and isinstance(content[0], dict) and content[0].get("type") == "tool_result":
                    for result in content:
                        converted.append(
                            {
                                "role": "tool",
                                "tool_call_id": result.get("tool_use_id"),
                                "content": result.get("content", ""),
                            }
                        )
                else:
                    converted.append({"role": role, "content": content})

            else:
                converted.append({"role": role, "content": content})

        # Append new tool results
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

    def _parse_response(self, data: dict[str, Any]) -> ModelResponse:
        """Parse Ollama response into unified format.

        Args:
            data: Raw API response data

        Returns:
            Unified ModelResponse
        """
        choices = data.get("choices", [])
        if not choices:
            return ModelResponse(text="", stop_reason="error")

        choice = choices[0]
        message = choice.get("message", {})

        tool_calls: list[ToolCall] = []
        if message.get("tool_calls"):
            for tc in message["tool_calls"]:
                func = tc.get("function", {})
                try:
                    arguments = json.loads(func.get("arguments", "{}"))
                except json.JSONDecodeError:
                    arguments = {"raw": func.get("arguments", "")}

                tool_calls.append(
                    ToolCall(
                        id=tc.get("id", ""),
                        name=func.get("name", ""),
                        arguments=arguments,
                    )
                )

        usage = {}
        if data.get("usage"):
            usage = {
                "input_tokens": data["usage"].get("prompt_tokens", 0),
                "output_tokens": data["usage"].get("completion_tokens", 0),
            }

        return ModelResponse(
            text=message.get("content"),
            tool_calls=tool_calls,
            stop_reason=choice.get("finish_reason"),
            usage=usage,
            raw=data,
        )

    async def list_models(self) -> list[str]:
        """List available models on the Ollama server.

        Returns:
            List of model names
        """
        response = await self.client.get("/api/tags")
        response.raise_for_status()
        data = response.json()
        return [model["name"] for model in data.get("models", [])]

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
