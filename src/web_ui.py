"""
Web dashboard for the eBOM-to-mBOM Conversion Platform.

Adds: a product catalog dropdown (switch between multiple sample
products without touching code), plain-English explanations for every
mBOM line (for non-technical viewers), and an animated background.
Core logic is unchanged — this file only adds a presentation layer and
a product-selection endpoint on top of the already-tested pipeline.
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import db as db_module
import genai_query
import products
from conversion_engine import convert_ebom_to_mbom
from validator import validate_ebom

app = FastAPI(title="eBOM-to-mBOM Dashboard")


class AskRequest(BaseModel):
    question: str


class SelectProductRequest(BaseModel):
    product_id: str


# -----------------------------------------------------------------
# Plain-English explanation generator
# -----------------------------------------------------------------

def explain_mbom_line(row: dict) -> str:
    """Turns one mBOM row into a short, non-technical sentence."""
    if row["part_type"] in ("ASSEMBLY", "SUBASSEMBLY"):
        return "A structural grouping that holds other parts together — not manufactured itself."

    if row["is_manufacturing_only"]:
        pn = row["part_number"]
        desc = row["description"]
        if "BOLT" in pn:
            return f"An extra bolt automatically added because '{desc}' needs to be fastened together."
        if "WELD-WIRE" in pn:
            return f"Welding material added because '{desc}' needs to be welded."
        if "SHIELD-GAS" in pn:
            return "Shielding gas added because welding needs an inert gas to protect the weld."
        if "ANODIZE" in pn:
            return "A surface treatment added because aluminum parts need anodizing for corrosion resistance."
        if "DOWEL" in pn:
            return "An alignment pin added so this precision part lines up correctly during assembly."
        if "PASSIVATE" in pn:
            return "A chemical treatment added because stainless steel needs passivation to resist corrosion."
        if "RELEASE-AGENT" in pn:
            return "A release agent added so this molded plastic part doesn't stick in the mold."
        if "GREASE" in pn:
            return "Lubricant added because this bearing needs grease to work properly."
        if "GASKET" in pn:
            return "A sealing gasket added so this housing keeps out dust and moisture."
        if "QC-CERT" in pn:
            return "A quality inspection step added because precision rotating parts must be checked before shipping."
        return "An item needed to build the product, but never appeared in the original design."

    routing_map = {
        "10-CUT": "gets cut to size first",
        "20-MACHINE": "gets machined for precision",
        "10-MACHINE": "gets machined for precision",
        "20-DEBURR": "gets smoothed/deburred",
        "10-MOLD": "gets molded into shape",
        "20-POLISH": "gets polished",
        "10-WELD": "gets welded",
        "30-PAINT": "gets painted as the final step",
    }
    step_text = routing_map.get(row["routing_step"], "goes through manufacturing")
    return f"A real designed part ({row['material']}) that {step_text}."


def build_plain_summary(mbom_rows: list[dict], product_name: str) -> str:
    total = len(mbom_rows)
    from_design = sum(1 for r in mbom_rows if not r["is_manufacturing_only"])
    added = sum(1 for r in mbom_rows if r["is_manufacturing_only"])
    return (
        f"This is the manufacturing plan for the {product_name}. "
        f"Out of {total} total items needed to build it, {from_design} came directly "
        f"from the original engineering design, and {added} extra items "
        f"(bolts, welding gas, surface treatments, lubricants, inspections, and more) "
        f"were automatically added because the factory needs them to actually build "
        f"the product — even though the original designer never listed them."
    )


# -----------------------------------------------------------------
# Pipeline logic
# -----------------------------------------------------------------

def _run_pipeline_for_product(product_id: str):
    ebom_lines = products.build_product(product_id)
    issues = validate_ebom(ebom_lines)
    mbom_lines = convert_ebom_to_mbom(ebom_lines)

    conn = db_module.get_connection()
    db_module.reset_tables(conn)
    db_module.save_ebom(conn, ebom_lines)
    db_module.save_mbom(conn, mbom_lines)
    db_module.save_validation_issues(conn, issues)
    conn.close()

    return ebom_lines, mbom_lines, issues


@app.get("/api/products")
def list_products():
    return [{"id": pid, **info} for pid, info in products.PRODUCTS.items()]


@app.post("/api/select-product")
def select_product(body: SelectProductRequest):
    ebom, mbom, issues = _run_pipeline_for_product(body.product_id)
    product_name = products.PRODUCTS[body.product_id]["name"]

    conn = db_module.get_connection()
    mbom_rows = db_module.query(conn, "SELECT * FROM mbom")
    conn.close()

    return {
        "product_name": product_name,
        "ebom_count": len(ebom),
        "mbom_count": len(mbom),
        "errors": len([i for i in issues if i.severity == "ERROR"]),
        "warnings": len([i for i in issues if i.severity == "WARNING"]),
        "plain_summary": build_plain_summary(mbom_rows, product_name),
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
    for row in rows:
        row["explanation"] = explain_mbom_line(row)
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
    --success: #4fd68c;
  }
  * { box-sizing: border-box; }

  body {
    margin: 0;
    font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
    background: #0f1420;
    color: var(--text);
    min-height: 100vh;
    padding: 32px;
    position: relative;
    overflow-x: hidden;
  }

  .bg-anim {
    position: fixed;
    top: 0; left: 0; width: 100%; height: 100%;
    z-index: 0;
    overflow: hidden;
    pointer-events: none;
  }
  .bg-anim span {
    position: absolute;
    display: block;
    width: 18px; height: 18px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    opacity: 0.12;
    border-radius: 4px;
    animation: float 18s linear infinite;
  }
  .bg-anim span:nth-child(1)  { left: 5%;  width: 60px; height: 60px; animation-duration: 22s; animation-delay: 0s; }
  .bg-anim span:nth-child(2)  { left: 15%; width: 30px; height: 30px; animation-duration: 16s; animation-delay: 2s; }
  .bg-anim span:nth-child(3)  { left: 28%; width: 90px; height: 90px; animation-duration: 26s; animation-delay: 1s; }
  .bg-anim span:nth-child(4)  { left: 42%; width: 24px; height: 24px; animation-duration: 14s; animation-delay: 4s; }
  .bg-anim span:nth-child(5)  { left: 55%; width: 45px; height: 45px; animation-duration: 20s; animation-delay: 0s; }
  .bg-anim span:nth-child(6)  { left: 68%; width: 70px; height: 70px; animation-duration: 24s; animation-delay: 3s; }
  .bg-anim span:nth-child(7)  { left: 78%; width: 20px; height: 20px; animation-duration: 15s; animation-delay: 5s; }
  .bg-anim span:nth-child(8)  { left: 88%; width: 55px; height: 55px; animation-duration: 19s; animation-delay: 2s; }
  .bg-anim span:nth-child(9)  { left: 95%; width: 35px; height: 35px; animation-duration: 21s; animation-delay: 1s; }
  .bg-anim span:nth-child(10) { left: 35%; width: 15px; height: 15px; animation-duration: 12s; animation-delay: 6s; }

  @keyframes float {
    0%   { transform: translateY(110vh) rotate(0deg); opacity: 0; }
    10%  { opacity: 0.12; }
    90%  { opacity: 0.12; }
    100% { transform: translateY(-10vh) rotate(360deg); opacity: 0; }
  }

  .content { position: relative; z-index: 1; }

  h1 {
    font-size: 26px;
    margin-bottom: 4px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .subtitle { color: var(--muted); margin-bottom: 24px; }

  .controls { display: flex; gap: 12px; align-items: center; margin-bottom: 28px; flex-wrap: wrap; }
  select {
    background: var(--card);
    color: var(--text);
    border: 1px solid rgba(255,255,255,0.1);
    padding: 12px 16px;
    border-radius: 10px;
    font-size: 14px;
    min-width: 280px;
  }
  button {
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    border: none;
    color: white;
    padding: 12px 22px;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
  }
  button:hover { opacity: 0.9; }

  .grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 20px;
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

  .summary-box {
    background: linear-gradient(135deg, rgba(79,157,255,0.1), rgba(124,92,255,0.1));
    border: 1px solid rgba(79,157,255,0.25);
    border-radius: 14px;
    padding: 18px 22px;
    margin-bottom: 28px;
    font-size: 14.5px;
    line-height: 1.6;
  }
  .summary-box strong { color: var(--accent); }

  .panel {
    background: var(--card);
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 20px;
    border: 1px solid rgba(255,255,255,0.06);
  }
  .panel h2 { margin-top: 0; font-size: 16px; color: var(--accent); }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid rgba(255,255,255,0.06); vertical-align: top; }
  th { color: var(--muted); font-weight: 600; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; }
  .badge.ERROR { background: rgba(255,92,92,0.15); color: var(--error); }
  .badge.WARNING { background: rgba(255,184,79,0.15); color: var(--warning); }
  .explanation { color: var(--muted); font-style: italic; }

  .ask-box { display: flex; gap: 10px; margin-bottom: 16px; }
  .ask-box input {
    flex: 1; padding: 12px 14px; border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.1); background: #10192b;
    color: var(--text); font-size: 14px;
  }
  .answer { background: #10192b; border-radius: 10px; padding: 14px; white-space: pre-wrap; font-size: 13px; min-height: 20px; }
</style>
</head>
<body>

  <div class="bg-anim">
    <span></span><span></span><span></span><span></span><span></span>
    <span></span><span></span><span></span><span></span><span></span>
  </div>

  <div class="content">
    <h1>eBOM → mBOM Conversion Dashboard</h1>
    <div class="subtitle">Engineering-to-Manufacturing BOM Conversion Platform</div>

    <div class="controls">
      <select id="productSelect"></select>
      <button onclick="runPipeline()">▶ Convert This Product</button>
    </div>

    <div class="grid" id="stats">
      <div class="stat-card"><div class="label">eBOM Lines</div><div class="value" id="ebomCount">–</div></div>
      <div class="stat-card"><div class="label">mBOM Lines</div><div class="value" id="mbomCount">–</div></div>
      <div class="stat-card error"><div class="label">Validation Errors</div><div class="value" id="errorCount">–</div></div>
      <div class="stat-card warning"><div class="label">Warnings</div><div class="value" id="warningCount">–</div></div>
    </div>

    <div class="summary-box" id="plainSummary">
      Select a product above and click "Convert This Product" to see a plain-English explanation here.
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
      <table id="mbomTable">
        <thead><tr><th>Part #</th><th>Description</th><th>Type</th><th>What is this?</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>
  </div>

<script>
async function loadProducts() {
  const res = await fetch('/api/products');
  const list = await res.json();
  const select = document.getElementById('productSelect');
  select.innerHTML = list.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
}

async function runPipeline() {
  const productId = document.getElementById('productSelect').value;
  const res = await fetch('/api/select-product', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ product_id: productId })
  });
  const data = await res.json();
  document.getElementById('ebomCount').innerText = data.ebom_count;
  document.getElementById('mbomCount').innerText = data.mbom_count;
  document.getElementById('errorCount').innerText = data.errors;
  document.getElementById('warningCount').innerText = data.warnings;
  document.getElementById('plainSummary').innerHTML = '<strong>In plain English: </strong>' + data.plain_summary;
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
      <td>${r.is_manufacturing_only ? 'Added for manufacturing' : 'From original design'}</td>
      <td class="explanation">${r.explanation}</td>
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

loadProducts();
loadIssues();
loadMbom();
</script>
</body>
</html>
"""