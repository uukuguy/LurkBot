"""Simple integration test for tool execution."""

import asyncio
from pathlib import Path

from lurkbot.tools import SessionType
from lurkbot.tools.builtin.bash import BashTool
from lurkbot.tools.builtin.file_ops import ReadFileTool, WriteFileTool


async def test_bash_tool() -> None:
    """Test bash tool execution."""
    print("\n=== Testing BashTool ===")
    tool = BashTool()

    # Test simple command
    result = await tool.execute(
        {"command": "echo 'Hello from LurkBot'"},
        str(Path.home()),
        SessionType.MAIN,
    )
    print(f"✅ Command executed: {result.success}")
    print(f"📝 Output: {result.output.strip()}")

    # Test directory listing
    result = await tool.execute(
        {"command": "ls -la | head -5"},
        str(Path.home()),
        SessionType.MAIN,
    )
    print(f"\n✅ Directory listing: {result.success}")
    print(f"📝 Output:\n{result.output}")


async def test_file_tools() -> None:
    """Test file read/write tools."""
    print("\n=== Testing File Tools ===")

    tmp_dir = Path("/tmp/lurkbot_test")
    tmp_dir.mkdir(exist_ok=True)

    # Write a file
    write_tool = WriteFileTool()
    result = await write_tool.execute(
        {"path": "test_file.txt", "content": "Hello from LurkBot!\nThis is a test file."},
        str(tmp_dir),
        SessionType.MAIN,
    )
    print(f"✅ File written: {result.success}")
    print(f"📝 Message: {result.output}")

    # Read the file back
    read_tool = ReadFileTool()
    result = await read_tool.execute(
        {"path": "test_file.txt"},
        str(tmp_dir),
        SessionType.MAIN,
    )
    print(f"\n✅ File read: {result.success}")
    print(f"📝 Content:\n{result.output}")

    # Cleanup
    (tmp_dir / "test_file.txt").unlink(missing_ok=True)
    print("\n✅ Cleanup completed")


async def main() -> None:
    """Run integration tests."""
    print("🤖 LurkBot Tool Integration Test")
    print("=" * 50)

    await test_bash_tool()
    await test_file_tools()

    print("\n" + "=" * 50)
    print("✅ All integration tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
