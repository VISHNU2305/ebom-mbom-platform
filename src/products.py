"""
Sample product catalog.

Multiple example products, chosen to reflect the kind of equipment a
company like Shibaura Machine actually manufactures (machine tools,
injection molding machines, industrial robots). Each product follows
the exact same assembly-tree structure as the original — this proves
the pipeline is fully data-driven: switching products never requires
touching validation, conversion, or query logic, only the input data.
"""

import random
from datetime import date, timedelta

from models import EBOMLine, PartType


def _d(days_ago: int) -> date:
    return date.today() - timedelta(days=days_ago)


PRODUCTS = {
    "conveyor": {
        "name": "Conveyor Drive Unit",
        "description": "Material-handling conveyor drive mechanism",
    },
    "cnc_spindle": {
        "name": "CNC Machine Tool Spindle Assembly",
        "description": "Precision spindle unit for a CNC machining center",
    },
    "injection_clamp": {
        "name": "Injection Molding Clamping Unit",
        "description": "Clamping mechanism for a plastic injection molding machine",
    },
    "robot_joint": {
        "name": "Industrial Robot Arm Joint",
        "description": "Rotary joint module for a 6-axis industrial robot arm",
    },
}


def build_product(product_id: str) -> list[EBOMLine]:
    builders = {
        "conveyor": _build_conveyor,
        "cnc_spindle": _build_cnc_spindle,
        "injection_clamp": _build_injection_clamp,
        "robot_joint": _build_robot_joint,
    }
    if product_id not in builders:
        raise ValueError(f"Unknown product_id: {product_id}")
    return builders[product_id]()


def _build_conveyor() -> list[EBOMLine]:
    lines = [
        EBOMLine("ASM-1000", "Conveyor Drive Unit Assembly", "C", PartType.ASSEMBLY,
                 "N/A", 1, "EA", None, "ASM-1000.SLDASM", _d(3)),
        EBOMLine("SUB-1100", "Gearbox Subassembly", "B", PartType.SUBASSEMBLY,
                 "N/A", 1, "EA", "ASM-1000", "SUB-1100.SLDASM", _d(20)),
        EBOMLine("SUB-1200", "Drive Roller Subassembly", "A", PartType.SUBASSEMBLY,
                 "N/A", 1, "EA", "ASM-1000", "SUB-1200.SLDASM", _d(15)),
        EBOMLine("SUB-1300", "Frame Subassembly", "D", PartType.SUBASSEMBLY,
                 "N/A", 1, "EA", "ASM-1000", "SUB-1300.SLDASM", _d(30)),
    ]
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
    for pn, desc, parent, mat, qty in components:
        lines.append(EBOMLine(pn, desc, random.choice(["A", "B", "C"]), PartType.COMPONENT,
                               mat, qty, "EA", parent, f"{pn}.SLDPRT", _d(random.randint(1, 90))))
    return lines


def _build_cnc_spindle() -> list[EBOMLine]:
    lines = [
        EBOMLine("ASM-2000", "CNC Spindle Assembly", "B", PartType.ASSEMBLY,
                 "N/A", 1, "EA", None, "ASM-2000.SLDASM", _d(5)),
        EBOMLine("SUB-2100", "Spindle Housing Subassembly", "A", PartType.SUBASSEMBLY,
                 "N/A", 1, "EA", "ASM-2000", "SUB-2100.SLDASM", _d(10)),
        EBOMLine("SUB-2200", "Bearing Pack Subassembly", "B", PartType.SUBASSEMBLY,
                 "N/A", 1, "EA", "ASM-2000", "SUB-2200.SLDASM", _d(8)),
        EBOMLine("SUB-2300", "Motor Mount Subassembly", "A", PartType.SUBASSEMBLY,
                 "N/A", 1, "EA", "ASM-2000", "SUB-2300.SLDASM", _d(12)),
    ]
    components = [
        ("CMP-2101", "Spindle Housing Body", "SUB-2100", "S355 Structural Steel", 1),
        ("CMP-2102", "Housing End Cap", "SUB-2100", "A5052 Aluminum", 2),
        ("CMP-2201", "Precision Bearing Race", "SUB-2200", "SUS304 Stainless", 2),
        ("CMP-2202", "Bearing Retainer Ring", "SUB-2200", "SUS304 Stainless", 2),
        ("CMP-2301", "Motor Mount Plate", "SUB-2300", "S355 Structural Steel", 1),
        ("CMP-2302", "Vibration Damper Pad", "SUB-2300", "ABS Resin", 4),
    ]
    for pn, desc, parent, mat, qty in components:
        lines.append(EBOMLine(pn, desc, random.choice(["A", "B", "C"]), PartType.COMPONENT,
                               mat, qty, "EA", parent, f"{pn}.SLDPRT", _d(random.randint(1, 90))))
    return lines


