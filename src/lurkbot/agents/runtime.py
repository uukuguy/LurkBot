"""Agent runtime for managing agent sessions."""

from collections.abc import AsyncIterator
from typing import Any

from loguru import logger

from lurkbot.agents.base import Agent, AgentContext, ChatMessage
from lurkbot.config import Settings


class ClaudeAgent(Agent):
    """Agent using Anthropic's Claude API."""

    def __init__(self, model: str, api_key: str, **kwargs: Any) -> None:
        super().__init__(model, **kwargs)
        self.api_key = api_key
        self._client: Any = None

    @property
    def client(self) -> Any:
        """Lazy-load the Anthropic client."""
        if self._client is None:
            import anthropic

            self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def chat(self, context: AgentContext, message: str) -> str:
        """Process a chat message using Claude."""
        context.messages.append(ChatMessage(role="user", content=message))

        messages = [{"role": m.role, "content": m.content} for m in context.messages]

        response = await self.client.messages.create(
            model=self.model.replace("anthropic/", ""),
            max_tokens=self.config.get("max_tokens", 4096),
            messages=messages,
        )

        assistant_message = response.content[0].text
        context.messages.append(ChatMessage(role="assistant", content=assistant_message))

        return assistant_message

    async def stream_chat(self, context: AgentContext, message: str) -> AsyncIterator[str]:
        """Stream a chat response using Claude."""
        context.messages.append(ChatMessage(role="user", content=message))

        messages = [{"role": m.role, "content": m.content} for m in context.messages]

        full_response = ""
        async with self.client.messages.stream(
            model=self.model.replace("anthropic/", ""),
            max_tokens=self.config.get("max_tokens", 4096),
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                full_response += text
                yield text

        context.messages.append(ChatMessage(role="assistant", content=full_response))


class AgentRuntime:
    """Runtime for managing agent sessions."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.sessions: dict[str, AgentContext] = {}
        self.agents: dict[str, Agent] = {}

    def get_or_create_session(
        self,
        session_id: str,
        channel: str,
        sender_id: str,
        sender_name: str | None = None,
    ) -> AgentContext:
        """Get or create an agent session."""
        if session_id not in self.sessions:
            self.sessions[session_id] = AgentContext(
                session_id=session_id,
                channel=channel,
                sender_id=sender_id,
                sender_name=sender_name,
                workspace=str(self.settings.agent.workspace),
            )
            logger.info(f"Created new session: {session_id}")
        return self.sessions[session_id]

    def get_agent(self, model: str | None = None) -> Agent:
        """Get or create an agent for the specified model."""
        model = model or self.settings.agent.model

        if model not in self.agents:
            if model.startswith("anthropic/"):
                if not self.settings.anthropic_api_key:
                    raise ValueError("ANTHROPIC_API_KEY not configured")
                self.agents[model] = ClaudeAgent(
                    model=model,
                    api_key=self.settings.anthropic_api_key,
                    max_tokens=self.settings.agent.max_tokens,
                    temperature=self.settings.agent.temperature,
                )
            else:
                raise ValueError(f"Unsupported model: {model}")

        return self.agents[model]

    async def chat(
        self,
        session_id: str,
        channel: str,
        sender_id: str,
        message: str,
        sender_name: str | None = None,
        model: str | None = None,
    ) -> str:
        """Process a chat message."""
        context = self.get_or_create_session(session_id, channel, sender_id, sender_name)
        agent = self.get_agent(model)
        return await agent.chat(context, message)

    async def stream_chat(
        self,
        session_id: str,
        channel: str,
        sender_id: str,
        message: str,
        sender_name: str | None = None,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream a chat response."""
        context = self.get_or_create_session(session_id, channel, sender_id, sender_name)
        agent = self.get_agent(model)
        async for chunk in agent.stream_chat(context, message):
            yield chunk
