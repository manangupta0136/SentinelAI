# Air-Gapped Predictive Copilot for Secure MPLS Operations

An offline AI-powered NOC Copilot that predicts network failures before they happen.

## Setup

### 1. Install Ollama
```bash
brew install ollama
ollama pull qwen2.5
ollama serve
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the backend (choose one)
```bash
cd backend
python main.py
```
or
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Open the dashboard
```
http://localhost:8000
```

---

## Fault Injection

The dashboard provides 5 fault injection buttons, each simulating a different network issue:

| Button | Backend Fault | Effect |
|---|---|---|
| Inject Congestion | `congestion` | High latency, low bandwidth |
| Inject Tunnel Failure | `tunnel_failure` | Tunnel latency spikes, packet loss |
| Inject CPU Spike | `high_cpu` | CPU utilization > 90% |
| Inject BGP Flap | `bgp_flap` | BGP event storm, routing instability |
| Inject MPLS Failure | `mpls_failure` | Widespread latency + packet loss |

Each fault can be applied to any location (Hub, Branch1-3, Datacenter). Click **Clear All Faults** or a per-location clear button to reset.

---

## Demo Flow

1. Open `http://localhost:8000`
2. Click **Run Prediction** — see healthy network
3. Click **Inject Congestion (Hub)**
4. Click **Run Prediction** again — see failure predicted with explanation
5. Ask Copilot: *"What should I do right now?"*
6. Click **Clear All Faults** — network returns to healthy

---

## Architecture

```
Synthetic Telemetry
  → Signal Workers (Latency, Bandwidth, CPU, PacketLoss, Jitter, Routing, Tunnel)
  → Failure Workers (Congestion, Routing, Tunnel, Device)
  → Confidence Gate (filters < 70% confidence)
  → Graph Engine (affected sites, apps, rerouting)
  → RAG (runbooks, SOPs, historical incidents)
  → Context Builder (assembles one JSON)
  → Ollama LLM (explains in natural language)
  → FastAPI → Frontend Dashboard
```

## Project Structure

```
backend/
  main.py                  — FastAPI app
  supervisor/              — Pipeline orchestrator + confidence gate
  workers/                 — Signal workers (one per metric)
  failure_workers/         — Failure detection workers
  graph/graph.py           — Network topology + impact analysis
  rag/rag.py               — RAG knowledge base
  context_builder/         — Context assembly for LLM
  llm/inference.py         — Ollama LLM client
  telemetry/synthetic.py   — Synthetic telemetry generator
  database/db.py           — SQLite logging

frontend/
  templates/index.html     — Dashboard
  static/css/style.css     — Dark theme
  static/js/app.js         — Dashboard logic

data/
  topology/topology.json   — Network topology
  runbooks/                — MPLS, Tunnel, BGP, CPU runbooks
  sops/                    — Escalation matrix, packet loss SOP
  incidents/               — Historical incidents
```
