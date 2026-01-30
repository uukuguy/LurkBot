# Installation

This guide covers how to install LurkBot on your system.

## Prerequisites

### Required

- **Python 3.12+**: LurkBot requires Python 3.12 or higher
- **Git**: For cloning the repository

### Recommended

- **[uv](https://docs.astral.sh/uv/)**: Fast Python package manager (recommended over pip)
- **Docker**: Required for sandbox isolation features

### Optional

- **API Keys**: For AI providers (Anthropic, OpenAI, Google)
- **Bot Tokens**: For messaging platforms (Telegram, Discord, Slack)

## Installation Methods

### Method 1: Using uv (Recommended)

[uv](https://docs.astral.sh/uv/) is a fast, modern Python package manager.

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/uukuguy/lurkbot.git
cd lurkbot

# Install dependencies
make dev
```

### Method 2: Using pip

```bash
# Clone the repository
git clone https://github.com/uukuguy/lurkbot.git
cd lurkbot

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### Method 3: From PyPI (Coming Soon)

```bash
pip install lurkbot
```

## Verify Installation

After installation, verify everything is working:

```bash
# Check CLI is available
lurkbot --version

# Run tests
make test

# Verify imports
python -c "from lurkbot import __version__; print(f'LurkBot {__version__}')"
```

## Configuration

### 1. Create Configuration Directory

```bash
mkdir -p ~/.lurkbot
```

### 2. Set Up Environment Variables

Create `~/.lurkbot/.env`:

```bash
# AI Provider API Keys (choose at least one)
LURKBOT_ANTHROPIC_API_KEY=sk-ant-api03-...
LURKBOT_OPENAI_API_KEY=sk-...
LURKBOT_GOOGLE_API_KEY=...

# Optional: Default model
LURKBOT_DEFAULT_MODEL=claude-sonnet-4-20250514
```

### 3. Configure Channels (Optional)

For Telegram:

```bash
# Add to ~/.lurkbot/.env
LURKBOT_TELEGRAM__BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
LURKBOT_TELEGRAM__ENABLED=true
```

## Docker Setup (Optional)

For sandbox isolation features:

```bash
# Install Docker
# See: https://docs.docker.com/get-docker/

# Verify Docker is running
docker --version
docker ps

# Pull the sandbox image (optional, will be pulled automatically)
docker pull ubuntu:22.04
```

## Development Setup

For contributors:

```bash
# Install all development dependencies
make dev

# Install pre-commit hooks
pre-commit install

# Run all checks
make check
```

## Troubleshooting

### Python Version Issues

```bash
# Check Python version
python --version

# If using pyenv
pyenv install 3.12
pyenv local 3.12
```

### Permission Issues

```bash
# On Linux/macOS, you may need to fix permissions
chmod +x ~/.local/bin/lurkbot
```

### Import Errors

```bash
# Ensure you're in the virtual environment
source .venv/bin/activate

# Reinstall in development mode
pip install -e ".[dev]"
```

## Next Steps

- [Quick Start](quick-start.md) - Run your first chat session
- [First Bot](first-bot.md) - Create a Telegram bot
- [Configuration](../user-guide/configuration/index.md) - Advanced configuration options
