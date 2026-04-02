"""Verdict Dashboard — FastAPI web application for viewing verification reports.

Provides:
- Upload and verify trace files via web UI
- View historical reports
- Real-time verification status
- Trust score visualization
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from verdict.checks.registry import get_default_checks
from verdict.core.reporter import Reporter
from verdict.core.scorer import TrustScorer
from verdict.core.tracer import Trace
from verdict.core.types import ActionType, AgentAction, ToolCall, ToolResult
from verdict.core.verifier import Verifier


def _parse_trace(data: dict[str, Any]) -> Trace:
    """Parse a trace from JSON data."""
    trace = Trace(name=data.get("name", "uploaded"), agent_name=data.get("agent_name", "unknown"))
    trace.id = data.get("id", trace.id)

    for a in data.get("actions", []):
        action_type = ActionType(a["action_type"])
        tc = ToolCall(**a["tool_call"]) if a.get("tool_call") else None
        tr = ToolResult(**a["tool_result"]) if a.get("tool_result") else None
        action = AgentAction(
            id=a.get("id", ""),
            action_type=action_type,
            tool_call=tc,
            tool_result=tr,
            content=a.get("content"),
            metadata=a.get("metadata", {}),
        )
        trace.actions.append(action)

    return trace


def create_app() -> FastAPI:
    """Create the Verdict dashboard FastAPI application."""

    app = FastAPI(
        title="Verdict Dashboard",
        description="The verification layer for AI agents",
        version="0.1.0",
    )

    # In-memory report storage
    reports: list[dict[str, Any]] = []

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return _get_dashboard_html(reports)

    @app.post("/api/verify")
    async def verify_trace(file: UploadFile = File(...)) -> JSONResponse:
        content = await file.read()
        data = json.loads(content)
        trace = _parse_trace(data)

        verifier = Verifier()
        for check in get_default_checks():
            verifier.add_check(check)
        report = verifier.verify(trace)

        report_dict = Reporter.to_dict(report)
        reports.append(report_dict)

        return JSONResponse(content=report_dict)

    @app.get("/api/reports")
    async def list_reports() -> JSONResponse:
        return JSONResponse(content=reports)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.1.0"}

    return app


def _get_dashboard_html(reports: list[dict[str, Any]]) -> str:
    """Generate the dashboard HTML."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verdict Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0f;
            color: #e0e0e0;
            min-height: 100vh;
        }
        .header {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            padding: 2rem;
            border-bottom: 1px solid #2a2a4a;
        }
        .header h1 {
            font-size: 2rem;
            background: linear-gradient(90deg, #00d4ff, #7b2ff7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header p { color: #888; margin-top: 0.5rem; }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .upload-zone {
            border: 2px dashed #2a2a4a;
            border-radius: 12px;
            padding: 3rem;
            text-align: center;
            margin: 2rem 0;
            transition: all 0.3s;
            cursor: pointer;
        }
        .upload-zone:hover { border-color: #00d4ff; background: rgba(0,212,255,0.05); }
        .upload-zone h3 { color: #00d4ff; margin-bottom: 1rem; }
        .btn {
            background: linear-gradient(90deg, #00d4ff, #7b2ff7);
            color: white;
            border: none;
            padding: 0.75rem 2rem;
            border-radius: 8px;
            font-size: 1rem;
            cursor: pointer;
            transition: opacity 0.3s;
        }
        .btn:hover { opacity: 0.8; }
        .score-card {
            background: #1a1a2e;
            border-radius: 12px;
            padding: 2rem;
            margin: 1rem 0;
            border: 1px solid #2a2a4a;
        }
        .score-display {
            font-size: 4rem;
            font-weight: bold;
            text-align: center;
        }
        .grade-A { color: #00ff88; }
        .grade-B { color: #ffdd00; }
        .grade-C { color: #ff8800; }
        .grade-F { color: #ff3344; }
        .results-table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
        }
        .results-table th {
            background: #1a1a2e;
            padding: 1rem;
            text-align: left;
            border-bottom: 2px solid #2a2a4a;
            color: #00d4ff;
        }
        .results-table td {
            padding: 0.75rem 1rem;
            border-bottom: 1px solid #1a1a2e;
        }
        .status-pass { color: #00ff88; font-weight: bold; }
        .status-fail { color: #ff3344; font-weight: bold; }
        .severity-critical { color: #ff3344; font-weight: bold; }
        .severity-high { color: #ff6644; }
        .severity-medium { color: #ffdd00; }
        .severity-low { color: #888; }
        #result { display: none; }
        .footer {
            text-align: center;
            padding: 2rem;
            color: #444;
            border-top: 1px solid #1a1a2e;
            margin-top: 3rem;
        }
        .footer a { color: #00d4ff; text-decoration: none; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 1rem 0;
        }
        .stat-box {
            background: #1a1a2e;
            border-radius: 8px;
            padding: 1.5rem;
            text-align: center;
            border: 1px solid #2a2a4a;
        }
        .stat-value { font-size: 2rem; font-weight: bold; color: #00d4ff; }
        .stat-label { color: #888; margin-top: 0.5rem; font-size: 0.9rem; }
        .loading { display: none; text-align: center; padding: 2rem; }
        .spinner {
            border: 3px solid #2a2a4a;
            border-top: 3px solid #00d4ff;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>VERDICT</h1>
            <p>The verification layer for AI agents &mdash; by Zaphenath Labs</p>
        </div>
    </div>

    <div class="container">
        <div class="upload-zone" onclick="document.getElementById('fileInput').click()">
            <h3>Upload Agent Trace</h3>
            <p>Drop a trace.json file here or click to browse</p>
            <input type="file" id="fileInput" accept=".json" style="display:none" onchange="handleUpload(this)">
            <br><br>
            <button class="btn" onclick="event.stopPropagation(); runDemo()">Run Demo</button>
        </div>

        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p style="margin-top: 1rem; color: #888;">Verifying trace...</p>
        </div>

        <div id="result"></div>
    </div>

    <div class="footer">
        <p>Verdict v0.1.0 &mdash; <a href="https://verdict.zaphenath.app">verdict.zaphenath.app</a> &mdash; Built by <a href="https://zaphenath.app">Zaphenath Labs</a></p>
    </div>

    <script>
        async function handleUpload(input) {
            const file = input.files[0];
            if (!file) return;
            const formData = new FormData();
            formData.append('file', file);
            document.getElementById('loading').style.display = 'block';
            document.getElementById('result').style.display = 'none';
            try {
                const res = await fetch('/api/verify', { method: 'POST', body: formData });
                const data = await res.json();
                renderReport(data);
            } catch (e) {
                alert('Error: ' + e.message);
            }
            document.getElementById('loading').style.display = 'none';
        }

        function runDemo() {
            const demo = {
                name: "demo-task", agent_name: "demo-agent",
                actions: [
                    { action_type: "tool_call", tool_call: { id: "t1", name: "read_file", arguments: { path: "src/app.py" } } },
                    { action_type: "tool_result", tool_result: { tool_call_id: "t1", output: "code here" } },
                    { action_type: "shell_exec", content: "npm run build", metadata: { exit_code: 0, output: "ok" } },
                    { action_type: "shell_exec", content: "rm -rf /tmp/old", metadata: { exit_code: 0 } },
                    { action_type: "tool_call", tool_call: { id: "t2", name: "bash", arguments: { command: "echo sk-proj-test123456789" } } },
                    { action_type: "tool_result", tool_result: { tool_call_id: "t2", output: "sk-proj-test123456789" } },
                    { action_type: "http_request", content: "GET https://api.example.com/data", metadata: { status_code: 500 } }
                ]
            };
            const blob = new Blob([JSON.stringify(demo)], { type: 'application/json' });
            const formData = new FormData();
            formData.append('file', blob, 'demo.json');
            document.getElementById('loading').style.display = 'block';
            document.getElementById('result').style.display = 'none';
            fetch('/api/verify', { method: 'POST', body: formData })
                .then(r => r.json())
                .then(renderReport)
                .finally(() => { document.getElementById('loading').style.display = 'none'; });
        }

        function renderReport(data) {
            const gradeClass = data.trust_score >= 90 ? 'grade-A' : data.trust_score >= 80 ? 'grade-B' : data.trust_score >= 60 ? 'grade-C' : 'grade-F';
            let html = `
                <div class="score-card">
                    <div class="score-display ${gradeClass}">${data.trust_score}/100 (${data.trust_grade})</div>
                </div>
                <div class="stats-grid">
                    <div class="stat-box"><div class="stat-value">${data.total_actions}</div><div class="stat-label">Actions Traced</div></div>
                    <div class="stat-box"><div class="stat-value">${data.checks_passed}</div><div class="stat-label">Checks Passed</div></div>
                    <div class="stat-box"><div class="stat-value">${data.checks_failed}</div><div class="stat-label">Checks Failed</div></div>
                    <div class="stat-box"><div class="stat-value">${data.agent_name}</div><div class="stat-label">Agent</div></div>
                </div>`;
            if (data.results && data.results.length > 0) {
                html += `<table class="results-table"><thead><tr><th>Check</th><th>Category</th><th>Severity</th><th>Status</th><th>Message</th></tr></thead><tbody>`;
                for (const r of data.results) {
                    const status = r.passed ? '<span class="status-pass">PASS</span>' : '<span class="status-fail">FAIL</span>';
                    const sevClass = 'severity-' + r.severity;
                    html += `<tr><td>${r.check_name}</td><td>${r.category}</td><td class="${sevClass}">${r.severity.toUpperCase()}</td><td>${status}</td><td>${r.message}</td></tr>`;
                }
                html += '</tbody></table>';
            }
            document.getElementById('result').innerHTML = html;
            document.getElementById('result').style.display = 'block';
        }
    </script>
</body>
</html>"""
