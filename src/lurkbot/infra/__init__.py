"""Infrastructure utilities.

LurkBot 基础设施模块，包含 8 个核心子系统。

对标 MoltBot `src/infra/`

子模块:
- system_events: 系统事件队列
- system_presence: 系统存在感
- tailscale: Tailscale VPN 集成
- ssh_tunnel: SSH 隧道管理
- bonjour: mDNS 服务发现
- device_pairing: 设备配对
- exec_approvals: 执行审批
- voicewake: 语音唤醒
"""

from lurkbot.infra.system_events import (
    MAX_EVENTS_PER_SESSION,
    SessionQueue,
    SystemEvent,
    SystemEventQueue,
    drain_system_event_entries,
    drain_system_events,
    enqueue_system_event,
    has_system_events,
    is_system_event_context_changed,
    peek_system_events,
    system_event_queue,
)
from lurkbot.infra.system_presence import (
    PRESENCE_TTL_SECONDS,
    MAX_PRESENCE_ENTRIES,
    SystemPresence,
    SystemPresenceUpdate,
    clear_presence_cache,
    get_self_presence,
    list_system_presence,
    register_update_callback,
    update_system_presence,
    upsert_presence,
)
from lurkbot.infra.tailscale import (
    TailscaleClient,
    TailscaleConfig,
    TailscaleNode,
    TailscaleStatus,
    get_tailscale_ip,
    get_tailscale_status,
    is_tailscale_available,
    list_tailscale_peers,
    tailscale_client,
)
from lurkbot.infra.ssh_tunnel import (
    SshParsedTarget,
    SshTunnel,
    SshTunnelConfig,
    SshTunnelManager,
    find_available_port,
    parse_ssh_target,
    start_ssh_port_forward,
)
from lurkbot.infra.bonjour import (
    BonjourBrowseResult,
    BonjourBrowser,
    BonjourConfig,
    BonjourPublisher,
    BonjourService,
    browse_services,
    is_bonjour_available,
    publish_service,
)
from lurkbot.infra.device_pairing import (
    DeviceAuthToken,
    DevicePairingData,
    DevicePairingManager,
    DevicePairingPendingRequest,
    PairedDevice,
    TokenVerifyParams,
    TokenVerifyResult,
    approve_device_pairing,
    device_pairing_manager,
    get_paired_device,
    list_device_pairing,
    reject_device_pairing,
    request_device_pairing,
    verify_device_token,
)
from lurkbot.infra.exec_approvals import (
    ExecAllowlistEntry,
    ExecApprovalsAgent,
    ExecApprovalsDefaults,
    ExecApprovalsFile,
    ExecApprovalsManager,
    ExecApprovalsSocket,
    ExecAsk,
    ExecCheckResult,
    ExecSecurity,
    add_to_allowlist,
    check_exec_allowed,
    exec_approvals_manager,
    load_exec_approvals,
    save_exec_approvals,
)
from lurkbot.infra.voicewake import (
    DEFAULT_VOICE_WAKE_TRIGGERS,
    VoiceWakeConfig,
    VoiceWakeManager,
    get_voice_wake_triggers,
    load_voice_wake_config,
    set_voice_wake_triggers,
    voice_wake_manager,
)

__all__ = [
    # System Events
    "SystemEvent",
    "SessionQueue",
    "SystemEventQueue",
    "MAX_EVENTS_PER_SESSION",
    "system_event_queue",
    "enqueue_system_event",
    "drain_system_event_entries",
    "drain_system_events",
    "peek_system_events",
    "has_system_events",
    "is_system_event_context_changed",
    # System Presence
    "SystemPresence",
    "SystemPresenceUpdate",
    "PRESENCE_TTL_SECONDS",
    "MAX_PRESENCE_ENTRIES",
    "update_system_presence",
    "upsert_presence",
    "list_system_presence",
    "get_self_presence",
    "register_update_callback",
    "clear_presence_cache",
    # Tailscale
    "TailscaleNode",
    "TailscaleStatus",
    "TailscaleConfig",
    "TailscaleClient",
    "tailscale_client",
    "get_tailscale_status",
    "get_tailscale_ip",
    "is_tailscale_available",
    "list_tailscale_peers",
    # SSH Tunnel
    "SshParsedTarget",
    "SshTunnel",
    "SshTunnelConfig",
    "SshTunnelManager",
    "parse_ssh_target",
    "start_ssh_port_forward",
    "find_available_port",
    # Bonjour
    "BonjourService",
    "BonjourBrowseResult",
    "BonjourConfig",
    "BonjourBrowser",
    "BonjourPublisher",
    "browse_services",
    "publish_service",
    "is_bonjour_available",
    # Device Pairing
    "DevicePairingPendingRequest",
    "DeviceAuthToken",
    "PairedDevice",
    "DevicePairingData",
    "TokenVerifyParams",
    "TokenVerifyResult",
    "DevicePairingManager",
    "device_pairing_manager",
    "list_device_pairing",
    "get_paired_device",
    "request_device_pairing",
    "approve_device_pairing",
    "reject_device_pairing",
    "verify_device_token",
    # Exec Approvals
    "ExecSecurity",
    "ExecAsk",
    "ExecApprovalsDefaults",
    "ExecAllowlistEntry",
    "ExecApprovalsAgent",
    "ExecApprovalsSocket",
    "ExecApprovalsFile",
    "ExecCheckResult",
    "ExecApprovalsManager",
    "exec_approvals_manager",
    "load_exec_approvals",
    "save_exec_approvals",
    "check_exec_allowed",
    "add_to_allowlist",
    # Voice Wake
    "VoiceWakeConfig",
    "DEFAULT_VOICE_WAKE_TRIGGERS",
    "VoiceWakeManager",
    "voice_wake_manager",
    "get_voice_wake_triggers",
    "set_voice_wake_triggers",
    "load_voice_wake_config",
]