def _build_injection_clamp() -> list[EBOMLine]:
    lines = [
        EBOMLine("ASM-3000", "Injection Molding Clamping Unit", "A", PartType.ASSEMBLY,
                 "N/A", 1, "EA", None, "ASM-3000.SLDASM", _d(2)),
        EBOMLine("SUB-3100", "Clamping Frame Subassembly", "B", PartType.SUBASSEMBLY,
                 "N/A", 1, "EA", "ASM-3000", "SUB-3100.SLDASM", _d(18)),
        EBOMLine("SUB-3200", "Toggle Linkage Subassembly", "A", PartType.SUBASSEMBLY,
                 "N/A", 1, "EA", "ASM-3000", "SUB-3200.SLDASM", _d(14)),
        EBOMLine("SUB-3300", "Mold Platen Subassembly", "C", PartType.SUBASSEMBLY,
                 "N/A", 1, "EA", "ASM-3000", "SUB-3300.SLDASM", _d(25)),
    ]
    components = [
        ("CMP-3101", "Frame Tie Bar", "SUB-3100", "S355 Structural Steel", 4),
        ("CMP-3102", "Frame Base Plate", "SUB-3100", "S355 Structural Steel", 1),
        ("CMP-3201", "Toggle Link Arm", "SUB-3200", "S45C Steel", 4),
        ("CMP-3202", "Toggle Pivot Pin", "SUB-3200", "SUS304 Stainless", 4),
        ("CMP-3301", "Fixed Mold Platen", "SUB-3300", "S355 Structural Steel", 1),
        ("CMP-3302", "Moving Mold Platen", "SUB-3300", "S355 Structural Steel", 1),
        ("CMP-3303", "Platen Guide Bushing", "SUB-3300", "A5052 Aluminum", 4),
    ]
    for pn, desc, parent, mat, qty in components:
        lines.append(EBOMLine(pn, desc, random.choice(["A", "B", "C"]), PartType.COMPONENT,
                               mat, qty, "EA", parent, f"{pn}.SLDPRT", _d(random.randint(1, 90))))
    return lines


def _build_robot_joint() -> list[EBOMLine]:
    lines = [
        EBOMLine("ASM-4000", "Robot Arm Joint Module", "D", PartType.ASSEMBLY,
                 "N/A", 1, "EA", None, "ASM-4000.SLDASM", _d(1)),
        EBOMLine("SUB-4100", "Joint Housing Subassembly", "B", PartType.SUBASSEMBLY,
                 "N/A", 1, "EA", "ASM-4000", "SUB-4100.SLDASM", _d(22)),
        EBOMLine("SUB-4200", "Harmonic Drive Subassembly", "A", PartType.SUBASSEMBLY,
                 "N/A", 1, "EA", "ASM-4000", "SUB-4200.SLDASM", _d(9)),
        EBOMLine("SUB-4300", "Servo Motor Mount Subassembly", "C", PartType.SUBASSEMBLY,
                 "N/A", 1, "EA", "ASM-4000", "SUB-4300.SLDASM", _d(16)),
    ]
    components = [
        ("CMP-4101", "Joint Outer Housing", "SUB-4100", "A5052 Aluminum", 1),
        ("CMP-4102", "Joint Inner Housing", "SUB-4100", "A5052 Aluminum", 1),
        ("CMP-4201", "Harmonic Drive Gear", "SUB-4200", "S45C Steel", 1),
        ("CMP-4202", "Flex Spline", "SUB-4200", "SUS304 Stainless", 1),
        ("CMP-4301", "Servo Mount Bracket", "SUB-4300", "S355 Structural Steel", 1),
        ("CMP-4302", "Cable Routing Cover", "SUB-4300", "ABS Resin", 2),
    ]
    for pn, desc, parent, mat, qty in components:
        lines.append(EBOMLine(pn, desc, random.choice(["A", "B", "C"]), PartType.COMPONENT,
                               mat, qty, "EA", parent, f"{pn}.SLDPRT", _d(random.randint(1, 90))))
    return lines