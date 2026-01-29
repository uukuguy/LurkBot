"""Heartbeat system for periodic agent wake-up.

Ported from moltbot/src/infra/heartbeat-runner.ts

The heartbeat system provides:
1. Periodic agent wake-up based on configurable intervals
2. Active hours window support
3. HEARTBEAT_OK token for silent acknowledgment
4. Duplicate message suppression within 24 hours
5. Event emission for monitoring

MoltBot heartbeat flow:
1. Check if enabled and within active hours
2. Check if requests are in flight
3. Read HEARTBEAT.md file
4. Build heartbeat prompt
5. Get LLM reply
6. Check for HEARTBEAT_OK token
7. Suppress duplicates
8. Deliver message to target
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Any, Callable, Literal

# =============================================================================
# Constants
# =============================================================================

HEARTBEAT_OK_TOKEN = "HEARTBEAT_OK"
DEFAULT_HEARTBEAT_EVERY = "5m"
DEFAULT_HEARTBEAT_ACK_MAX_CHARS = 100
DEFAULT_HEARTBEAT_TARGET: Literal["main", "last"] = "last"


# =============================================================================
# Type Definitions
# =============================================================================


@dataclass
class ActiveHours:
    """Active hours window configuration.

    Matches MoltBot activeHours config.
    """

    start: str  # "HH:MM" format
    end: str  # "HH:MM" or "24:00" format
    timezone: str = "local"  # "user" | "local" | specific tz


@dataclass
class HeartbeatConfig:
    """Heartbeat configuration.

    Matches MoltBot HeartbeatConfig from src/infra/heartbeat-runner.ts.
    """

    enabled: bool = True
    every: str = DEFAULT_HEARTBEAT_EVERY  # "5m", "30s", etc.
    prompt: str | None = None  # Custom prompt override
    target: Literal["main", "last"] = DEFAULT_HEARTBEAT_TARGET
    model: str | None = None  # Model override
    ack_max_chars: int = DEFAULT_HEARTBEAT_ACK_MAX_CHARS
    session: str | None = None  # Session override
    active_hours: ActiveHours | None = None
    include_reasoning: bool = False


@dataclass
class HeartbeatEventPayload:
    """Heartbeat event payload.

    Matches MoltBot HeartbeatEventPayload.

    Status types:
    - sent: Message was delivered to user
    - ok-empty: HEARTBEAT.md was empty
    - ok-token: LLM responded with HEARTBEAT_OK
    - skipped: Heartbeat was skipped (with reason)
    - failed: Heartbeat execution failed
    """

    ts: int  # Timestamp in milliseconds
    status: Literal["sent", "ok-empty", "ok-token", "skipped", "failed"]
    to: str | None = None  # Delivery target
    preview: str | None = None  # Message preview
    duration_ms: int | None = None
    has_media: bool = False
    reason: str | None = None  # Skip/failure reason
    channel: str | None = None
    silent: bool = False
    indicator_type: Literal["ok", "alert", "error"] | None = None


# Type alias for event listeners
HeartbeatEventListener = Callable[[HeartbeatEventPayload], None]


# =============================================================================
# HeartbeatRunner
# =============================================================================


class HeartbeatRunner:
    """Heartbeat runner for periodic agent wake-up.

    Matches MoltBot HeartbeatRunner from src/infra/heartbeat-runner.ts.

    The runner executes heartbeat cycles at configured intervals,
    reading HEARTBEAT.md and prompting the agent for action.
    """

    def __init__(
        self,
        workspace_dir: str | Path,
        agent_id: str,
        config: HeartbeatConfig | None = None,
        on_get_reply: Callable[[str, str | None], Any] | None = None,
        on_deliver_message: Callable[[str, str | None], Any] | None = None,
        on_check_requests_in_flight: Callable[[], bool] | None = None,
    ):
        """Initialize heartbeat runner.

        Args:
            workspace_dir: Agent workspace directory
            agent_id: Agent identifier
            config: Heartbeat configuration
            on_get_reply: Callback to get LLM reply (prompt, model) -> reply
            on_deliver_message: Callback to deliver message (text, target) -> None
            on_check_requests_in_flight: Callback to check if requests are in flight
        """
        self.workspace = Path(workspace_dir)
        self.agent_id = agent_id
        self.config = config or HeartbeatConfig()

        # Callbacks
        self._on_get_reply = on_get_reply
        self._on_deliver_message = on_deliver_message
        self._on_check_requests_in_flight = on_check_requests_in_flight

        # State
        self._running = False
        self._task: asyncio.Task | None = None
        self._last_event: HeartbeatEventPayload | None = None
        self._event_listeners: list[HeartbeatEventListener] = []

        # Duplicate suppression: store message hashes from last 24h
        self._recent_message_hashes: list[tuple[str, int]] = []  # (hash, timestamp)
        self._max_recent_messages = 100
        self._duplicate_window_ms = 24 * 60 * 60 * 1000  # 24 hours

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def on_event(self, listener: HeartbeatEventListener) -> Callable[[], None]:
        """Register an event listener.

        Args:
            listener: Callback function receiving HeartbeatEventPayload

        Returns:
            Unsubscribe function
        """
        self._event_listeners.append(listener)

        def unsubscribe() -> None:
            if listener in self._event_listeners:
                self._event_listeners.remove(listener)

        return unsubscribe

    def get_last_event(self) -> HeartbeatEventPayload | None:
        """Get the last heartbeat event."""
        return self._last_event

    async def start(self) -> None:
        """Start the heartbeat loop."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    def stop(self) -> None:
        """Stop the heartbeat loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    async def run_once(self) -> HeartbeatEventPayload:
        """Execute a single heartbeat check.

        Matches MoltBot runHeartbeatOnce() flow:
        1. Check if enabled
        2. Check if within active hours
        3. Check if requests are in flight
        4. Read HEARTBEAT.md
        5. Build prompt
        6. Get LLM reply
        7. Check for HEARTBEAT_OK
        8. Suppress duplicates
        9. Deliver message

        Returns:
            HeartbeatEventPayload with result status
        """
        start_time = datetime.now()

        # 1. Check if enabled
        if not self.config.enabled:
            return self._create_event("skipped", reason="disabled")

        # 2. Check if within active hours
        if not self._is_within_active_hours():
            return self._create_event("skipped", reason="quiet-hours")

        # 3. Check if requests are in flight
        if await self._has_requests_in_flight():
            return self._create_event("skipped", reason="requests-in-flight")

        # 4. Read HEARTBEAT.md
        heartbeat_file = self.workspace / "HEARTBEAT.md"
        if not heartbeat_file.exists():
            return self._create_event("skipped", reason="no-heartbeat-file")

        try:
            content = heartbeat_file.read_text().strip()
        except Exception as e:
            return self._create_event("failed", reason=f"read-error: {e}")

        if self._is_effectively_empty(content):
            return self._create_event("ok-empty", reason="empty-heartbeat-file")

        # 5. Build heartbeat prompt
        prompt = self.config.prompt or self._build_default_prompt(content)

        # 6. Get LLM reply
        try:
            reply = await self._get_reply(prompt)
        except Exception as e:
            return self._create_event("failed", reason=f"llm-error: {e}")

        # 7. Check for HEARTBEAT_OK token
        stripped = self._strip_heartbeat_token(reply)
        if stripped["is_heartbeat_ok"]:
            return self._create_event(
                "ok-token",
                duration_ms=self._duration_ms(start_time),
            )

        # 8. Suppress duplicates
        message_text = stripped["text"]
        if self._is_duplicate_within_24h(message_text):
            return self._create_event("skipped", reason="duplicate")

        # 9. Deliver message
        try:
            target = self._resolve_delivery_target()
            await self._deliver_message(message_text, target)
        except Exception as e:
            return self._create_event("failed", reason=f"deliver-error: {e}")

        # Mark as recent message
        self._add_recent_message(message_text)

        return self._create_event(
            "sent",
            preview=message_text[: self.config.ack_max_chars],
            duration_ms=self._duration_ms(start_time),
            to=target,
        )

    # -------------------------------------------------------------------------
    # Internal Methods
    # -------------------------------------------------------------------------

    async def _run_loop(self) -> None:
        """Main heartbeat loop."""
        interval_seconds = self._parse_interval(self.config.every)

        while self._running:
            try:
                result = await self.run_once()
                self._emit_event(result)
            except Exception:
                # Log but don't crash the loop
                pass

            await asyncio.sleep(interval_seconds)

    def _is_within_active_hours(self) -> bool:
        """Check if current time is within active hours window."""
        if not self.config.active_hours:
            return True

        now = datetime.now().time()

        # Parse start time
        start = dt_time.fromisoformat(self.config.active_hours.start)

        # Parse end time (handle 24:00)
        end_str = self.config.active_hours.end
        if end_str == "24:00":
            end = dt_time(23, 59, 59, 999999)
        else:
            end = dt_time.fromisoformat(end_str)

        # Check window (handle overnight windows)
        if start <= end:
            return start <= now <= end
        else:
            # Overnight window (e.g., 22:00 - 06:00)
            return now >= start or now <= end

    def _strip_heartbeat_token(self, text: str) -> dict[str, Any]:
        """Extract HEARTBEAT_OK token from response.

        Args:
            text: LLM response text

        Returns:
            Dict with 'is_heartbeat_ok' bool and 'text' with token removed
        """
        stripped = text.strip()

        if HEARTBEAT_OK_TOKEN in stripped:
            # Remove the token and any surrounding whitespace
            cleaned = re.sub(
                rf"\s*{re.escape(HEARTBEAT_OK_TOKEN)}\s*",
                " ",
                stripped,
            ).strip()
            return {"is_heartbeat_ok": True, "text": cleaned}

        return {"is_heartbeat_ok": False, "text": stripped}

    def _is_duplicate_within_24h(self, text: str) -> bool:
        """Check if message is a duplicate within 24 hours."""
        now_ms = int(datetime.now().timestamp() * 1000)
        text_hash = self._hash_message(text)

        # Clean old entries
        self._recent_message_hashes = [
            (h, ts)
            for h, ts in self._recent_message_hashes
            if now_ms - ts < self._duplicate_window_ms
        ]

        # Check for duplicate
        for h, _ in self._recent_message_hashes:
            if h == text_hash:
                return True

        return False

    def _add_recent_message(self, text: str) -> None:
        """Add message to recent messages list."""
        now_ms = int(datetime.now().timestamp() * 1000)
        text_hash = self._hash_message(text)

        self._recent_message_hashes.append((text_hash, now_ms))

        # Trim to max size
        if len(self._recent_message_hashes) > self._max_recent_messages:
            self._recent_message_hashes = self._recent_message_hashes[
                -self._max_recent_messages :
            ]

    def _hash_message(self, text: str) -> str:
        """Create hash for message deduplication."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _is_effectively_empty(self, content: str) -> bool:
        """Check if HEARTBEAT.md content is effectively empty.

        Empty means no non-comment, non-whitespace lines.
        """
        lines = content.split("\n")
        for line in lines:
            stripped = line.strip()
            # Skip empty lines and comment lines
            if stripped and not stripped.startswith("#"):
                return False
        return True

    def _build_default_prompt(self, content: str) -> str:
        """Build default heartbeat prompt."""
        return f"""## Heartbeat Check

It's time for your periodic check. Please review and handle these tasks:

{content}

After completing checks:
1. If anything needs user attention, notify them
2. If no action needed, respond with {HEARTBEAT_OK_TOKEN}

Keep responses brief and actionable.
"""

    def _resolve_delivery_target(self) -> str | None:
        """Resolve message delivery target.

        Returns session key or channel identifier.
        """
        if self.config.session:
            return self.config.session

        if self.config.target == "main":
            return f"agent:{self.agent_id}:main"

        # "last" target - would need session manager integration
        return f"agent:{self.agent_id}:main"

    def _create_event(
        self,
        status: Literal["sent", "ok-empty", "ok-token", "skipped", "failed"],
        **kwargs: Any,
    ) -> HeartbeatEventPayload:
        """Create a heartbeat event payload."""
        # Determine indicator type based on status
        indicator_type: Literal["ok", "alert", "error"] | None = None
        if status in ("sent", "ok-empty", "ok-token"):
            indicator_type = "ok"
        elif status == "skipped":
            indicator_type = "alert"
        elif status == "failed":
            indicator_type = "error"

        return HeartbeatEventPayload(
            ts=int(datetime.now().timestamp() * 1000),
            status=status,
            indicator_type=indicator_type,
            **kwargs,
        )

    def _emit_event(self, event: HeartbeatEventPayload) -> None:
        """Emit heartbeat event to listeners."""
        self._last_event = event
        for listener in self._event_listeners:
            try:
                listener(event)
            except Exception:
                pass

    def _duration_ms(self, start: datetime) -> int:
        """Calculate duration in milliseconds."""
        return int((datetime.now() - start).total_seconds() * 1000)

    def _parse_interval(self, interval: str) -> float:
        """Parse interval string to seconds.

        Supports formats: "30s", "5m", "1h"
        """
        if interval.endswith("s"):
            return float(interval[:-1])
        elif interval.endswith("m"):
            return float(interval[:-1]) * 60
        elif interval.endswith("h"):
            return float(interval[:-1]) * 3600
        else:
            # Default to 5 minutes
            return 300

    async def _has_requests_in_flight(self) -> bool:
        """Check if there are requests currently in flight."""
        if self._on_check_requests_in_flight:
            result = self._on_check_requests_in_flight()
            if asyncio.iscoroutine(result):
                return await result
            return result
        return False

    async def _get_reply(self, prompt: str) -> str:
        """Get LLM reply for heartbeat prompt."""
        if self._on_get_reply:
            result = self._on_get_reply(prompt, self.config.model)
            if asyncio.iscoroutine(result):
                return await result
            return result

        # Placeholder - actual implementation needs agent integration
        raise NotImplementedError("on_get_reply callback not configured")

    async def _deliver_message(self, text: str, target: str | None) -> None:
        """Deliver message to target."""
        if self._on_deliver_message:
            result = self._on_deliver_message(text, target)
            if asyncio.iscoroutine(result):
                await result
            return

        # Placeholder - actual implementation needs gateway integration
        raise NotImplementedError("on_deliver_message callback not configured")


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "HEARTBEAT_OK_TOKEN",
    "DEFAULT_HEARTBEAT_EVERY",
    "DEFAULT_HEARTBEAT_ACK_MAX_CHARS",
    "DEFAULT_HEARTBEAT_TARGET",
    "ActiveHours",
    "HeartbeatConfig",
    "HeartbeatEventPayload",
    "HeartbeatRunner",
    "HeartbeatEventListener",
]
