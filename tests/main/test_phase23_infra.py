"""Phase 23: Infrastructure Subsystems Tests.

Tests for the Infra module including:
- system_events: Event queue with deduplication
- system_presence: Presence tracking with TTL
- tailscale: Tailscale VPN integration
- ssh_tunnel: SSH tunnel management
- bonjour: mDNS service discovery
- device_pairing: Device pairing and token management
- exec_approvals: Execution approval system
- voicewake: Voice wake trigger management
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# =============================================================================
# System Events Tests
# =============================================================================


class TestSystemEventsTypes:
    """Tests for system_events type definitions."""

    def test_system_event_dataclass(self):
        """Test SystemEvent dataclass."""
        from lurkbot.infra.system_events import SystemEvent

        event = SystemEvent(text="test event")
        assert event.text == "test event"
        assert isinstance(event.ts, datetime)

    def test_session_queue_dataclass(self):
        """Test SessionQueue dataclass."""
        from lurkbot.infra.system_events import SessionQueue

        queue = SessionQueue()
        assert queue.events == []
        assert queue.last_event_text is None
        assert queue.last_context_key is None

    def test_max_events_constant(self):
        """Test MAX_EVENTS_PER_SESSION constant."""
        from lurkbot.infra.system_events import MAX_EVENTS_PER_SESSION

        assert MAX_EVENTS_PER_SESSION == 20


class TestSystemEventQueue:
    """Tests for SystemEventQueue class."""

    def test_enqueue_event(self):
        """Test enqueueing events."""
        from lurkbot.infra.system_events import SystemEventQueue

        queue = SystemEventQueue()
        queue.enqueue("session1", "event1")

        events = queue.peek("session1")
        assert len(events) == 1
        assert events[0].text == "event1"

    def test_enqueue_deduplication(self):
        """Test that duplicate events are not added."""
        from lurkbot.infra.system_events import SystemEventQueue

        queue = SystemEventQueue()
        queue.enqueue("session1", "same event")
        queue.enqueue("session1", "same event")

        events = queue.peek("session1")
        assert len(events) == 1

    def test_enqueue_different_events(self):
        """Test that different events are added."""
        from lurkbot.infra.system_events import SystemEventQueue

        queue = SystemEventQueue()
        queue.enqueue("session1", "event1")
        queue.enqueue("session1", "event2")

        events = queue.peek("session1")
        assert len(events) == 2

    def test_drain_events(self):
        """Test draining events from queue."""
        from lurkbot.infra.system_events import SystemEventQueue

        queue = SystemEventQueue()
        queue.enqueue("session1", "event1")
        queue.enqueue("session1", "event2")

        events = queue.drain("session1")
        assert len(events) == 2

        # After drain, queue should be empty
        remaining = queue.peek("session1")
        assert len(remaining) == 0

    def test_has_events(self):
        """Test has_events method."""
        from lurkbot.infra.system_events import SystemEventQueue

        queue = SystemEventQueue()
        assert not queue.has_events("session1")

        queue.enqueue("session1", "event1")
        assert queue.has_events("session1")

    def test_context_changed(self):
        """Test is_context_changed method."""
        from lurkbot.infra.system_events import SystemEventQueue

        queue = SystemEventQueue()

        # First context key
        assert queue.is_context_changed("session1", "context1")

        # Same context key - not changed
        assert not queue.is_context_changed("session1", "context1")

        # Different context key - changed
        assert queue.is_context_changed("session1", "context2")

    def test_max_events_limit(self):
        """Test that queue respects max events limit."""
        from lurkbot.infra.system_events import SystemEventQueue, MAX_EVENTS_PER_SESSION

        queue = SystemEventQueue()

        # Add more than max events
        for i in range(MAX_EVENTS_PER_SESSION + 10):
            queue.enqueue("session1", f"event{i}")

        events = queue.peek("session1")
        assert len(events) == MAX_EVENTS_PER_SESSION

    def test_multiple_sessions(self):
        """Test that sessions are isolated."""
        from lurkbot.infra.system_events import SystemEventQueue

        queue = SystemEventQueue()
        queue.enqueue("session1", "event1")
        queue.enqueue("session2", "event2")

        events1 = queue.peek("session1")
        events2 = queue.peek("session2")

        assert len(events1) == 1
        assert len(events2) == 1
        assert events1[0].text == "event1"
        assert events2[0].text == "event2"


class TestSystemEventsConvenienceFunctions:
    """Tests for system_events convenience functions."""

    def test_global_queue_instance(self):
        """Test global queue instance exists."""
        from lurkbot.infra.system_events import system_event_queue

        assert system_event_queue is not None


# =============================================================================
# System Presence Tests
# =============================================================================


class TestSystemPresenceTypes:
    """Tests for system_presence type definitions."""

    def test_system_presence_dataclass(self):
        """Test SystemPresence dataclass."""
        from lurkbot.infra.system_presence import SystemPresence

        presence = SystemPresence(
            host="test-host",
            ip="192.168.1.1",
            version="1.0.0",
        )
        assert presence.host == "test-host"
        assert presence.ip == "192.168.1.1"
        assert presence.version == "1.0.0"
        assert presence.roles == []
        assert presence.scopes == []

    def test_system_presence_update_dataclass(self):
        """Test SystemPresenceUpdate dataclass."""
        from lurkbot.infra.system_presence import SystemPresenceUpdate, SystemPresence

        presence = SystemPresence(host="test-host", ip="192.168.1.1")
        update = SystemPresenceUpdate(
            key="test-key",
            previous=None,
            next=presence,
            changes={"host": "test-host"},
            changed_keys=["host"],
        )
        assert update.key == "test-key"
        assert update.next.host == "test-host"
        assert update.changed_keys == ["host"]

    def test_presence_constants(self):
        """Test presence constants."""
        from lurkbot.infra.system_presence import PRESENCE_TTL_SECONDS, MAX_PRESENCE_ENTRIES

        assert PRESENCE_TTL_SECONDS == 300
        assert MAX_PRESENCE_ENTRIES == 200


class TestSystemPresenceManager:
    """Tests for system presence management."""

    def test_update_presence(self):
        """Test updating presence."""
        from lurkbot.infra.system_presence import (
            update_system_presence,
            list_system_presence,
            clear_presence_cache,
            SystemPresence,
        )

        clear_presence_cache()

        presence = SystemPresence(
            host="test-host",
            ip="192.168.1.1",
        )
        update_system_presence("test-key", presence)

        presences = list_system_presence()
        assert len(presences) >= 1
        assert "test-key" in presences

    def test_upsert_presence(self):
        """Test upserting presence."""
        from lurkbot.infra.system_presence import (
            upsert_presence,
            list_system_presence,
            clear_presence_cache,
            SystemPresence,
        )

        clear_presence_cache()

        presence = SystemPresence(
            host="test-host",
            ip="192.168.1.1",
            version="1.0.0",
        )
        upsert_presence("test-key", presence)

        presences = list_system_presence()
        assert len(presences) >= 1

    def test_upsert_merges_roles(self):
        """Test that upsert merges roles and scopes."""
        from lurkbot.infra.system_presence import (
            upsert_presence,
            list_system_presence,
            clear_presence_cache,
            SystemPresence,
        )

        clear_presence_cache()

        # First presence with roles
        presence1 = SystemPresence(host="test-host", roles=["admin"])
        upsert_presence("test-key", presence1)

        # Second presence with additional roles
        presence2 = SystemPresence(host="test-host", roles=["user"])
        upsert_presence("test-key", presence2)

        presences = list_system_presence()
        assert "admin" in presences["test-key"].roles
        assert "user" in presences["test-key"].roles

    def test_clear_presence_cache(self):
        """Test clearing presence cache."""
        from lurkbot.infra.system_presence import (
            upsert_presence,
            list_system_presence,
            clear_presence_cache,
            SystemPresence,
        )

        presence = SystemPresence(host="test-host")
        upsert_presence("test-key", presence)

        clear_presence_cache()

        presences = list_system_presence()
        assert len(presences) == 0

    def test_register_update_callback(self):
        """Test registering update callback."""
        from lurkbot.infra.system_presence import (
            register_update_callback,
            update_system_presence,
            clear_presence_cache,
            SystemPresence,
        )

        clear_presence_cache()

        callback_called = []

        def callback(update):
            callback_called.append(update)

        register_update_callback(callback)

        presence = SystemPresence(host="test-host")
        update_system_presence("callback-test-key", presence)

        assert len(callback_called) >= 1
        assert callback_called[0].key == "callback-test-key"

    def test_get_self_presence(self):
        """Test getting self presence."""
        from lurkbot.infra.system_presence import get_self_presence

        presence = get_self_presence()
        assert presence.host is not None
        assert presence.reason == "self"


# =============================================================================
# Tailscale Tests
# =============================================================================


class TestTailscaleTypes:
    """Tests for tailscale type definitions."""

    def test_tailscale_node_dataclass(self):
        """Test TailscaleNode dataclass."""
        from lurkbot.infra.tailscale import TailscaleNode

        node = TailscaleNode(
            id="node1",
            name="test-node",
            hostname="test-hostname",
            ip="100.64.0.1",
        )
        assert node.id == "node1"
        assert node.name == "test-node"
        assert node.hostname == "test-hostname"
        assert node.ip == "100.64.0.1"
        assert node.online is False
        assert node.tags == []

    def test_tailscale_status_dataclass(self):
        """Test TailscaleStatus dataclass."""
        from lurkbot.infra.tailscale import TailscaleStatus

        status = TailscaleStatus(
            backend_state="Running",
        )
        assert status.backend_state == "Running"
        assert status.self_node is None
        assert status.peers == {}
        assert status.health == []

    def test_tailscale_config_dataclass(self):
        """Test TailscaleConfig dataclass."""
        from lurkbot.infra.tailscale import TailscaleConfig

        config = TailscaleConfig()
        assert config.auth_key is None
        assert config.timeout_seconds == 30
        assert config.accept_routes is True


class TestTailscaleClient:
    """Tests for TailscaleClient class."""

    def test_client_initialization(self):
        """Test client initialization."""
        from lurkbot.infra.tailscale import TailscaleClient, TailscaleConfig

        config = TailscaleConfig(timeout_seconds=60)
        client = TailscaleClient(config)

        assert client._config.timeout_seconds == 60

    def test_is_available_returns_bool(self):
        """Test is_available returns bool."""
        from lurkbot.infra.tailscale import TailscaleClient

        client = TailscaleClient()
        available = client.is_available()
        assert isinstance(available, bool)

    def test_global_client_instance(self):
        """Test global client instance exists."""
        from lurkbot.infra.tailscale import tailscale_client

        assert tailscale_client is not None


class TestTailscaleConvenienceFunctions:
    """Tests for tailscale convenience functions."""

    def test_is_tailscale_available(self):
        """Test is_tailscale_available function."""
        from lurkbot.infra.tailscale import is_tailscale_available

        # Should return bool without error
        result = is_tailscale_available()
        assert isinstance(result, bool)


# =============================================================================
# SSH Tunnel Tests
# =============================================================================


class TestSshTunnelTypes:
    """Tests for ssh_tunnel type definitions."""

    def test_ssh_parsed_target_dataclass(self):
        """Test SshParsedTarget dataclass."""
        from lurkbot.infra.ssh_tunnel import SshParsedTarget

        target = SshParsedTarget(
            host="example.com",
            port=22,
            user="testuser",
        )
        assert target.host == "example.com"
        assert target.port == 22
        assert target.user == "testuser"

    def test_ssh_tunnel_config_dataclass(self):
        """Test SshTunnelConfig dataclass."""
        from lurkbot.infra.ssh_tunnel import SshTunnelConfig

        config = SshTunnelConfig(
            target="user@host:22",
            local_port=8080,
            remote_port=80,
        )
        assert config.target == "user@host:22"
        assert config.local_port == 8080
        assert config.remote_port == 80
        assert config.connect_timeout_seconds == 30

    def test_ssh_tunnel_dataclass(self):
        """Test SshTunnel dataclass."""
        from lurkbot.infra.ssh_tunnel import SshTunnel, SshParsedTarget

        parsed = SshParsedTarget(host="example.com", port=22, user="testuser")
        tunnel = SshTunnel(
            parsed_target=parsed,
            local_port=8080,
            remote_port=80,
        )
        assert tunnel.parsed_target.host == "example.com"
        assert tunnel.local_port == 8080
        assert tunnel.remote_port == 80
        assert tunnel.pid is None
        assert tunnel.is_running is False


class TestSshTunnelParsing:
    """Tests for SSH target parsing."""

    def test_parse_simple_target(self):
        """Test parsing simple user@host target."""
        from lurkbot.infra.ssh_tunnel import parse_ssh_target

        result = parse_ssh_target("user@example.com")
        assert result.user == "user"
        assert result.host == "example.com"
        assert result.port == 22

    def test_parse_target_with_port(self):
        """Test parsing user@host:port target."""
        from lurkbot.infra.ssh_tunnel import parse_ssh_target

        result = parse_ssh_target("user@example.com:2222")
        assert result.user == "user"
        assert result.host == "example.com"
        assert result.port == 2222

    def test_parse_target_without_user(self):
        """Test parsing host-only target."""
        from lurkbot.infra.ssh_tunnel import parse_ssh_target

        result = parse_ssh_target("example.com")
        assert result.user is None
        assert result.host == "example.com"
        assert result.port == 22

    def test_parse_target_host_with_port(self):
        """Test parsing host:port target."""
        from lurkbot.infra.ssh_tunnel import parse_ssh_target

        result = parse_ssh_target("example.com:2222")
        assert result.user is None
        assert result.host == "example.com"
        assert result.port == 2222


class TestSshTunnelManager:
    """Tests for SshTunnelManager class."""

    def test_manager_initialization(self):
        """Test manager initialization."""
        from lurkbot.infra.ssh_tunnel import SshTunnelManager

        manager = SshTunnelManager()
        assert manager._tunnels == {}

    def test_find_available_port(self):
        """Test finding available port."""
        from lurkbot.infra.ssh_tunnel import find_available_port

        port = find_available_port()
        assert isinstance(port, int)
        assert 1024 <= port <= 65535


# =============================================================================
# Bonjour Tests
# =============================================================================


class TestBonjourTypes:
    """Tests for bonjour type definitions."""

    def test_bonjour_service_dataclass(self):
        """Test BonjourService dataclass."""
        from lurkbot.infra.bonjour import BonjourService

        service = BonjourService(
            name="test-service",
            type="_http._tcp",
            port=8080,
        )
        assert service.name == "test-service"
        assert service.type == "_http._tcp"
        assert service.port == 8080
        assert service.txt == {}
        assert service.domain == "local"

    def test_bonjour_browse_result_dataclass(self):
        """Test BonjourBrowseResult dataclass."""
        from lurkbot.infra.bonjour import BonjourBrowseResult, BonjourService

        service = BonjourService(name="test", type="_http._tcp")
        result = BonjourBrowseResult(service=service, event="added")
        assert result.service.name == "test"
        assert result.event == "added"

    def test_bonjour_config_dataclass(self):
        """Test BonjourConfig dataclass."""
        from lurkbot.infra.bonjour import BonjourConfig

        config = BonjourConfig()
        assert config.service_type == "_lurkbot._tcp"
        assert config.browse_timeout_seconds == 10


class TestBonjourAvailability:
    """Tests for bonjour availability."""

    def test_is_bonjour_available(self):
        """Test is_bonjour_available function."""
        from lurkbot.infra.bonjour import is_bonjour_available

        result = is_bonjour_available()
        assert isinstance(result, bool)


class TestBonjourBrowser:
    """Tests for BonjourBrowser class."""

    def test_browser_initialization(self):
        """Test browser initialization."""
        from lurkbot.infra.bonjour import BonjourBrowser, BonjourConfig

        config = BonjourConfig(browse_timeout_seconds=10)
        browser = BonjourBrowser(config)

        assert browser._config.browse_timeout_seconds == 10


class TestBonjourPublisher:
    """Tests for BonjourPublisher class."""

    def test_publisher_initialization(self):
        """Test publisher initialization."""
        from lurkbot.infra.bonjour import BonjourPublisher, BonjourConfig

        config = BonjourConfig(service_name="test-service")
        publisher = BonjourPublisher(config)

        assert publisher._config.service_name == "test-service"


# =============================================================================
# Device Pairing Tests
# =============================================================================


class TestDevicePairingTypes:
    """Tests for device_pairing type definitions."""

    def test_device_pairing_pending_request_dataclass(self):
        """Test DevicePairingPendingRequest dataclass."""
        from lurkbot.infra.device_pairing import DevicePairingPendingRequest

        request = DevicePairingPendingRequest(
            request_id="req1",
            device_id="device1",
            public_key="pubkey123",
            display_name="Test Device",
            ts=1234567890,
        )
        assert request.request_id == "req1"
        assert request.device_id == "device1"
        assert request.public_key == "pubkey123"
        assert request.display_name == "Test Device"
        assert request.ts == 1234567890

    def test_device_auth_token_dataclass(self):
        """Test DeviceAuthToken dataclass."""
        from lurkbot.infra.device_pairing import DeviceAuthToken

        token = DeviceAuthToken(
            token="test-token",
            role="user",
            scopes=["read", "write"],
        )
        assert token.token == "test-token"
        assert token.role == "user"
        assert token.scopes == ["read", "write"]

    def test_paired_device_dataclass(self):
        """Test PairedDevice dataclass."""
        from lurkbot.infra.device_pairing import PairedDevice

        device = PairedDevice(
            device_id="device1",
            public_key="pubkey123",
            display_name="Test Device",
        )
        assert device.device_id == "device1"
        assert device.public_key == "pubkey123"
        assert device.display_name == "Test Device"
        assert device.tokens == {}

    def test_token_verify_params_dataclass(self):
        """Test TokenVerifyParams dataclass."""
        from lurkbot.infra.device_pairing import TokenVerifyParams

        params = TokenVerifyParams(
            device_id="device1",
            token="test-token",
            required_scopes=["read"],
        )
        assert params.device_id == "device1"
        assert params.token == "test-token"
        assert params.required_scopes == ["read"]

    def test_token_verify_result_dataclass(self):
        """Test TokenVerifyResult dataclass."""
        from lurkbot.infra.device_pairing import TokenVerifyResult

        result = TokenVerifyResult(
            valid=True,
        )
        assert result.valid is True
        assert result.device is None
        assert result.error is None


class TestDevicePairingManager:
    """Tests for DevicePairingManager class."""

    def test_manager_initialization(self):
        """Test manager initialization."""
        from lurkbot.infra.device_pairing import DevicePairingManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DevicePairingManager(Path(tmpdir))
            assert manager._devices_dir == Path(tmpdir)

    @pytest.mark.asyncio
    async def test_request_pairing(self):
        """Test requesting device pairing."""
        from lurkbot.infra.device_pairing import DevicePairingManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DevicePairingManager(Path(tmpdir))

            request = await manager.request_pairing(
                "device1",
                "pubkey123",
                display_name="Test Device",
            )
            assert request.device_id == "device1"
            assert request.public_key == "pubkey123"
            assert request.display_name == "Test Device"

    @pytest.mark.asyncio
    async def test_list_pending_requests(self):
        """Test listing pending requests."""
        from lurkbot.infra.device_pairing import DevicePairingManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DevicePairingManager(Path(tmpdir))

            await manager.request_pairing("device1", "pubkey123")
            pending, paired = await manager.list_pairing()

            assert len(pending) == 1
            assert pending[0].device_id == "device1"

    @pytest.mark.asyncio
    async def test_approve_pairing(self):
        """Test approving device pairing."""
        from lurkbot.infra.device_pairing import DevicePairingManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DevicePairingManager(Path(tmpdir))

            request = await manager.request_pairing(
                "device1",
                "pubkey123",
                scopes=["read", "write"],
            )
            device = await manager.approve_pairing(request.request_id)

            assert device is not None
            assert device.device_id == "device1"
            assert "default" in device.tokens

    @pytest.mark.asyncio
    async def test_reject_pairing(self):
        """Test rejecting device pairing."""
        from lurkbot.infra.device_pairing import DevicePairingManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DevicePairingManager(Path(tmpdir))

            request = await manager.request_pairing("device1", "pubkey123")
            result = await manager.reject_pairing(request.request_id)

            assert result is True

            pending, _ = await manager.list_pairing()
            assert len(pending) == 0

    @pytest.mark.asyncio
    async def test_verify_token(self):
        """Test verifying device token."""
        from lurkbot.infra.device_pairing import DevicePairingManager, TokenVerifyParams

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DevicePairingManager(Path(tmpdir))

            request = await manager.request_pairing(
                "device1",
                "pubkey123",
                scopes=["read", "write"],
            )
            device = await manager.approve_pairing(request.request_id)
            token = device.tokens["default"].token

            params = TokenVerifyParams(
                device_id="device1",
                token=token,
                required_scopes=["read"],
            )
            result = await manager.verify_token(params)

            assert result.valid is True
            assert result.device.device_id == "device1"

    @pytest.mark.asyncio
    async def test_verify_invalid_token(self):
        """Test verifying invalid token."""
        from lurkbot.infra.device_pairing import DevicePairingManager, TokenVerifyParams

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DevicePairingManager(Path(tmpdir))

            params = TokenVerifyParams(
                device_id="nonexistent",
                token="invalid-token",
                required_scopes=[],
            )
            result = await manager.verify_token(params)

            assert result.valid is False
            assert result.error is not None


# =============================================================================
# Exec Approvals Tests
# =============================================================================


class TestExecApprovalsTypes:
    """Tests for exec_approvals type definitions."""

    def test_exec_security_enum(self):
        """Test ExecSecurity enum values."""
        from lurkbot.infra.exec_approvals import ExecSecurity

        assert ExecSecurity.DENY.value == "deny"
        assert ExecSecurity.ALLOWLIST.value == "allowlist"
        assert ExecSecurity.FULL.value == "full"

    def test_exec_ask_enum(self):
        """Test ExecAsk enum values."""
        from lurkbot.infra.exec_approvals import ExecAsk

        assert ExecAsk.OFF.value == "off"
        assert ExecAsk.ON_MISS.value == "on-miss"
        assert ExecAsk.ALWAYS.value == "always"

    def test_exec_approvals_defaults_dataclass(self):
        """Test ExecApprovalsDefaults dataclass."""
        from lurkbot.infra.exec_approvals import ExecApprovalsDefaults, ExecSecurity, ExecAsk

        defaults = ExecApprovalsDefaults()
        assert defaults.security == ExecSecurity.DENY
        assert defaults.ask == ExecAsk.ON_MISS
        assert defaults.ask_fallback == ExecSecurity.DENY
        assert defaults.auto_allow_skills is False

    def test_exec_allowlist_entry_dataclass(self):
        """Test ExecAllowlistEntry dataclass."""
        from lurkbot.infra.exec_approvals import ExecAllowlistEntry

        entry = ExecAllowlistEntry(
            pattern="^ls.*",
            id="entry1",
        )
        assert entry.pattern == "^ls.*"
        assert entry.id == "entry1"

    def test_exec_check_result_dataclass(self):
        """Test ExecCheckResult dataclass."""
        from lurkbot.infra.exec_approvals import ExecCheckResult

        result = ExecCheckResult(
            allowed=True,
            reason="allowlist",
            matched_pattern="^ls.*",
        )
        assert result.allowed is True
        assert result.reason == "allowlist"
        assert result.matched_pattern == "^ls.*"


class TestExecApprovalsManager:
    """Tests for ExecApprovalsManager class."""

    def test_manager_initialization(self):
        """Test manager initialization."""
        from lurkbot.infra.exec_approvals import ExecApprovalsManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ExecApprovalsManager(Path(tmpdir) / "exec-approvals.json")
            assert manager._file_path == Path(tmpdir) / "exec-approvals.json"

    @pytest.mark.asyncio
    async def test_load_empty_config(self):
        """Test loading empty config."""
        from lurkbot.infra.exec_approvals import ExecApprovalsManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ExecApprovalsManager(Path(tmpdir) / "exec-approvals.json")
            config = await manager.load()

            assert config.version == 1
            assert config.defaults is not None

    @pytest.mark.asyncio
    async def test_add_to_allowlist(self):
        """Test adding to allowlist."""
        from lurkbot.infra.exec_approvals import ExecApprovalsManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ExecApprovalsManager(Path(tmpdir) / "exec-approvals.json")

            entry = await manager.add_to_allowlist("^ls.*", agent_id="test-agent")
            assert entry.pattern == "^ls.*"

            config = await manager.load()
            assert "test-agent" in config.agents
            assert len(config.agents["test-agent"].allowlist) == 1

    @pytest.mark.asyncio
    async def test_check_allowed_with_allowlist(self):
        """Test checking if command is allowed."""
        from lurkbot.infra.exec_approvals import ExecApprovalsManager, ExecSecurity

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ExecApprovalsManager(Path(tmpdir) / "exec-approvals.json")

            # First set security to allowlist mode
            config = await manager.load()
            config.defaults.security = ExecSecurity.ALLOWLIST
            await manager.save()

            await manager.add_to_allowlist("^ls.*", agent_id="test-agent")
            result = await manager.check("ls -la", agent_id="test-agent")

            assert result.allowed is True
            assert result.reason == "allowlist"

    @pytest.mark.asyncio
    async def test_check_denied_without_allowlist(self):
        """Test checking denied command."""
        from lurkbot.infra.exec_approvals import ExecApprovalsManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ExecApprovalsManager(Path(tmpdir) / "exec-approvals.json")

            result = await manager.check("rm -rf /", agent_id="test-agent")

            assert result.allowed is False

    @pytest.mark.asyncio
    async def test_save_and_load(self):
        """Test saving and loading config."""
        from lurkbot.infra.exec_approvals import ExecApprovalsManager

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "exec-approvals.json"

            # Save
            manager1 = ExecApprovalsManager(file_path)
            await manager1.add_to_allowlist("^ls.*", agent_id="test-agent")

            # Load in new manager
            manager2 = ExecApprovalsManager(file_path)
            config = await manager2.load()

            assert "test-agent" in config.agents

    @pytest.mark.asyncio
    async def test_remove_from_allowlist(self):
        """Test removing from allowlist."""
        from lurkbot.infra.exec_approvals import ExecApprovalsManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ExecApprovalsManager(Path(tmpdir) / "exec-approvals.json")

            await manager.add_to_allowlist("^ls.*", agent_id="test-agent")
            result = await manager.remove_from_allowlist("^ls.*", agent_id="test-agent")

            assert result is True

            entries = await manager.list_allowlist(agent_id="test-agent")
            assert len(entries) == 0


class TestExecApprovalsConvenienceFunctions:
    """Tests for exec_approvals convenience functions."""

    def test_global_manager_instance(self):
        """Test global manager instance exists."""
        from lurkbot.infra.exec_approvals import exec_approvals_manager

        assert exec_approvals_manager is not None


# =============================================================================
# Voice Wake Tests
# =============================================================================


class TestVoiceWakeTypes:
    """Tests for voicewake type definitions."""

    def test_voice_wake_config_dataclass(self):
        """Test VoiceWakeConfig dataclass."""
        from lurkbot.infra.voicewake import VoiceWakeConfig

        config = VoiceWakeConfig(
            triggers=["hey", "hello"],
            updated_at_ms=1234567890,
        )
        assert config.triggers == ["hey", "hello"]
        assert config.updated_at_ms == 1234567890

    def test_default_triggers(self):
        """Test default voice wake triggers."""
        from lurkbot.infra.voicewake import DEFAULT_VOICE_WAKE_TRIGGERS

        assert "lurkbot" in DEFAULT_VOICE_WAKE_TRIGGERS
        assert "claude" in DEFAULT_VOICE_WAKE_TRIGGERS
        assert "computer" in DEFAULT_VOICE_WAKE_TRIGGERS


class TestVoiceWakeManager:
    """Tests for VoiceWakeManager class."""

    def test_manager_initialization(self):
        """Test manager initialization."""
        from lurkbot.infra.voicewake import VoiceWakeManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = VoiceWakeManager(Path(tmpdir) / "voicewake.json")
            assert manager._file_path == Path(tmpdir) / "voicewake.json"

    @pytest.mark.asyncio
    async def test_load_default_config(self):
        """Test loading default config."""
        from lurkbot.infra.voicewake import VoiceWakeManager, DEFAULT_VOICE_WAKE_TRIGGERS

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = VoiceWakeManager(Path(tmpdir) / "voicewake.json")
            config = await manager.load()

            assert config.triggers == list(DEFAULT_VOICE_WAKE_TRIGGERS)

    @pytest.mark.asyncio
    async def test_get_triggers(self):
        """Test getting triggers."""
        from lurkbot.infra.voicewake import VoiceWakeManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = VoiceWakeManager(Path(tmpdir) / "voicewake.json")
            triggers = await manager.get_triggers()

            assert isinstance(triggers, list)
            assert len(triggers) > 0

    @pytest.mark.asyncio
    async def test_set_triggers(self):
        """Test setting triggers."""
        from lurkbot.infra.voicewake import VoiceWakeManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = VoiceWakeManager(Path(tmpdir) / "voicewake.json")

            new_triggers = ["hey", "hello", "hi"]
            result = await manager.set_triggers(new_triggers)

            assert result == new_triggers

    @pytest.mark.asyncio
    async def test_add_trigger(self):
        """Test adding a trigger."""
        from lurkbot.infra.voicewake import VoiceWakeManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = VoiceWakeManager(Path(tmpdir) / "voicewake.json")

            result = await manager.add_trigger("new-trigger")
            assert result is True

            triggers = await manager.get_triggers()
            assert "new-trigger" in triggers

    @pytest.mark.asyncio
    async def test_add_duplicate_trigger(self):
        """Test adding duplicate trigger."""
        from lurkbot.infra.voicewake import VoiceWakeManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = VoiceWakeManager(Path(tmpdir) / "voicewake.json")

            await manager.add_trigger("test-trigger")
            result = await manager.add_trigger("test-trigger")

            assert result is False

    @pytest.mark.asyncio
    async def test_remove_trigger(self):
        """Test removing a trigger."""
        from lurkbot.infra.voicewake import VoiceWakeManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = VoiceWakeManager(Path(tmpdir) / "voicewake.json")

            await manager.add_trigger("to-remove")
            result = await manager.remove_trigger("to-remove")

            assert result is True

            triggers = await manager.get_triggers()
            assert "to-remove" not in triggers

    @pytest.mark.asyncio
    async def test_reset_to_default(self):
        """Test resetting to default triggers."""
        from lurkbot.infra.voicewake import VoiceWakeManager, DEFAULT_VOICE_WAKE_TRIGGERS

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = VoiceWakeManager(Path(tmpdir) / "voicewake.json")

            await manager.set_triggers(["custom1", "custom2"])
            result = await manager.reset_to_default()

            assert result == list(DEFAULT_VOICE_WAKE_TRIGGERS)

    def test_is_trigger(self):
        """Test is_trigger method."""
        from lurkbot.infra.voicewake import VoiceWakeManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = VoiceWakeManager(Path(tmpdir) / "voicewake.json")

            # Uses default triggers without loading
            assert manager.is_trigger("hey lurkbot")
            assert manager.is_trigger("Hello Claude!")
            assert not manager.is_trigger("random text")

    @pytest.mark.asyncio
    async def test_save_and_load(self):
        """Test saving and loading config."""
        from lurkbot.infra.voicewake import VoiceWakeManager

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "voicewake.json"

            # Save
            manager1 = VoiceWakeManager(file_path)
            await manager1.set_triggers(["custom1", "custom2"])

            # Load in new manager
            manager2 = VoiceWakeManager(file_path)
            triggers = await manager2.get_triggers()

            assert triggers == ["custom1", "custom2"]


class TestVoiceWakeConvenienceFunctions:
    """Tests for voicewake convenience functions."""

    def test_global_manager_instance(self):
        """Test global manager instance exists."""
        from lurkbot.infra.voicewake import voice_wake_manager

        assert voice_wake_manager is not None

    @pytest.mark.asyncio
    async def test_get_voice_wake_triggers(self):
        """Test get_voice_wake_triggers function."""
        from lurkbot.infra.voicewake import get_voice_wake_triggers

        triggers = await get_voice_wake_triggers()
        assert isinstance(triggers, list)


# =============================================================================
# Integration Tests
# =============================================================================


class TestInfraModuleExports:
    """Tests for infra module exports."""

    def test_all_exports_available(self):
        """Test that all expected exports are available."""
        from lurkbot import infra

        # System Events
        assert hasattr(infra, "SystemEvent")
        assert hasattr(infra, "SystemEventQueue")
        assert hasattr(infra, "system_event_queue")
        assert hasattr(infra, "enqueue_system_event")

        # System Presence
        assert hasattr(infra, "SystemPresence")
        assert hasattr(infra, "update_system_presence")
        assert hasattr(infra, "list_system_presence")

        # Tailscale
        assert hasattr(infra, "TailscaleClient")
        assert hasattr(infra, "tailscale_client")
        assert hasattr(infra, "is_tailscale_available")

        # SSH Tunnel
        assert hasattr(infra, "SshTunnelManager")
        assert hasattr(infra, "parse_ssh_target")

        # Bonjour
        assert hasattr(infra, "BonjourBrowser")
        assert hasattr(infra, "BonjourPublisher")
        assert hasattr(infra, "is_bonjour_available")

        # Device Pairing
        assert hasattr(infra, "DevicePairingManager")
        assert hasattr(infra, "device_pairing_manager")

        # Exec Approvals
        assert hasattr(infra, "ExecApprovalsManager")
        assert hasattr(infra, "exec_approvals_manager")

        # Voice Wake
        assert hasattr(infra, "VoiceWakeManager")
        assert hasattr(infra, "voice_wake_manager")

    def test_import_all(self):
        """Test importing all from infra module."""
        from lurkbot.infra import (
            # System Events
            SystemEvent,
            SystemEventQueue,
            system_event_queue,
            # System Presence
            SystemPresence,
            update_system_presence,
            # Tailscale
            TailscaleClient,
            tailscale_client,
            # SSH Tunnel
            SshTunnelManager,
            parse_ssh_target,
            # Bonjour
            BonjourBrowser,
            BonjourPublisher,
            # Device Pairing
            DevicePairingManager,
            device_pairing_manager,
            # Exec Approvals
            ExecApprovalsManager,
            exec_approvals_manager,
            # Voice Wake
            VoiceWakeManager,
            voice_wake_manager,
        )

        # All imports should succeed
        assert SystemEvent is not None
        assert SystemEventQueue is not None
        assert system_event_queue is not None
        assert SystemPresence is not None
        assert TailscaleClient is not None
        assert SshTunnelManager is not None
        assert BonjourBrowser is not None
        assert DevicePairingManager is not None
        assert ExecApprovalsManager is not None
        assert VoiceWakeManager is not None
