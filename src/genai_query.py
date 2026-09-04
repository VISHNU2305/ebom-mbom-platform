"""
GenAI-assisted query layer — lets an engineer ask natural-language
questions about the BOM data instead of writing SQL.

Design: this is a retrieval-augmented pattern, NOT a raw LLM-guesses-SQL
pattern, because raw text-to-SQL over a manufacturing database is risky
(hallucinated columns, wrong joins). Instead:

  1. A small set of *structured* retrieval functions answer the common
     question types (revision changes, mfg-only parts, validation
     issues, part lineage) directly from the database — this is the
     deterministic, auditable "ground truth" layer.
  2. If an ANTHROPIC_API_KEY is available, the retrieved structured data
     is handed to Claude to be turned into a clear natural-language
     answer. If no key is set, the tool still works — it prints the
     structured result directly, so the pipeline never hard-depends on
     an external API call.

This mirrors how you'd actually want to deploy GenAI inside an
enterprise PDM/ERP system: LLM for *language*, database for *facts*.
"""

import json
import os
from pathlib import Path

import db as db_module

try:
    import requests
except ImportError:
    requests = None


# ---------------------------------------------------------------------
# Structured retrieval functions (the deterministic "ground truth")
# ---------------------------------------------------------------------

def find_manufacturing_only_parts(conn) -> list[dict]:
    return db_module.query(
        conn,
        "SELECT part_number, description, quantity, unit, routing_step "
        "FROM mbom WHERE is_manufacturing_only = 1"
    )


def find_validation_issues(conn, severity: str = None) -> list[dict]:
    if severity:
        return db_module.query(
            conn, "SELECT * FROM validation_issues WHERE severity = ?", (severity,)
        )
    return db_module.query(conn, "SELECT * FROM validation_issues")


def find_part_lineage(conn, part_number: str) -> list[dict]:
    """Walks up the parent chain for a given part number."""
    lineage = []
    current = part_number
    seen = set()
    while current and current not in seen:
        seen.add(current)
        rows = db_module.query(
            conn, "SELECT * FROM ebom WHERE part_number = ?", (current,)
        )
        if not rows:
            break
        lineage.append(rows[0])
        current = rows[0]["parent_part_number"]
    return lineage


def find_routing_for_material(conn, material_keyword: str) -> list[dict]:
    return db_module.query(
        conn,
        "SELECT part_number, description, material, routing_step, work_center "
        "FROM mbom WHERE material LIKE ? AND routing_step IS NOT NULL",
        (f"%{material_keyword}%",),
    )


# ---------------------------------------------------------------------
# Simple intent router — maps a natural-language question to a
# retrieval function. A production version would use embeddings/RAG
# over a larger schema; this keyword router keeps the demo dependency-free.
# ---------------------------------------------------------------------

def route_question(conn, question: str) -> tuple[str, list[dict]]:
    q = question.lower().replace("-", " ")
    if "manufacturing only" in q or "fastener" in q or "consumable" in q:
        return "manufacturing_only_parts", find_manufacturing_only_parts(conn)
    if "error" in q or "warning" in q or "issue" in q or "validation" in q:
        return "validation_issues", find_validation_issues(conn)
    if "steel" in q or "aluminum" in q or "stainless" in q or "resin" in q:
        for material in ["steel", "aluminum", "stainless", "resin"]:
            if material in q:
                return "routing_for_material", find_routing_for_material(conn, material)
    # fallback: try to detect a part number pattern like ASM-1000 / CMP-1101
    import re
    match = re.search(r"[A-Z]{2,4}-\d{3,5}", question.upper())
    if match:
        return "part_lineage", find_part_lineage(conn, match.group(0))
    return "unknown", []


# ---------------------------------------------------------------------
# Optional LLM summarization layer
# ---------------------------------------------------------------------

def summarize_with_claude(question: str, retrieved_data: list[dict]) -> str | None:
    """
    Calls the Anthropic API to turn structured retrieval results into a
    natural-language answer. Returns None if no API key is configured
    or the call fails, so callers can gracefully fall back to raw data.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or requests is None:
        return None

    prompt = (
        "You are a manufacturing-engineering assistant embedded in a PDM system. "
        "Answer the user's question in 2-4 concise sentences, using ONLY the "
        "structured data provided. Do not invent part numbers or values.\n\n"
        f"Question: {question}\n\n"
        f"Retrieved data (JSON):\n{json.dumps(retrieved_data, indent=2)}"
    )
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=20,
        )
        resp.raise_for_status()
        content = resp.json()["content"]
        return "".join(block.get("text", "") for block in content)
    except Exception as e:
        return f"[LLM summarization unavailable: {e}]"


def answer_question(conn, question: str) -> str:
    intent, data = route_question(conn, question)

    if intent == "unknown" or not data:
        return (
            "I couldn't find data matching that question. Try asking about "
            "manufacturing-only parts, validation issues, routing for a "
            "specific material, or a specific part number (e.g. 'ASM-1000')."
        )

    llm_answer = summarize_with_claude(question, data)
    if llm_answer:
        return llm_answer

    # Fallback: deterministic, readable summary with no LLM dependency
    lines = [f"Found {len(data)} result(s) for intent '{intent}':"]
    for row in data[:10]:
        lines.append("  - " + ", ".join(f"{k}={v}" for k, v in row.items() if v not in (None, "")))
    return "\n".join(lines)
