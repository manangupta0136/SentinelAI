"""
Supervisor
----------
Orchestrates the entire prediction pipeline.
Does NOT perform any prediction itself.

Flow:
  telemetry → signal workers → failure workers → confidence gate → output
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workers import (
    LatencyWorker, BandwidthWorker, CPUWorker,
    PacketLossWorker, JitterWorker, RoutingWorker, TunnelWorker
)
from failure_workers import (
    CongestionWorker, RoutingFailureWorker,
    TunnelFailureWorker, DeviceFailureWorker
)
from supervisor.confidence_gate import pick_highest


_signal_workers = [
    LatencyWorker(),
    BandwidthWorker(),
    CPUWorker(),
    PacketLossWorker(),
    JitterWorker(),
    RoutingWorker(),
    TunnelWorker(),
]

_failure_workers = [
    CongestionWorker(),
    RoutingFailureWorker(),
    TunnelFailureWorker(),
    DeviceFailureWorker(),
]


def run_pipeline(telemetry: dict) -> dict:
    """
    Run the full signal → failure → gate pipeline for one telemetry snapshot.
    Returns the gated failure prediction + all signal worker outputs.
    """
    signal_outputs = [w.run(telemetry) for w in _signal_workers]
    failure_outputs = [w.run(signal_outputs) for w in _failure_workers]
    gated = pick_highest(failure_outputs)

    return {
        "signal_outputs": signal_outputs,
        "failure_outputs": failure_outputs,
        "gated": gated,
    }


if __name__ == "__main__":
    from telemetry.synthetic import generate_telemetry, inject_fault

    inject_fault("congestion", "Hub")
    telemetry = generate_telemetry("Hub")
    print("Telemetry:", telemetry)
    print()

    result = run_pipeline(telemetry)
    print("Signal Workers:")
    for s in result["signal_outputs"]:
        print(f"  {s['worker']}: {s['prediction']} ({s['confidence']}%)")

    print()
    print("Gated Failure:", result["gated"])