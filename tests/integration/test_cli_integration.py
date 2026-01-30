"""Integration tests for CLI commands.

Tests the complete CLI command flow including:
- Command parsing and validation
- Command execution
- Output formatting
- Error handling
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from lurkbot.cli.main import app


class TestCLIBasicCommands:
    """Test basic CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.mark.integration
    def test_cli_help(self, runner: CliRunner):
        """Test CLI help command."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "LurkBot" in result.output or "lurkbot" in result.output.lower()

    @pytest.mark.integration
    def test_cli_version(self, runner: CliRunner):
        """Test CLI version command."""
        result = runner.invoke(app, ["version"])

        assert result.exit_code == 0
        # Should contain version number
        assert "LurkBot" in result.output or "v" in result.output

    @pytest.mark.integration
    def test_cli_unknown_command(self, runner: CliRunner):
        """Test CLI with unknown command."""
        result = runner.invoke(app, ["unknown-command"])

        # Typer returns exit code 2 for unknown commands
        assert result.exit_code != 0


class TestChatCommand:
    """Test chat command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.mark.integration
    def test_chat_help(self, runner: CliRunner):
        """Test chat command help."""
        result = runner.invoke(app, ["chat", "--help"])

        assert result.exit_code == 0
        assert "chat" in result.output.lower() or "model" in result.output.lower()

    @pytest.mark.integration
    def test_chat_default(self, runner: CliRunner):
        """Test chat command with defaults."""
        result = runner.invoke(app, ["chat"])

        # Should start chat (or show message about starting)
        assert result.exit_code == 0
        assert "chat" in result.output.lower() or "model" in result.output.lower()

    @pytest.mark.integration
    def test_chat_with_model_option(self, runner: CliRunner):
        """Test chat command with model option."""
        result = runner.invoke(app, ["chat", "--model", "gpt-4o"])

        assert result.exit_code == 0
        assert "gpt-4o" in result.output

    @pytest.mark.integration
    def test_chat_with_workspace_option(self, runner: CliRunner, temp_workspace: Path):
        """Test chat command with workspace option."""
        result = runner.invoke(app, ["chat", "--workspace", str(temp_workspace)])

        assert result.exit_code == 0


class TestGatewayCommand:
    """Test gateway command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.mark.integration
    def test_gateway_help(self, runner: CliRunner):
        """Test gateway command help."""
        result = runner.invoke(app, ["gateway", "--help"])

        assert result.exit_code == 0
        assert "gateway" in result.output.lower() or "host" in result.output.lower()

    @pytest.mark.integration
    def test_gateway_default(self, runner: CliRunner):
        """Test gateway command with defaults."""
        result = runner.invoke(app, ["gateway"])

        assert result.exit_code == 0
        assert "gateway" in result.output.lower() or "0.0.0.0" in result.output

    @pytest.mark.integration
    def test_gateway_with_port(self, runner: CliRunner):
        """Test gateway command with custom port."""
        result = runner.invoke(app, ["gateway", "--port", "9000"])

        assert result.exit_code == 0
        assert "9000" in result.output


class TestWizardCommand:
    """Test wizard command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.mark.integration
    def test_wizard_help(self, runner: CliRunner):
        """Test wizard command help."""
        result = runner.invoke(app, ["wizard", "--help"])

        assert result.exit_code == 0
        assert "wizard" in result.output.lower() or "setup" in result.output.lower()

    @pytest.mark.integration
    def test_wizard_with_mode(self, runner: CliRunner):
        """Test wizard command with mode option."""
        with patch("lurkbot.wizard.run_onboarding_wizard") as mock_wizard:
            mock_wizard.return_value = {"accepted_risk": True}

            result = runner.invoke(app, ["wizard", "--mode", "local", "--accept-risk"])

            # Should attempt to run wizard
            assert result.exit_code == 0 or mock_wizard.called


