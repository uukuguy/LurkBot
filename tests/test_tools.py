"""Tests for tool system."""

from pathlib import Path

import pytest

from lurkbot.tools import SessionType, Tool, ToolPolicy, ToolRegistry, ToolResult
from lurkbot.tools.builtin.bash import BashTool
from lurkbot.tools.builtin.file_ops import ReadFileTool, WriteFileTool


class DummyTool(Tool):
    """Dummy tool for testing."""

    def __init__(
        self,
        name: str = "dummy",
        description: str = "A dummy tool",
        policy: ToolPolicy | None = None,
    ):
        super().__init__(name, description, policy)

    async def execute(
        self,
        arguments: dict,
        workspace: str,
        session_type: SessionType,
    ) -> ToolResult:
        """Execute dummy tool."""
        return ToolResult(success=True, output="dummy output")

    def get_schema(self) -> dict:
        """Get dummy tool schema."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        }


@pytest.fixture
def tool_registry() -> ToolRegistry:
    """Create a tool registry for testing."""
    return ToolRegistry()


def test_tool_registry_initialization(tool_registry: ToolRegistry) -> None:
    """Test tool registry initialization."""
    assert len(tool_registry) == 0


def test_tool_registration(tool_registry: ToolRegistry) -> None:
    """Test tool registration."""
    tool = DummyTool()
    tool_registry.register(tool)

    assert len(tool_registry) == 1
    assert "dummy" in tool_registry
    assert tool_registry.get("dummy") is tool


def test_tool_registration_multiple(tool_registry: ToolRegistry) -> None:
    """Test registering multiple tools."""
    tool1 = DummyTool(name="tool1")
    tool2 = DummyTool(name="tool2")

    tool_registry.register(tool1)
    tool_registry.register(tool2)

    assert len(tool_registry) == 2
    assert tool_registry.get("tool1") is tool1
    assert tool_registry.get("tool2") is tool2


def test_tool_get_nonexistent(tool_registry: ToolRegistry) -> None:
    """Test getting a non-existent tool."""
    result = tool_registry.get("nonexistent")
    assert result is None


def test_list_all_tools(tool_registry: ToolRegistry) -> None:
    """Test listing all tools."""
    tool1 = DummyTool(name="tool1")
    tool2 = DummyTool(name="tool2")

    tool_registry.register(tool1)
    tool_registry.register(tool2)

    tools = tool_registry.list_tools()
    assert len(tools) == 2
    assert tool1 in tools
    assert tool2 in tools


def test_list_tools_by_session_type() -> None:
    """Test listing tools filtered by session type."""
    registry = ToolRegistry()

    # Tool only for MAIN sessions
    main_only_tool = DummyTool(
        name="main_only",
        policy=ToolPolicy(allowed_session_types={SessionType.MAIN}),
    )

    # Tool for MAIN and DM sessions
    main_dm_tool = DummyTool(
        name="main_dm",
        policy=ToolPolicy(allowed_session_types={SessionType.MAIN, SessionType.DM}),
    )

    # Tool for all session types
    all_sessions_tool = DummyTool(
        name="all_sessions",
        policy=ToolPolicy(
            allowed_session_types={
                SessionType.MAIN,
                SessionType.GROUP,
                SessionType.DM,
                SessionType.TOPIC,
            }
        ),
    )

    registry.register(main_only_tool)
    registry.register(main_dm_tool)
    registry.register(all_sessions_tool)

    # Test MAIN session
    main_tools = registry.list_tools(SessionType.MAIN)
    assert len(main_tools) == 3
    assert all(t in main_tools for t in [main_only_tool, main_dm_tool, all_sessions_tool])

    # Test DM session
    dm_tools = registry.list_tools(SessionType.DM)
    assert len(dm_tools) == 2
    assert all(t in dm_tools for t in [main_dm_tool, all_sessions_tool])
    assert main_only_tool not in dm_tools

    # Test GROUP session
    group_tools = registry.list_tools(SessionType.GROUP)
    assert len(group_tools) == 1
    assert all_sessions_tool in group_tools


def test_check_policy() -> None:
    """Test tool policy checking."""
    registry = ToolRegistry()

    tool = DummyTool(
        name="main_only",
        policy=ToolPolicy(allowed_session_types={SessionType.MAIN}),
    )
    registry.register(tool)

    # Should be allowed for MAIN
    assert registry.check_policy(tool, SessionType.MAIN) is True

    # Should not be allowed for GROUP
    assert registry.check_policy(tool, SessionType.GROUP) is False


def test_get_tool_schemas() -> None:
    """Test getting tool schemas for AI models."""
    registry = ToolRegistry()

    tool1 = DummyTool(
        name="tool1",
        policy=ToolPolicy(allowed_session_types={SessionType.MAIN}),
    )
    tool2 = DummyTool(
        name="tool2",
        policy=ToolPolicy(allowed_session_types={SessionType.MAIN, SessionType.DM}),
    )

    registry.register(tool1)
    registry.register(tool2)

    # Get schemas for MAIN session
    schemas = registry.get_tool_schemas(SessionType.MAIN)
    assert len(schemas) == 2
    assert all("name" in schema for schema in schemas)
    assert all("description" in schema for schema in schemas)
    assert all("input_schema" in schema for schema in schemas)

    # Get schemas for DM session (should only have tool2)
    dm_schemas = registry.get_tool_schemas(SessionType.DM)
    assert len(dm_schemas) == 1
    assert dm_schemas[0]["name"] == "tool2"


@pytest.mark.asyncio
async def test_dummy_tool_execution() -> None:
    """Test dummy tool execution."""
    tool = DummyTool()
    result = await tool.execute({}, "/tmp", SessionType.MAIN)

    assert result.success is True
    assert result.output == "dummy output"
    assert result.error is None


def test_tool_policy_defaults() -> None:
    """Test tool policy default values."""
    policy = ToolPolicy()

    assert policy.allowed_session_types == {SessionType.MAIN}
    assert policy.requires_approval is False
    assert policy.sandbox_required is False
    assert policy.max_execution_time == 30


# === BashTool Tests ===


@pytest.mark.asyncio
async def test_bash_tool_simple_command(tmp_path: Path) -> None:
    """Test bash tool with a simple command."""
    tool = BashTool()
    result = await tool.execute(
        {"command": "echo 'hello world'"},
        str(tmp_path),
        SessionType.MAIN,
    )

    assert result.success is True
    assert "hello world" in result.output
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_bash_tool_command_with_working_directory(tmp_path: Path) -> None:
    """Test that bash tool respects working directory."""
    tool = BashTool()
    result = await tool.execute(
        {"command": "pwd"},
        str(tmp_path),
        SessionType.MAIN,
    )

    assert result.success is True
    assert str(tmp_path) in result.output


@pytest.mark.asyncio
async def test_bash_tool_command_failure() -> None:
    """Test bash tool with a failing command."""
    tool = BashTool()
    result = await tool.execute(
        {"command": "exit 1"},
        "/tmp",
        SessionType.MAIN,
    )

    assert result.success is False
    assert result.exit_code == 1


@pytest.mark.asyncio
async def test_bash_tool_missing_command() -> None:
    """Test bash tool with missing command argument."""
    tool = BashTool()
    result = await tool.execute(
        {},
        "/tmp",
        SessionType.MAIN,
    )

    assert result.success is False
    assert "Missing 'command'" in result.error


@pytest.mark.asyncio
async def test_bash_tool_invalid_command_type() -> None:
    """Test bash tool with invalid command type."""
    tool = BashTool()
    result = await tool.execute(
        {"command": 123},
        "/tmp",
        SessionType.MAIN,
    )

    assert result.success is False
    assert "must be a string" in result.error


@pytest.mark.asyncio
async def test_bash_tool_timeout(tmp_path: Path) -> None:
    """Test bash tool timeout protection."""
    tool = BashTool()
    # Override timeout for faster testing
    tool.policy.max_execution_time = 1

    result = await tool.execute(
        {"command": "sleep 10"},
        str(tmp_path),
        SessionType.MAIN,
    )

    assert result.success is False
    assert "timed out" in result.error.lower()


def test_bash_tool_schema() -> None:
    """Test bash tool schema."""
    tool = BashTool()
    schema = tool.get_schema()

    assert schema["name"] == "bash"
    assert "command" in schema["input_schema"]["properties"]
    assert "command" in schema["input_schema"]["required"]


def test_bash_tool_policy() -> None:
    """Test bash tool policy."""
    tool = BashTool()

    assert SessionType.MAIN in tool.policy.allowed_session_types
    assert tool.policy.requires_approval is True
    assert tool.policy.max_execution_time == 30


# === ReadFileTool Tests ===


@pytest.mark.asyncio
async def test_read_file_tool_success(tmp_path: Path) -> None:
    """Test reading a file successfully."""
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_content = "Hello, World!"
    test_file.write_text(test_content)

    tool = ReadFileTool()
    result = await tool.execute(
        {"path": "test.txt"},
        str(tmp_path),
        SessionType.MAIN,
    )

    assert result.success is True
    assert result.output == test_content


@pytest.mark.asyncio
async def test_read_file_tool_subdirectory(tmp_path: Path) -> None:
    """Test reading a file in a subdirectory."""
    # Create subdirectory and file
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    test_file = subdir / "test.txt"
    test_content = "Test content"
    test_file.write_text(test_content)

    tool = ReadFileTool()
    result = await tool.execute(
        {"path": "subdir/test.txt"},
        str(tmp_path),
        SessionType.MAIN,
    )

    assert result.success is True
    assert result.output == test_content


@pytest.mark.asyncio
async def test_read_file_tool_file_not_found(tmp_path: Path) -> None:
    """Test reading a non-existent file."""
    tool = ReadFileTool()
    result = await tool.execute(
        {"path": "nonexistent.txt"},
        str(tmp_path),
        SessionType.MAIN,
    )

    assert result.success is False
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_read_file_tool_path_traversal(tmp_path: Path) -> None:
    """Test path traversal protection."""
    tool = ReadFileTool()
    result = await tool.execute(
        {"path": "../../etc/passwd"},
        str(tmp_path),
        SessionType.MAIN,
    )

    assert result.success is False
    assert "outside workspace" in result.error


@pytest.mark.asyncio
async def test_read_file_tool_missing_path(tmp_path: Path) -> None:
    """Test missing path argument."""
    tool = ReadFileTool()
    result = await tool.execute(
        {},
        str(tmp_path),
        SessionType.MAIN,
    )

    assert result.success is False
    assert "Missing 'path'" in result.error


def test_read_file_tool_schema() -> None:
    """Test read file tool schema."""
    tool = ReadFileTool()
    schema = tool.get_schema()

    assert schema["name"] == "read_file"
    assert "path" in schema["input_schema"]["properties"]
    assert "path" in schema["input_schema"]["required"]


def test_read_file_tool_policy() -> None:
    """Test read file tool policy."""
    tool = ReadFileTool()

    assert SessionType.MAIN in tool.policy.allowed_session_types
    assert SessionType.DM in tool.policy.allowed_session_types
    assert tool.policy.requires_approval is False  # Reading is safe


# === WriteFileTool Tests ===


@pytest.mark.asyncio
async def test_write_file_tool_success(tmp_path: Path) -> None:
    """Test writing a file successfully."""
    tool = WriteFileTool()
    test_content = "Hello, World!"

    result = await tool.execute(
        {"path": "test.txt", "content": test_content},
        str(tmp_path),
        SessionType.MAIN,
    )

    assert result.success is True

    # Verify file was written
    test_file = tmp_path / "test.txt"
    assert test_file.exists()
    assert test_file.read_text() == test_content


@pytest.mark.asyncio
async def test_write_file_tool_creates_directories(tmp_path: Path) -> None:
    """Test that write file tool creates parent directories."""
    tool = WriteFileTool()

    result = await tool.execute(
        {"path": "subdir/nested/test.txt", "content": "test"},
        str(tmp_path),
        SessionType.MAIN,
    )

    assert result.success is True

    # Verify file and directories were created
    test_file = tmp_path / "subdir" / "nested" / "test.txt"
    assert test_file.exists()
    assert test_file.read_text() == "test"


@pytest.mark.asyncio
async def test_write_file_tool_overwrite(tmp_path: Path) -> None:
    """Test overwriting an existing file."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("old content")

    tool = WriteFileTool()
    result = await tool.execute(
        {"path": "test.txt", "content": "new content"},
        str(tmp_path),
        SessionType.MAIN,
    )

    assert result.success is True
    assert test_file.read_text() == "new content"


