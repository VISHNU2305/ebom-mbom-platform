"""
Generates a realistic sample eBOM dataset to simulate a 3D-CAD/PDM export.

In production this module would be replaced by a real connector
(e.g. reading a Windchill/Teamcenter/SolidWorks PDM export via API or
file drop). The rest of the pipeline is written against the EBOMLine
model, so swapping the source is a one-file change.
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

from models import EBOMLine, PartType

OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_ebom.csv"

MATERIALS = ["S45C Steel", "A5052 Aluminum", "SUS304 Stainless", "ABS Resin", "S355 Structural Steel"]


def build_sample_assembly() -> list[EBOMLine]:
    """
    Builds a small but realistic industrial-equipment assembly tree:
    a gearbox-driven conveyor unit, similar in spirit to material-handling
    equipment (stacker crane / AGV drive units), with 3 levels:
    top assembly -> subassemblies -> components.
    """
    today = date.today()
    lines: list[EBOMLine] = []

    # Top-level assembly
    lines.append(EBOMLine(
        part_number="ASM-1000",
        description="Conveyor Drive Unit Assembly",
        revision="C",
        part_type=PartType.ASSEMBLY,
        material="N/A",
        quantity=1,
        unit="EA",
        parent_part_number=None,
        cad_file_ref="ASM-1000.SLDASM",
        last_modified=today,
    ))

    # Subassemblies
    subassemblies = [
        ("SUB-1100", "Gearbox Subassembly", "B"),
        ("SUB-1200", "Drive Roller Subassembly", "A"),
        ("SUB-1300", "Frame Subassembly", "D"),
    ]
    for pn, desc, rev in subassemblies:
        lines.append(EBOMLine(
            part_number=pn,
            description=desc,
            revision=rev,
            part_type=PartType.SUBASSEMBLY,
            material="N/A",
            quantity=1,
            unit="EA",
            parent_part_number="ASM-1000",
            cad_file_ref=f"{pn}.SLDASM",
            last_modified=today - timedelta(days=random.randint(1, 60)),
        ))

    # Components under each subassembly
    components = [
        ("CMP-1101", "Gearbox Housing", "SUB-1100", "A5052 Aluminum", 1),
        ("CMP-1102", "Output Shaft", "SUB-1100", "S45C Steel", 1),
        ("CMP-1103", "Bevel Gear Set", "SUB-1100", "S45C Steel", 1),
        ("CMP-1201", "Drive Roller Shell", "SUB-1200", "SUS304 Stainless", 1),
        ("CMP-1202", "Roller Bearing Housing", "SUB-1200", "A5052 Aluminum", 2),
        ("CMP-1301", "Side Rail - Left", "SUB-1300", "S355 Structural Steel", 1),
        ("CMP-1302", "Side Rail - Right", "SUB-1300", "S355 Structural Steel", 1),
        ("CMP-1303", "Cross Brace", "SUB-1300", "S355 Structural Steel", 4),
        ("CMP-1304", "Mounting Plate", "SUB-1300", "S355 Structural Steel", 2),
    ]
    for pn, desc, parent, material, qty in components:
        lines.append(EBOMLine(
            part_number=pn,
            description=desc,
            revision=random.choice(["A", "B", "C"]),
            part_type=PartType.COMPONENT,
            material=material,
            quantity=qty,
            unit="EA",
            parent_part_number=parent,
            cad_file_ref=f"{pn}.SLDPRT",
            last_modified=today - timedelta(days=random.randint(1, 90)),
        ))

    return lines


def inject_data_quality_issues(lines: list[EBOMLine]) -> list[EBOMLine]:
    """
    Deliberately injects a few realistic data-quality problems so the
    validation layer has something real to catch — mirrors the kind of
    issues that show up in live PDM exports (stale revisions, orphaned
    parents, duplicate part numbers).
    """
    # 1. Duplicate part number (common copy-paste error in CAD BOMs)
    dup = lines[-1]
    lines.append(EBOMLine(
        part_number=dup.part_number,   # duplicate on purpose
        description=dup.description + " (dup)",
        revision="A",
        part_type=dup.part_type,
        material=dup.material,
        quantity=1,
        unit="EA",
        parent_part_number=dup.parent_part_number,
    ))

    # 2. Orphaned part — parent that doesn't exist in the dataset
    lines.append(EBOMLine(
        part_number="CMP-9999",
        description="Sensor Bracket (orphaned)",
        revision="A",
        part_type=PartType.COMPONENT,
        material="A5052 Aluminum",
        quantity=1,
        unit="EA",
        parent_part_number="SUB-9900",  # does not exist
    ))

    return lines


def write_csv(lines: list[EBOMLine], path: Path = OUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "part_number", "description", "revision", "part_type",
            "material", "quantity", "unit", "parent_part_number",
            "cad_file_ref", "last_modified"
        ])
        for line in lines:
            writer.writerow([
                line.part_number, line.description, line.revision,
                line.part_type.value, line.material, line.quantity,
                line.unit, line.parent_part_number or "",
                line.cad_file_ref or "", line.last_modified.isoformat(),
            ])


if __name__ == "__main__":
    data = build_sample_assembly()
    data = inject_data_quality_issues(data)
    write_csv(data)
    print(f"Wrote {len(data)} eBOM lines to {OUT_PATH}")