class TestResetCommand:
    """Test reset command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.mark.integration
    def test_reset_help(self, runner: CliRunner):
        """Test reset command help."""
        result = runner.invoke(app, ["reset", "--help"])

        assert result.exit_code == 0
        assert "reset" in result.output.lower() or "scope" in result.output.lower()

    @pytest.mark.integration
    def test_reset_with_force(self, runner: CliRunner):
        """Test reset command with force flag."""
        result = runner.invoke(app, ["reset", "--force"])

        assert result.exit_code == 0
        assert "reset" in result.output.lower() or "complete" in result.output.lower()

    @pytest.mark.integration
    def test_reset_with_scope(self, runner: CliRunner):
        """Test reset command with scope option."""
        result = runner.invoke(app, ["reset", "--scope", "config", "--force"])

        assert result.exit_code == 0


class TestSecuritySubcommand:
    """Test security subcommand."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.mark.integration
    def test_security_help(self, runner: CliRunner):
        """Test security subcommand help."""
        result = runner.invoke(app, ["security", "--help"])

        assert result.exit_code == 0
        assert "security" in result.output.lower()


class TestCLIOutputFormatting:
    """Test CLI output formatting."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.mark.integration
    def test_version_output_format(self, runner: CliRunner):
        """Test version output format."""
        result = runner.invoke(app, ["version"])

        assert result.exit_code == 0
        # Should have clean output
        assert "LurkBot" in result.output

    @pytest.mark.integration
    def test_help_output_format(self, runner: CliRunner):
        """Test help output format."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        # Should list available commands
        assert "chat" in result.output
        assert "gateway" in result.output
        assert "wizard" in result.output


class TestCLIErrorHandling:
    """Test CLI error handling."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.mark.integration
    def test_invalid_option(self, runner: CliRunner):
        """Test error with invalid option."""
        result = runner.invoke(app, ["chat", "--invalid-option"])

        # Should fail with invalid option
        assert result.exit_code != 0

    @pytest.mark.integration
    def test_missing_required_value(self, runner: CliRunner):
        """Test error when option value is missing."""
        result = runner.invoke(app, ["chat", "--model"])

        # Should fail with missing value
        assert result.exit_code != 0

    @pytest.mark.integration
    def test_invalid_port_value(self, runner: CliRunner):
        """Test error with invalid port value."""
        result = runner.invoke(app, ["gateway", "--port", "invalid"])

        # Should fail with invalid port
        assert result.exit_code != 0


class TestCLIIntegrationWithModules:
    """Test CLI integration with other modules."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.mark.integration
    def test_chat_imports_correctly(self, runner: CliRunner):
        """Test that chat command imports work correctly."""
        # This tests that all imports in the chat command work
        result = runner.invoke(app, ["chat", "--help"])
        assert result.exit_code == 0

    @pytest.mark.integration
    def test_gateway_imports_correctly(self, runner: CliRunner):
        """Test that gateway command imports work correctly."""
        result = runner.invoke(app, ["gateway", "--help"])
        assert result.exit_code == 0

    @pytest.mark.integration
    def test_wizard_imports_correctly(self, runner: CliRunner):
        """Test that wizard command imports work correctly."""
        result = runner.invoke(app, ["wizard", "--help"])
        assert result.exit_code == 0


# Test count verification
def test_cli_integration_test_count():
    """Verify the number of integration tests."""
    import inspect

    test_classes = [
        TestCLIBasicCommands,
        TestChatCommand,
        TestGatewayCommand,
        TestWizardCommand,
        TestResetCommand,
        TestSecuritySubcommand,
        TestCLIOutputFormatting,
        TestCLIErrorHandling,
        TestCLIIntegrationWithModules,
    ]

    total_tests = 0
    for cls in test_classes:
        methods = [m for m in dir(cls) if m.startswith("test_")]
        total_tests += len(methods)

    # Add standalone test
    total_tests += 1  # test_cli_integration_test_count

    print(f"\n✅ CLI integration tests: {total_tests} tests")
    assert total_tests >= 20, f"Expected at least 20 tests, got {total_tests}"
