# Auth Profiles

Auth profiles allow you to maintain multiple configurations for different environments (development, staging, production) or use cases.

## Overview

Profiles are stored in `~/.lurkbot/profiles/`:

```
~/.lurkbot/profiles/
├── default.json
├── development.json
├── production.json
└── testing.json
```

## Creating Profiles

### Using CLI

```bash
# Create a new profile
lurkbot config profile create production

# Edit profile
lurkbot config profile edit production
```

### Manually

Create `~/.lurkbot/profiles/production.json`:

```json
{
  "name": "production",
  "description": "Production environment",
  "agent": {
    "model": "claude-sonnet-4-20250514"
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "bot_token": "${PROD_TELEGRAM_BOT_TOKEN}"
    }
  },
  "sandbox": {
    "enabled": true
  }
}
```

## Using Profiles

### Command Line

```bash
# Use a specific profile
lurkbot --profile production gateway start

# Or set environment variable
export LURKBOT_PROFILE=production
lurkbot gateway start
```

### Environment Variable

```bash
# Set default profile
export LURKBOT_PROFILE=production
```

## Profile Structure

```json
{
  "name": "profile-name",
  "description": "Profile description",
  "extends": "default",

  "agent": { ... },
  "channels": { ... },
  "tools": { ... },
  "sandbox": { ... },

  "env": {
    "CUSTOM_VAR": "value"
  }
}
```

### Inheritance

Profiles can extend other profiles:

```json
{
  "name": "staging",
  "extends": "production",
  "description": "Staging environment",

  "agent": {
    "model": "claude-haiku-3-5-20241022"
  }
}
```

## Example Profiles

### Default Profile

`~/.lurkbot/profiles/default.json`:

```json
{
  "name": "default",
  "description": "Default development profile",

  "agent": {
    "model": "claude-sonnet-4-20250514",
    "temperature": 0.7
  },

  "gateway": {
    "host": "127.0.0.1",
    "port": 18789,
    "log_level": "info"
  },

  "tools": {
    "policy": {
      "default": "allow"
    }
  },

  "sandbox": {
    "enabled": false
  }
}
```

### Development Profile

`~/.lurkbot/profiles/development.json`:

```json
{
  "name": "development",
  "extends": "default",
  "description": "Local development",

  "gateway": {
    "log_level": "debug"
  },

  "agent": {
    "model": "claude-haiku-3-5-20241022"
  }
}
```

### Production Profile

`~/.lurkbot/profiles/production.json`:

```json
{
  "name": "production",
  "extends": "default",
  "description": "Production environment",

  "gateway": {
    "daemon": true,
    "log_level": "warning"
  },

  "agent": {
    "model": "claude-sonnet-4-20250514",
    "fallback_models": ["gpt-4o"]
  },

  "channels": {
    "telegram": {
      "enabled": true,
      "bot_token": "${PROD_TELEGRAM_TOKEN}",
      "allowlist": ["123456789"]
    }
  },

  "tools": {
    "policy": {
      "default": "deny",
      "ask": ["read", "glob"]
    },
    "audit": {
      "enabled": true
    }
  },

  "sandbox": {
    "enabled": true
  }
}
```

### Testing Profile

`~/.lurkbot/profiles/testing.json`:

```json
{
  "name": "testing",
  "extends": "default",
  "description": "Automated testing",

  "agent": {
    "model": "claude-haiku-3-5-20241022",
    "temperature": 0
  },

  "tools": {
    "disabled": ["bash", "write", "edit"]
  },

  "sandbox": {
    "enabled": true
  }
}
```

## Profile Management

### List Profiles

```bash
lurkbot config profile list
```

Output:

```
Available Profiles:
  * default      - Default development profile
    development  - Local development
    production   - Production environment
    testing      - Automated testing

Current: default
```

### Show Profile

```bash
lurkbot config profile show production
```

### Delete Profile

```bash
lurkbot config profile delete testing
```

### Copy Profile

```bash
lurkbot config profile copy production staging
```

## Environment-Specific Secrets

Use different environment variables per profile:

```json
{
  "name": "production",
  "env": {
    "LURKBOT_ANTHROPIC_API_KEY": "${PROD_ANTHROPIC_KEY}",
    "LURKBOT_TELEGRAM__BOT_TOKEN": "${PROD_TELEGRAM_TOKEN}"
  }
}
```

Then set the actual values:

```bash
export PROD_ANTHROPIC_KEY=sk-ant-api03-...
export PROD_TELEGRAM_TOKEN=123456789:ABC...
```

## Profile Switching

### In Scripts

```bash
#!/bin/bash

# Development
LURKBOT_PROFILE=development lurkbot gateway start &

# Wait for gateway
sleep 2

# Run tests
LURKBOT_PROFILE=testing lurkbot agent run "Run tests"

# Stop gateway
lurkbot gateway stop
```

### In CI/CD

```yaml
# GitHub Actions example
jobs:
  test:
    runs-on: ubuntu-latest
    env:
      LURKBOT_PROFILE: testing
    steps:
      - uses: actions/checkout@v4
      - run: lurkbot gateway start --daemon
      - run: lurkbot agent run "Run all tests"
```

---

## See Also

- [Config File](config-file.md) - JSON configuration
- [Environment Variables](environment.md) - All environment variables
- [Configuration Overview](index.md) - Configuration hierarchy
