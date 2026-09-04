"""
Main pipeline orchestrator.

Run modes:
  python main.py setup      -> generates sample eBOM data
  python main.py run        -> ingest -> validate -> convert -> persist
  python main.py ask "..."  -> ask a natural-language question over the data
  python main.py report     -> print eBOM/mBOM/validation summary
"""

import sys
from pathlib import Path

import db as db_module
import generate_sample_data
import genai_query
from conversion_engine import convert_ebom_to_mbom
from ingest import load_ebom_csv
from validator import print_report, validate_ebom

DATA_CSV = Path(__file__).resolve().parent.parent / "data" / "sample_ebom.csv"


def cmd_setup():
    lines = generate_sample_data.build_sample_assembly()
    lines = generate_sample_data.inject_data_quality_issues(lines)
    generate_sample_data.write_csv(lines)
    print(f"Sample eBOM written to {DATA_CSV} ({len(lines)} lines).")


def cmd_run():
    if not DATA_CSV.exists():
        print("No sample data found — run `python main.py setup` first.")
        return

    print("Step 1/4: Ingesting eBOM export...")
    ebom_lines = load_ebom_csv(DATA_CSV)
    print(f"  Loaded {len(ebom_lines)} eBOM lines.")

    print("\nStep 2/4: Validating eBOM data integrity...")
    issues = validate_ebom(ebom_lines)
    print_report(issues)

    print("\nStep 3/4: Converting eBOM -> mBOM...")
    mbom_lines = convert_ebom_to_mbom(ebom_lines)
    mfg_only = sum(1 for l in mbom_lines if l.is_manufacturing_only)
    print(f"  Generated {len(mbom_lines)} mBOM lines "
          f"({mfg_only} manufacturing-only lines auto-injected).")

    print("\nStep 4/4: Persisting to database...")
    conn = db_module.get_connection()
    db_module.reset_tables(conn)
    db_module.save_ebom(conn, ebom_lines)
    db_module.save_mbom(conn, mbom_lines)
    db_module.save_validation_issues(conn, issues)
    conn.close()
    print(f"  Saved to {db_module.DB_PATH}")

    print("\nPipeline complete. Try: python main.py ask \"what are the manufacturing-only parts?\"")


def cmd_ask(question: str):
    conn = db_module.get_connection()
    answer = genai_query.answer_question(conn, question)
    conn.close()
    print(f"\nQ: {question}\n\nA: {answer}\n")


def cmd_report():
    conn = db_module.get_connection()
    ebom_count = db_module.query(conn, "SELECT COUNT(*) as c FROM ebom")[0]["c"]
    mbom_count = db_module.query(conn, "SELECT COUNT(*) as c FROM mbom")[0]["c"]
    errors = db_module.query(conn, "SELECT COUNT(*) as c FROM validation_issues WHERE severity='ERROR'")[0]["c"]
    warnings = db_module.query(conn, "SELECT COUNT(*) as c FROM validation_issues WHERE severity='WARNING'")[0]["c"]
    mfg_only = db_module.query(conn, "SELECT COUNT(*) as c FROM mbom WHERE is_manufacturing_only=1")[0]["c"]
    conn.close()

    print("=== BOM Platform Summary ===")
    print(f"eBOM lines:              {ebom_count}")
    print(f"mBOM lines:               {mbom_count}")
    print(f"  of which mfg-only:      {mfg_only}")
    print(f"Validation errors:        {errors}")
    print(f"Validation warnings:      {warnings}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    command = sys.argv[1]
    if command == "setup":
        cmd_setup()
    elif command == "run":
        cmd_run()
    elif command == "ask":
        if len(sys.argv) < 3:
            print("Usage: python main.py ask \"your question here\"")
        else:
            cmd_ask(sys.argv[2])
    elif command == "report":
        cmd_report()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
