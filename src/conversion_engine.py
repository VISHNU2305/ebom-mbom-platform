"""
Core conversion engine: eBOM -> mBOM.

An eBOM describes design intent (what a part IS). An mBOM describes
production intent (how it's BUILT): it adds manufacturing-only items
(fasteners, consumables, treatments, inspections) and routing/work-center
information that never existed in the CAD model at all.

This engine is rule-based rather than a black box, by design — in a
real PDM/ERP integration, manufacturing engineers need to be able to
audit *why* a line was added or changed, which a pure ML model can't
give you. The rules below encode common manufacturing-engineering
knowledge: different materials and part types need different downstream
treatments (welding needs shielding gas, aluminum needs anodizing,
stainless needs passivation, bearings need lubrication, precision
rotating parts need inspection sign-off, etc.)
"""

from models import EBOMLine, MBOMLine, PartType

# Routing templates keyed by material family — a simplified stand-in for
# a real manufacturing process-planning ruleset.
ROUTING_RULES = {
    "Steel":     [("10-CUT", "SAW-01"), ("20-MACHINE", "CNC-02"), ("30-PAINT", "PAINT-BAY")],
    "Aluminum":  [("10-MACHINE", "CNC-01"), ("20-DEBURR", "FINISH-01")],
    "Stainless": [("10-MACHINE", "CNC-03"), ("20-POLISH", "FINISH-02")],
    "Resin":     [("10-MOLD", "INJ-MOLD-01")],
}

FASTENER_RULE_MATERIALS = {"S355 Structural Steel"}


def _routing_family(material: str) -> str:
    material_lower = material.lower()
    if "steel" in material_lower and "stainless" not in material_lower:
        return "Steel"
    if "aluminum" in material_lower:
        return "Aluminum"
    if "stainless" in material_lower:
        return "Stainless"
    if "resin" in material_lower or "abs" in material_lower:
        return "Resin"
    return "Steel"


