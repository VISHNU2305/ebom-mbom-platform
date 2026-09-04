"""
Web dashboard for the eBOM-to-mBOM Conversion Platform.

This is a thin presentation layer over the already-tested core logic
(ingest.py, validator.py, conversion_engine.py, genai_query.py). No
business logic lives here — every endpoint just calls existing,
already-proven functions and returns the result as JSON, or serves the
HTML/CSS/JS dashboard that displays it.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import db as db_module
import genai_query
from conversion_engine import convert_ebom_to_mbom
from ingest import load_ebom_csv
from validator import validate_ebom

app = FastAPI(title="eBOM-to-mBOM Dashboard")

DATA_CSV = Path(__file__).resolve().parent.parent / "data" / "sample_ebom.csv"


class AskRequest(BaseModel):
    question: str


def _run_pipeline():
    """Runs the full pipeline and persists results — reuses existing, tested logic."""
    ebom_lines = load_ebom_csv(DATA_CSV)
    issues = validate_ebom(ebom_lines)
    mbom_lines = convert_ebom_to_mbom(ebom_lines)

    conn = db_module.get_connection()
    db_module.reset_tables(conn)
    db_module.save_ebom(conn, ebom_lines)
    db_module.save_mbom(conn, mbom_lines)
    db_module.save_validation_issues(conn, issues)
    conn.close()

    return ebom_lines, mbom_lines, issues


@app.post("/api/run")
def run_pipeline():
    ebom, mbom, issues = _run_pipeline()
    return {
        "ebom_count": len(ebom),
        "mbom_count": len(mbom),
        "errors": len([i for i in issues if i.severity == "ERROR"]),
        "warnings": len([i for i in issues if i.severity == "WARNING"]),
    }


@app.get("/api/ebom")
def get_ebom():
    conn = db_module.get_connection()
    rows = db_module.query(conn, "SELECT * FROM ebom")
    conn.close()
    return rows


@app.get("/api/mbom")
def get_mbom():
    conn = db_module.get_connection()
    rows = db_module.query(conn, "SELECT * FROM mbom")
    conn.close()
    return rows


@app.get("/api/issues")
def get_issues():
    conn = db_module.get_connection()
    rows = db_module.query(conn, "SELECT * FROM validation_issues")
    conn.close()
    return rows


@app.post("/api/ask")
def ask_question(body: AskRequest):
    conn = db_module.get_connection()
    answer = genai_query.answer_question(conn, body.question)
    conn.close()
    return {"question": body.question, "answer": answer}


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return DASHBOARD_HTML


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>eBOM → mBOM Dashboard</title>
<style>
  :root {
    --bg: #0f1420;
    --card: #1a2233;
    --accent: #4f9dff;
    --accent2: #7c5cff;
    --text: #e8ecf4;
    --muted: #8892a6;
    --error: #ff5c5c;
    --warning: #ffb84f;
    --success: #4fd papers;
    --success: #4fd68c;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
    background: linear-gradient(160deg, #0f1420, #161d2e);
    color: var(--text);
    min-height: 100vh;
    padding: 32px;
  }
  h1 {
    font-size: 26px;
    margin-bottom: 4px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .subtitle { color: var(--muted); margin-bottom: 28px; }
  .grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 28px;
  }
  .stat-card {
    background: var(--card);
    border-radius: 14px;
    padding: 20px;
    border: 1px solid rgba(255,255,255,0.06);
  }
  .stat-card .label { color: var(--muted); font-size: 13px; margin-bottom: 6px; }
  .stat-card .value { font-size: 30px; font-weight: 700; }
  .stat-card.error .value { color: var(--error); }
  .stat-card.warning .value { color: var(--warning); }
  .stat-card.success .value { color: var(--success); }
  button {
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    border: none;
    color: white;
    padding: 12px 22px;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    margin-bottom: 28px;
  }
  button:hover { opacity: 0.9; }
  .panel {
    background: var(--card);
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 20px;
    border: 1px solid rgba(255,255,255,0.06);
  }
  .panel h2 { margin-top: 0; font-size: 16px; color: var(--accent); }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid rgba(255,255,255,0.06); }
  th { color: var(--muted); font-weight: 600; }
  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 700;
  }
  .badge.ERROR { background: rgba(255,92,92,0.15); color: var(--error); }
  .badge.WARNING { background: rgba(255,184,79,0.15); color: var(--warning); }
  .ask-box { display: flex; gap: 10px; margin-bottom: 16px; }
  .ask-box input {
    flex: 1;
    padding: 12px 14px;
    border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.1);
    background: #10192b;
    color: var(--text);
    font-size: 14px;
  }
  .answer {
    background: #10192b;
    border-radius: 10px;
    padding: 14px;
    white-space: pre-wrap;
    font-size: 13px;
    color: var(--text);
    min-height: 20px;
  }
</style>
</head>
<body>
  <h1>eBOM → mBOM Conversion Dashboard</h1>
  <div class="subtitle">Engineering-to-Manufacturing BOM Conversion Platform</div>

  <button onclick="runPipeline()">▶ Run Conversion Pipeline</button>

  <div class="grid" id="stats">
    <div class="stat-card"><div class="label">eBOM Lines</div><div class="value" id="ebomCount">–</div></div>
    <div class="stat-card"><div class="label">mBOM Lines</div><div class="value" id="mbomCount">–</div></div>
    <div class="stat-card error"><div class="label">Validation Errors</div><div class="value" id="errorCount">–</div></div>
    <div class="stat-card warning"><div class="label">Warnings</div><div class="value" id="warningCount">–</div></div>
  </div>

  <div class="panel">
    <h2>Ask a Question</h2>
    <div class="ask-box">
      <input id="questionInput" placeholder="e.g. what are the manufacturing-only parts?" />
      <button onclick="askQuestion()">Ask</button>
    </div>
    <div class="answer" id="answerBox">Ask something above to see an answer here.</div>
  </div>

  <div class="panel">
    <h2>Validation Issues</h2>
    <table id="issuesTable"><thead><tr><th>Severity</th><th>Type</th><th>Part</th><th>Message</th></tr></thead><tbody></tbody></table>
  </div>

  <div class="panel">
    <h2>mBOM (Manufacturing Bill of Materials)</h2>
    <table id="mbomTable"><thead><tr><th>Part #</th><th>Description</th><th>Routing</th><th>Work Center</th><th>Type</th></tr></thead><tbody></tbody></table>
  </div>

<script>
async function runPipeline() {
  const res = await fetch('/api/run', { method: 'POST' });
  const data = await res.json();
  document.getElementById('ebomCount').innerText = data.ebom_count;
  document.getElementById('mbomCount').innerText = data.mbom_count;
  document.getElementById('errorCount').innerText = data.errors;
  document.getElementById('warningCount').innerText = data.warnings;
  loadIssues();
  loadMbom();
}

async function loadIssues() {
  const res = await fetch('/api/issues');
  const rows = await res.json();
  const tbody = document.querySelector('#issuesTable tbody');
  tbody.innerHTML = rows.map(r => `
    <tr>
      <td><span class="badge ${r.severity}">${r.severity}</span></td>
      <td>${r.issue_type}</td>
      <td>${r.part_number}</td>
      <td>${r.message}</td>
    </tr>`).join('');
}

async function loadMbom() {
  const res = await fetch('/api/mbom');
  const rows = await res.json();
  const tbody = document.querySelector('#mbomTable tbody');
  tbody.innerHTML = rows.map(r => `
    <tr>
      <td>${r.part_number}</td>
      <td>${r.description}</td>
      <td>${r.routing_step || '-'}</td>
      <td>${r.work_center || '-'}</td>
      <td>${r.is_manufacturing_only ? 'Mfg-only' : 'From design'}</td>
    </tr>`).join('');
}

async function askQuestion() {
  const q = document.getElementById('questionInput').value;
  if (!q) return;
  document.getElementById('answerBox').innerText = 'Thinking...';
  const res = await fetch('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question: q })
  });
  const data = await res.json();
  document.getElementById('answerBox').innerText = data.answer;
}

// Load whatever's already in the DB on page load
loadIssues();
loadMbom();
</script>
</body>
</html>
"""