"""Sentinel App - Phase 1.

Internal Sentinel Stacks web application for managing security work items.
Phase 1 uses in-memory sample data only (no database, no authentication).
"""

from flask import Flask, jsonify, render_template

app = Flask(__name__)

APP_TITLE = "Sentinel Stacks — Security Work Management"

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