def convert_line(ebom_line: EBOMLine) -> list[MBOMLine]:
    """Converts a single eBOM line into one or more mBOM lines."""
    results: list[MBOMLine] = []

    # Assemblies and subassemblies pass through mostly unchanged.
    if ebom_line.part_type in (PartType.ASSEMBLY, PartType.SUBASSEMBLY):
        results.append(MBOMLine(
            part_number=ebom_line.part_number,
            description=ebom_line.description,
            revision=ebom_line.revision,
            part_type=ebom_line.part_type,
            material=ebom_line.material,
            quantity=ebom_line.quantity,
            unit=ebom_line.unit,
            parent_part_number=ebom_line.parent_part_number,
            routing_step=None,
            work_center=None,
            source_ebom_part_number=ebom_line.part_number,
        ))
        return results

    # Physical components get a routing step assigned based on material
    family = _routing_family(ebom_line.material)
    routing_steps = ROUTING_RULES.get(family, ROUTING_RULES["Steel"])
    final_step, final_wc = routing_steps[-1]

    results.append(MBOMLine(
        part_number=ebom_line.part_number,
        description=ebom_line.description,
        revision=ebom_line.revision,
        part_type=ebom_line.part_type,
        material=ebom_line.material,
        quantity=ebom_line.quantity,
        unit=ebom_line.unit,
        parent_part_number=ebom_line.parent_part_number,
        routing_step=final_step,
        work_center=final_wc,
        source_ebom_part_number=ebom_line.part_number,
        notes=f"Routing: {' -> '.join(s for s, _ in routing_steps)}",
    ))

    # ---- Structural steel: fasteners + weld wire + shielding gas ----
    if ebom_line.material in FASTENER_RULE_MATERIALS:
        results.append(MBOMLine(
            part_number=f"{ebom_line.part_number}-BOLT-M8",
            description=f"M8x25 Hex Bolt (for {ebom_line.description})",
            revision="-", part_type=PartType.FASTENER,
            material="Steel, Zinc Plated", quantity=4 * ebom_line.quantity,
            unit="EA", parent_part_number=ebom_line.parent_part_number,
            routing_step="20-ASSEMBLE", work_center="ASSY-01",
            source_ebom_part_number=None, is_manufacturing_only=True,
            notes="Auto-injected: structural steel parts require fastener kit.",
        ))
        results.append(MBOMLine(
            part_number=f"{ebom_line.part_number}-WELD-WIRE",
            description=f"Welding Wire Allocation (for {ebom_line.description})",
            revision="-", part_type=PartType.CONSUMABLE,
            material="ER70S-6", quantity=0.05 * ebom_line.quantity,
            unit="KG", parent_part_number=ebom_line.parent_part_number,
            routing_step="10-WELD", work_center="WELD-BAY-1",
            source_ebom_part_number=None, is_manufacturing_only=True,
            notes="Auto-injected: structural steel parts require weld consumable allocation.",
        ))
        results.append(MBOMLine(
            part_number=f"{ebom_line.part_number}-SHIELD-GAS",
            description=f"Shielding Gas Allocation (for {ebom_line.description})",
            revision="-", part_type=PartType.CONSUMABLE,
            material="Argon/CO2 Mix", quantity=0.3 * ebom_line.quantity,
            unit="M3", parent_part_number=ebom_line.parent_part_number,
            routing_step="10-WELD", work_center="WELD-BAY-1",
            source_ebom_part_number=None, is_manufacturing_only=True,
            notes="Auto-injected: welding requires shielding gas to protect the weld pool.",
        ))

    # ---- Aluminum: anodizing + alignment dowels ----
    if "Aluminum" in ebom_line.material:
        results.append(MBOMLine(
            part_number=f"{ebom_line.part_number}-ANODIZE",
            description=f"Anodizing Treatment (for {ebom_line.description})",
            revision="-", part_type=PartType.CONSUMABLE,
            material="Anodizing Chemical Bath", quantity=1 * ebom_line.quantity,
            unit="EA", parent_part_number=ebom_line.parent_part_number,
            routing_step="30-FINISH", work_center="ANODIZE-01",
            source_ebom_part_number=None, is_manufacturing_only=True,
            notes="Auto-injected: aluminum parts require anodizing for corrosion resistance.",
        ))
        results.append(MBOMLine(
            part_number=f"{ebom_line.part_number}-DOWEL",
            description=f"Alignment Dowel Pin (for {ebom_line.description})",
            revision="-", part_type=PartType.FASTENER,
            material="Steel, Hardened", quantity=2 * ebom_line.quantity,
            unit="EA", parent_part_number=ebom_line.parent_part_number,
            routing_step="20-ASSEMBLE", work_center="ASSY-01",
            source_ebom_part_number=None, is_manufacturing_only=True,
            notes="Auto-injected: precision aluminum housings need dowels for alignment.",
        ))

    # ---- Stainless steel: passivation ----
    if "Stainless" in ebom_line.material or "SUS" in ebom_line.material:
        results.append(MBOMLine(
            part_number=f"{ebom_line.part_number}-PASSIVATE",
            description=f"Passivation Treatment (for {ebom_line.description})",
            revision="-", part_type=PartType.CONSUMABLE,
            material="Nitric Acid Solution", quantity=1 * ebom_line.quantity,
            unit="EA", parent_part_number=ebom_line.parent_part_number,
            routing_step="30-FINISH", work_center="TREAT-01",
            source_ebom_part_number=None, is_manufacturing_only=True,
            notes="Auto-injected: stainless steel requires passivation to prevent corrosion.",
        ))

    # ---- Resin/plastic: mold release agent ----
    if "Resin" in ebom_line.material or "ABS" in ebom_line.material:
        results.append(MBOMLine(
            part_number=f"{ebom_line.part_number}-RELEASE-AGENT",
            description=f"Mold Release Agent (for {ebom_line.description})",
            revision="-", part_type=PartType.CONSUMABLE,
            material="Silicone Release Compound", quantity=0.02 * ebom_line.quantity,
            unit="KG", parent_part_number=ebom_line.parent_part_number,
            routing_step="10-MOLD", work_center="INJ-MOLD-01",
            source_ebom_part_number=None, is_manufacturing_only=True,
            notes="Auto-injected: injection molding requires release agent.",
        ))

    # ---- Bearings: lubricant ----
    if "Bearing" in ebom_line.description:
        results.append(MBOMLine(
            part_number=f"{ebom_line.part_number}-GREASE",
            description=f"Lubricant Grease (for {ebom_line.description})",
            revision="-", part_type=PartType.CONSUMABLE,
            material="Industrial Bearing Grease", quantity=0.01 * ebom_line.quantity,
            unit="KG", parent_part_number=ebom_line.parent_part_number,
            routing_step="20-ASSEMBLE", work_center="ASSY-01",
            source_ebom_part_number=None, is_manufacturing_only=True,
            notes="Auto-injected: bearings require lubrication before assembly.",
        ))

    # ---- Housings: gasket/seal ----
    if "Housing" in ebom_line.description:
        results.append(MBOMLine(
            part_number=f"{ebom_line.part_number}-GASKET",
            description=f"Sealing Gasket (for {ebom_line.description})",
            revision="-", part_type=PartType.CONSUMABLE,
            material="Nitrile Rubber", quantity=1 * ebom_line.quantity,
            unit="EA", parent_part_number=ebom_line.parent_part_number,
            routing_step="20-ASSEMBLE", work_center="ASSY-01",
            source_ebom_part_number=None, is_manufacturing_only=True,
            notes="Auto-injected: housings require a gasket to seal out dust/moisture.",
        ))

    # ---- Gears/Shafts: quality inspection sign-off ----
    if "Gear" in ebom_line.description or "Shaft" in ebom_line.description:
        results.append(MBOMLine(
            part_number=f"{ebom_line.part_number}-QC-CERT",
            description=f"Dimensional Inspection Certificate (for {ebom_line.description})",
            revision="-", part_type=PartType.CONSUMABLE,
            material="N/A - Quality Record", quantity=1,
            unit="EA", parent_part_number=ebom_line.parent_part_number,
            routing_step="40-INSPECT", work_center="QC-LAB",
            source_ebom_part_number=None, is_manufacturing_only=True,
            notes="Auto-injected: precision rotating parts require dimensional inspection sign-off.",
        ))

    return results


def convert_ebom_to_mbom(ebom_lines: list[EBOMLine]) -> list[MBOMLine]:
    mbom_lines: list[MBOMLine] = []
    for line in ebom_lines:
        mbom_lines.extend(convert_line(line))
    return mbom_lines