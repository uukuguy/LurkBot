# Custom Channels

Learn how to create custom channel adapters to connect LurkBot to new messaging platforms.

> **Note**: The channel system is currently under development. This documentation describes the planned architecture based on the MoltBot design patterns.

## Overview

Channel adapters connect external messaging platforms to LurkBot. Each adapter:

- Receives messages from the platform
- Converts them to internal format
- Routes responses back to users

## Planned Channel Interface

All channels will implement the `ChannelAdapter` base class:

```python
# src/lurkbot/channels/base.py (planned)
from abc import ABC, abstractmethod
from typing import Callable
from dataclasses import dataclass
from pydantic import BaseModel

@dataclass
class ChannelMessage:
    """Internal message format."""
    chat_id: str
    user_id: str
    content: str
    platform: str
    metadata: dict | None = None

class ChannelAdapter(ABC):
    """Base class for channel adapters."""

    name: str  # Channel identifier

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the messaging platform."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the platform."""
        pass

    @abstractmethod
    async def send_message(
        self,
        chat_id: str,
        content: str,
        **kwargs
    ) -> None:
        """Send a message to a chat."""
        pass

    @abstractmethod
    async def on_message(
        self,
        callback: Callable[[ChannelMessage], None]
    ) -> None:
        """Register a message handler."""
        pass

    async def send_typing(self, chat_id: str) -> None:
        """Send typing indicator (optional)."""
        pass

    async def send_media(
        self,
        chat_id: str,
        media_type: str,
        media_path: str,
        **kwargs
    ) -> None:
        """Send media (optional)."""
        pass
```

## Creating a Custom Channel

### Step 1: Create the Adapter

Create `src/lurkbot/channels/myplatform.py`:

```python
from .base import ChannelAdapter, ChannelMessage
from typing import Callable
from loguru import logger

class MyPlatformChannel(ChannelAdapter):
    """MyPlatform channel adapter."""

    name = "myplatform"

    def __init__(self, config: dict):
        self.config = config
        self.token = config.get("bot_token")
        self.allowlist = config.get("allowlist", [])
        self._callback: Callable | None = None
        self._client = None

    async def connect(self) -> None:
        """Connect to MyPlatform."""
        # Initialize your platform's client
        self._client = MyPlatformClient(self.token)
        await self._client.connect()

        # Set up message handler
        self._client.on_message(self._handle_message)

        logger.info(f"MyPlatform channel connected")

    async def disconnect(self) -> None:
        """Disconnect from MyPlatform."""
        if self._client:
            await self._client.disconnect()

    async def _handle_message(self, raw_message) -> None:
        """Handle incoming messages."""
        # Check allowlist
        if self.allowlist and raw_message.user_id not in self.allowlist:
            return

        # Convert to internal format
        message = ChannelMessage(
            chat_id=raw_message.chat_id,
            user_id=raw_message.user_id,
            content=raw_message.text,
            platform=self.name,
            metadata={
                "raw": raw_message,
                "timestamp": raw_message.timestamp
            }
        )

        # Call registered callback
        if self._callback:
            await self._callback(message)

    async def send_message(
        self,
        chat_id: str,
        content: str,
        **kwargs
    ) -> None:
        """Send a message."""
        await self._client.send(chat_id, content)

    async def on_message(
        self,
        callback: Callable[[ChannelMessage], None]
    ) -> None:
        """Register message handler."""
        self._callback = callback

    async def send_typing(self, chat_id: str) -> None:
        """Send typing indicator."""
        await self._client.send_typing(chat_id)
```

### Step 2: Register the Channel

Add to `src/lurkbot/channels/__init__.py`:

```python
from .base import ChannelAdapter, ChannelMessage
from .myplatform import MyPlatformChannel

# Channel registry
CHANNELS: dict[str, type[ChannelAdapter]] = {
    "myplatform": MyPlatformChannel,
}

def get_channel(name: str, config: dict) -> ChannelAdapter:
    """Get a channel adapter by name."""
    if name not in CHANNELS:
        raise ValueError(f"Unknown channel: {name}")
    return CHANNELS[name](config)
```

### Step 3: Add Configuration

Add configuration options using Pydantic settings:

```python
# src/lurkbot/config/channels.py
from pydantic import BaseModel, Field

class MyPlatformConfig(BaseModel):
    """MyPlatform channel configuration."""
    enabled: bool = False
    bot_token: str = Field(..., description="Bot API token")
    allowlist: list[str] = Field(default_factory=list)
    mention_gating: bool = False
```

### Step 4: Add Environment Variables

Document the environment variables:

