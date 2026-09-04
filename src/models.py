"""
Data models for the eBOM -> mBOM conversion platform.

eBOM  = Engineering Bill of Materials (design intent: what the part IS)
mBOM  = Manufacturing Bill of Materials (production intent: how it's BUILT)

These dataclasses mirror the kind of structured export you'd get from a
3D-CAD / PDM system (e.g. part number, revision, material, quantity) and
are intentionally CAD-agnostic so the pipeline can later be pointed at a
real PDM export (SolidWorks PDM, Teamcenter, Windchill, etc.) with only
the ingestion layer needing to change.
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class PartType(str, Enum):
    ASSEMBLY = "ASSEMBLY"
    SUBASSEMBLY = "SUBASSEMBLY"
    COMPONENT = "COMPONENT"
    RAW_MATERIAL = "RAW_MATERIAL"
    FASTENER = "FASTENER"          # manufacturing-only, not in eBOM
    CONSUMABLE = "CONSUMABLE"      # manufacturing-only (e.g. weld wire, lubricant)


@dataclass
class EBOMLine:
    """One row of an engineering BOM, as authored by design/CAD."""
    part_number: str
    description: str
    revision: str
    part_type: PartType
    material: str
    quantity: float
    unit: str                      # EA, KG, M, etc.
    parent_part_number: Optional[str]   # None for the top-level assembly
    cad_file_ref: Optional[str] = None
    last_modified: date = field(default_factory=date.today)


@dataclass
class MBOMLine:
    """
    One row of a manufacturing BOM. A single eBOM line can expand into
    multiple mBOM lines (e.g. a welded bracket assembly -> raw plate +
    fasteners + consumables + the routing step that consumes them).
    """
    part_number: str
    description: str
    revision: str
    part_type: PartType
    material: str
    quantity: float
    unit: str
    parent_part_number: Optional[str]
    routing_step: Optional[str]        # e.g. "10-CUT", "20-WELD", "30-PAINT"
    work_center: Optional[str]         # e.g. "CNC-03", "WELD-BAY-1"
    source_ebom_part_number: Optional[str] = None  # traceability back to eBOM
    is_manufacturing_only: bool = False            # True for fasteners/consumables
    notes: Optional[str] = None


@dataclass
class ValidationIssue:
    severity: str           # "ERROR" | "WARNING"
    part_number: str
    issue_type: str         # e.g. "MISSING_PART", "REVISION_MISMATCH", "DUPLICATE"
    message: str
