"""Human staff role and department catalogs for Sentinel App.

Roles and departments are organizational metadata only. They are independent of
staff identities. A suggested primary department on a role is not a permission
grant, not authentication, and not an exclusive membership rule.

This module does not create staff accounts, sessions, or authorization checks.
Having a role ID in the catalog does not imply that any person is authenticated
or authorized to act in that role.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping

# Immutable department catalog: stable ID -> display name.
# Outer catalog and nested records are read-only MappingProxyType views.
DEPARTMENTS: Mapping[str, Mapping[str, str]] = MappingProxyType(
    {
        "DEPT-SEC": MappingProxyType(
            {"id": "DEPT-SEC", "name": "Security Engineering"}
        ),
        "DEPT-IAM": MappingProxyType(
            {"id": "DEPT-IAM", "name": "Identity & Access Management"}
        ),
        "DEPT-CLOUD": MappingProxyType(
            {"id": "DEPT-CLOUD", "name": "Cloud Security"}
        ),
        "DEPT-DEVSECOPS": MappingProxyType(
            {"id": "DEPT-DEVSECOPS", "name": "DevSecOps"}
        ),
        "DEPT-APPSEC": MappingProxyType(
            {"id": "DEPT-APPSEC", "name": "Application Security"}
        ),
        "DEPT-GRC": MappingProxyType(
            {"id": "DEPT-GRC", "name": "Governance, Risk & Compliance"}
        ),
        "DEPT-MGMT": MappingProxyType(
            {"id": "DEPT-MGMT", "name": "Security Management"}
        ),
        "DEPT-INFRA": MappingProxyType(
            {"id": "DEPT-INFRA", "name": "IT & Infrastructure"}
        ),
    }
)

# Immutable role catalog. suggested_primary_department_id is optional metadata
# only; it does not grant permissions or bind a role exclusively to one department.
ROLES: Mapping[str, Mapping[str, Any]] = MappingProxyType(
    {
        "ROLE-SEC-ENG": MappingProxyType(
            {
                "id": "ROLE-SEC-ENG",
                "name": "Security Engineer",
                "suggested_primary_department_id": "DEPT-SEC",
            }
        ),
        "ROLE-IAM-ENG": MappingProxyType(
            {
                "id": "ROLE-IAM-ENG",
                "name": "IAM Engineer",
                "suggested_primary_department_id": "DEPT-IAM",
            }
        ),
        "ROLE-CLOUD-ENG": MappingProxyType(
            {
                "id": "ROLE-CLOUD-ENG",
                "name": "Cloud Security Engineer",
                "suggested_primary_department_id": "DEPT-CLOUD",
            }
        ),
        "ROLE-DEVSECOPS-ENG": MappingProxyType(
            {
                "id": "ROLE-DEVSECOPS-ENG",
                "name": "DevSecOps Engineer",
                "suggested_primary_department_id": "DEPT-DEVSECOPS",
            }
        ),
        "ROLE-APPSEC-ENG": MappingProxyType(
            {
                "id": "ROLE-APPSEC-ENG",
                "name": "Application Security Engineer",
                "suggested_primary_department_id": "DEPT-APPSEC",
            }
        ),
        "ROLE-GRC-ANALYST": MappingProxyType(
            {
                "id": "ROLE-GRC-ANALYST",
                "name": "Compliance Analyst",
                "suggested_primary_department_id": "DEPT-GRC",
            }
        ),
        "ROLE-SEC-MGR": MappingProxyType(
            {
                "id": "ROLE-SEC-MGR",
                "name": "Security Manager",
                "suggested_primary_department_id": "DEPT-MGMT",
            }
        ),
        "ROLE-INFRA-ENG": MappingProxyType(
            {
                "id": "ROLE-INFRA-ENG",
                "name": "Infrastructure Engineer",
                "suggested_primary_department_id": "DEPT-INFRA",
            }
        ),
    }
)


def role_exists(role_id: object) -> bool:
    """Return True if ``role_id`` is a known role catalog key."""
    return isinstance(role_id, str) and role_id in ROLES


def department_exists(department_id: object) -> bool:
    """Return True if ``department_id`` is a known department catalog key."""
    return isinstance(department_id, str) and department_id in DEPARTMENTS


def validate_catalog_integrity(
    departments: Mapping[str, Mapping[str, Any]] | None = None,
    roles: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[str]:
    """Validate role/department catalogs; return descriptive errors.

    Does not mutate catalog data. Defaults to the module DEPARTMENTS and ROLES.
    Accepts immutable production catalogs and ordinary dicts supplied by tests.
    Catalog presence alone never implies authentication or authorization.
    """
    errors: list[str] = []
    depts = DEPARTMENTS if departments is None else departments
    role_catalog = ROLES if roles is None else roles

    if not isinstance(depts, Mapping):
        return ["departments catalog must be a mapping"]
    if not isinstance(role_catalog, Mapping):
        return ["roles catalog must be a mapping"]

    dept_ids: list[str] = []
    for key, record in depts.items():
        if not isinstance(key, str) or not key.strip():
            errors.append("department catalog key must be a non-empty string")
            continue
        if not isinstance(record, Mapping):
            errors.append(f"department {key!r} record must be a mapping")
            continue

        record_id = record.get("id")
        name = record.get("name")
        if record_id != key:
            errors.append(
                f"department key {key!r} does not match record id {record_id!r}"
            )
        if not isinstance(record_id, str):
            errors.append(f"department {key!r} id must be a string")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"department {key!r} name must be a non-empty string")
        dept_ids.append(key)

    if len(dept_ids) != len(set(dept_ids)):
        errors.append("department catalog IDs must be unique")

    role_ids: list[str] = []
    for key, record in role_catalog.items():
        if not isinstance(key, str) or not key.strip():
            errors.append("role catalog key must be a non-empty string")
            continue
        if not isinstance(record, Mapping):
            errors.append(f"role {key!r} record must be a mapping")
            continue

        record_id = record.get("id")
        name = record.get("name")
        if record_id != key:
            errors.append(f"role key {key!r} does not match record id {record_id!r}")
        if not isinstance(record_id, str):
            errors.append(f"role {key!r} id must be a string")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"role {key!r} name must be a non-empty string")

        suggested = record.get("suggested_primary_department_id")
        if suggested is not None:
            if not isinstance(suggested, str) or not suggested.strip():
                errors.append(
                    f"role {key!r} suggested_primary_department_id must be a "
                    "non-empty string when provided"
                )
            elif suggested not in depts:
                errors.append(
                    f"role {key!r} suggested_primary_department_id "
                    f"{suggested!r} is not a known department"
                )

        role_ids.append(key)

    if len(role_ids) != len(set(role_ids)):
        errors.append("role catalog IDs must be unique")

    overlapping = set(dept_ids) & set(role_ids)
    if overlapping:
        errors.append(
            "role and department catalog IDs must be unique across both catalogs: "
            + ", ".join(sorted(overlapping))
        )

    return errors
