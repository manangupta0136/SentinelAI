const metricColors = {
  latency: "#155f96",
  jitter: "#6554b8",
  packet_loss: "#c93636",
  bandwidth: "#17855d",
  cpu: "#b36b00",
  memory: "#4d7884",
  route_flaps: "#b0447a",
  tunnel_loss: "#d2632a",
};

const metricOrder = ["latency", "jitter", "packet_loss", "bandwidth", "cpu", "memory", "route_flaps", "tunnel_loss"];

const telemetryKeys = {
  latency: "latency_ms",
  jitter: "jitter_ms",
  packet_loss: "packet_loss_pct",
  bandwidth: "bandwidth_mbps",
  cpu: "cpu_pct",
  memory: "memory_pct",
  route_flaps: "bgp_events",
  tunnel_loss: "tunnel_packet_loss_pct",
};

const metricLimits = {
  latency: { label: "Latency", unit: "ms", limit: 200 },
  jitter: { label: "Jitter", unit: "ms", limit: 50 },
  packet_loss: { label: "Packet loss", unit: "%", limit: 20 },
  bandwidth: { label: "Bandwidth", unit: "Mbps", limit: 100 },
  cpu: { label: "CPU", unit: "%", limit: 100 },
  memory: { label: "Memory", unit: "%", limit: 100 },
  route_flaps: { label: "Route flaps", unit: "", limit: 30 },
  tunnel_loss: { label: "Tunnel loss", unit: "%", limit: 30 },
};

const scenarioMap = {
  "progressive_congestion": { fault_type: "congestion", location: "Hub" },
  "bgp_flap": { fault_type: "bgp_flap", location: "Hub" },
  "tunnel_degradation": { fault_type: "tunnel_failure", location: "Branch1" },
  "high_cpu": { fault_type: "high_cpu", location: "Hub" },
  "mpls_failure": { fault_type: "mpls_failure", location: "Hub" },
};

const nodePositions = {
  "Datacenter": { x: 50, y: 15 },
  "Hub": { x: 50, y: 40 },
  "Branch1": { x: 18, y: 76 },
  "Branch2": { x: 50, y: 82 },
  "Branch3": { x: 82, y: 76 },
};

let dashboardData = null;
let topologyFrame = null;
let seriesBuffer = {};

const $ = (id) => document.getElementById(id);

function fitCanvas(canvas) {
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.max(320, Math.floor(rect.width * ratio));
  canvas.height = Math.max(220, Math.floor(rect.height * ratio));
  const ctx = canvas.getContext("2d");
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  return { ctx, width: rect.width, height: rect.height };
}

