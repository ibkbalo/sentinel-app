"""Sentinel App.

Internal Sentinel Stacks web application for managing security work items.

Work items are loaded from SQLite (authoritative store). Schema initialization
is idempotent and does not insert sample or fictional records.

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

from flask import Flask, abort, g, jsonify, render_template

from work_item_store import WorkItemStore, default_database_path
from work_item_validation import (
    CATEGORIES,
    SEVERITIES,
    STATUSES,
    WORK_ITEM_ID_PATTERN,
    normalize_work_item_fields,
    validate_work_item,
)

app = Flask(__name__)

APP_TITLE = "Sentinel Stacks — Security Work Management"

# Re-exported from work_item_validation for existing imports (tests and callers).
__all__ = [
    "CATEGORIES",
    "SEVERITIES",
    "STATUSES",
    "WORK_ITEM_ID_PATTERN",
    "app",
    "build_summary",
    "normalize_work_item_fields",
    "validate_work_item",
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


def get_work_item_store() -> WorkItemStore:
    """Return a request-scoped WorkItemStore; closed on app-context teardown."""
    store = getattr(g, "work_item_store", None)
    if store is None:
        store = WorkItemStore(default_database_path())
        g.work_item_store = store
    return store


@app.teardown_appcontext
def close_work_item_store(exception=None):
    """Close the request-scoped SQLite store connection, if any."""
    store = g.pop("work_item_store", None)
    if store is not None:
        store.close()


def load_display_work_items():
    """Load work items from SQLite for HTML pages (no automatic seeding)."""
    store = get_work_item_store()
    store.initialize_schema()
    return store.list_all()


@app.route("/")
def index():
    try:
        items = load_display_work_items()
    except Exception:
        app.logger.exception("Failed to load work items for dashboard")
        abort(500, description="Unable to load work items.")

    return render_template(
        "index.html",
        title=APP_TITLE,
        summary=build_summary(items),
        is_empty=len(items) == 0,
    )


@app.route("/work-items")
def work_items():
    try:
        items = load_display_work_items()
    except Exception:
        app.logger.exception("Failed to load work items for work-items page")
        abort(500, description="Unable to load work items.")

    return render_template(
        "work_items.html",
        title=APP_TITLE,
        work_items=items,
        is_empty=len(items) == 0,
    )


@app.route("/health")
def health():
    return jsonify(status="healthy", service="sentinel-app")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
