# Contributing

Thank you for your interest in contributing to LurkBot! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Git
- Docker (optional, for sandbox testing)

### Clone and Install

```bash
# Clone the repository
git clone https://github.com/uukuguy/lurkbot.git
cd lurkbot

# Install development dependencies with uv
make dev

# Or with pip
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Verify Setup

```bash
# Run tests
make test

# Run linting
make lint

# Run type checking
make typecheck

# Run all checks
make check
```

## Code Style

### Python Style

We follow [PEP 8](https://pep8.org/) with modifications defined in `pyproject.toml`:

```toml
# pyproject.toml:102-119
[tool.ruff]
line-length = 100
target-version = "py312"
src = ["src"]

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
    "ARG", # flake8-unused-arguments
    "SIM", # flake8-simplify
]
```

### Formatting

We use [ruff](https://docs.astral.sh/ruff/) for formatting and linting:

```bash
# Format code
make format

# Check formatting
make lint
```

### Type Hints

All public APIs must have type hints (Python 3.12+ syntax):

```python
# Good - using modern type syntax
def process_message(session: Session, content: str) -> AsyncIterator[str]:
    """Process a message and stream the response."""
    ...

# Good - using union syntax
def get_config(key: str) -> str | None:
    ...

# Bad - missing type hints
def process_message(session, content):
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def execute_tool(tool: str, args: dict[str, Any]) -> ToolResult:
    """Execute a tool with the given arguments.

    Args:
        tool: The name of the tool to execute.
        args: Arguments to pass to the tool.

    Returns:
        The result of the tool execution.

    Raises:
        ToolNotFoundError: If the tool doesn't exist.
        ToolPolicyError: If the tool is not allowed.
    """
    ...
```

## Testing

### Running Tests

```bash
# Run all tests (fail fast, verbose)
pytest -xvs

# Run specific test file
pytest tests/test_gateway.py -xvs

# Run with coverage
pytest --cov=src/lurkbot --cov-report=term-missing

# Run async tests (auto mode configured)
pytest tests/test_agents.py
```

### Test Configuration

Test settings are defined in `pyproject.toml:96-100`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
addopts = "-xvs"
```

### Writing Tests

Tests are in the `tests/` directory:

```python
# tests/test_gateway.py
import pytest
from lurkbot.gateway.server import GatewayServer

@pytest.fixture
def gateway():
    """Create a test gateway."""
    return GatewayServer()

async def test_gateway_version(gateway):
    """Test gateway version."""
    assert gateway.VERSION == "0.1.0"
    assert gateway.PROTOCOL_VERSION == 1

async def test_message_routing(gateway):
    """Test message routing."""
    # ...
```

### Test Categories

- **Unit tests**: `tests/` - Test individual functions/classes
- **Integration tests**: `tests/integration/` - Test component interactions
- **Main tests**: `tests/main/` - Test full workflows

## Project Structure

```
lurkbot/
├── src/lurkbot/           # Main source code
│   ├── __init__.py
│   ├── gateway/           # Gateway server
│   │   ├── __init__.py
│   │   ├── server.py      # GatewayServer class
│   │   ├── connection.py  # GatewayConnection
│   │   └── methods.py     # RPC method registry
│   ├── agents/            # Agent runtime
│   │   ├── __init__.py
│   │   ├── runtime.py     # PydanticAI agent creation
│   │   ├── bootstrap.py   # Bootstrap file system
│   │   └── providers/     # AI provider adapters
│   ├── tools/             # Built-in tools
│   │   ├── __init__.py
│   │   ├── builtin/       # 22 native tools
│   │   │   ├── __init__.py
│   │   │   ├── common.py  # ToolResult, helpers
│   │   │   ├── exec_tool.py
│   │   │   ├── fs_tool.py
│   │   │   └── ...
│   │   └── policy.py      # Nine-layer policy system
│   ├── skills/            # Skill system
│   │   ├── __init__.py
│   │   ├── frontmatter.py # YAML frontmatter parsing
│   │   ├── workspace.py   # Skill discovery
│   │   └── registry.py    # SkillManager
│   ├── sessions/          # Session management
│   │   ├── __init__.py
│   │   └── session.py
│   ├── config/            # Configuration
│   │   ├── __init__.py
│   │   └── settings.py
│   └── cli/               # CLI commands
│       ├── __init__.py
│       └── main.py
├── tests/                 # Test suite
│   ├── __init__.py
│   ├── main/              # Main feature tests
│   └── integration/       # Integration tests
├── docs/                  # Documentation
├── pyproject.toml         # Project configuration
├── Makefile               # Build commands
└── README.md
```

## Pull Request Process

### 1. Create a Branch

```bash
# Create feature branch
git checkout -b feature/my-feature

# Or bugfix branch
git checkout -b fix/my-bugfix
```

### 2. Make Changes

- Write code following style guidelines
- Add tests for new functionality
- Update documentation if needed

### 3. Run Checks

```bash
# Run all checks
make check
```

### 4. Commit Changes

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Feature
git commit -m "feat: add new tool for X"

# Bug fix
git commit -m "fix: resolve issue with Y"

# Documentation
git commit -m "docs: update installation guide"

# Refactoring
git commit -m "refactor: simplify message routing"
```

### 5. Push and Create PR

```bash
git push origin feature/my-feature
```

Then create a Pull Request on GitHub.

### PR Guidelines

- Keep PRs focused and small
- Write a clear description
- Reference related issues
- Ensure all checks pass
- Request review from maintainers

## Adding Features

### Adding a Tool

1. Create tool in `src/lurkbot/tools/builtin/`:

```python
# src/lurkbot/tools/builtin/my_tool.py
from pydantic import BaseModel
from .common import ToolResult, text_result, error_result

class MyToolParams(BaseModel):
    """Parameters for my_tool."""
    arg1: str
    arg2: int = 10

async def my_tool(params: MyToolParams) -> ToolResult:
    """Execute my custom tool."""
    try:
        result = do_something(params.arg1, params.arg2)
        return text_result(f"Result: {result}")
    except Exception as e:
        return error_result(str(e))
```

2. Register in `src/lurkbot/tools/builtin/__init__.py`
3. Add to appropriate tool group in `src/lurkbot/tools/policy.py`
4. Write tests
5. Update documentation

### Adding a Skill

1. Create skill file (e.g., `.skills/my-skill/SKILL.md`):

```markdown
---
description: My custom skill description
tags:
  - custom
  - example
userInvocable: true
---

# My Skill

System prompt content goes here...
```

2. Skills are auto-discovered from:
   - `.skills/` (workspace, priority 1)
   - `.skill-bundles/` (managed, priority 2)
   - Bundled skills (priority 3)

3. Test with `lurkbot skills list`

## Documentation

### Building Docs

```bash
# Install docs dependencies
pip install -e ".[docs]"

# Build docs
make docs

# Serve locally
make docs-serve
```

### Documentation Style

- Use clear, concise language
- Include code examples with source references
- Add cross-references
- Keep up-to-date with code

## Getting Help

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and discussions

## Code of Conduct

Please be respectful and inclusive. We follow the [Contributor Covenant](https://www.contributor-covenant.org/).

---

## See Also

- [Architecture](architecture.md) - System design
- [Extending](extending/index.md) - Add custom components
- [API Reference](../api/index.md) - Complete API docs
