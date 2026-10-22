"""Synthetic work-item fixtures for tests only (not used by production code)."""

from app import CATEGORIES, SEVERITIES, STATUSES

# Deliberately mirrors the former demo status mix so summary math stays covered.
SYNTHETIC_WORK_ITEMS = [
    {
        "id": "SWI-9001",
        "title": "Test: patch critical service dependency",
        "category": CATEGORIES[0],
        "severity": SEVERITIES[0],
        "status": STATUSES[0],
        "owner": "Test Owner Alpha",
    },
    {
        "id": "SWI-9002",
        "title": "Test: enforce MFA on privileged accounts",
        "category": CATEGORIES[1],
        "severity": SEVERITIES[1],
        "status": STATUSES[2],
        "owner": "Test Owner Beta",
    },
    {
        "id": "SWI-9003",
        "title": "Test: remove public cloud storage access",
        "category": CATEGORIES[2],
        "severity": SEVERITIES[0],
        "status": STATUSES[1],
        "owner": "Test Owner Gamma",
    },
    {
        "id": "SWI-9004",
        "title": "Test: upgrade vulnerable application library",
        "category": CATEGORIES[3],
        "severity": SEVERITIES[1],
        "status": STATUSES[0],
        "owner": "Test Owner Delta",
    },
    {
        "id": "SWI-9005",
        "title": "Test: complete incident key rotation",
        "category": CATEGORIES[4],
        "severity": SEVERITIES[2],
        "status": STATUSES[3],
        "owner": "Test Owner Epsilon",
    },
    {
        "id": "SWI-9006",
        "title": "Test: tighten internal firewall rules",
        "category": CATEGORIES[1],
        "severity": SEVERITIES[2],
        "status": STATUSES[2],
        "owner": "Test Owner Beta",
    },
    {
        "id": "SWI-9007",
        "title": "Test: enable encryption for database snapshots",
        "category": CATEGORIES[2],
        "severity": SEVERITIES[1],
        "status": STATUSES[3],
        "owner": "Test Owner Gamma",
    },
    {
        "id": "SWI-9008",
        "title": "Test: remediate hardcoded credentials finding",
        "category": CATEGORIES[3],
        "severity": SEVERITIES[3],
        "status": STATUSES[1],
        "owner": "Test Owner Delta",
    },
]

EXPECTED_SYNTHETIC_SUMMARY = {
    "open": 6,
    "critical": 2,
    "awaiting_approval": 2,
    "completed": 2,
}
