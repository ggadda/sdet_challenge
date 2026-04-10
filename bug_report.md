# Bug Report — User Management API

**Environment:** `http://localhost:3000`
**Test suite:** `test_user_api.py`
**Date:** 2026-04-09

---

## BUG-001 — Invalid email format is accepted on user creation

**Endpoint:** `POST /users`
**Severity:** High
**Test:** `TestCreateUser::test_invalid_email_format_returns_400`

### Description
The API accepts email addresses with invalid format (e.g. missing `@` symbol) and creates the user successfully instead of rejecting the request.

### Steps to Reproduce
1. Send `POST /users` with payload `{"name": "Bob", "email": "Missing", "age": 25}`
2. Observe the response

### Expected Result
`400 Bad Request` — email format is invalid

### Actual Result
`201 Created` — user is created with a malformed email

---

## BUG-002 — Duplicate email on creation returns 500 instead of 409

**Endpoint:** `POST /users`
**Severity:** High
**Test:** `TestCreateUser::test_duplicate_email_returns_409`

### Description
When attempting to create a user with an email that already exists, the API crashes with a 500 Internal Server Error instead of returning a proper conflict response.

### Steps to Reproduce
1. Create a user with `POST /users` using any email
2. Send a second `POST /users` request with the same email
3. Observe the response

### Expected Result
`409 Conflict` — email already in use

### Actual Result
`500 Internal Server Error` — unhandled exception, likely a database unique constraint violation

---

## BUG-003 — GET on non-existent user returns 500 instead of 404

**Endpoint:** `GET /users/{email}`
**Severity:** High
**Test:** `TestGetUser::test_nonexistent_user_returns_404`

### Description
Requesting a user that does not exist causes the API to crash with a 500 Internal Server Error instead of returning a not-found response.

### Steps to Reproduce
1. Send `GET /users/nobody_<random>@example.com` for an email that does not exist
2. Observe the response

### Expected Result
`404 Not Found`

### Actual Result
`500 Internal Server Error`

---

## BUG-004 — GET on deleted user returns 500 instead of 404

**Endpoint:** `GET /users/{email}`
**Severity:** High
**Test:** `TestDeleteUser::test_deleted_user_no_longer_retrievable`

### Description
After a user is successfully deleted, attempting to retrieve that user returns 500 instead of 404. This is the same root cause as BUG-003 — the not-found case is unhandled.

### Steps to Reproduce
1. Create a user with `POST /users`
2. Delete the user with `DELETE /users/{email}`
3. Send `GET /users/{email}` for the deleted user
4. Observe the response

### Expected Result
`404 Not Found`

### Actual Result
`500 Internal Server Error`

---

## BUG-005 — DELETE without Authorization header succeeds (Dev only)

**Endpoint:** `DELETE /users/{email}`
**Severity:** Critical
**Environment:** Dev only — Prod correctly returns 401
**Test:** `TestDeleteUser::test_delete_without_auth_header_returns_401`

### Description
The DELETE endpoint performs no authentication check. A request with no `Authorization` header is accepted and the user is deleted successfully.

### Steps to Reproduce
1. Create a user with `POST /users`
2. Send `DELETE /users/{email}` with no headers
3. Observe the response

### Expected Result
`401 Unauthorized`

### Actual Result
`204 No Content` — user is deleted without any credentials

---

## BUG-006 — DELETE with invalid token succeeds (Dev only)

**Endpoint:** `DELETE /users/{email}`
**Severity:** Critical
**Environment:** Dev only — Prod correctly returns 401
**Test:** `TestDeleteUser::test_delete_with_invalid_token_returns_401`

### Description
The DELETE endpoint does not validate the provided token. A request with an incorrect `Authentication` header value is accepted and the user is deleted.

### Steps to Reproduce
1. Create a user with `POST /users`
2. Send `DELETE /users/{email}` with header `Authentication: invalid-token-xyz`
3. Observe the response

### Expected Result
`401 Unauthorized`

### Actual Result
`204 No Content` — user is deleted despite the invalid token

---

## Summary

| ID      | Endpoint            | Description                              | Severity |
|---------|---------------------|------------------------------------------|----------|
| BUG-001 | `POST /users`       | Invalid email format accepted            | High     |
| BUG-002 | `POST /users`       | Duplicate email returns 500 not 409      | High     |
| BUG-003 | `GET /users/{email}`| Non-existent user returns 500 not 404    | High     |
| BUG-004 | `GET /users/{email}`| Deleted user returns 500 not 404         | High     |
| BUG-005 | `DELETE /users/{email}` | No auth required to delete a user (dev only)   | Critical |
| BUG-006 | `DELETE /users/{email}` | Invalid token accepted on delete (dev only)    | Critical |