```bash
# MyPlatform Channel
LURKBOT_MYPLATFORM__ENABLED=true
LURKBOT_MYPLATFORM__BOT_TOKEN=your-token
LURKBOT_MYPLATFORM__ALLOWLIST=user1,user2
LURKBOT_MYPLATFORM__MENTION_GATING=false
```

## Planned Channel Support

Based on `pyproject.toml:34-37`, LurkBot includes dependencies for:

| Platform | Package | Status |
|----------|---------|--------|
| Telegram | `python-telegram-bot>=21.0` | Planned |
| Discord | `discord.py>=2.4.0` | Planned |
| Slack | `slack-sdk>=3.33.0` | Planned |

## Advanced Features

### Media Support

Add media handling:

```python
async def send_media(
    self,
    chat_id: str,
    media_type: str,
    media_path: str,
    caption: str | None = None,
    **kwargs
) -> None:
    """Send media to a chat."""
    if media_type == "image":
        await self._client.send_image(chat_id, media_path, caption)
    elif media_type == "file":
        await self._client.send_file(chat_id, media_path, caption)
    elif media_type == "voice":
        await self._client.send_voice(chat_id, media_path)
    else:
        raise ValueError(f"Unsupported media type: {media_type}")
```

### Reactions

Add reaction support:

```python
async def add_reaction(
    self,
    chat_id: str,
    message_id: str,
    emoji: str
) -> None:
    """Add a reaction to a message."""
    await self._client.add_reaction(chat_id, message_id, emoji)
```

### Message Editing

Add message editing:

```python
async def edit_message(
    self,
    chat_id: str,
    message_id: str,
    content: str
) -> None:
    """Edit an existing message."""
    await self._client.edit(chat_id, message_id, content)
```

### Webhooks

For platforms that support webhooks:

```python
class MyPlatformChannel(ChannelAdapter):
    """MyPlatform channel with webhook support."""

    async def setup_webhook(self, url: str, secret: str) -> None:
        """Set up webhook for receiving messages."""
        await self._client.set_webhook(url, secret)

    async def handle_webhook(self, request: dict) -> None:
        """Handle incoming webhook request."""
        # Verify signature
        if not self._verify_signature(request):
            raise ValueError("Invalid webhook signature")

        # Process message
        message = self._parse_webhook(request)
        if self._callback:
            await self._callback(message)
```

## Testing

### Unit Tests

```python
# tests/channels/test_myplatform.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from lurkbot.channels.myplatform import MyPlatformChannel

@pytest.fixture
def channel():
    config = {
        "bot_token": "test-token",
        "allowlist": ["user1"]
    }
    return MyPlatformChannel(config)

async def test_connect(channel):
    channel._client = AsyncMock()
    await channel.connect()
    channel._client.connect.assert_called_once()

async def test_send_message(channel):
    channel._client = AsyncMock()
    await channel.send_message("chat1", "Hello")
    channel._client.send.assert_called_once_with("chat1", "Hello")

async def test_allowlist_filtering(channel):
    callback = AsyncMock()
    await channel.on_message(callback)

    # Allowed user
    await channel._handle_message(MagicMock(
        user_id="user1",
        chat_id="chat1",
        text="Hello",
        timestamp=123456
    ))
    assert callback.called

    # Blocked user
    callback.reset_mock()
    await channel._handle_message(MagicMock(
        user_id="user2",
        chat_id="chat1",
        text="Hello",
        timestamp=123456
    ))
    assert not callback.called
```

### Integration Tests

```python
# tests/integration/test_myplatform_integration.py
import pytest
import os
from lurkbot.channels.myplatform import MyPlatformChannel

@pytest.mark.integration
async def test_real_connection():
    """Test real connection (requires credentials)."""
    token = os.environ.get("MYPLATFORM_TOKEN")
    if not token:
        pytest.skip("MYPLATFORM_TOKEN not set")

    config = {"bot_token": token}
    channel = MyPlatformChannel(config)

    await channel.connect()
    assert channel._client.is_connected
    await channel.disconnect()
```

## Best Practices

1. **Handle errors gracefully**: Catch and log platform-specific errors
2. **Implement rate limiting**: Respect platform rate limits
3. **Support reconnection**: Handle disconnections gracefully
4. **Validate input**: Check message content before processing
5. **Log appropriately**: Use loguru for structured logging
6. **Use type hints**: Python 3.12+ syntax required
7. **Follow async patterns**: Use `async/await` consistently

---

## See Also

- [Channels Overview](../../user-guide/channels/index.md) - User documentation
- [Custom Tools](custom-tools.md) - Create custom tools
- [Architecture](../architecture.md) - System design