function setClock(timestamp) {
  const time = new Date(timestamp * 1000);
  $("clock").textContent = time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function severityColor(severity) {
  if (severity === "high" || severity === "critical") return "#c93636";
  if (severity === "medium") return "#b36b00";
  return "#17855d";
}

function renderSummary(data) {
  $("systemState").textContent = data.system.air_gap;
  $("scenarioName").textContent = data.system.scenario_name;
  $("riskConfidence").textContent = `${data.risk.confidence}%`;
  $("riskRoot").textContent = data.risk.root;
  $("riskImpact").textContent = data.risk.impact;
  $("timeImpact").textContent = data.risk.time_to_impact;
  $("severity").textContent = data.risk.severity.toUpperCase();
  $("severity").style.color = severityColor(data.risk.severity);
  $("recommendation").textContent = data.risk.recommendation;
  setClock(data.system.updated_at);
}

function renderWorkers(workers) {
  $("workerList").innerHTML = workers.map((worker) => `
    <div class="worker-row ${worker.status === "active" ? "active" : ""}">
      <div>
        <strong>${worker.name}</strong>
        <span>${worker.signal}</span>
      </div>
      <strong>${worker.confidence}%</strong>
    </div>
  `).join("");
}

function renderMetrics(metrics) {
  $("metricTable").innerHTML = metricOrder.map((key) => {
    if (!metrics[key]) return "";
    const metric = metrics[key];
    const level = Math.min(100, Math.round((metric.value / metric.limit) * 100));
    return `
      <div class="metric-row">
        <div>
          <strong>${metric.label}</strong>
          <span>${level}% of watch limit</span>
        </div>
        <strong>${metric.value}${metric.unit}</strong>
        <div class="metric-bar"><i style="width:${level}%; background:${metricColors[key]}"></i></div>
      </div>
    `;
  }).join("");
}

function renderImpact(data) {
  const affected = data.risk.affected && data.risk.affected.length ? data.risk.affected : ["No impacted sites"];
  $("affectedList").innerHTML = affected.map((item) => `<span>${item}</span>`).join("");
  $("incidentList").innerHTML = data.incidents.map((incident) => `
    <div class="incident-card">
      <span>${incident.id}</span>
      <strong>${incident.title}</strong>
      <span>${incident.result}</span>
    </div>
  `).join("");
}

function renderLegend(metrics) {
  $("chartLegend").innerHTML = metricOrder.map((key) => {
    if (!metrics[key]) return "";
    return `<span><i style="background:${metricColors[key]}"></i>${metrics[key].label}</span>`;
  }).join("");
}

function drawMetricsChart(data) {
  const canvas = $("metricsCanvas");
  const { ctx, width, height } = fitCanvas(canvas);
  const pad = { left: 44, right: 22, top: 18, bottom: 34 };
  const chartW = width - pad.left - pad.right;
  const chartH = height - pad.top - pad.bottom;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fbfdfd";
  ctx.fillRect(0, 0, width, height);

  const dangerY = pad.top + chartH * 0.25;
  ctx.fillStyle = "rgba(201, 54, 54, 0.07)";
  ctx.fillRect(pad.left, pad.top, chartW, dangerY - pad.top);

  ctx.strokeStyle = "rgba(16, 33, 42, 0.12)";
  ctx.lineWidth = 1;
  ctx.fillStyle = "#657782";
  ctx.font = "12px Inter, system-ui";

  for (let i = 0; i <= 4; i += 1) {
    const y = pad.top + (chartH * i) / 4;
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(width - pad.right, y);
    ctx.stroke();
    ctx.fillText(`${100 - i * 25}%`, 7, y + 4);
  }

  const forecastX = pad.left + chartW * 0.68;
  ctx.setLineDash([5, 7]);
  ctx.strokeStyle = "rgba(15, 139, 154, 0.42)";
  ctx.beginPath();
  ctx.moveTo(forecastX, pad.top);
  ctx.lineTo(forecastX, height - pad.bottom);
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle = "#0f8b9a";
  ctx.fillText("forecast", forecastX + 8, pad.top + 14);

  metricOrder.forEach((key) => {
    const values = data.series && data.series[key];
    if (!values || values.length < 2) return;
    const limit = data.metrics && data.metrics[key] ? data.metrics[key].limit : 100;
    ctx.beginPath();
    values.forEach((value, index) => {
      const x = pad.left + (index / (values.length - 1)) * chartW;
      const y = pad.top + chartH - (Math.min(value / limit, 1) * chartH);
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = metricColors[key];
    ctx.lineWidth = key === "latency" || key === "bandwidth" || key === "packet_loss" ? 2.8 : 1.7;
    ctx.globalAlpha = key === "memory" || key === "route_flaps" ? 0.78 : 1;
    ctx.stroke();
    ctx.globalAlpha = 1;
  });

  ctx.fillStyle = "#657782";
  ctx.fillText("-48m", pad.left - 6, height - 11);
  ctx.fillText("now", width - pad.right - 24, height - 11);
}

function roundedRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function curvePoint(a, b, curve, t) {
  const mx = (a.x + b.x) / 2;
  const my = (a.y + b.y) / 2;
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const len = Math.max(1, Math.hypot(dx, dy));
  const cx = mx - (dy / len) * curve;
  const cy = my + (dx / len) * curve;
  const x = (1 - t) * (1 - t) * a.x + 2 * (1 - t) * t * cx + t * t * b.x;
  const y = (1 - t) * (1 - t) * a.y + 2 * (1 - t) * t * cy + t * t * b.y;
  return { x, y, cx, cy };
}

function drawTopologyBackground(ctx, width, height) {
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fbfdfd";
  ctx.fillRect(0, 0, width, height);

  ctx.fillStyle = "rgba(21, 95, 150, 0.045)";
  roundedRect(ctx, 18, 18, width - 36, height * 0.36, 8);
  ctx.fill();
  ctx.fillStyle = "rgba(23, 133, 93, 0.045)";
  roundedRect(ctx, 18, height * 0.48, width - 36, height * 0.38, 8);
  ctx.fill();

  ctx.strokeStyle = "rgba(15, 139, 154, 0.12)";
  ctx.lineWidth = 1;
  for (let x = 28; x < width; x += 34) {
    ctx.beginPath();
    ctx.moveTo(x, 20);
    ctx.lineTo(x, height - 20);
    ctx.stroke();
  }
  for (let y = 26; y < height; y += 34) {
    ctx.beginPath();
    ctx.moveTo(20, y);
    ctx.lineTo(width - 20, y);
    ctx.stroke();
  }
}

function drawCurvedEdge(ctx, a, b, edge, phase) {
  const curve = edge.label === "backup" || edge.label === "SD-WAN" ? -34 : 28;
  const mid = curvePoint(a, b, curve, 0.5);
  const risk = edge.status === "risk";

  ctx.beginPath();
  ctx.moveTo(a.x, a.y);
  ctx.quadraticCurveTo(mid.cx, mid.cy, b.x, b.y);
  ctx.strokeStyle = risk ? "rgba(201, 54, 54, 0.72)" : "rgba(21, 95, 150, 0.34)";
  ctx.lineWidth = risk ? 3.4 : 2.1;
  ctx.stroke();

  ctx.setLineDash([2, 9]);
  ctx.beginPath();
  ctx.moveTo(a.x, a.y);
  ctx.quadraticCurveTo(mid.cx, mid.cy, b.x, b.y);
  ctx.strokeStyle = risk ? "rgba(201, 54, 54, 0.35)" : "rgba(15, 139, 154, 0.35)";
  ctx.lineWidth = 7;
  ctx.stroke();
  ctx.setLineDash([]);

  for (let i = 0; i < 2; i += 1) {
    const t = (phase * (risk ? 0.95 : 0.55) + i * 0.5) % 1;
    const point = curvePoint(a, b, curve, t);
    ctx.beginPath();
    ctx.arc(point.x, point.y, risk ? 4.2 : 3.4, 0, Math.PI * 2);
    ctx.fillStyle = risk ? "#c93636" : "#0f8b9a";
    ctx.fill();
  }

  ctx.font = "700 11px Inter, system-ui";
  ctx.fillStyle = "rgba(16, 33, 42, 0.56)";
  ctx.fillText(edge.label, mid.x + 6, mid.y - 6);
}

function drawNode(ctx, node, phase) {
  const risk = node.status === "risk";
  const w = node.type === "IPSec" || node.type === "Backup" || node.type === "tunnel" ? 94 : 112;
  const h = 54;
  const x = node.x - w / 2;
  const y = node.y - h / 2;

  if (risk) {
    const pulse = 10 + Math.sin(phase * Math.PI * 2) * 4;
    ctx.beginPath();
    ctx.arc(node.x, node.y, Math.max(w, h) / 2 + pulse, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(201, 54, 54, 0.08)";
    ctx.fill();
  }

  roundedRect(ctx, x, y, w, h, 8);
  ctx.fillStyle = risk ? "#fff3f1" : "#ffffff";
  ctx.fill();
  ctx.strokeStyle = risk ? "#c93636" : "#155f96";
  ctx.lineWidth = risk ? 2.4 : 1.8;
  ctx.stroke();

  ctx.fillStyle = risk ? "#c93636" : "#0f8b9a";
  ctx.beginPath();
  ctx.arc(x + 18, y + 19, 6, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = risk ? "rgba(201, 54, 54, 0.35)" : "rgba(15, 139, 154, 0.35)";
  ctx.lineWidth = 4;
  ctx.stroke();

  ctx.fillStyle = "#10212a";
  ctx.font = "800 12px Inter, system-ui";
  ctx.fillText(node.label, x + 32, y + 21);
  ctx.fillStyle = "#657782";
  ctx.font = "11px Inter, system-ui";
  ctx.fillText(node.type, x + 32, y + 38);
}

function drawTopology(data, time) {
  const canvas = $("topologyCanvas");
  const { ctx, width, height } = fitCanvas(canvas);
  const nodesById = Object.fromEntries(data.topology.nodes.map((node) => [node.id, {
    ...node,
    x: (node.x / 100) * width,
    y: (node.y / 100) * height,
  }]));
  const phase = (time / 2400) % 1;

  drawTopologyBackground(ctx, width, height);
  data.topology.edges.forEach((edge) => drawCurvedEdge(ctx, nodesById[edge.source], nodesById[edge.target], edge, phase));
  data.topology.nodes.forEach((node) => drawNode(ctx, nodesById[node.id], phase));
}

function startTopologyAnimation() {
  if (topologyFrame) cancelAnimationFrame(topologyFrame);
  const step = (time) => {
    if (dashboardData) drawTopology(dashboardData, time);
    topologyFrame = requestAnimationFrame(step);
  };
  topologyFrame = requestAnimationFrame(step);
}

// ---- SentinelAI Backend Integration ----

async function fetchJson(path) {
  const response = await fetch(path);
  return response.json();
}

function getWorstTelemetry(telemetry) {
  const result = {};
  metricOrder.forEach((key) => {
    const tKey = telemetryKeys[key];
    if (!tKey) return;
    let worst = null;
    let worstVal = -Infinity;
    telemetry.forEach((loc) => {
      const val = loc[tKey];
      if (val !== undefined && val > worstVal) {
        worstVal = val;
        worst = loc;
      }
    });
    if (worst !== null) {
      result[key] = { value: worstVal, ...metricLimits[key] };
    }
  });
  return result;
}

function buildSeries(telemetry) {
  if (!seriesBuffer) seriesBuffer = {};
  telemetry.forEach((loc) => {
    metricOrder.forEach((key) => {
      const tKey = telemetryKeys[key];
      if (!tKey) return;
      if (!seriesBuffer[key]) seriesBuffer[key] = [];
      const val = loc[tKey];
      if (val !== undefined) {
        seriesBuffer[key].push(val);
        if (seriesBuffer[key].length > 48) seriesBuffer[key].shift();
      }
    });
  });
  return seriesBuffer;
}

const faultLocations = ["Hub", "Branch1", "Branch2", "Branch3", "Datacenter"];

async function loadDashboard() {
  try {
    const [status, telemetryRes, predictRes, graphRes] = await Promise.all([
      fetchJson("/api/status"),
      fetchJson("/api/telemetry"),
      fetchJson("/api/predict"),
      fetchJson("/api/graph"),
    ]);

    const telemetry = telemetryRes.telemetry || [];
    const predictions = predictRes.predictions || [];
    const topPrediction = predictions.length > 0 ? predictions[0] : null;

    const metrics = getWorstTelemetry(telemetry);
    const series = buildSeries(telemetry);

    let risk = {
      confidence: 0,
      root: "No active risks detected",
      impact: "Network telemetry within normal thresholds.",
      time_to_impact: "N/A",
      severity: "low",
      recommendation: "Continue passive monitoring.",
      affected: [],
    };

    let workers = [
      { name: "CPU Worker", confidence: 42, status: "watching", signal: "below gate" },
      { name: "Latency Worker", confidence: 48, status: "watching", signal: "below gate" },
      { name: "Packet Loss Worker", confidence: 46, status: "watching", signal: "below gate" },
      { name: "Bandwidth Worker", confidence: 52, status: "watching", signal: "below gate" },
      { name: "Routing Worker", confidence: 34, status: "watching", signal: "below gate" },
      { name: "Tunnel Worker", confidence: 55, status: "watching", signal: "below gate" },
    ];
    let incidents = [];

    if (topPrediction) {
      const llm = topPrediction.llm || {};
      const graph = topPrediction.graph || {};
      const sev = (llm.severity || "medium").toLowerCase();

      risk = {
        confidence: Math.round(topPrediction.confidence),
        root: `${topPrediction.failure} at ${topPrediction.location}`,
        impact: llm.explanation || `Affecting ${(graph.affected_sites || []).join(", ") || "multiple sites"}`,
        time_to_impact: topPrediction.time_to_impact || "Unknown",
        severity: sev,
        recommendation: (llm.recommended_actions || []).join(". ") || graph.reroute || "No specific action",
        affected: graph.affected_sites || [],
      };

      workers = (topPrediction.signal_outputs || []).map((s) => ({
        name: `${s.worker} Worker`,
        confidence: Math.round(s.confidence),
        status: s.confidence >= 70 ? "active" : "watching",
        signal: s.confidence >= 70 ? "above gate" : "below gate",
        prediction: s.prediction,
        severity: s.severity,
      }));

      incidents = [
        {
          id: "PREDICTION",
          title: topPrediction.failure,
          result: `${topPrediction.confidence}% confidence · ${topPrediction.location}`,
        },
        ...(llm.recommended_actions || []).slice(0, 2).map((a, i) => ({
          id: `ACT-0${i + 1}`,
          title: "Recommended action",
          result: a,
        })),
      ];
    }

    const riskNodes = (risk.affected || []).map((s) => s.toLowerCase().replace(/\s+/g, ""));
    const allNodeIds = (graphRes.nodes || []).map((n) => n.id.toLowerCase());
    const topologyNodes = (graphRes.nodes || []).map((node) => ({
      id: node.id,
      label: node.id,
      type: node.type,
      x: (nodePositions[node.id] || { x: 50, y: 50 }).x,
      y: (nodePositions[node.id] || { x: 50, y: 50 }).y,
      status: riskNodes.includes(node.id.toLowerCase()) ? "risk" : "healthy",
    }));

    const topologyEdges = (graphRes.edges || []).map((edge) => ({
      source: edge.source,
      target: edge.target,
      label: edge.type || edge.tunnel || "link",
      status: riskNodes.includes(edge.source.toLowerCase()) || riskNodes.includes(edge.target.toLowerCase())
        ? "risk" : "healthy",
    }));

    const scenarioName = topPrediction ? topPrediction.failure : "Normal baseline";
    const activeFaults = status.active_faults || {};
    const activeFaultNames = Object.keys(activeFaults);

    dashboardData = {
      system: {
        name: "Air-Gapped MPLS Copilot",
        online: status.status === "online",
        scenario: activeFaultNames.length > 0 ? activeFaultNames[0] : "normal",
        scenario_name: scenarioName,
        air_gap: "Outbound network disabled",
        updated_at: Math.floor(Date.now() / 1000),
      },
      risk,
      metrics,
      series,
      workers,
      topology: { nodes: topologyNodes, edges: topologyEdges },
      incidents,
    };

    renderSummary(dashboardData);
    renderWorkers(dashboardData.workers);
    renderMetrics(dashboardData.metrics);
    renderImpact(dashboardData);
    renderLegend(dashboardData.metrics);
    drawMetricsChart(dashboardData);

    document.querySelectorAll("[data-scenario]").forEach((button) => {
      button.classList.toggle("active", button.dataset.scenario === dashboardData.system.scenario);
    });
  } catch (e) {
    console.error("Dashboard load failed:", e);
  }
}

async function injectScenario(scenario) {
  if (scenario === "normal") {
    for (const loc of faultLocations) {
      await fetch("/api/clear_fault", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ location: loc }),
      });
    }
  } else {
    const fault = scenarioMap[scenario];
    if (fault) {
      await fetch("/api/inject_fault", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fault_type: fault.fault_type, location: fault.location }),
      });
    }
  }
  await loadDashboard();
}

async function askCopilot(question) {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  const data = await response.json();
  $("copilotOutput").innerHTML = `
    <strong>${data.question}</strong>
    <p>${data.answer}</p>
    <span class="muted">Grounded on: telemetry · graph · RAG · LLM</span>
  `;
}

document.addEventListener("click", (event) => {
  const scenarioButton = event.target.closest("[data-scenario]");
  if (scenarioButton) injectScenario(scenarioButton.dataset.scenario);

  const promptButton = event.target.closest("[data-question]");
  if (promptButton) askCopilot(promptButton.dataset.question);
});

$("copilotForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const input = $("copilotInput");
  askCopilot(input.value);
  input.value = "";
});

$("refreshBtn").addEventListener("click", loadDashboard);
window.addEventListener("resize", () => {
  if (!dashboardData) return;
  drawMetricsChart(dashboardData);
  drawTopology(dashboardData);
});

loadDashboard().then(startTopologyAnimation);
setInterval(loadDashboard, 5000);
