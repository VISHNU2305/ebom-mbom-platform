"""
Validation layer for eBOM data, run BEFORE conversion to mBOM.

This is the "data integrity / governance" piece that maps to Shibaura's
emphasis on centrally managing product technical information and
strengthening governance around company systems. Catching bad data
before it reaches manufacturing prevents costly downstream errors
(wrong parts ordered, mismatched revisions on the shop floor, etc.)
"""

from collections import defaultdict

from models import EBOMLine, ValidationIssue


def validate_ebom(lines: list[EBOMLine]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    part_numbers_seen = defaultdict(list)
    all_part_numbers = {line.part_number for line in lines}

    for line in lines:
        part_numbers_seen[line.part_number].append(line)

    # --- Rule 1: Duplicate part numbers -------------------------------
    for pn, occurrences in part_numbers_seen.items():
        if len(occurrences) > 1:
            issues.append(ValidationIssue(
                severity="ERROR",
                part_number=pn,
                issue_type="DUPLICATE_PART_NUMBER",
                message=(
                    f"Part number '{pn}' appears {len(occurrences)} times "
                    f"in the eBOM. Each part number must be unique."
                ),
            ))

    # --- Rule 2: Orphaned parts (parent doesn't exist) -----------------
    for line in lines:
        if line.parent_part_number and line.parent_part_number not in all_part_numbers:
            issues.append(ValidationIssue(
                severity="ERROR",
                part_number=line.part_number,
                issue_type="ORPHANED_PART",
                message=(
                    f"Part '{line.part_number}' references parent "
                    f"'{line.parent_part_number}', which does not exist "
                    f"anywhere in the eBOM."
                ),
            ))

    # --- Rule 3: Missing / placeholder material on physical parts ------
    for line in lines:
        if line.part_type.value in ("COMPONENT", "RAW_MATERIAL") and (
            not line.material or line.material.strip().upper() in ("N/A", "TBD", "")
        ):
            issues.append(ValidationIssue(
                severity="WARNING",
                part_number=line.part_number,
                issue_type="MISSING_MATERIAL",
                message=f"Part '{line.part_number}' has no material specified.",
            ))

    # --- Rule 4: Zero or negative quantity ------------------------------
    for line in lines:
        if line.quantity <= 0:
            issues.append(ValidationIssue(
                severity="ERROR",
                part_number=line.part_number,
                issue_type="INVALID_QUANTITY",
                message=f"Part '{line.part_number}' has non-positive quantity ({line.quantity}).",
            ))

    # --- Rule 5: Stale revision naming pattern check --------------------
    # (simple sanity check: revision should be a single uppercase letter
    #  or a numeric string — catches CAD export corruption)
    for line in lines:
        rev = line.revision.strip()
        if not (rev.isalpha() and rev.isupper() and len(rev) <= 2) and not rev.isdigit():
            issues.append(ValidationIssue(
                severity="WARNING",
                part_number=line.part_number,
                issue_type="REVISION_FORMAT",
                message=f"Part '{line.part_number}' has an unusual revision format: '{rev}'.",
            ))

    return issues


def print_report(issues: list[ValidationIssue]) -> None:
    errors = [i for i in issues if i.severity == "ERROR"]
    warnings = [i for i in issues if i.severity == "WARNING"]

    print(f"\n=== Validation Report: {len(errors)} error(s), {len(warnings)} warning(s) ===")
    for issue in issues:
        print(f"[{issue.severity}] {issue.issue_type} — {issue.part_number}: {issue.message}")
    if not issues:
        print("No issues found. eBOM is clean.")
