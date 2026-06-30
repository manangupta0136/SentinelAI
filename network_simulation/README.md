# SentinelAI Network Simulation & Fault Injection Engine

An air-gapped predictive copilot for secure MPLS operations — this module
generates **realistic synthetic network telemetry** and **labeled fault scenarios**
via Monte Carlo simulation. It does **not** perform prediction, ML inference,
RAG, or LLM work.

## Quick Start

```bash
pip install -r requirements.txt
python main.py --visualize
```

Output files land in `output/`:
- `telemetry.csv` / `telemetry.json` — tick-by-tick device, link, and tunnel metrics
- `ground_truth.csv` — every injected fault labelled with type, device, severity, timing, and impact
- `fault_events.json` — full fault event log
- `simulation_summary.json` — run statistics
- `metadata.json` — simulation parameters and topology snapshot
- `topology.png` — network graph visualization (with `--visualize`)
- `telemetry_dashboard.png` — multi-panel metric plots
- `fault_timeline.png` — Gantt chart of fault events over time

## Project Structure

```
network_simulation/
├── main.py                         # CLI entry point
├── config/                         # YAML config (no hardcoded values in code)
│   ├── network.yaml                # Devices, links, tunnels, correlation coefficients
│   ├── simulation.yaml             # Tick count, interval, seed, logging
│   ├── traffic.yaml                # Application profiles, time-of-day curves
│   └── faults.yaml                 # Monte Carlo distributions, fault parameters
├── topology/                       # Network representation (NetworkX DiGraph)
│   ├── devices.py                  # Device dataclass with correlated metrics
│   ├── links.py                    # Link & Tunnel dataclasses
│   ├── network_builder.py          # Builds graph from config
│   ├── routing.py                  # Shortest-path routing engine
│   └── qos.py                      # QoS profiles and bandwidth guarantees
├── traffic/                        # Enterprise traffic simulation
│   ├── application_profiles.py     # App definitions (ERP, DB, Video, Web, Sync)
│   ├── bandwidth_model.py          # Time-of-day + burst demand calculation
│   └── traffic_generator.py        # Updates device/link metrics each tick
├── telemetry/                      # Telemetry collection and export
│   ├── metrics.py                  # TelemetryRecord / TelemetryFrame
│   ├── collector.py                # Reads topology state into records
│   ├── exporters.py                # CSV + JSON export
│   └── timestamp.py                # UTC ISO 8601 timestamps
├── monte_carlo/                    # Stochastic fault engine
│   ├── random_seed.py              # Reproducible NumPy Generator
│   ├── distributions.py            # Beta, Normal, Lognormal, Uniform, etc.
│   ├── scheduler.py                # Decides when/what faults occur
│   └── simulator.py                # Tick loop orchestrator
├── fault_injection/                # 10 fault types (apply/recover/serialize)
│   ├── injector.py                 # Abstract base class
│   ├── congestion.py               # Progressive link congestion
│   ├── bgp_flap.py                 # BGP route flapping
│   ├── ospf_failure.py             # OSPF LSA / adjacency instability
│   ├── tunnel_failure.py           # IPSec/GRE tunnel degradation
│   ├── mpls_failure.py             # MPLS LSP degradation
│   ├── controller_error.py         # SDN controller misconfiguration
│   ├── cpu_overload.py             # CPU spike (with correlated metrics)
│   ├── memory_exhaustion.py        # Memory leak (with correlated metrics)
│   ├── packet_loss_escalation.py   # Escalating interface loss
│   └── recovery.py                 # Post-fault recovery actions
├── labeling/                       # Ground truth and dataset assembly
│   ├── ground_truth.py             # Label dataclass
│   ├── event_logger.py             # Tracks fault start/end → labels
│   └── dataset_builder.py          # Joins telemetry + labels
├── visualization/                  # Matplotlib-based plotting
│   ├── topology_plot.py            # Network graph
│   ├── telemetry_dashboard.py      # Multi-panel metric plots
│   └── fault_timeline.py           # Gantt chart
├── utils/                          # Shared utilities
│   ├── constants.py                # True invariants only
│   ├── helpers.py                  # Config loading, math, time helpers
│   └── logger.py                   # Structured logging (console + file)
├── tests/                          # pytest suite (mirrors source structure)
│   ├── conftest.py                 # Fixtures (small topology, fixed seed)
│   ├── test_topology.py
│   ├── test_traffic.py
│   ├── test_telemetry.py
│   ├── test_monte_carlo.py
│   ├── test_fault_injection.py
│   ├── test_labeling.py
│   ├── test_utils.py
│   ├── test_visualization.py
│   └── test_integration.py
└── output/                         # Generated datasets (gitignored)
```

## Architecture

```
Config (YAML)
    ↓
NetworkBuilder → NetworkX DiGraph (Devices + Links + Tunnels)
    ↓
TrafficGenerator ← BandwidthModel ← ApplicationProfiles  (every tick)
    ↓
MonteCarloSimulator (tick loop)
    ├── FaultScheduler → decides if/when a fault occurs
    ├── FaultInjector.apply()  → modifies topology state
    ├── TelemetryCollector     → reads state → TelemetryRecords
    ├── EventLogger            → creates GroundTruthLabels
    └── TelemetryExporter      → CSV + JSON output
```

### Metric Correlations

The `Device.update_correlated_metrics()` method implements explicit,
configurable correlation functions so labels remain explainable:

- **cpu_temperature** = `cpu_temp_alpha * cpu_utilization + 45.0`
- **interrupt_rate**   = `base_interrupt_rate + interrupt_beta * interface_packet_rate`
- **memory_utilization** = `base_memory + gamma_process * (process_count - base_process_count) + gamma_cpu * (cpu - base_cpu)`

All coefficients are defined in `config/network.yaml` per device, not
hardcoded.

## Running Tests

```bash
pytest tests/ -v --cov=network_simulation
```

## Design Decisions & Assumptions

1. **No real-time clock dependency.** Simulation time is synthetic and
   derived from tick count × tick interval.
2. **NetworkX DiGraph** is used because routing is directional (forwarding
   paths matter).
3. **Fault injectors use dependency injection** — they receive the
   NetworkBuilder and RoutingEngine rather than reaching into globals.
4. **Faults do not nest.** If a fault is already active on a link, a
   second fault on the same link overwrites rather than stacks.
5. **Traffic generation is causal.** A single `TrafficGenerator.update()`
   call produces all device/link state changes, keeping the mapping from
   traffic volume to telemetry traceable.
6. **All distributions are parameterized in YAML.** Adding a new
   distribution type requires code in `distributions.py`; parameters
   never appear as magic numbers in source.
7. **Weekend traffic is a global multiplier.** Per-app weekend profiles
   are not supported; the global `weekend_multiplier` is applied after
   the time-of-day interpolation.
