# Troubleshooting

Common issues and solutions for LurkBot.

## Quick Diagnostics

Run the built-in health check:

```bash
lurkbot doctor
```

This checks:

- Python version
- Dependencies installed
- Configuration valid
- API keys configured
- Gateway reachable
- Docker available (optional)

## Common Issues

### Installation Issues

#### "Python version not supported"

LurkBot requires Python 3.12+:

```bash
# Check your version
python --version

# Install Python 3.12
# macOS
brew install python@3.12

# Ubuntu
sudo apt install python3.12
```

#### "Module not found"

Reinstall dependencies:

```bash
pip install -e ".[all]"
```

### Configuration Issues

#### "API key not found"

Ensure your API key is set:

```bash
# Check if set
echo $LURKBOT_ANTHROPIC_API_KEY

# Set it
export LURKBOT_ANTHROPIC_API_KEY=sk-ant-api03-...

# Or add to ~/.lurkbot/.env
echo "LURKBOT_ANTHROPIC_API_KEY=sk-ant-api03-..." >> ~/.lurkbot/.env
```

#### "Invalid configuration"

Validate your configuration:

```bash
lurkbot config validate
```

Check for:

- YAML/JSON syntax errors
- Missing required fields
- Invalid values

### Gateway Issues

#### "Address already in use"

Another process is using the port:

```bash
# Find the process
lsof -i :18789

# Kill it (if safe)
kill <PID>

# Or use a different port
lurkbot gateway start --port 8080
```

#### "Connection refused"

Gateway is not running:

```bash
# Check status
lurkbot gateway status

# Start it
lurkbot gateway start
```

#### "Gateway not responding"

Restart the gateway:

```bash
lurkbot gateway stop
lurkbot gateway start
```

### Channel Issues

#### Telegram: "Unauthorized"

Bot token is invalid:

1. Go to [@BotFather](https://t.me/botfather)
2. Send `/token` to get a new token
3. Update your configuration

#### Telegram: "User not in allowlist"

Add your user ID to the allowlist:

```bash
# Get your user ID from @userinfobot
LURKBOT_TELEGRAM__ALLOWLIST=YOUR_USER_ID
```

#### Discord: "Missing Permissions"

Re-invite the bot with correct permissions:

1. Go to Discord Developer Portal
2. OAuth2 → URL Generator
3. Select required permissions
4. Use the new invite URL

#### Discord: "Missing Access"

Enable Message Content Intent:

1. Go to Discord Developer Portal
2. Bot settings
3. Enable "Message Content Intent"

#### Slack: "invalid_auth"

Regenerate tokens:

1. Go to Slack API
2. Reinstall app to workspace
3. Copy new tokens

### AI Model Issues

#### "Model not available"

Check your API key has access:

```bash
# Test Anthropic
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $LURKBOT_ANTHROPIC_API_KEY" \
  -H "content-type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"claude-sonnet-4-20250514","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'
```

#### "Rate limit exceeded"

- Wait and retry
- Use a different model
- Upgrade your API plan

#### "Context too long"

Enable context compaction:

```bash
LURKBOT_COMPACT_AFTER=50
```

Or clear the session:

```bash
lurkbot sessions clear <session_key>
```

### Tool Issues

#### "Tool not allowed"

Check tool policies:

```bash
lurkbot tools policy bash --explain
```

Enable the tool:

```bash
LURKBOT_TOOL_POLICY_DEFAULT=allow
```

#### "Tool timeout"

Increase timeout:

```bash
LURKBOT_TOOL_TIMEOUT=60
LURKBOT_TOOL_BASH_TIMEOUT=120
```

#### "Sandbox error"

Check Docker is running:

```bash
docker ps
```

Or disable sandbox:

```bash
LURKBOT_SANDBOX_ENABLED=false
```

### Performance Issues

#### Slow responses

1. Check AI provider status
2. Try a faster model:
   ```bash
   LURKBOT_DEFAULT_MODEL=claude-haiku-3-5-20241022
   ```
3. Reduce context size
4. Check network latency

#### High memory usage

1. Enable session compaction
2. Reduce max sessions
3. Restart the gateway periodically

#### High CPU usage

1. Limit concurrent subagents
2. Set tool timeouts
3. Check for runaway processes

## Logs

### View Logs

```bash
# Gateway log
tail -f ~/.lurkbot/logs/gateway.log

# Error log
tail -f ~/.lurkbot/logs/gateway.err

# Tool audit log
tail -f ~/.lurkbot/logs/tool-audit.log
```

### Enable Debug Logging

```bash
LURKBOT_LOG_LEVEL=debug
lurkbot gateway start
```

### Log Locations

| Log | Location |
|-----|----------|
| Gateway | `~/.lurkbot/logs/gateway.log` |
| Errors | `~/.lurkbot/logs/gateway.err` |
| Tools | `~/.lurkbot/logs/tool-audit.log` |
| Sandbox | `~/.lurkbot/logs/sandbox.log` |

## Getting Help

### Self-Help Resources

1. Check this troubleshooting guide
2. Search [GitHub Issues](https://github.com/uukuguy/lurkbot/issues)
3. Read the [documentation](../index.md)

### Reporting Issues

When reporting issues, include:

1. LurkBot version: `lurkbot --version`
2. Python version: `python --version`
3. Operating system
4. Configuration (redact secrets)
5. Error messages
6. Steps to reproduce

### Community Support

- [GitHub Discussions](https://github.com/uukuguy/lurkbot/discussions)
- [GitHub Issues](https://github.com/uukuguy/lurkbot/issues)

---

## See Also

- [Configuration](../user-guide/configuration/index.md) - Configuration options
- [FAQ](faq.md) - Frequently asked questions
- [Getting Started](../getting-started/index.md) - Setup guide
