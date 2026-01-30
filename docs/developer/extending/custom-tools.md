# Custom Tools

Learn how to create custom tools that agents can use.

## Overview

Tools are capabilities that AI agents can invoke. Each tool in LurkBot:

- Has a name and description
- Defines parameters using Pydantic models
- Executes an async action
- Returns a structured `ToolResult`

## Tool Result Interface

Source: `src/lurkbot/tools/builtin/common.py:41-53`

```python
@dataclass
class ToolResult:
    """Standard tool result format.

    Matches moltbot AgentToolResult<TDetails>.
    """
    content: list[ToolResultContent] = field(default_factory=list)
    details: Any | None = None

    def to_text(self) -> str:
        """Get the text content of the result."""
        texts = [c.text for c in self.content if c.text]
        return "\n".join(texts)
```

### Content Types

Source: `src/lurkbot/tools/builtin/common.py:21-27`

```python
class ToolResultContentType(str, Enum):
    """Tool result content types."""
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
```

## Creating a Custom Tool

### Step 1: Define Parameters

Create a Pydantic model for your tool's parameters:

```python
# src/lurkbot/tools/builtin/weather_tool.py
from pydantic import BaseModel, Field

class WeatherParams(BaseModel):
    """Parameters for weather tool."""
    city: str = Field(..., description="The city name")
    units: str = Field(
        default="celsius",
        description="Temperature units (celsius or fahrenheit)"
    )
```

### Step 2: Implement the Tool Function

```python
from .common import ToolResult, text_result, error_result
import httpx

async def weather(params: WeatherParams) -> ToolResult:
    """Get current weather for a location.

    Args:
        params: Weather parameters

    Returns:
        ToolResult with weather information
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.weather.example.com/current",
                params={
                    "city": params.city,
                    "units": params.units,
                }
            )
            response.raise_for_status()
            data = response.json()

        return text_result(
            f"Weather in {params.city}: {data['temp']}°, {data['condition']}"
        )

    except httpx.HTTPError as e:
        return error_result(f"Failed to get weather: {str(e)}")
```

### Step 3: Register the Tool

Add to `src/lurkbot/tools/builtin/__init__.py`:

```python
from .weather_tool import weather, WeatherParams

# Add to tool exports
__all__ = [
    # ...existing tools...
    "weather",
    "WeatherParams",
]
```

### Step 4: Add to Policy System

Add your tool to the appropriate group in `src/lurkbot/tools/policy.py`:

```python
TOOL_GROUPS = {
    # ...existing groups...
    "group:utility": ["weather", "calculator"],
}
```

## Result Helper Functions

Source: `src/lurkbot/tools/builtin/common.py:61-123`

### text_result

Create a plain text result:

```python
from lurkbot.tools.builtin.common import text_result

result = text_result("Operation completed successfully")
result = text_result("Found 5 items", details={"count": 5})
```

### json_result

Create a JSON-formatted result:

```python
from lurkbot.tools.builtin.common import json_result

result = json_result({
    "status": "ok",
    "items": ["a", "b", "c"],
    "count": 3
})
```

### error_result

Create an error result:

```python
from lurkbot.tools.builtin.common import error_result

result = error_result("File not found")
result = error_result("Permission denied", {"code": 403, "path": "/etc/passwd"})
```

### image_result

Create an image result:

```python
from lurkbot.tools.builtin.common import image_result
import base64

with open("screenshot.png", "rb") as f:
    data = base64.b64encode(f.read()).decode()

result = image_result(
    label="Screenshot",
    path="/tmp/screenshot.png",
    base64_data=data,
    mime_type="image/png",
    extra_text="Captured at 2024-01-15 10:30:00"
)
```

## Parameter Reading Utilities

Source: `src/lurkbot/tools/builtin/common.py:131-316`

For tools that receive raw dictionaries instead of Pydantic models:

```python
from lurkbot.tools.builtin.common import (
    read_string_param,
    read_number_param,
    read_bool_param,
    read_string_array_param,
    read_dict_param,
    ParamError,
)

def process_params(params: dict) -> None:
    # Required string parameter
    name = read_string_param(params, "name", required=True)

    # Optional number with integer conversion
    count = read_number_param(params, "count", integer=True)

    # Boolean with default
    verbose = read_bool_param(params, "verbose", default=False)

    # String array
    tags = read_string_array_param(params, "tags")

    # Dictionary
    options = read_dict_param(params, "options")
```

## Tool Examples

### Database Query Tool

```python
from pydantic import BaseModel, Field
from .common import ToolResult, json_result, error_result

class DbQueryParams(BaseModel):
    """Parameters for database query."""
    query: str = Field(..., description="SQL SELECT query")
    database: str = Field(default="default", description="Database name")

async def db_query(params: DbQueryParams) -> ToolResult:
    """Execute a read-only database query."""
    # Validate query is read-only
    if not params.query.strip().upper().startswith("SELECT"):
        return error_result("Only SELECT queries are allowed")

    try:
        async with get_db_connection(params.database) as conn:
            result = await conn.execute(params.query)
            rows = await result.fetchall()

        return json_result({
            "rows": [dict(row) for row in rows],
            "count": len(rows)
        })
    except Exception as e:
        return error_result(str(e))
```

