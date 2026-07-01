"""
Latency Signal Worker
---------------------
Input  : telemetry snapshot (dict)
Output : SIGNAL_WORKER_OUTPUT (dict)

Rule-based logic for now.
Replace predict() internals with Prophet/XGBoost later.
"""


class LatencyWorker:

    THRESHOLDS = {
        "low":      30,
        "medium":   60,
        "high":     100,
        "critical": 200,
    }

    def preprocess(self, telemetry: dict) -> dict:
        return {
            "latency_ms": telemetry.get("latency_ms", 0),
            "jitter_ms": telemetry.get("jitter_ms", 0),
            "location": telemetry.get("location", "Unknown"),
        }

    def predict(self, data: dict) -> dict:
        latency = data["latency_ms"]
        jitter = data["jitter_ms"]

        if latency >= self.THRESHOLDS["critical"]:
            prediction = "Critical Latency Spike"
            confidence = 95.0
            severity = "Critical"
            time_to_impact = "Now"
        elif latency >= self.THRESHOLDS["high"]:
            prediction = "Latency Drift — High"
            confidence = 88.0
            severity = "High"
            time_to_impact = "5 min"
        elif latency >= self.THRESHOLDS["medium"]:
            prediction = "Latency Drift — Medium"
            confidence = 75.0
            severity = "Medium"
            time_to_impact = "15 min"
        elif latency >= self.THRESHOLDS["low"]:
            prediction = "Latency Drift — Low"
            confidence = 60.0
            severity = "Low"
            time_to_impact = "30 min"
        else:
            prediction = "Normal"
            confidence = 99.0
            severity = "None"
            time_to_impact = "N/A"

        # Jitter amplifies severity
        if jitter > 20 and severity not in ("Critical", "None"):
            confidence = min(confidence + 5, 99)

        return {
            "worker": "Latency",
            "prediction": prediction,
            "confidence": confidence,
            "severity": severity,
            "time_to_impact": time_to_impact,
            "location": data["location"],
        }

    def postprocess(self, result: dict) -> dict:
        result["confidence"] = round(result["confidence"], 1)
        return result

    def run(self, telemetry: dict) -> dict:
        data = self.preprocess(telemetry)
        result = self.predict(data)
        return self.postprocess(result)


if __name__ == "__main__":
    sample = {"latency_ms": 95, "jitter_ms": 25, "location": "Hub"}
    worker = LatencyWorker()
    print(worker.run(sample))