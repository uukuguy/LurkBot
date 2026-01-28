"""Tests for CLI commands."""

from typer.testing import CliRunner

from lurkbot.cli.main import app

runner = CliRunner()


class TestVersionCommand:
    """Tests for version command."""

    def test_version_command(self) -> None:
        """Test version command shows version."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "LurkBot" in result.stdout


class TestModelCommands:
    """Tests for model management commands."""

    def test_models_list(self) -> None:
        """Test listing models."""
        result = runner.invoke(app, ["models", "list"])
        assert result.exit_code == 0
        assert "Available Models" in result.stdout
        assert "claude" in result.stdout.lower() or "gpt" in result.stdout.lower()

    def test_models_list_filter_provider(self) -> None:
        """Test listing models filtered by provider."""
        result = runner.invoke(app, ["models", "list", "--provider", "anthropic"])
        assert result.exit_code == 0
        assert "Available Models" in result.stdout

    def test_models_info_valid(self) -> None:
        """Test getting info for a valid model."""
        result = runner.invoke(app, ["models", "info", "anthropic/claude-sonnet-4-20250514"])
        assert result.exit_code == 0
        assert "Claude" in result.stdout or "claude" in result.stdout.lower()
        assert "Capabilities" in result.stdout

    def test_models_info_invalid(self) -> None:
        """Test getting info for an invalid model."""
        result = runner.invoke(app, ["models", "info", "invalid/model"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_models_default_show(self) -> None:
        """Test showing default model."""
        result = runner.invoke(app, ["models", "default"])
        assert result.exit_code == 0
        assert "Default model" in result.stdout

    def test_models_default_set_invalid(self) -> None:
        """Test setting invalid default model."""
        result = runner.invoke(app, ["models", "default", "invalid/model"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()


class TestSessionCommands:
    """Tests for session management commands."""

    def test_sessions_list_empty(self) -> None:
        """Test listing sessions when empty."""
        result = runner.invoke(app, ["sessions", "list"])
        # May be empty or have sessions
        assert result.exit_code == 0

    def test_sessions_show_invalid(self) -> None:
        """Test showing invalid session."""
        result = runner.invoke(app, ["sessions", "show", "nonexistent-session"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_sessions_clear_invalid(self) -> None:
        """Test clearing invalid session."""
        result = runner.invoke(app, ["sessions", "clear", "--force", "nonexistent-session"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_sessions_delete_invalid(self) -> None:
        """Test deleting invalid session."""
        result = runner.invoke(app, ["sessions", "delete", "--force", "nonexistent-session"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()


class TestChatCommands:
    """Tests for chat commands."""

    def test_chat_help(self) -> None:
        """Test chat help."""
        result = runner.invoke(app, ["chat", "--help"])
        assert result.exit_code == 0
        assert "start" in result.stdout
        assert "send" in result.stdout


class TestConfigCommands:
    """Tests for configuration commands."""

    def test_config_show(self) -> None:
        """Test showing configuration."""
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "Configuration" in result.stdout
        assert "Gateway" in result.stdout


class TestGatewayCommands:
    """Tests for gateway commands."""

    def test_gateway_help(self) -> None:
        """Test gateway help."""
        result = runner.invoke(app, ["gateway", "--help"])
        assert result.exit_code == 0
        assert "start" in result.stdout
        assert "status" in result.stdout


class TestChannelCommands:
    """Tests for channel commands."""

    def test_channels_list(self) -> None:
        """Test listing channels."""
        result = runner.invoke(app, ["channels", "list"])
        assert result.exit_code == 0
        assert "Channels" in result.stdout
        assert "Telegram" in result.stdout
