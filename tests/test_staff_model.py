"""Unit tests for staff role and department catalogs."""

import pytest

from app import WORK_ITEMS, build_summary, validate_work_item
from staff_model import (
    DEPARTMENTS,
    ROLES,
    department_exists,
    role_exists,
    validate_catalog_integrity,
)

EXPECTED_SUMMARY = {
    "open": 6,
    "critical": 2,
    "awaiting_approval": 2,
    "completed": 2,
}

EXPECTED_DEPARTMENTS = {
    "DEPT-SEC": "Security Engineering",
    "DEPT-IAM": "Identity & Access Management",
    "DEPT-CLOUD": "Cloud Security",
    "DEPT-DEVSECOPS": "DevSecOps",
    "DEPT-APPSEC": "Application Security",
    "DEPT-GRC": "Governance, Risk & Compliance",
    "DEPT-MGMT": "Security Management",
    "DEPT-INFRA": "IT & Infrastructure",
}

EXPECTED_ROLES = {
    "ROLE-SEC-ENG": "Security Engineer",
    "ROLE-IAM-ENG": "IAM Engineer",
    "ROLE-CLOUD-ENG": "Cloud Security Engineer",
    "ROLE-DEVSECOPS-ENG": "DevSecOps Engineer",
    "ROLE-APPSEC-ENG": "Application Security Engineer",
    "ROLE-GRC-ANALYST": "Compliance Analyst",
    "ROLE-SEC-MGR": "Security Manager",
    "ROLE-INFRA-ENG": "Infrastructure Engineer",
}

EXPECTED_DEPARTMENT_IDS = set(EXPECTED_DEPARTMENTS)
EXPECTED_ROLE_IDS = set(EXPECTED_ROLES)


def test_all_eight_departments_exist():
    assert set(DEPARTMENTS) == EXPECTED_DEPARTMENT_IDS
    assert len(DEPARTMENTS) == 8


def test_all_eight_roles_exist():
    assert set(ROLES) == EXPECTED_ROLE_IDS
    assert len(ROLES) == 8


def test_every_catalog_id_is_unique():
    dept_ids = list(DEPARTMENTS)
    role_ids = list(ROLES)
    assert len(dept_ids) == len(set(dept_ids))
    assert len(role_ids) == len(set(role_ids))
    assert set(dept_ids).isdisjoint(set(role_ids))


def test_role_and_department_names_are_non_empty():
    for dept in DEPARTMENTS.values():
        assert isinstance(dept["name"], str)
        assert dept["name"].strip()
    for role in ROLES.values():
        assert isinstance(role["name"], str)
        assert role["name"].strip()


def test_catalog_records_have_expected_types():
    for key, dept in DEPARTMENTS.items():
        assert isinstance(key, str)
        assert dept["id"] == key
        assert isinstance(dept["name"], str)

    for key, role in ROLES.items():
        assert isinstance(key, str)
        assert role["id"] == key
        assert isinstance(role["name"], str)
        suggested = role.get("suggested_primary_department_id")
        assert suggested is None or isinstance(suggested, str)


def test_valid_ids_are_recognized():
    assert role_exists("ROLE-SEC-ENG") is True
    assert department_exists("DEPT-SEC") is True
    assert role_exists("ROLE-SEC-MGR") is True
    assert department_exists("DEPT-GRC") is True


def test_unknown_ids_are_rejected():
    assert role_exists("ROLE-UNKNOWN") is False
    assert department_exists("DEPT-UNKNOWN") is False
    assert role_exists("") is False
    assert department_exists(None) is False
    assert role_exists(123) is False
    assert department_exists(["DEPT-SEC"]) is False


def test_suggested_department_references_are_valid():
    for role in ROLES.values():
        suggested = role.get("suggested_primary_department_id")
        if suggested is not None:
            assert department_exists(suggested)
    assert validate_catalog_integrity() == []


def test_role_metadata_does_not_imply_authentication_or_authorization():
    """Catalog membership is not a session, permission grant, or login."""
    assert role_exists("ROLE-SEC-MGR") is True
    assert "permissions" not in ROLES["ROLE-SEC-MGR"]
    assert "authorized" not in ROLES["ROLE-SEC-MGR"]
    assert "authenticated" not in ROLES["ROLE-SEC-MGR"]
    assert ROLES["ROLE-SEC-MGR"]["suggested_primary_department_id"] == "DEPT-MGMT"


def test_existing_application_behavior_unchanged():
    assert build_summary(WORK_ITEMS) == EXPECTED_SUMMARY
    for item in WORK_ITEMS:
        assert validate_work_item(item) == []


def test_validate_catalog_integrity_rejects_bad_suggested_department():
    broken_roles = {
        "ROLE-SEC-ENG": {
            "id": "ROLE-SEC-ENG",
            "name": "Security Engineer",
            "suggested_primary_department_id": "DEPT-DOES-NOT-EXIST",
        }
    }
    errors = validate_catalog_integrity(roles=broken_roles)
    assert any("DEPT-DOES-NOT-EXIST" in error for error in errors)
    assert validate_catalog_integrity() == []
    assert ROLES["ROLE-SEC-ENG"]["suggested_primary_department_id"] == "DEPT-SEC"


def test_validate_catalog_integrity_rejects_empty_names():
    broken_departments = {
        "DEPT-SEC": {"id": "DEPT-SEC", "name": "   "},
    }
    errors = validate_catalog_integrity(departments=broken_departments, roles={})
    assert any("name" in error for error in errors)


