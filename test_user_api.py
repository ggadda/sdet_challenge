"""
User Management API - Test Suite
=================================
Prerequisites:
    pip install pytest requests

Run all tests:
    pytest test_user_api.py -v

Run a specific group:
    pytest test_user_api.py -v -k "create"

Configuration:
    Set BASE_URL below to match your local server.
"""

import os
import pytest
import requests
import uuid

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
BASE_URL = os.environ.get("BASE_URL", "http://localhost:3000/dev")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "mysecrettoken")
EMAIL = "test_user@example.com"


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def unique_email():
    """Generate a unique email to avoid conflicts between test runs."""
    return f"test_{uuid.uuid4().hex[:8]}@example.com"


def create_user(name="Test User", email=None, age=25):
    email = email or unique_email()
    payload = {"name": name, "email": email, "age": age}
    r = requests.post(f"{BASE_URL}/users", json=payload)
    return r, payload


def delete_user(email, token=AUTH_TOKEN):
    return requests.delete(
        f"{BASE_URL}/users/{email}",
        headers={"Authentication": token},
    )


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────
@pytest.fixture
def existing_user():
    """Creates a user before the test and cleans up after."""
    r, payload = create_user()
    assert r.status_code == 201, f"Setup failed: {r.text}"
    yield payload
    delete_user(payload["email"])  # best-effort cleanup


# ══════════════════════════════════════════════
# GET /users  – List all users
# ══════════════════════════════════════════════
class TestListUsers:

    def test_returns_200(self):
        r = requests.get(f"{BASE_URL}/users")
        assert r.status_code == 200

    def test_response_is_json_array(self):
        r = requests.get(f"{BASE_URL}/users")
        assert isinstance(r.json(), list)

    def test_user_objects_have_required_fields(self, existing_user):
        r = requests.get(f"{BASE_URL}/users")
        users = r.json()
        if users:
            u = users[0]
            assert "name" in u
            assert "email" in u
            assert "age" in u

    def test_newly_created_user_appears_in_list(self, existing_user):
        r = requests.get(f"{BASE_URL}/users")
        emails = [u["email"] for u in r.json()]
        assert existing_user["email"] in emails


# ══════════════════════════════════════════════
# POST /users  – Create a user
# ══════════════════════════════════════════════
class TestCreateUser:

    def test_valid_payload_returns_201(self):
        r, payload = create_user()
        assert r.status_code == 201
        delete_user(payload["email"])

    def test_response_body_matches_input(self):
        r, payload = create_user(name="Alice", age=28)
        body = r.json()
        assert body["name"] == payload["name"]
        assert body["email"] == payload["email"]
        assert body["age"] == payload["age"]
        delete_user(payload["email"])

    def test_missing_name_returns_400(self):
        r = requests.post(f"{BASE_URL}/users", json={"email": unique_email(), "age": 25})
        assert r.status_code == 400

    def test_missing_email_returns_400(self):
        r = requests.post(f"{BASE_URL}/users", json={"name": "Bob", "age": 25})
        assert r.status_code == 400

    def test_missing_age_returns_400(self):
        r = requests.post(f"{BASE_URL}/users", json={"name": "Bob", "email": unique_email()})
        assert r.status_code == 400

    @pytest.mark.xfail(reason="BUG-001: API accepts invalid email format instead of returning 400", strict=True)
    def test_invalid_email_format_returns_400(self):
        r = requests.post(f"{BASE_URL}/users", json={"name": "Bob", "email": "Missing", "age": 25})
        assert r.status_code == 400

    def test_age_below_minimum_returns_400(self):
        r = requests.post(f"{BASE_URL}/users", json={"name": "Bob", "email": unique_email(), "age": 0})
        assert r.status_code == 400

    def test_age_above_maximum_returns_400(self):
        r = requests.post(f"{BASE_URL}/users", json={"name": "Bob", "email": unique_email(), "age": 151})
        assert r.status_code == 400

    def test_age_at_minimum_boundary_returns_201(self):
        r, payload = create_user(age=1)
        assert r.status_code == 201
        delete_user(payload["email"])

    def test_age_at_maximum_boundary_returns_201(self):
        r, payload = create_user(age=150)
        assert r.status_code == 201
        delete_user(payload["email"])

    @pytest.mark.xfail(reason="BUG-002: Duplicate email returns 500 instead of 409", strict=True)
    def test_duplicate_email_returns_409(self, existing_user):
        r, _ = create_user(email=existing_user["email"])
        assert r.status_code == 409

    def test_error_response_has_error_field(self):
        r = requests.post(f"{BASE_URL}/users", json={"name": "Bob", "age": 25})
        assert "error" in r.json()

    def test_empty_body_returns_400(self):
        r = requests.post(f"{BASE_URL}/users", json={})
        assert r.status_code == 400


