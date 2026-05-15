#!/usr/bin/env python3
"""
LOKI DASHBOARD — Веб-интерфейс мониторинга сервера.
FastAPI + автообновляемый HTML с метриками в реальном времени.
"""

import os
import sys
import json
from datetime import datetime

NEXUS_CORE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, NEXUS_CORE)

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from agents.loki.loki_agent import (
    full_report, service_status, docker_ps, nexus_metrics,
    vpn_status, get_ram, get_disk, get_uptime, get_load,
    get_cpu_info, get_open_ports, fail2ban_status, who_is_online,
    LokiAgent,
)

app = FastAPI(title="Loki Dashboard", version="1.0.0")
agent = LokiAgent()


# =========================================================
# API ENDPOINTS
# =========================================================

@app.get("/api/status")
def api_status():
    return full_report()

@app.get("/api/services")
def api_services():
    services = [
        "nexus-api", "nginx", "mysql", "docker", "fail2ban",
        "ssh", "named", "exim4", "dovecot", "proftpd",
    ]
    return [service_status(s) for s in services]

@app.get("/api/docker")
def api_docker():
    return docker_ps()

@app.get("/api/nexus")
def api_nexus():
    return nexus_metrics()

@app.get("/api/vpn")
def api_vpn():
    return vpn_status()

@app.get("/api/disk")
def api_disk():
    return get_disk()

@app.get("/api/ram")
def api_ram():
    return get_ram()

@app.get("/api/diagnose")
def api_diagnose():
    return {"result": agent.diagnose()}

@app.post("/api/heal")
def api_heal():
    return agent.auto_heal(dry_run=False)


