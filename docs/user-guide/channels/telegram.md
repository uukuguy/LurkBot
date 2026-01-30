# Telegram Channel

Connect LurkBot to Telegram using the Bot API.

## Prerequisites

- A Telegram account
- LurkBot installed and configured

## Step 1: Create a Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Enter a display name (e.g., "My LurkBot")
4. Enter a username (must end in `bot`, e.g., `my_lurkbot`)
5. Copy the bot token:
   ```
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

> [!IMPORTANT]
> Keep your bot token secret! Anyone with this token can control your bot.

## Step 2: Configure LurkBot

Add the bot token to your configuration:

=== "Environment Variable"

    ```bash
    export LURKBOT_TELEGRAM__BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
    export LURKBOT_TELEGRAM__ENABLED=true
    ```

=== "Configuration File"

    Add to `~/.lurkbot/.env`:
    ```bash
    LURKBOT_TELEGRAM__BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
    LURKBOT_TELEGRAM__ENABLED=true
    ```

## Step 3: Get Your User ID

To configure the allowlist, you need your Telegram user ID:

1. Send `/start` to [@userinfobot](https://t.me/userinfobot)
2. Copy your user ID (a number like `123456789`)

## Step 4: Configure Allowlist

Restrict who can use your bot:

```bash
# Single user
LURKBOT_TELEGRAM__ALLOWLIST=123456789

# Multiple users
LURKBOT_TELEGRAM__ALLOWLIST=123456789,987654321
```

## Step 5: Start the Gateway

```bash
lurkbot gateway start
```

You should see:

```
INFO     | Gateway starting on ws://127.0.0.1:18789
INFO     | Telegram channel connected: @my_lurkbot
INFO     | Gateway ready
```

## Step 6: Test Your Bot

1. Open Telegram
2. Find your bot by username
3. Send `/start` or any message
4. Your bot should respond!

## Configuration Options

### Basic Options

| Option | Description | Default |
|--------|-------------|---------|
| `BOT_TOKEN` | Bot API token | Required |
| `ENABLED` | Enable/disable channel | `false` |
| `ALLOWLIST` | Allowed user IDs | Empty (all blocked) |

### Group Chat Options

| Option | Description | Default |
|--------|-------------|---------|
| `ALLOWED_GROUPS` | Allowed group IDs | Empty |
| `MENTION_GATING` | Require @mention | `false` |
| `GROUP_SANDBOX` | Sandbox group sessions | `true` |

### Advanced Options

| Option | Description | Default |
|--------|-------------|---------|
| `PARSE_MODE` | Message format | `Markdown` |
| `TYPING_INDICATOR` | Show typing | `true` |
| `MAX_MESSAGE_LENGTH` | Max message length | `4096` |

## Group Chat Setup

### Allow Specific Groups

```bash
# Get group ID by adding @RawDataBot to the group
LURKBOT_TELEGRAM__ALLOWED_GROUPS=-1001234567890,-1009876543210
```

### Mention Gating

Require @mention to respond in groups:

```bash
LURKBOT_TELEGRAM__MENTION_GATING=true
```

With this enabled, the bot only responds when mentioned:

```
User: @my_lurkbot what's the weather?
Bot: Let me check the weather for you...

User: what's the weather?
(no response - not mentioned)
```

### Group Permissions

Add your bot to a group:

1. Open group settings
2. Add member → search for your bot
3. (Optional) Make bot admin for full features

## Bot Commands

Configure bot commands in BotFather:

```
/setcommands
```

Suggested commands:

```
start - Start the bot
help - Show help
clear - Clear conversation
model - Change AI model
```

## Inline Mode (Optional)

Enable inline queries:

1. Send `/setinline` to @BotFather
2. Set a placeholder text
3. Configure in LurkBot:

```bash
LURKBOT_TELEGRAM__INLINE_MODE=true
```

## Webhook Mode (Advanced)

For production, use webhooks instead of polling:

```bash
LURKBOT_TELEGRAM__WEBHOOK_URL=https://your-domain.com/telegram/webhook
LURKBOT_TELEGRAM__WEBHOOK_SECRET=your-secret-token
```

## Troubleshooting

### "Unauthorized" error

Your bot token is invalid:

1. Check for typos
2. Regenerate token in @BotFather

### "User not in allowlist"

Add your user ID to the allowlist:

```bash
LURKBOT_TELEGRAM__ALLOWLIST=YOUR_USER_ID
```

### Bot doesn't respond in groups

1. Check `ALLOWED_GROUPS` includes the group ID
2. If `MENTION_GATING=true`, mention the bot
3. Ensure bot has permission to read messages

### Messages truncated

Telegram has a 4096 character limit. Long responses are automatically split.

### Slow responses

1. Check your AI provider status
2. Try a faster model
3. The first message may be slow due to cold start

## Example Configuration

Complete `.env` example:

```bash
# Telegram Channel
LURKBOT_TELEGRAM__ENABLED=true
LURKBOT_TELEGRAM__BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# Security
LURKBOT_TELEGRAM__ALLOWLIST=123456789,987654321
LURKBOT_TELEGRAM__ALLOWED_GROUPS=-1001234567890

# Group Settings
LURKBOT_TELEGRAM__MENTION_GATING=true
LURKBOT_TELEGRAM__GROUP_SANDBOX=true

# Display
LURKBOT_TELEGRAM__PARSE_MODE=Markdown
LURKBOT_TELEGRAM__TYPING_INDICATOR=true
```

---

## See Also

- [Channels Overview](index.md) - All supported channels
- [Discord Setup](discord.md) - Discord configuration
- [Tool Policies](../tools/tool-policies.md) - Security settings