@pytest.mark.asyncio
async def test_write_file_tool_path_traversal(tmp_path: Path) -> None:
    """Test path traversal protection."""
    tool = WriteFileTool()
    result = await tool.execute(
        {"path": "../../tmp/evil.txt", "content": "malicious"},
        str(tmp_path),
        SessionType.MAIN,
    )

    assert result.success is False
    assert "outside workspace" in result.error


@pytest.mark.asyncio
async def test_write_file_tool_missing_arguments(tmp_path: Path) -> None:
    """Test missing arguments."""
    tool = WriteFileTool()

    # Missing path
    result = await tool.execute(
        {"content": "test"},
        str(tmp_path),
        SessionType.MAIN,
    )
    assert result.success is False
    assert "Missing 'path'" in result.error

    # Missing content
    result = await tool.execute(
        {"path": "test.txt"},
        str(tmp_path),
        SessionType.MAIN,
    )
    assert result.success is False
    assert "Missing 'content'" in result.error


def test_write_file_tool_schema() -> None:
    """Test write file tool schema."""
    tool = WriteFileTool()
    schema = tool.get_schema()

    assert schema["name"] == "write_file"
    assert "path" in schema["input_schema"]["properties"]
    assert "content" in schema["input_schema"]["properties"]
    assert set(schema["input_schema"]["required"]) == {"path", "content"}


def test_write_file_tool_policy() -> None:
    """Test write file tool policy."""
    tool = WriteFileTool()

    assert SessionType.MAIN in tool.policy.allowed_session_types
    assert tool.policy.requires_approval is True  # Writing needs approval
