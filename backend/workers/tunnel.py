"""
Tunnel Health Signal Worker
---------------------------
Monitors IPSec tunnel latency and packet loss.
Input  : telemetry snapshot (dict)
Output : SIGNAL_WORKER_OUTPUT (dict)
"""


class TunnelWorker:

    def preprocess(self, telemetry: dict) -> dict:
        return {
            "tunnel_latency_ms": telemetry.get("tunnel_latency_ms", 0),
            "tunnel_packet_loss_pct": telemetry.get("tunnel_packet_loss_pct", 0),
            "location": telemetry.get("location", "Unknown"),
        }

    def predict(self, data: dict) -> dict:
        t_latency = data["tunnel_latency_ms"]
        t_loss = data["tunnel_packet_loss_pct"]

        if t_latency >= 400 or t_loss >= 20:
            prediction = "Tunnel Failure Imminent"
            confidence = 95.0
            severity = "Critical"
            time_to_impact = "Now"
        elif t_latency >= 200 or t_loss >= 10:
            prediction = "Tunnel Degradation — High"
            confidence = 87.0
            severity = "High"
            time_to_impact = "8 min"
        elif t_latency >= 100 or t_loss >= 3:
            prediction = "Tunnel Quality Degrading"
            confidence = 73.0
            severity = "Medium"
            time_to_impact = "18 min"
        elif t_latency >= 50 or t_loss >= 1:
            prediction = "Tunnel Quality Low"
            confidence = 58.0
            severity = "Low"
            time_to_impact = "35 min"
        else:
            prediction = "Normal"
            confidence = 99.0
            severity = "None"
            time_to_impact = "N/A"

        return {
            "worker": "Tunnel",
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
    sample = {"tunnel_latency_ms": 250, "tunnel_packet_loss_pct": 12, "location": "Branch1"}
    worker = TunnelWorker()
    print(worker.run(sample))