# ══════════════════════════════════════════════
# GET /users/{email}  – Get a user by email
# ══════════════════════════════════════════════
class TestGetUser:

    def test_existing_user_returns_200(self, existing_user):
        r = requests.get(f"{BASE_URL}/users/{existing_user['email']}")
        assert r.status_code == 200

    def test_response_fields_match(self, existing_user):
        r = requests.get(f"{BASE_URL}/users/{existing_user['email']}")
        body = r.json()
        assert body["name"] == existing_user["name"]
        assert body["email"] == existing_user["email"]
        assert body["age"] == existing_user["age"]

    @pytest.mark.xfail(reason="BUG-003: Non-existent user returns 500 instead of 404", strict=True)
    def test_nonexistent_user_returns_404(self):
        r = requests.get(f"{BASE_URL}/users/nobody_{uuid.uuid4().hex}@example.com")
        assert r.status_code == 404

    def test_404_response_has_error_field(self):
        r = requests.get(f"{BASE_URL}/users/ghost@example.com")
        assert "error" in r.json()


# ══════════════════════════════════════════════
# PUT /users/{email}  – Update a user
# ══════════════════════════════════════════════
class TestUpdateUser:

    def test_valid_update_returns_200(self, existing_user):
        payload = {**existing_user, "name": "Updated Name", "age": 40}
        r = requests.put(f"{BASE_URL}/users/{existing_user['email']}", json=payload)
        assert r.status_code == 200

    def test_response_reflects_updated_fields(self, existing_user):
        payload = {**existing_user, "name": "New Name", "age": 35}
        r = requests.put(f"{BASE_URL}/users/{existing_user['email']}", json=payload)
        body = r.json()
        assert body["name"] == "New Name"
        assert body["age"] == 35

    def test_update_nonexistent_user_returns_404(self):
        email = f"ghost_{uuid.uuid4().hex}@example.com"
        r = requests.put(f"{BASE_URL}/users/{email}", json={"name": "X", "email": email, "age": 20})
        assert r.status_code == 404

    def test_missing_required_field_returns_400(self, existing_user):
        r = requests.put(
            f"{BASE_URL}/users/{existing_user['email']}",
            json={"name": "No Age", "email": existing_user["email"]},
        )
        assert r.status_code == 400

    def test_invalid_age_returns_400(self, existing_user):
        payload = {**existing_user, "age": 200}
        r = requests.put(f"{BASE_URL}/users/{existing_user['email']}", json=payload)
        assert r.status_code == 400

    def test_duplicate_email_on_update_returns_409(self):
        """Updating to an email already owned by another user should return 409."""
        _, user_a = create_user()
        _, user_b = create_user()
        try:
            payload = {**user_b, "email": user_a["email"]}
            r = requests.put(f"{BASE_URL}/users/{user_b['email']}", json=payload)
            assert r.status_code == 409
        finally:
            delete_user(user_a["email"])
            delete_user(user_b["email"])


# ══════════════════════════════════════════════
# DELETE /users/{email}  – Delete a user
# ══════════════════════════════════════════════
class TestDeleteUser:

    def test_valid_delete_returns_204(self, existing_user):
        r = delete_user(existing_user["email"])
        assert r.status_code == 204

    @pytest.mark.xfail(reason="BUG-004: GET on deleted user returns 500 instead of 404", strict=True)
    def test_deleted_user_no_longer_retrievable(self, existing_user):
        delete_user(existing_user["email"])
        r = requests.get(f"{BASE_URL}/users/{existing_user['email']}")
        assert r.status_code == 404

    @pytest.mark.xfail(condition=BASE_URL.endswith("/dev"), reason="BUG-005: DELETE without auth header succeeds instead of returning 401 (dev only)", strict=True)
    def test_delete_without_auth_header_returns_401(self, existing_user):
        r = requests.delete(f"{BASE_URL}/users/{existing_user['email']}")
        assert r.status_code == 401

    @pytest.mark.xfail(condition=BASE_URL.endswith("/dev"), reason="BUG-006: DELETE with invalid token succeeds instead of returning 401 (dev only)", strict=True)
    def test_delete_with_invalid_token_returns_401(self, existing_user):
        r = requests.delete(
            f"{BASE_URL}/users/{existing_user['email']}",
            headers={"Authentication": "invalid-token-xyz"},
        )
        assert r.status_code == 401

    def test_delete_nonexistent_user_returns_404(self):
        email = f"ghost_{uuid.uuid4().hex}@example.com"
        r = delete_user(email)
        assert r.status_code == 404

    def test_delete_already_deleted_user_returns_404(self, existing_user):
        delete_user(existing_user["email"])
        r = delete_user(existing_user["email"])
        assert r.status_code == 404


# ══════════════════════════════════════════════
# Environment parity – /prod mirrors /dev
# ══════════════════════════════════════════════
class TestEnvironmentParity:
    """Both /dev and /prod must expose identical behavior."""

    PROD_URL = BASE_URL.replace("/dev", "/prod")

    def test_prod_list_users_returns_200(self):
        r = requests.get(f"{self.PROD_URL}/users")
        assert r.status_code == 200

    def test_prod_create_and_delete_user(self):
        email = unique_email()
        r = requests.post(f"{self.PROD_URL}/users", json={"name": "Prod User", "email": email, "age": 22})
        assert r.status_code == 201
        r = requests.delete(f"{self.PROD_URL}/users/{email}", headers={"Authentication": AUTH_TOKEN})
        assert r.status_code == 204
