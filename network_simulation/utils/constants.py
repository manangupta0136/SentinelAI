"""True constants for the simulation framework.

This module contains only immutable constants such as unit conversion
factors and enum-like string constants. All tunable parameters belong
in YAML configuration files, not here.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationConstants:
    """System-wide constants that never change between simulation runs."""

    BITS_PER_BYTE: int = 8
    BYTES_PER_KILOBYTE: int = 1024
    KILOBYTES_PER_MEGABYTE: int = 1024
    SECONDS_PER_MINUTE: int = 60
    MINUTES_PER_HOUR: int = 60
    HOURS_PER_DAY: int = 24
    SECONDS_PER_HOUR: int = 3600
    MICROSECONDS_PER_MILLISECOND: int = 1000
    MILLISECONDS_PER_SECOND: int = 1000
    MAX_QUEUE_DEPTH_PACKETS: int = 1024
    DEFAULT_MTU_BYTES: int = 1500


class LinkStatus:
    """Link status string constants."""

    UP: str = "UP"
    DEGRADED: str = "DEGRADED"
    DOWN: str = "DOWN"


class DeviceRole:
    """Device role string constants."""

    DATACENTER: str = "datacenter"
    MPLS_HUB: str = "mpls_hub"
    BRANCH: str = "branch"


class FaultType:
    """Fault type string constants matching config keys."""

    CONGESTION: str = "congestion"
    BGP_FLAP: str = "bgp_flap"
    OSPF_FAILURE: str = "ospf_failure"
    TUNNEL_FAILURE: str = "tunnel_failure"
    MPLS_FAILURE: str = "mpls_failure"
    LINK_FAILURE: str = "link_failure"
    CONTROLLER_ERROR: str = "controller_error"
    CPU_OVERLOAD: str = "cpu_overload"
    MEMORY_EXHAUSTION: str = "memory_exhaustion"
    PACKET_LOSS_ESCALATION: str = "packet_loss_escalation"


class RecoveryMethod:
    """Recovery method string constants."""

    AUTOMATIC: str = "automatic"
    MANUAL: str = "manual"
    AUTOMATIC_LSP_REROUTE: str = "automatic_lsp_reroute"
    MANUAL_TRAFFIC_ENGINEERING: str = "manual_traffic_engineering"
    MANUAL_ROUTE_POLICY_CHANGE: str = "manual_route_policy_change"
    MANUAL_INTERFACE_RESET: str = "manual_interface_reset"
    MANUAL_TUNNEL_REKEY: str = "manual_tunnel_rekey"
    MANUAL_REPAIR: str = "manual_repair"
    REDUNDANT_PATH_SWITCH: str = "redundant_path_switch"
    AUTOMATIC_RESTORATION: str = "automatic_restoration"
    AUTOMATIC_ROLLBACK: str = "automatic_rollback"
    MANUAL_CONFIG_PUSH: str = "manual_config_push"
    AUTOMATIC_PROCESS_TERMINATION: str = "automatic_process_termination"
    MANUAL_RELOAD: str = "manual_reload"
    AUTOMATIC_GC: str = "automatic_gc"
    MANUAL_INTERFACE_CLEAN: str = "manual_interface_clean"
