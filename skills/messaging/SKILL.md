---
name: messaging
description: Send messages to multiple channels including Discord, Slack, Telegram, CLI, and Web.
metadata: {"moltbot":{"emoji":"💬"}}
---

# Messaging

Send messages, reactions, polls, and media to various communication channels.

## Available Tool

- `message` - Multi-channel messaging with support for various actions

## Supported Channels

- Discord
- Slack
- Telegram
- CLI (command-line interface)
- Web (web interface)

## Supported Actions

- `send` - Send a message to a channel
- `delete` - Delete a message
- `react` - Add a reaction to a message
- `pin` / `unpin` - Pin or unpin messages
- `poll` - Create a poll
- `thread` - Create or reply to a thread
- `event` - Create calendar events
- `media` - Send media content

## Quick Examples

### Send a simple message

```bash
{
  "action": "send",
  "channel": "discord",
  "channelId": "channel-123",
  "content": "Hello from LurkBot!"
}
```

### Create a poll

```bash
{
  "action": "poll",
  "channel": "slack",
  "channelId": "general",
  "question": "Which framework should we use?",
  "options": ["FastAPI", "Flask", "Django"]
}
```

### Send media

```bash
{
  "action": "media",
  "channel": "telegram",
  "channelId": "chat-456",
  "mediaUrl": "https://example.com/image.png",
  "caption": "Check out this chart"
}
```

### React to a message

```bash
{
  "action": "react",
  "channel": "discord",
  "messageId": "msg-789",
  "emoji": "👍"
}
```

## Use Cases

**Notifications**: Send alerts or status updates to team channels.

**User responses**: Reply to users on their preferred platform.

**Polls and feedback**: Collect team input via polls.

**Media sharing**: Share images, charts, or files.

**Thread management**: Organize conversations in threads.

## Configuration

Channel configurations are loaded from config files. Each channel requires specific credentials and settings:

- **Discord**: Bot token, guild ID
- **Slack**: OAuth token, workspace ID
- **Telegram**: Bot token, chat ID

## Tips

- Channels must be configured before use
- Default channel is CLI for local development
- Media URLs must be publicly accessible
- Reactions use standard emoji codes
- Thread support varies by channel type

## Related Skills

- `sessions` - Send messages between agent sessions
- `automation/gateway` - Use Gateway for cross-channel messaging
