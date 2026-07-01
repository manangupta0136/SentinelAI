"""
Database — SQLite
-----------------
Logs all predictions, fault injections, and chat queries.
SQLite instead of PostgreSQL — simpler setup, same functionality for demo.
"""

import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "noc_copilot.db"
)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            failure TEXT,
            confidence REAL,
            time_to_impact TEXT,
            location TEXT,
            affected_sites TEXT,
            affected_apps TEXT,
            reroute TEXT,
            llm_explanation TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS fault_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            fault_type TEXT,
            location TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            question TEXT,
            answer TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS worker_outputs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            location TEXT,
            outputs TEXT
        )
    """)

    conn.commit()
    conn.close()
    print(f"[DB] Initialized at {DB_PATH}")


def log_prediction(prediction: dict, graph: dict, llm: dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO predictions
        (timestamp, failure, confidence, time_to_impact, location, affected_sites, affected_apps, reroute, llm_explanation)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.utcnow().isoformat(),
        prediction.get("failure"),
        prediction.get("confidence"),
        prediction.get("time_to_impact"),
        prediction.get("location"),
        json.dumps(graph.get("affected_sites", [])),
        json.dumps(graph.get("affected_apps", [])),
        graph.get("reroute"),
        llm.get("explanation"),
    ))
    conn.commit()
    conn.close()


def log_fault(fault_type: str, location: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO fault_logs (timestamp, fault_type, location) VALUES (?, ?, ?)",
        (datetime.utcnow().isoformat(), fault_type, location)
    )
    conn.commit()
    conn.close()


def log_chat(question: str, answer: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO chat_logs (timestamp, question, answer) VALUES (?, ?, ?)",
        (datetime.utcnow().isoformat(), question, answer)
    )
    conn.commit()
    conn.close()


def get_recent_predictions(limit: int = 20) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM predictions ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows


if __name__ == "__main__":
    init_db()
    print("DB ready.")