TELEMETRY_SCHEMA = {
    "timestamp": "str",
    "location": "str",
    "latency_ms": "float",
    "bandwidth_mbps": "float",
    "packet_loss_pct": "float",
    "cpu_pct": "float",
    "jitter_ms": "float",
    "bgp_events": "int",
    "ospf_events": "int",
    "tunnel_latency_ms": "float",
    "tunnel_packet_loss_pct": "float"
}

SIGNAL_WORKER_OUTPUT = {
    "worker": "str",
    "prediction": "str",
    "confidence": "float",
    "severity": "str",
    "time_to_impact": "str",
    "location": "str"
}

FAILURE_WORKER_OUTPUT = {
    "failure": "str",
    "confidence": "float",
    "time_to_impact": "str",
    "location": "str"
}

CONFIDENCE_GATE_OUTPUT = {
    "passed": "bool",
    "failure": "str",
    "confidence": "float",
    "time_to_impact": "str",
    "location": "str"
}

GRAPH_OUTPUT = {
    "affected_sites": ["str"],
    "affected_apps": ["str"],
    "reroute": "str",
    "impact_score": "float"
}

RAG_OUTPUT = {
    "runbook": "str",
    "sop": "str",
    "incident": "str"
}

CONTEXT_OUTPUT = {
    "failure": "str",
    "confidence": "float",
    "time_to_impact": "str",
    "location": "str",
    "graph": GRAPH_OUTPUT,
    "rag": RAG_OUTPUT
}

LLM_OUTPUT = {
    "explanation": "str",
    "recommended_actions": ["str"],
    "severity": "str"
}

API_RESPONSE = {
    "status": "str",
    "prediction": FAILURE_WORKER_OUTPUT,
    "graph": GRAPH_OUTPUT,
    "rag": RAG_OUTPUT,
    "llm": LLM_OUTPUT,
    "timestamp": "str"
}
