# AI Models

LurkBot supports multiple AI providers. This guide covers configuration for each.

## Anthropic (Claude)

Claude is the recommended model for LurkBot.

### Setup

1. Get an API key from [Anthropic Console](https://console.anthropic.com/)
2. Configure the key:

```bash
LURKBOT_ANTHROPIC_API_KEY=sk-ant-api03-...
```

### Available Models

| Model | Description | Best For |
|-------|-------------|----------|
| `claude-sonnet-4-20250514` | Latest Sonnet | General use (recommended) |
| `claude-opus-4-20250514` | Most capable | Complex tasks |
| `claude-haiku-3-5-20241022` | Fastest | Quick responses |

### Configuration

```bash
# API Key
LURKBOT_ANTHROPIC_API_KEY=sk-ant-api03-...

# Default model
LURKBOT_DEFAULT_MODEL=claude-sonnet-4-20250514

# Optional: Custom base URL
LURKBOT_ANTHROPIC_BASE_URL=https://api.anthropic.com
```

---

## OpenAI (GPT)

### Setup

1. Get an API key from [OpenAI Platform](https://platform.openai.com/)
2. Configure the key:

```bash
LURKBOT_OPENAI_API_KEY=sk-...
```

### Available Models

| Model | Description | Best For |
|-------|-------------|----------|
| `gpt-4o` | Latest GPT-4 | General use |
| `gpt-4o-mini` | Faster GPT-4 | Quick tasks |
| `gpt-4-turbo` | GPT-4 Turbo | Long context |
| `gpt-3.5-turbo` | GPT-3.5 | Cost-effective |

### Configuration

```bash
# API Key
LURKBOT_OPENAI_API_KEY=sk-...

# Default model
LURKBOT_DEFAULT_MODEL=gpt-4o

# Optional: Organization ID
LURKBOT_OPENAI_ORG_ID=org-...

# Optional: Custom base URL (for Azure, etc.)
LURKBOT_OPENAI_BASE_URL=https://api.openai.com/v1
```

---

## Google (Gemini)

### Setup

1. Get an API key from [Google AI Studio](https://makersuite.google.com/)
2. Configure the key:

```bash
LURKBOT_GOOGLE_API_KEY=...
```

### Available Models

| Model | Description | Best For |
|-------|-------------|----------|
| `gemini-pro` | Gemini Pro | General use |
| `gemini-pro-vision` | With vision | Image analysis |
| `gemini-flash` | Fast model | Quick responses |

### Configuration

```bash
# API Key
LURKBOT_GOOGLE_API_KEY=...

# Default model
LURKBOT_DEFAULT_MODEL=gemini-pro
```

---

## Ollama (Local)

Run AI models locally with Ollama.

### Setup

1. Install Ollama from [ollama.ai](https://ollama.ai/)
2. Pull a model:

```bash
ollama pull llama2
```

3. Configure LurkBot:

```bash
LURKBOT_OLLAMA_BASE_URL=http://localhost:11434
LURKBOT_DEFAULT_MODEL=ollama/llama2
```

### Available Models

Any model available in Ollama:

| Model | Size | Description |
|-------|------|-------------|
| `llama2` | 7B | Meta's Llama 2 |
| `mistral` | 7B | Mistral AI |
| `codellama` | 7B | Code-focused |
| `mixtral` | 8x7B | Mixture of experts |

### Configuration

```bash
# Ollama server URL
LURKBOT_OLLAMA_BASE_URL=http://localhost:11434

# Model (prefix with ollama/)
LURKBOT_DEFAULT_MODEL=ollama/llama2

# Optional: Custom model parameters
LURKBOT_OLLAMA_NUM_CTX=4096
```

---

## Model Selection

### Per-Session Model

Change model for a specific session:

```bash
# In CLI chat
/model gpt-4o

# Or via environment
LURKBOT_SESSION_MODEL=gpt-4o
```

### Per-Channel Model

Use different models for different channels:

```bash
LURKBOT_TELEGRAM__MODEL=claude-sonnet-4-20250514
LURKBOT_DISCORD__MODEL=gpt-4o
```

### Fallback Models

Configure fallback if primary model fails:

```bash
LURKBOT_FALLBACK_MODELS=gpt-4o,claude-haiku-3-5-20241022
```

---

## Advanced Configuration

### Token Limits

```bash
# Max tokens in response
LURKBOT_MAX_TOKENS=4096

# Max context tokens
LURKBOT_MAX_CONTEXT_TOKENS=128000
```

### Temperature

Control response randomness:

```bash
# 0.0 = deterministic, 1.0 = creative
LURKBOT_TEMPERATURE=0.7
```

### System Prompt

Customize the AI's behavior:

```bash
# Custom system prompt
LURKBOT_SYSTEM_PROMPT="You are a helpful coding assistant..."

# Or from file
LURKBOT_SYSTEM_PROMPT_FILE=~/.lurkbot/system-prompt.txt
```

---

## Troubleshooting

### "API key not found"

Ensure your API key is set:

```bash
echo $LURKBOT_ANTHROPIC_API_KEY
```

### "Model not available"

Check your API key has access to the model:

```bash
# Test with curl
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $LURKBOT_ANTHROPIC_API_KEY" \
  -H "content-type: application/json" \
  -d '{"model":"claude-sonnet-4-20250514","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'
```

### "Rate limit exceeded"

- Wait and retry
- Use a different model
- Upgrade your API plan

---

## See Also

- [Sessions](sessions.md) - Session management
- [Subagents](subagents.md) - Specialized agents
- [Configuration](../configuration/index.md) - All configuration options
