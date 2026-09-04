"""
Ingestion layer: reads a CSV eBOM export (simulating a PDM/CAD export)
into a list of EBOMLine objects.

Swapping this for a real PDM connector (REST API pull from Windchill /
Teamcenter / SolidWorks PDM) later only requires changing this file —
everything downstream consumes EBOMLine objects, not raw CSV rows.
"""

import csv
from datetime import date
from pathlib import Path

from models import EBOMLine, PartType


def load_ebom_csv(path: Path) -> list[EBOMLine]:
    lines: list[EBOMLine] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lines.append(EBOMLine(
                part_number=row["part_number"],
                description=row["description"],
                revision=row["revision"],
                part_type=PartType(row["part_type"]),
                material=row["material"],
                quantity=float(row["quantity"]),
                unit=row["unit"],
                parent_part_number=row["parent_part_number"] or None,
                cad_file_ref=row["cad_file_ref"] or None,
                last_modified=date.fromisoformat(row["last_modified"]),
            ))
    return lines
