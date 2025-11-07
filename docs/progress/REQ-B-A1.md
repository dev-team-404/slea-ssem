# REQ-B-A1: Samsung AD 인증 및 사용자 세션 관리

**Developer**: bwyoon
**Status**: ✅ Done (Phase 4)
**Merge Commit**: f5412e9
**Merge Date**: 2025-11-07

---

## 📋 Specification (Phase 1)

### Requirements

| REQ ID | Description | Priority |
|--------|---|---|
| REQ-B-A1-1 | Samsung AD 사용자 정보 수신 및 users 테이블에 저장 | **M** |
| REQ-B-A1-2 | JWT 토큰 생성 (knox_id, iat, exp만 포함) | **M** |
| REQ-B-A1-3 | 신규 사용자: 레코드 생성 + JWT + is_new_user=true | **M** |
| REQ-B-A1-4 | 기존 사용자: JWT 재생성 + last_login 업데이트 + is_new_user=false | **M** |

### Implementation Location

```
src/backend/
├── models/user.py           # User SQLAlchemy ORM
├── services/auth_service.py # AuthService class
├── api/auth.py              # FastAPI /auth/login endpoint
├── config.py                # JWT configuration
└── database.py              # Session management
```

### Key Design Decisions

1. **JWT Payload**: Only `knox_id`, `iat`, `exp` (no PII in token)
2. **Status Codes**: 201 for new users, 200 for existing users
3. **Database**: SQLite for MVP (configurable via env)
4. **Expiration**: 24 hours default (configurable)

---

## 🧪 Test Design (Phase 2)

### Test Suite: `tests/backend/test_auth_*.py`

**Unit Tests (7 tests)**:
- ✅ New user registration with JWT generation
- ✅ Existing user re-login with last_login update
- ✅ JWT payload validation (only knox_id, iat, exp)
- ✅ Input validation (missing required fields)
- ✅ Duplicate knox_id handling
- ✅ JWT expiration validation
- ✅ Invalid JWT decoding error handling

**Integration Tests (4 tests)**:
- ✅ POST /auth/login with new user (201 Created)
- ✅ POST /auth/login with existing user (200 OK)
- ✅ Missing required field validation (422)
- ✅ Invalid payload handling (422)

**Test Coverage**: 11/11 passing (100%)

---

## 💻 Implementation (Phase 3)

### Files Created (9 files)

**Core Implementation**:
1. `src/backend/models/user.py` - User model with all required fields
2. `src/backend/services/auth_service.py` - JWT & auth logic
3. `src/backend/api/auth.py` - FastAPI endpoint
4. `src/backend/config.py` - JWT configuration
5. `src/backend/database.py` - Session management

**Package Inits**:
6. `src/backend/models/__init__.py`
7. `src/backend/services/__init__.py`
8. `src/backend/api/__init__.py`

**Test Infrastructure**:
9. `tests/conftest.py` - Pytest fixtures & setup
10. `tests/backend/test_auth_service.py` - Unit tests
11. `tests/backend/test_auth_endpoint.py` - Integration tests

### Dependencies Added

```
fastapi==0.121.0
sqlalchemy==2.0.44
PyJWT==2.10.1
python-dotenv==1.2.1
sqlalchemy-utils==0.42.0
pytest-httpx==0.35.0  (dev)
```

### Code Quality

- ✅ **Ruff**: All checks pass
- ✅ **Type Hints**: mypy strict mode compliant
- ✅ **Docstrings**: All public APIs documented
- ✅ **Line Length**: ≤120 chars

---

## ✅ Summary (Phase 4)

### Test Results

```
tests/backend/test_auth_endpoint.py::TestAuthEndpoint::test_post_auth_login_new_user PASSED
tests/backend/test_auth_endpoint.py::TestAuthEndpoint::test_post_auth_login_existing_user PASSED
tests/backend/test_auth_endpoint.py::TestAuthEndpoint::test_post_auth_login_missing_required_field PASSED
tests/backend/test_auth_endpoint.py::TestAuthEndpoint::test_post_auth_login_invalid_payload PASSED
tests/backend/test_auth_service.py::TestAuthServiceNewUserRegistration::test_authenticate_or_create_user_creates_new_user PASSED
tests/backend/test_auth_service.py::TestAuthServiceExistingUserLogin::test_authenticate_or_create_user_existing_user_updates_login PASSED
tests/backend/test_auth_service.py::TestJWTTokenPayload::test_jwt_token_payload_contains_knox_id_only PASSED
tests/backend/test_auth_service.py::TestAuthServiceInputValidation::test_authenticate_or_create_user_missing_required_fields PASSED
tests/backend/test_auth_service.py::TestAuthServiceInputValidation::test_authenticate_or_create_user_duplicate_knox_id PASSED
tests/backend/test_auth_service.py::TestJWTTokenExpiration::test_jwt_token_has_valid_expiration PASSED
tests/backend/test_auth_service.py::TestJWTTokenDecoding::test_decode_invalid_jwt_raises_error PASSED

11/11 PASSED ✅
```

### Git Commit

```
commit f5412e9
Author: Claude <noreply@anthropic.com>
Date:   2025-11-07

    feat: Implement REQ-B-A1 Samsung AD authentication and JWT session management

    - User ORM model with Samsung AD fields
    - JWT token generation (knox_id, iat, exp)
    - FastAPI /auth/login endpoint
    - Input validation & duplicate handling
    - 11 unit/integration tests (100% pass)
```

### REQ Traceability

| REQ ID | Implementation | Test Coverage | Status |
|--------|---|---|---|
| REQ-B-A1-1 | User model + validation | test_authenticate_or_create_user_creates_new_user | ✅ |
| REQ-B-A1-2 | JWT generation | test_jwt_token_payload_contains_knox_id_only | ✅ |
| REQ-B-A1-3 | New user + is_new_user=true | test_post_auth_login_new_user | ✅ |
| REQ-B-A1-4 | Re-login + last_login update | test_authenticate_or_create_user_existing_user_updates_login | ✅ |

---

## 📝 Notes

- JWT secret key should be set via `JWT_SECRET_KEY` environment variable (defaults to dev key)
- Database URL configurable via `DATABASE_URL` (SQLite for MVP)
- All datetime fields use UTC
- Thread-safe session management with Depends injection
