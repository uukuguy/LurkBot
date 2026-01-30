# More Channels

This page covers additional messaging platforms supported by LurkBot.

## WhatsApp

Connect to WhatsApp using the Baileys library (unofficial API).

### Setup

1. **Configure LurkBot**:

```bash
LURKBOT_WHATSAPP__ENABLED=true
```

2. **Start Gateway**:

```bash
lurkbot gateway start
```

3. **Scan QR Code**:

A QR code will appear in the terminal. Scan it with WhatsApp:

- Open WhatsApp on your phone
- Go to Settings → Linked Devices
- Tap "Link a Device"
- Scan the QR code

### Configuration

```bash
# Basic
LURKBOT_WHATSAPP__ENABLED=true

# Security
LURKBOT_WHATSAPP__ALLOWLIST=1234567890@s.whatsapp.net

# Groups
LURKBOT_WHATSAPP__ALLOWED_GROUPS=123456789-1234567890@g.us
LURKBOT_WHATSAPP__MENTION_GATING=true
```

### Notes

- Session persists in `~/.lurkbot/whatsapp/`
- Re-scan QR if session expires
- Unofficial API - use at your own risk

---

## Signal

Connect to Signal using signal-cli.

### Prerequisites

1. Install signal-cli:

```bash
# macOS
brew install signal-cli

# Linux
# Download from https://github.com/AsamK/signal-cli/releases
```

2. Register or link a phone number:

```bash
# Register new number
signal-cli -u +1234567890 register

# Or link to existing Signal account
signal-cli link -n "LurkBot"
```

### Configuration

```bash
LURKBOT_SIGNAL__ENABLED=true
LURKBOT_SIGNAL__PHONE_NUMBER=+1234567890

# Security
LURKBOT_SIGNAL__ALLOWLIST=+1987654321,+1555555555
```

### Notes

- Requires signal-cli to be installed and configured
- Phone number must be registered with Signal
- End-to-end encrypted

---

## iMessage

Connect to iMessage on macOS.

### Prerequisites

- macOS only
- Messages app configured
- Full Disk Access for terminal

### Setup

1. Grant Full Disk Access:
   - System Preferences → Security & Privacy → Privacy
   - Add Terminal (or your terminal app)

2. Configure LurkBot:

```bash
LURKBOT_IMESSAGE__ENABLED=true
```

### Configuration

```bash
LURKBOT_IMESSAGE__ENABLED=true

# Security
LURKBOT_IMESSAGE__ALLOWLIST=+1234567890,email@example.com
```

### Notes

- macOS only
- Uses AppleScript/imsg library
- Requires Full Disk Access

---

## Matrix

Connect to Matrix (decentralized messaging).

### Prerequisites

- A Matrix account (e.g., on matrix.org)
- Access token for your account

### Setup

1. Get access token:

```bash
curl -X POST "https://matrix.org/_matrix/client/r0/login" \
  -H "Content-Type: application/json" \
  -d '{"type":"m.login.password","user":"@username:matrix.org","password":"your-password"}'
```

2. Configure LurkBot:

```bash
LURKBOT_MATRIX__ENABLED=true
LURKBOT_MATRIX__HOMESERVER=https://matrix.org
LURKBOT_MATRIX__USER_ID=@lurkbot:matrix.org
LURKBOT_MATRIX__ACCESS_TOKEN=syt_...
```

### Configuration

```bash
LURKBOT_MATRIX__ENABLED=true
LURKBOT_MATRIX__HOMESERVER=https://matrix.org
LURKBOT_MATRIX__USER_ID=@lurkbot:matrix.org
LURKBOT_MATRIX__ACCESS_TOKEN=syt_...

# Security
LURKBOT_MATRIX__ALLOWLIST=@user:matrix.org
LURKBOT_MATRIX__ALLOWED_ROOMS=!roomid:matrix.org
```

### Notes

- Decentralized and federated
- End-to-end encryption supported
- Works with any Matrix homeserver

---

## MS Teams

Connect to Microsoft Teams using Bot Framework.

### Prerequisites

- Azure account
- Microsoft 365 organization

### Setup

1. Create Azure Bot:
   - Go to Azure Portal
   - Create "Azure Bot" resource
   - Note the App ID and Password

2. Configure Teams channel:
   - In Azure Bot, go to Channels
   - Add Microsoft Teams channel

3. Configure LurkBot:

```bash
LURKBOT_TEAMS__ENABLED=true
LURKBOT_TEAMS__APP_ID=your-app-id
LURKBOT_TEAMS__APP_PASSWORD=your-app-password
```

### Configuration

```bash
LURKBOT_TEAMS__ENABLED=true
LURKBOT_TEAMS__APP_ID=...
LURKBOT_TEAMS__APP_PASSWORD=...

# Security
LURKBOT_TEAMS__TENANT_ID=your-tenant-id
LURKBOT_TEAMS__ALLOWLIST=user@company.com
```

### Notes

- Requires Azure subscription
- Enterprise-focused
- Supports adaptive cards

---

## Google Chat

Connect to Google Chat using the Chat API.

### Prerequisites

- Google Workspace account
- Google Cloud project

### Setup

1. Enable Chat API in Google Cloud Console
2. Create service account
3. Configure Chat bot in Admin Console

### Configuration

```bash
LURKBOT_GOOGLE_CHAT__ENABLED=true
LURKBOT_GOOGLE_CHAT__SERVICE_ACCOUNT_FILE=/path/to/service-account.json
LURKBOT_GOOGLE_CHAT__PROJECT_ID=your-project-id
```

### Notes

- Requires Google Workspace
- Uses service account authentication
- Supports spaces and DMs

---

## Adding Custom Channels

LurkBot's channel system is extensible. See [Custom Channels](../../developer/extending/custom-channels.md) for how to create your own channel adapter.

---

## See Also

- [Channels Overview](index.md) - All supported channels
- [Telegram Setup](telegram.md) - Most popular channel
- [Custom Channels](../../developer/extending/custom-channels.md) - Build your own