def test_outer_department_catalog_cannot_be_modified():
    with pytest.raises(TypeError):
        DEPARTMENTS["DEPT-NEW"] = {"id": "DEPT-NEW", "name": "New"}  # type: ignore[index]
    with pytest.raises(TypeError):
        del DEPARTMENTS["DEPT-SEC"]  # type: ignore[arg-type]
    assert "DEPT-SEC" in DEPARTMENTS
    assert len(DEPARTMENTS) == 8


def test_outer_role_catalog_cannot_be_modified():
    with pytest.raises(TypeError):
        ROLES["ROLE-NEW"] = {"id": "ROLE-NEW", "name": "New"}  # type: ignore[index]
    with pytest.raises(TypeError):
        del ROLES["ROLE-SEC-ENG"]  # type: ignore[arg-type]
    assert "ROLE-SEC-ENG" in ROLES
    assert len(ROLES) == 8


def test_nested_department_records_cannot_be_modified():
    with pytest.raises(TypeError):
        DEPARTMENTS["DEPT-SEC"]["name"] = "Changed"  # type: ignore[index]
    with pytest.raises(TypeError):
        DEPARTMENTS["DEPT-SEC"]["extra"] = "nope"  # type: ignore[index]
    assert DEPARTMENTS["DEPT-SEC"]["name"] == "Security Engineering"


def test_nested_role_records_cannot_be_modified():
    with pytest.raises(TypeError):
        ROLES["ROLE-SEC-ENG"]["name"] = "Changed"  # type: ignore[index]
    with pytest.raises(TypeError):
        ROLES["ROLE-SEC-ENG"]["suggested_primary_department_id"] = "DEPT-UNKNOWN"  # type: ignore[index]
    assert ROLES["ROLE-SEC-ENG"]["name"] == "Security Engineer"
    assert ROLES["ROLE-SEC-ENG"]["suggested_primary_department_id"] == "DEPT-SEC"


def test_exact_approved_department_names():
    assert len(DEPARTMENTS) == len(EXPECTED_DEPARTMENTS)
    for dept_id, name in EXPECTED_DEPARTMENTS.items():
        assert DEPARTMENTS[dept_id]["name"] == name
        assert DEPARTMENTS[dept_id]["id"] == dept_id


def test_exact_approved_role_names():
    assert len(ROLES) == len(EXPECTED_ROLES)
    for role_id, name in EXPECTED_ROLES.items():
        assert ROLES[role_id]["name"] == name
        assert ROLES[role_id]["id"] == role_id


def test_key_record_id_mismatch():
    broken_departments = {
        "DEPT-SEC": {"id": "DEPT-OTHER", "name": "Security Engineering"},
    }
    errors = validate_catalog_integrity(departments=broken_departments, roles={})
    assert any("does not match record id" in error for error in errors)

    broken_roles = {
        "ROLE-SEC-ENG": {
            "id": "ROLE-OTHER",
            "name": "Security Engineer",
            "suggested_primary_department_id": "DEPT-SEC",
        }
    }
    role_errors = validate_catalog_integrity(roles=broken_roles)
    assert any("does not match record id" in error for error in role_errors)


def test_multiple_invalid_fields_produce_multiple_errors():
    broken_departments = {
        "DEPT-SEC": {"id": 123, "name": "   "},
    }
    errors = validate_catalog_integrity(departments=broken_departments, roles={})
    assert any("does not match record id" in error for error in errors)
    assert any("id must be a string" in error for error in errors)
    assert any("name must be a non-empty string" in error for error in errors)
    assert len(errors) >= 3

    broken_roles = {
        "ROLE-SEC-ENG": {
            "id": 456,
            "name": "",
            "suggested_primary_department_id": "DEPT-DOES-NOT-EXIST",
        }
    }
    role_errors = validate_catalog_integrity(roles=broken_roles)
    assert any("does not match record id" in error for error in role_errors)
    assert any("id must be a string" in error for error in role_errors)
    assert any("name must be a non-empty string" in error for error in role_errors)
    assert any("DEPT-DOES-NOT-EXIST" in error for error in role_errors)
    assert len(role_errors) >= 4


def test_invalid_suggested_department_references():
    broken_roles = {
        "ROLE-SEC-ENG": {
            "id": "ROLE-SEC-ENG",
            "name": "Security Engineer",
            "suggested_primary_department_id": "   ",
        }
    }
    errors = validate_catalog_integrity(roles=broken_roles)
    assert any("suggested_primary_department_id" in error for error in errors)

    broken_roles_unknown = {
        "ROLE-IAM-ENG": {
            "id": "ROLE-IAM-ENG",
            "name": "IAM Engineer",
            "suggested_primary_department_id": "DEPT-NOT-REAL",
        }
    }
    unknown_errors = validate_catalog_integrity(roles=broken_roles_unknown)
    assert any("DEPT-NOT-REAL" in error for error in unknown_errors)


def test_existing_catalog_integrity_checks_remain_functional():
    assert validate_catalog_integrity() == []
    assert validate_catalog_integrity(departments=DEPARTMENTS, roles=ROLES) == []
    # Ordinary dicts remain accepted for test-time validation.
    assert (
        validate_catalog_integrity(
            departments={k: dict(v) for k, v in DEPARTMENTS.items()},
            roles={k: dict(v) for k, v in ROLES.items()},
        )
        == []
    )