# =========================================================
# DASHBOARD HTML
# =========================================================

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🛡️ Loki Dashboard</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  background: #0d1117; color: #c9d1d9;
  min-height: 100vh;
}
.header {
  background: linear-gradient(135deg, #161b22 0%, #1a2332 100%);
  border-bottom: 1px solid #30363d;
  padding: 16px 24px;
  display: flex; align-items: center; justify-content: space-between;
}
.header h1 { font-size: 1.4em; color: #58a6ff; }
.header .time { color: #8b949e; font-size: 0.9em; }
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px; padding: 20px;
}
.card {
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 12px;
  padding: 20px;
}
.card h2 {
  font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.05em;
  color: #8b949e; margin-bottom: 12px;
}
.metric {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 0; border-bottom: 1px solid #21262d;
}
.metric:last-child { border-bottom: none; }
.metric .label { color: #8b949e; }
.metric .value { font-weight: 600; color: #c9d1d9; }
.status-dot {
  display: inline-block; width: 10px; height: 10px;
  border-radius: 50%; margin-right: 8px;
}
.status-dot.green { background: #3fb950; box-shadow: 0 0 8px #3fb95066; }
.status-dot.red { background: #f85149; box-shadow: 0 0 8px #f8514966; }
.status-dot.yellow { background: #d29922; box-shadow: 0 0 8px #d2992266; }
.btn {
  background: #238636; color: white; border: none; padding: 8px 16px;
  border-radius: 6px; cursor: pointer; font-size: 0.9em;
  transition: background 0.2s;
}
.btn:hover { background: #2ea043; }
.btn-blue { background: #1f6feb; }
.btn-blue:hover { background: #388bfd; }
.log-output {
  background: #0d1117; border: 1px solid #30363d; border-radius: 8px;
  padding: 12px; font-family: 'JetBrains Mono', monospace;
  font-size: 0.8em; white-space: pre-wrap; max-height: 300px;
  overflow-y: auto; color: #7ee787;
}
.progress-bar {
  height: 8px; background: #21262d; border-radius: 4px; overflow: hidden;
  margin-top: 4px;
}
.progress-bar .fill {
  height: 100%; border-radius: 4px; transition: width 0.5s;
}
.progress-bar .fill.green { background: #3fb950; }
.progress-bar .fill.yellow { background: #d29922; }
.progress-bar .fill.red { background: #f85149; }
</style>
</head>
<body>
<div class="header">
  <h1>🛡️ Loki Dashboard</h1>
  <div class="time" id="time">Loading...</div>
</div>
<div class="grid">

  <!-- SYSTEM -->
  <div class="card">
    <h2>📊 System</h2>
    <div class="metric">
      <span class="label">Uptime</span>
      <span class="value" id="uptime">—</span>
    </div>
    <div class="metric">
      <span class="label">Load</span>
      <span class="value" id="load">—</span>
    </div>
    <div class="metric">
      <span class="label">CPU</span>
      <span class="value" id="cpu">—</span>
    </div>
  </div>

  <!-- RAM -->
  <div class="card">
    <h2>🧮 Memory</h2>
    <div class="metric">
      <span class="label">Used</span>
      <span class="value" id="ram-used">—</span>
    </div>
    <div class="metric">
      <span class="label">Available</span>
      <span class="value" id="ram-avail">—</span>
    </div>
    <div class="progress-bar">
      <div class="fill green" id="ram-bar" style="width: 0%"></div>
    </div>
  </div>

  <!-- DISK -->
  <div class="card">
    <h2>💾 Disk</h2>
    <div class="metric">
      <span class="label">Used</span>
      <span class="value" id="disk-used">—</span>
    </div>
    <div class="metric">
      <span class="label">Free</span>
      <span class="value" id="disk-free">—</span>
    </div>
    <div class="progress-bar">
      <div class="fill green" id="disk-bar" style="width: 0%"></div>
    </div>
  </div>

  <!-- NEXUS -->
  <div class="card">
    <h2>🧠 Nexus API</h2>
    <div class="metric">
      <span class="label">Completed</span>
      <span class="value" id="nexus-completed">—</span>
    </div>
    <div class="metric">
      <span class="label">Queue</span>
      <span class="value" id="nexus-queue">—</span>
    </div>
    <div class="metric">
      <span class="label">Failed</span>
      <span class="value" id="nexus-failed">—</span>
    </div>
  </div>

  <!-- VPN -->
  <div class="card">
    <h2>🔒 VPN</h2>
    <div class="metric">
      <span class="label">Status</span>
      <span class="value" id="vpn-status">—</span>
    </div>
    <div class="metric">
      <span class="label">Endpoint</span>
      <span class="value" id="vpn-endpoint">—</span>
    </div>
    <div class="metric">
      <span class="label">Last Handshake</span>
      <span class="value" id="vpn-handshake">—</span>
    </div>
  </div>

  <!-- DOCKER -->
  <div class="card">
    <h2>🐳 Docker</h2>
    <div id="docker-list">Loading...</div>
  </div>

  <!-- SERVICES -->
  <div class="card">
    <h2>📋 Services</h2>
    <div id="services-list">Loading...</div>
  </div>

  <!-- DIAGNOSE & HEAL -->
  <div class="card">
    <h2>🔧 Actions</h2>
    <div style="display:flex;gap:8px;margin-bottom:12px;">
      <button class="btn btn-blue" onclick="runDiagnose()">🔍 Diagnose</button>
      <button class="btn" onclick="runHeal()">🔧 Auto-Heal</button>
    </div>
    <div class="log-output" id="action-log">Ready.</div>
  </div>

</div>

<script>
function setStatus(id, value, isGood) {
  const el = document.getElementById(id);
  if (!el) return;
  const dot = `<span class="status-dot ${isGood ? 'green' : 'red'}"></span>`;
  el.innerHTML = dot + value;
}

function updateDashboard() {
  fetch('/api/status')
    .then(r => r.json())
    .then(data => {
      document.getElementById('time').textContent = data.timestamp;
      document.getElementById('uptime').textContent = data.uptime;
      document.getElementById('load').textContent = data.load;
      document.getElementById('cpu').textContent = data.cpu.cores + ' cores';

      // RAM
      const ram = data.ram;
      document.getElementById('ram-used').textContent = ram.mem_used + ' / ' + ram.mem_total;
      document.getElementById('ram-avail').textContent = ram.mem_available;
      try {
        const used = parseFloat(ram.mem_used);
        const total = parseFloat(ram.mem_total);
        const pct = Math.round((used / total) * 100);
        const bar = document.getElementById('ram-bar');
        bar.style.width = pct + '%';
        bar.className = 'fill ' + (pct > 85 ? 'red' : pct > 70 ? 'yellow' : 'green');
      } catch(e) {}

      // Disk
      if (data.disk && data.disk[0]) {
        const d = data.disk[0];
        document.getElementById('disk-used').textContent = d.used + ' / ' + d.size;
        document.getElementById('disk-free').textContent = d.avail;
        const pct = parseInt(d.use_percent);
        const bar = document.getElementById('disk-bar');
        bar.style.width = d.use_percent;
        bar.className = 'fill ' + (pct > 85 ? 'red' : pct > 70 ? 'yellow' : 'green');
      }

      // Nexus
      const n = data.nexus;
      document.getElementById('nexus-completed').textContent = n.completed_requests;
      document.getElementById('nexus-queue').textContent = n.queue;
      document.getElementById('nexus-failed').textContent = n.failed_requests;

      // Time
      document.getElementById('time').textContent = '🕐 ' + data.timestamp;
    })
    .catch(e => console.error('Status error:', e));

  // Services
  fetch('/api/services')
    .then(r => r.json())
    .then(data => {
      const html = data.map(s => {
        const dot = s.active ? 'green' : 'red';
        return `<div class="metric"><span class="label"><span class="status-dot ${dot}"></span>${s.name}</span><span class="value">${s.active ? 'up' : 'down'}</span></div>`;
      }).join('');
      document.getElementById('services-list').innerHTML = html;
    })
    .catch(e => console.error('Services error:', e));

  // Docker
  fetch('/api/docker')
    .then(r => r.json())
    .then(data => {
      const html = data.map(c => {
        let dot = 'yellow';
        if (c.status.toLowerCase().includes('up') && !c.status.toLowerCase().includes('unhealthy')) dot = 'green';
        if (c.status.toLowerCase().includes('unhealthy')) dot = 'red';
        if (c.status.toLowerCase().includes('exited')) dot = 'yellow';
        return `<div class="metric"><span class="label"><span class="status-dot ${dot}"></span>${c.name}</span><span class="value" style="font-size:0.8em">${c.status}</span></div>`;
      }).join('');
      document.getElementById('docker-list').innerHTML = html;
    })
    .catch(e => console.error('Docker error:', e));

  // VPN
  fetch('/api/vpn')
    .then(r => r.json())
    .then(data => {
      const isUp = data.status === 'up';
      setStatus('vpn-status', data.status, isUp);
      document.getElementById('vpn-endpoint').textContent = data.endpoint || '—';
      document.getElementById('vpn-handshake').textContent = data['latest handshake'] || '—';
    })
    .catch(e => console.error('VPN error:', e));
}

function runDiagnose() {
  document.getElementById('action-log').textContent = 'Running diagnosis...';
  fetch('/api/diagnose')
    .then(r => r.json())
    .then(data => {
      document.getElementById('action-log').textContent = data.result;
    })
    .catch(e => {
      document.getElementById('action-log').textContent = 'Error: ' + e;
    });
}

function runHeal() {
  document.getElementById('action-log').textContent = 'Running auto-heal...';
  fetch('/api/heal', { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      let text = data.actions.join('\\n');
      if (data.errors.length) text += '\\n\\nErrors:\\n' + data.errors.join('\\n');
      if (!data.actions.length) text = 'No issues found!';
      document.getElementById('action-log').textContent = text;
    })
    .catch(e => {
      document.getElementById('action-log').textContent = 'Error: ' + e;
    });
}

// Initial load
updateDashboard();
// Auto-refresh every 10 seconds
setInterval(updateDashboard, 10000);
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return DASHBOARD_HTML


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="warning")