### File Processing Tool

```python
from pydantic import BaseModel, Field
from pathlib import Path
from .common import ToolResult, text_result, image_result, error_result

class ImageResizeParams(BaseModel):
    """Parameters for image resize."""
    input_path: str = Field(..., description="Path to input image")
    width: int = Field(..., description="Target width in pixels")
    height: int = Field(..., description="Target height in pixels")
    output_path: str | None = Field(None, description="Output path (optional)")

async def image_resize(params: ImageResizeParams) -> ToolResult:
    """Resize an image to specified dimensions."""
    try:
        from PIL import Image
        import base64

        img = Image.open(params.input_path)
        resized = img.resize((params.width, params.height))

        output = params.output_path or params.input_path
        resized.save(output)

        # Return with preview
        with open(output, "rb") as f:
            data = base64.b64encode(f.read()).decode()

        return image_result(
            label="Resized image",
            path=output,
            base64_data=data,
            mime_type="image/png",
            extra_text=f"Resized to {params.width}x{params.height}"
        )
    except Exception as e:
        return error_result(str(e))
```

### API Integration Tool

```python
from pydantic import BaseModel, Field
from typing import Literal
from .common import ToolResult, json_result, error_result

class GitHubParams(BaseModel):
    """Parameters for GitHub operations."""
    action: Literal["list_repos", "get_issues", "create_issue"]
    repo: str | None = Field(None, description="Repository (owner/name)")
    data: dict | None = Field(None, description="Additional data")

async def github(params: GitHubParams) -> ToolResult:
    """Interact with GitHub API."""
    import httpx

    async with httpx.AsyncClient() as client:
        client.headers["Authorization"] = f"token {get_github_token()}"

        if params.action == "list_repos":
            response = await client.get("https://api.github.com/user/repos")
            return json_result(response.json())

        elif params.action == "get_issues":
            if not params.repo:
                return error_result("repo required for get_issues")
            response = await client.get(
                f"https://api.github.com/repos/{params.repo}/issues"
            )
            return json_result(response.json())

        elif params.action == "create_issue":
            if not params.repo or not params.data:
                return error_result("repo and data required for create_issue")
            response = await client.post(
                f"https://api.github.com/repos/{params.repo}/issues",
                json=params.data
            )
            return json_result(response.json())

        return error_result(f"Unknown action: {params.action}")
```

## Tool Policy Integration

### Adding to Tool Groups

Source: `src/lurkbot/tools/policy.py:62-126`

```python
TOOL_GROUPS = {
    "group:fs": ["read", "write", "edit", "apply_patch"],
    "group:runtime": ["exec", "process"],
    "group:web": ["web_search", "web_fetch"],
    # Add your custom group
    "group:custom": ["weather", "db_query", "github"],
}
```

### Tool Profiles

Your tool can be included in profiles:

```python
TOOL_PROFILES = {
    ToolProfileId.CODING: {
        "allow": ["group:fs", "group:runtime", "group:custom"]
    },
    ToolProfileId.FULL: {}  # Empty = allow all
}
```

## Testing Tools

```python
# tests/tools/test_weather.py
import pytest
from unittest.mock import AsyncMock, patch
from lurkbot.tools.builtin.weather_tool import weather, WeatherParams

@pytest.fixture
def weather_params():
    return WeatherParams(city="London", units="celsius")

async def test_weather_success(weather_params):
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "temp": 20,
            "condition": "Sunny"
        }
        mock_response.raise_for_status = lambda: None
        mock_get.return_value = mock_response

        result = await weather(weather_params)

        assert "20" in result.to_text()
        assert "Sunny" in result.to_text()

async def test_weather_error(weather_params):
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = Exception("API error")

        result = await weather(weather_params)

        assert "error" in result.to_text().lower()
```

## Best Practices

1. **Use Pydantic models**: Define parameters with Field descriptions for AI understanding
2. **Return structured results**: Use `ToolResult` with appropriate content types
3. **Handle errors gracefully**: Return `error_result()` instead of raising exceptions
4. **Validate inputs**: Check parameters before execution
5. **Set timeouts**: Use httpx timeouts for external API calls
6. **Log appropriately**: Use loguru for debugging
7. **Consider security**: Validate and sanitize all inputs
8. **Add to policy system**: Register in appropriate tool groups

---

## See Also

- [Tools Overview](../../user-guide/tools/index.md) - User documentation
- [Tool Policies](../../user-guide/tools/tool-policies.md) - Security and access control
- [Custom Skills](custom-skills.md) - Create skills
- [Architecture](../architecture.md) - System design
