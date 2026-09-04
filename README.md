# eBOM → mBOM Conversion Platform

A rule-based platform that converts Engineering Bills of Materials (eBOM) into Manufacturing Bills of Materials (mBOM), with built-in data validation and a natural-language query interface powered by GenAI.

**Live demo:** _[add your Render URL here once deployed]_

---

## Problem

When a product is designed in CAD, engineers produce an eBOM — a list of parts as *designed*. But manufacturing needs an mBOM: the same parts, plus everything the factory floor actually needs to build it (fasteners, weld consumables, machine routing, work centers) — none of which exist in the original CAD data.

Converting eBOM → mBOM is traditionally a manual, error-prone process. This project automates it, catches data-integrity issues before they reach the shop floor, and lets engineers query the results in plain English instead of digging through spreadsheets.

## What it does

1. **Ingests** an eBOM export (simulating a 3D-CAD/PDM system output)
2. **Validates** the data — catches duplicate part numbers, orphaned parts, missing materials, and other integrity issues *before* conversion
3. **Converts** eBOM → mBOM using explicit, auditable manufacturing rules (routing steps by material family, automatic fastener/consumable injection for structural parts)
4. **Persists** everything to a database
5. **Answers natural-language questions** about the data (e.g. "what are the manufacturing-only parts?") using a retrieval-grounded GenAI layer — the LLM only summarizes real retrieved data, never invents facts
6. **Displays** all of this through a live web dashboard

## Why rule-based, not ML, for the conversion logic

Manufacturing decisions need to be auditable — an engineer needs to know *why* a part was added. A black-box ML model can't reliably explain itself; a fixed rule set can. The conversion engine is intentionally deterministic. GenAI is used only where explainability matters less: turning already-correct data into readable language.

## Architecture

CAD/PDM export (CSV)
→ ingest.py (reads into structured objects)
→ validator.py (data-integrity checks)
→ conversion_engine.py (eBOM → mBOM, rule-based)
→ db.py (SQLite persistence)
→ genai_query.py (natural-language Q&A, retrieval-grounded)
→ web_ui.py (FastAPI + dashboard)


## Tech stack

Python · FastAPI · SQLite · Anthropic API (optional, graceful fallback if no key set)

## Running locally

```bash
pip install -r requirements.txt
cd src
python main.py setup      # generate sample data
python main.py run        # run the full pipeline
uvicorn web_ui:app --reload
```
Then open `http://127.0.0.1:8000`

## Known limitations

- Sample eBOM data is synthetically generated, not pulled from a real PDM system (the `ingest.py` layer is designed so a real PDM connector could be swapped in without touching downstream logic)
- Manufacturing rules cover a small set of material families as a proof of concept

