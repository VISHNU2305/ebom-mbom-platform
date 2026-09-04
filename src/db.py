"""
Persistence layer. Uses SQLite for a self-contained, zero-setup demo —
the schema is written in plain SQL so it maps 1:1 onto a real
PostgreSQL/enterprise-DB deployment with no logic changes, only a
connection-string swap.
"""

import sqlite3
from pathlib import Path

from models import EBOMLine, MBOMLine

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "bom_platform.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS ebom (
    part_number TEXT PRIMARY KEY,
    description TEXT,
    revision TEXT,
    part_type TEXT,
    material TEXT,
    quantity REAL,
    unit TEXT,
    parent_part_number TEXT,
    cad_file_ref TEXT,
    last_modified TEXT
);

CREATE TABLE IF NOT EXISTS mbom (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_number TEXT,
    description TEXT,
    revision TEXT,
    part_type TEXT,
    material TEXT,
    quantity REAL,
    unit TEXT,
    parent_part_number TEXT,
    routing_step TEXT,
    work_center TEXT,
    source_ebom_part_number TEXT,
    is_manufacturing_only INTEGER,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS validation_issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    severity TEXT,
    part_number TEXT,
    issue_type TEXT,
    message TEXT
);
"""


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def reset_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        DELETE FROM ebom;
        DELETE FROM mbom;
        DELETE FROM validation_issues;
    """)
    conn.commit()


def save_ebom(conn: sqlite3.Connection, lines: list[EBOMLine]) -> None:
    conn.executemany(
        """INSERT OR REPLACE INTO ebom
           (part_number, description, revision, part_type, material,
            quantity, unit, parent_part_number, cad_file_ref, last_modified)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        [
            (l.part_number, l.description, l.revision, l.part_type.value,
             l.material, l.quantity, l.unit, l.parent_part_number,
             l.cad_file_ref, l.last_modified.isoformat())
            for l in lines
        ],
    )
    conn.commit()


def save_mbom(conn: sqlite3.Connection, lines: list[MBOMLine]) -> None:
    conn.executemany(
        """INSERT INTO mbom
           (part_number, description, revision, part_type, material,
            quantity, unit, parent_part_number, routing_step, work_center,
            source_ebom_part_number, is_manufacturing_only, notes)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [
            (l.part_number, l.description, l.revision, l.part_type.value,
             l.material, l.quantity, l.unit, l.parent_part_number,
             l.routing_step, l.work_center, l.source_ebom_part_number,
             int(l.is_manufacturing_only), l.notes)
            for l in lines
        ],
    )
    conn.commit()


def save_validation_issues(conn: sqlite3.Connection, issues) -> None:
    conn.executemany(
        """INSERT INTO validation_issues (severity, part_number, issue_type, message)
           VALUES (?,?,?,?)""",
        [(i.severity, i.part_number, i.issue_type, i.message) for i in issues],
    )
    conn.commit()


def query(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    conn.row_factory = sqlite3.Row
    cur = conn.execute(sql, params)
    return [dict(row) for row in cur.fetchall()]
