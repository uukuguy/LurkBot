"""Anthropic Claude model adapter."""

from collections.abc import AsyncIterator
from typing import Any

from loguru import logger

from lurkbot.models.base import ModelAdapter
from lurkbot.models.types import (
    ModelResponse,
    StreamChunk,
    ToolCall,
    ToolResult,
)


class AnthropicAdapter(ModelAdapter):
    """Adapter for Anthropic Claude models.

    Uses the native Anthropic SDK for optimal performance and feature support.
    Supports vision, tool use, and extended thinking capabilities.
    """

    @property
    def client(self) -> Any:
        """Lazy-load the Anthropic client."""
        if self._client is None:
            import anthropic

            self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_results: list[ToolResult] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Send a chat completion request to Claude.

        Args:
            messages: Conversation messages
            tools: Available tools in Anthropic format
            tool_results: Results from previous tool executions
            **kwargs: Additional parameters (max_tokens, temperature, etc.)

        Returns:
            Unified model response
        """
        # Prepare messages with tool results if any
        api_messages = self._prepare_messages(messages, tool_results)

        # Build request parameters
        request_params: dict[str, Any] = {
            "model": self.config.model_id,
            "max_tokens": self._get_max_tokens(**kwargs),
            "messages": api_messages,
        }

        # Add tools if provided
        if tools:
            request_params["tools"] = tools
            logger.debug(f"Providing {len(tools)} tools to Claude")

        # Add optional parameters
        if "temperature" in kwargs:
            request_params["temperature"] = kwargs["temperature"]
        if "system" in kwargs:
            request_params["system"] = kwargs["system"]

        # Call API
        response = await self.client.messages.create(**request_params)

        return self._parse_response(response)

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_results: list[ToolResult] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a chat completion response from Claude.

        Args:
            messages: Conversation messages
            tools: Available tools in Anthropic format
            tool_results: Results from previous tool executions
            **kwargs: Additional parameters

        Yields:
            Stream chunks containing text or tool use deltas
        """
        # Prepare messages with tool results if any
        api_messages = self._prepare_messages(messages, tool_results)

        # Build request parameters
        request_params: dict[str, Any] = {
            "model": self.config.model_id,
            "max_tokens": self._get_max_tokens(**kwargs),
            "messages": api_messages,
        }

        # Add tools if provided
        if tools:
            request_params["tools"] = tools

        # Add optional parameters
        if "temperature" in kwargs:
            request_params["temperature"] = kwargs["temperature"]
        if "system" in kwargs:
            request_params["system"] = kwargs["system"]

        # Stream response
        async with self.client.messages.stream(**request_params) as stream:
            current_tool_id: str | None = None
            current_tool_name: str | None = None

            async for event in stream:
                if event.type == "content_block_start":
                    if (
                        hasattr(event.content_block, "type")
                        and event.content_block.type == "tool_use"
                    ):
                        current_tool_id = event.content_block.id
                        current_tool_name = event.content_block.name
                        yield StreamChunk(
                            tool_use_id=current_tool_id,
                            tool_name=current_tool_name,
                        )

                elif event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        yield StreamChunk(text=event.delta.text)
                    elif hasattr(event.delta, "partial_json"):
                        yield StreamChunk(
                            tool_use_id=current_tool_id,
                            tool_name=current_tool_name,
                            tool_input_delta=event.delta.partial_json,
                        )

                elif event.type == "message_stop":
                    yield StreamChunk(finish_reason="end_turn")

    def _prepare_messages(
        self,
        messages: list[dict[str, Any]],
        tool_results: list[ToolResult] | None = None,
    ) -> list[dict[str, Any]]:
        """Prepare messages for the Anthropic API.

        Anthropic expects tool results as a user message with tool_result content blocks.

        Args:
            messages: Original conversation messages
            tool_results: Results from tool executions

        Returns:
            Messages formatted for Anthropic API
        """
        # Make a copy to avoid modifying the original
        api_messages = list(messages)

        # Append tool results if any
        if tool_results:
            tool_result_content = [
                {
                    "type": "tool_result",
                    "tool_use_id": result.tool_use_id,
                    "content": result.content,
                    "is_error": result.is_error,
                }
                for result in tool_results
            ]
            api_messages.append({"role": "user", "content": tool_result_content})

        return api_messages

    def _parse_response(self, response: Any) -> ModelResponse:
        """Parse Anthropic response into unified format.

        Args:
            response: Raw Anthropic API response

        Returns:
            Unified ModelResponse
        """
        tool_calls: list[ToolCall] = []
        text_parts: list[str] = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input,
                    )
                )

        return ModelResponse(
            text="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            raw=response,
        )
