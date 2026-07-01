import random
import time
from datetime import datetime


LOCATIONS = ["Hub", "Branch1", "Branch2", "Branch3", "Datacenter"]

BASELINES = {
    "latency_ms": (10, 30),
    "bandwidth_mbps": (60, 90),
    "packet_loss_pct": (0.0, 0.5),
    "cpu_pct": (20, 50),
    "jitter_ms": (1, 5),
    "bgp_events": (0, 1),
    "ospf_events": (0, 1),
    "tunnel_latency_ms": (12, 35),
    "tunnel_packet_loss_pct": (0.0, 0.5),
}

FAULT_PROFILES = {
    "congestion": {
        "latency_ms": (80, 200),
        "bandwidth_mbps": (5, 20),
        "packet_loss_pct": (3.0, 10.0),
        "jitter_ms": (20, 60),
    },
    "tunnel_failure": {
        "tunnel_latency_ms": (200, 500),
        "tunnel_packet_loss_pct": (10.0, 30.0),
    },
    "high_cpu": {
        "cpu_pct": (85, 99),
    },
    "bgp_flap": {
        "bgp_events": (10, 30),
        "latency_ms": (50, 120),
    },
    "mpls_failure": {
        "latency_ms": (300, 999),
        "packet_loss_pct": (20.0, 60.0),
        "bandwidth_mbps": (0, 5),
    },
}

# Active faults — can be set externally via fault injector
active_faults = {}


def inject_fault(fault_type: str, location: str):
    active_faults[location] = fault_type


def clear_fault(location: str):
    active_faults.pop(location, None)


def generate_telemetry(location: str = None) -> dict:
    if location is None:
        location = random.choice(LOCATIONS)

    telemetry = {
        "timestamp": datetime.utcnow().isoformat(),
        "location": location,
    }

    fault = active_faults.get(location)

    for metric, (low, high) in BASELINES.items():
        if fault and metric in FAULT_PROFILES.get(fault, {}):
            f_low, f_high = FAULT_PROFILES[fault][metric]
            telemetry[metric] = round(random.uniform(f_low, f_high), 2)
        else:
            telemetry[metric] = round(random.uniform(low, high), 2)

    return telemetry


def generate_all_locations() -> list:
    return [generate_telemetry(loc) for loc in LOCATIONS]


def generate_history(location: str, steps: int = 20) -> list:
    history = []
    for i in range(steps):
        snap = generate_telemetry(location)
        history.append(snap)
    return history


if __name__ == "__main__":
    snap = generate_telemetry("Hub")
    print(snap)