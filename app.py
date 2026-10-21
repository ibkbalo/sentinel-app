"""Sentinel App - Phase 1.

Internal Sentinel Stacks web application for managing security work items.
Phase 1 uses in-memory sample data only (no database, no authentication).

Multi-role architecture (future; not implemented in this module yet):
- Staff identity (person) is separate from job role (professional capacity).
- A staff identity may hold multiple authorized roles.
- Departments/teams are distinct from individual staff identities.
- Work items will eventually support assignment to accountable staff and/or
  responsible teams (the legacy free-text ``owner`` field is temporary schema
  compatibility only, not a permanent single-operator model).
- Future activity/audit records must identify the authenticated person and the
  role used for an action.
- A role assignment is not proof of authentication.
- Role-based review and approval permissions belong in a later approved step.
"""

import re

from flask import Flask, jsonify, render_template

app = Flask(__name__)

APP_TITLE = "Sentinel Stacks — Security Work Management"

# Allowed work-item enum values. Exact strings must match sample data and
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


WORK_ITEMS = [
    {
        "id": "SWI-1001",
        "title": "Patch OpenSSL on customer-facing load balancers",
        "category": "Vulnerability Remediation",
        "severity": "Critical",
        "status": "Open",
        "owner": "Priya Natarajan",
    },
    {
        "id": "SWI-1002",
        "title": "Enforce MFA for all VPN user accounts",
        "category": "Security Configuration Change",
        "severity": "High",
        "status": "Awaiting Approval",
        "owner": "Marcus Chen",
    },
    {
        "id": "SWI-1003",
        "title": "Remove public read access from analytics storage bucket",
        "category": "Cloud Security Finding",
        "severity": "Critical",
        "status": "In Progress",
        "owner": "Elena Rodriguez",
    },
    {
        "id": "SWI-1004",
        "title": "Upgrade vulnerable logging library in billing service",
        "category": "DevSecOps Finding",
        "severity": "High",
        "status": "Open",
        "owner": "Daniel Okafor",
    },
    {
        "id": "SWI-1005",
        "title": "Rotate service account keys after phishing incident",
        "category": "Incident Follow-up",
        "severity": "Medium",
        "status": "Completed",
        "owner": "Sarah Lindqvist",
    },
    {
        "id": "SWI-1006",
        "title": "Tighten firewall rules for internal admin subnet",
        "category": "Security Configuration Change",
        "severity": "Medium",
        "status": "Awaiting Approval",
        "owner": "Marcus Chen",
    },
    {
        "id": "SWI-1007",
        "title": "Enable encryption at rest for HR database snapshots",
        "category": "Cloud Security Finding",
        "severity": "High",
        "status": "Completed",
        "owner": "Elena Rodriguez",
    },
    {
        "id": "SWI-1008",
        "title": "Fix hardcoded test credentials flagged in code review",
        "category": "DevSecOps Finding",
        "severity": "Low",
        "status": "In Progress",
        "owner": "Daniel Okafor",
    },
]


def build_summary(items):
    """Compute dashboard summary counts from the work items."""
    return {
        "open": sum(1 for i in items if i["status"] != "Completed"),
        "critical": sum(
            1 for i in items if i["severity"] == "Critical" and i["status"] != "Completed"
        ),
        "awaiting_approval": sum(1 for i in items if i["status"] == "Awaiting Approval"),
        "completed": sum(1 for i in items if i["status"] == "Completed"),
    }


@app.route("/")
def index():
    return render_template("index.html", title=APP_TITLE, summary=build_summary(WORK_ITEMS))


@app.route("/work-items")
def work_items():
    return render_template("work_items.html", title=APP_TITLE, work_items=WORK_ITEMS)


@app.route("/health")
def health():
    return jsonify(status="healthy", service="sentinel-app")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
