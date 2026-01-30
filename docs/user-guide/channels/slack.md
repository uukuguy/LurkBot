# Slack Channel

Connect LurkBot to Slack using the Bolt SDK with Socket Mode.

## Prerequisites

- A Slack workspace where you have admin permissions
- LurkBot installed and configured

## Step 1: Create a Slack App

1. Go to [Slack API](https://api.slack.com/apps)
2. Click "Create New App"
3. Choose "From scratch"
4. Enter app name (e.g., "LurkBot")
5. Select your workspace
6. Click "Create App"

## Step 2: Configure Bot Permissions

1. Go to "OAuth & Permissions"
2. Under "Scopes" → "Bot Token Scopes", add:
   - `app_mentions:read` - Read mentions
   - `chat:write` - Send messages
   - `channels:history` - Read channel messages
   - `groups:history` - Read private channel messages
   - `im:history` - Read DM messages
   - `im:write` - Send DMs

## Step 3: Enable Socket Mode

1. Go to "Socket Mode"
2. Enable Socket Mode
3. Create an App-Level Token:
   - Name: "socket-token"
   - Scope: `connections:write`
4. Copy the token (starts with `xapp-`)

## Step 4: Enable Events

1. Go to "Event Subscriptions"
2. Enable Events
3. Subscribe to bot events:
   - `app_mention` - When bot is mentioned
   - `message.channels` - Channel messages
   - `message.groups` - Private channel messages
   - `message.im` - Direct messages

## Step 5: Install App to Workspace

1. Go to "Install App"
2. Click "Install to Workspace"
3. Authorize the app
4. Copy the "Bot User OAuth Token" (starts with `xoxb-`)

## Step 6: Configure LurkBot

Add tokens to your configuration:

=== "Environment Variable"

    ```bash
    export LURKBOT_SLACK__BOT_TOKEN=xoxb-...
    export LURKBOT_SLACK__APP_TOKEN=xapp-...
    export LURKBOT_SLACK__ENABLED=true
    ```

=== "Configuration File"

    Add to `~/.lurkbot/.env`:
    ```bash
    LURKBOT_SLACK__BOT_TOKEN=xoxb-...
    LURKBOT_SLACK__APP_TOKEN=xapp-...
    LURKBOT_SLACK__ENABLED=true
    ```

## Step 7: Configure Allowlist

Get your Slack user ID:

1. Click your profile in Slack
2. Click "Profile"
3. Click "..." → "Copy member ID"

```bash
LURKBOT_SLACK__ALLOWLIST=U0123456789
```

## Step 8: Start the Gateway

```bash
lurkbot gateway start
```

You should see:

```
INFO     | Gateway starting on ws://127.0.0.1:18789
INFO     | Slack channel connected: LurkBot
INFO     | Gateway ready
```

## Configuration Options

### Basic Options

| Option | Description | Default |
|--------|-------------|---------|
| `BOT_TOKEN` | Bot OAuth token (xoxb-) | Required |
| `APP_TOKEN` | App-level token (xapp-) | Required |
| `ENABLED` | Enable/disable channel | `false` |
| `ALLOWLIST` | Allowed user IDs | Empty |

### Channel Options

| Option | Description | Default |
|--------|-------------|---------|
| `ALLOWED_CHANNELS` | Allowed channel IDs | Empty (all) |
| `MENTION_GATING` | Require @mention | `true` |
| `DM_ENABLED` | Allow direct messages | `true` |

### Advanced Options

| Option | Description | Default |
|--------|-------------|---------|
| `THREAD_REPLIES` | Reply in threads | `true` |
| `UNFURL_LINKS` | Unfurl links | `false` |
| `UNFURL_MEDIA` | Unfurl media | `true` |

## Mention Gating

By default, Slack requires @mention to respond:

```bash
LURKBOT_SLACK__MENTION_GATING=true
```

Usage:

```
User: @LurkBot what's the status?
Bot: Let me check...

User: what's the status?
(no response - not mentioned)
```

## Thread Replies

LurkBot replies in threads by default:

```bash
LURKBOT_SLACK__THREAD_REPLIES=true
```

This keeps conversations organized and reduces channel noise.

## Channel Restrictions

### Allow Specific Channels

```bash
# Get channel ID from channel details
LURKBOT_SLACK__ALLOWED_CHANNELS=C0123456789,C9876543210
```

## Slash Commands (Optional)

Add custom slash commands:

1. Go to "Slash Commands"
2. Create new command (e.g., `/lurkbot`)
3. Set Request URL (if using HTTP mode)

## Home Tab (Optional)

Create an app home:

1. Go to "App Home"
2. Enable "Home Tab"
3. Configure welcome message

## Troubleshooting

### "invalid_auth"

1. Regenerate tokens
2. Reinstall app to workspace

### "missing_scope"

Add required scopes in "OAuth & Permissions" and reinstall.

### "not_in_channel"

Invite the bot to the channel:

```
/invite @LurkBot
```

### Bot doesn't respond

1. Check Socket Mode is enabled
2. Verify event subscriptions
3. Check allowlist includes your user ID

### Slow responses

Socket Mode may have slight latency. For production, consider HTTP mode with webhooks.

## Example Configuration

Complete `.env` example:

```bash
# Slack Channel
LURKBOT_SLACK__ENABLED=true
LURKBOT_SLACK__BOT_TOKEN=xoxb-123456789-...
LURKBOT_SLACK__APP_TOKEN=xapp-1-...

# Security
LURKBOT_SLACK__ALLOWLIST=U0123456789,U9876543210
LURKBOT_SLACK__ALLOWED_CHANNELS=C0123456789

# Behavior
LURKBOT_SLACK__MENTION_GATING=true
LURKBOT_SLACK__DM_ENABLED=true
LURKBOT_SLACK__THREAD_REPLIES=true
```

---

## See Also

- [Channels Overview](index.md) - All supported channels
- [Telegram Setup](telegram.md) - Telegram configuration
- [Discord Setup](discord.md) - Discord configuration
