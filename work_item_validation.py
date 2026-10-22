"""Shared work-item normalization and validation for Sentinel App.

Used by Flask (`app.py`) and SQLite persistence (`work_item_store.py`) so those
modules do not import each other for validation. This module has no Flask or
database dependencies.
"""

import re

# Allowed work-item enum values. Exact strings must match
# build_summary() comparisons (status/severity literals).
CATEGORIES = (
    "Vulnerability Remediation",
    "Security Configuration Change",
    "Cloud Security Finding",
    "DevSecOps Finding",
    "Incident Follow-up",
)

SEVERITIES = ("Critical", "High", "Medium", "Low")

STATUSES = ("Open", "In Progress", "Awaiting Approval", "Completed")

WORK_ITEM_ID_PATTERN = re.compile(r"^SWI-[0-9]+$")

_STRING_FIELDS = ("id", "title", "category", "severity", "status", "owner")


def normalize_work_item_fields(item):
    """Return a new work-item dict with string fields whitespace-stripped.

    Preserves field names and case. Does not mutate ``item``. Does not remap
    or replace invalid enum values. Non-string values are copied unchanged.
    """
    if not isinstance(item, dict):
        raise TypeError("work item must be a dictionary")

    normalized = dict(item)
    for field in _STRING_FIELDS:
        if field not in normalized:
            continue
        value = normalized[field]
        if isinstance(value, str):
            normalized[field] = value.strip()
    return normalized


def validate_work_item(item, *, existing_ids=None, require_id=True):
    """Validate a work-item dict; return a list of descriptive error messages.

    ``owner`` is validated as non-empty free text for legacy schema compatibility
    only. Future assignment will use distinct staff identity / role / team
    references; this check is not a permanent single-operator assumption.
    """
    errors = []

    if not isinstance(item, dict):
        return ["Work item must be a dictionary"]

    normalized = normalize_work_item_fields(item)

    if require_id:
        if "id" not in item:
            errors.append("Missing required field: id")
        else:
            work_id = normalized.get("id")
            if not isinstance(work_id, str):
                errors.append("id must be a string")
            elif not WORK_ITEM_ID_PATTERN.fullmatch(work_id):
                errors.append("id must match SWI-<digits> (for example SWI-1001)")
            elif existing_ids is not None and work_id in existing_ids:
                errors.append(f"Duplicate work-item id: {work_id}")

    if "title" not in item:
        errors.append("Missing required field: title")
    else:
        title = normalized.get("title")
        if not isinstance(title, str):
            errors.append("title must be a string")
        elif not title:
            errors.append("title must contain non-whitespace text")

    # Legacy free-text owner (temporary). Not a staff-identity or role model.
    if "owner" not in item:
        errors.append("Missing required field: owner")
    else:
        owner = normalized.get("owner")
        if not isinstance(owner, str):
            errors.append("owner must be a string")
        elif not owner:
            errors.append("owner must contain non-whitespace text")

    if "category" not in item:
        errors.append("Missing required field: category")
    else:
        category = normalized.get("category")
        if not isinstance(category, str):
            errors.append("category must be a string")
        elif category not in CATEGORIES:
            errors.append("category is not an allowed value")

    if "severity" not in item:
        errors.append("Missing required field: severity")
    else:
        severity = normalized.get("severity")
        if not isinstance(severity, str):
            errors.append("severity must be a string")
        elif severity not in SEVERITIES:
            errors.append("severity is not an allowed value")

    if "status" not in item:
        errors.append("Missing required field: status")
    else:
        status = normalized.get("status")
        if not isinstance(status, str):
            errors.append("status must be a string")
        elif status not in STATUSES:
            errors.append("status is not an allowed value")

    return errors
