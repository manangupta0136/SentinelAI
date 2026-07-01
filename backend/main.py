"""
FastAPI — Main Application
--------------------------
All routes. No business logic inside routes — each route calls one module.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime
import json

from supervisor.supervisor import run_pipeline
from graph.graph import GraphEngine
from rag.rag import get_rag_engine
from context_builder.builder import build_context
from llm.inference import query_llm, query_chat
from telemetry.synthetic import generate_all_locations, inject_fault, clear_fault, active_faults
from database.db import init_db, log_prediction, log_fault, log_chat, get_recent_predictions

app = FastAPI(title="Air-Gapped NOC Copilot", version="1.0.0")

init_db()
graph_engine = GraphEngine()
rag_engine = get_rag_engine()

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "static")), name="static")


class ChatRequest(BaseModel):
    question: str

class FaultRequest(BaseModel):
    fault_type: str
    location: str

class ClearFaultRequest(BaseModel):
    location: str


@app.get("/")
def serve_dashboard():
    index_path = os.path.join(FRONTEND_DIR, "templates", "index.html")
    with open(index_path, "r") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/status")
def status():
    return {
        "status": "online",
        "timestamp": datetime.utcnow().isoformat(),
        "active_faults": dict(active_faults),
        "rag_ready": rag_engine._ingested,
    }


@app.get("/api/telemetry")
def get_telemetry():
    """Return current telemetry for all locations."""
    snapshots = generate_all_locations()
    return {"telemetry": snapshots, "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/predict")
def predict():
    """
    Run the full prediction pipeline across all locations.
    Returns the highest-confidence failure prediction.
    """
    all_results = []

    for snapshot in generate_all_locations():
        result = run_pipeline(snapshot)
        gated = result["gated"]

        if gated["passed"]:
            graph_out = graph_engine.analyze(gated)
            rag_out   = rag_engine.retrieve(gated["failure"])
            context   = build_context(gated, graph_out, rag_out)
            llm_out   = query_llm(context)

            log_prediction(gated, graph_out, llm_out)

            all_results.append({
                "failure":         gated["failure"],
                "confidence":      gated["confidence"],
                "time_to_impact":  gated["time_to_impact"],
                "location":        gated["location"],
                "graph":           graph_out,
                "llm":             llm_out,
                "signal_outputs":  result["signal_outputs"],
                "timestamp":       datetime.utcnow().isoformat(),
            })

    if not all_results:
        return {"status": "healthy", "predictions": [], "timestamp": datetime.utcnow().isoformat()}

    all_results.sort(key=lambda x: x["confidence"], reverse=True)
    return {"status": "alert", "predictions": all_results, "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/chat")
def chat(req: ChatRequest):
    """Copilot chat — answer an operator's question."""
    snapshots = generate_all_locations()
    best_context = {"failure": "None", "location": "Unknown", "graph": {}}

    for snapshot in snapshots:
        result = run_pipeline(snapshot)
        if result["gated"]["passed"]:
            graph_out = graph_engine.analyze(result["gated"])
            best_context = build_context(result["gated"], graph_out, {})
            break

    answer = query_chat(req.question, best_context)
    log_chat(req.question, answer)
    return {"question": req.question, "answer": answer, "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/inject_fault")
def inject_fault_route(req: FaultRequest):
    """Inject a fault for demo purposes."""
    inject_fault(req.fault_type, req.location)
    log_fault(req.fault_type, req.location)
    return {
        "status": "injected",
        "fault_type": req.fault_type,
        "location": req.location,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/api/clear_fault")
def clear_fault_route(req: ClearFaultRequest):
    """Clear an active fault."""
    clear_fault(req.location)
    return {"status": "cleared", "location": req.location}


@app.get("/api/graph")
def get_graph():
    """Return the network topology for visualization."""
    import json
    topo_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "topology", "topology.json"
    )
    with open(topo_path, "r") as f:
        topology = json.load(f)
    return topology


@app.get("/api/history")
def get_history():
    """Return recent prediction history."""
    return {"predictions": get_recent_predictions(20)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)