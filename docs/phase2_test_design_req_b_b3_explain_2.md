# Phase 2: Test Design for REQ-B-B3-Explain-2
**Session Explanations Batch Retrieval API**

## Overview

This document outlines the test design for implementing `GET /questions/explanations/session/{session_id}` endpoint.

**REQ ID**: REQ-B-B3-Explain-2
**Feature**: Session Explanations Batch Retrieval API
**Test File**: `tests/backend/test_session_explanations_endpoint.py`
**Duration**: ~2-3 hours (implementation + validation)

## Requirements Summary

| Requirement | Detail |
|-------------|--------|
| **Endpoint** | `GET /questions/explanations/session/{session_id}` |
| **Auth** | JWT required + session isolation |
| **Response** | All answers with explanations (auto-generate if missing) |
| **Performance** | < 10 seconds for complete retrieval + generation |
| **Error Handling** | 401 (unauthorized), 404 (not found), 422 (invalid format) |

## Test Cases Design

### Test Case 1: Happy Path - Retrieve Explanations for Completed Session

**Test Name**: `test_get_session_explanations_success`

**Setup**:
1. Create user with JWT token
2. Create test session (round 1, 5 questions)
3. Create 5 questions with different types (multiple_choice, true_false, short_answer)
4. Create 5 attempt answers (all answered, mixed correctness: 3 correct, 2 incorrect)
5. Create 5 AnswerExplanation records (pre-generated explanations)
6. Mark session as "completed"

**Test Action**:
```python
headers = {"Authorization": f"Bearer {valid_jwt_token}"}
response = client.get(
    f"/questions/explanations/session/{session_id}",
    headers=headers
)
```

**Assertions**:
- Status code: **200 OK**
- Response contains:
  - `session_id`: matches request
  - `status`: "completed"
  - `round`: 1
  - `answered_count`: 5
  - `total_questions`: 5
  - `explanations`: list with 5 items
- Each explanation contains:
  - `question_id`: valid UUID
  - `user_answer`: matches stored answer
  - `is_correct`: boolean
  - `score`: 0-100
  - `explanation`:
    - `id`: valid UUID (explanation ID)
    - `explanation_text`: >= 200 chars
    - `explanation_sections`: list with >= 2 sections
    - `reference_links`: list with >= 3 links (each with title, url)
    - `user_answer_summary`: dict with user_answer_text, correct_answer_text, question_type
    - `is_correct`: boolean
    - `created_at`: ISO timestamp
    - `is_fallback`: false (since pre-generated)

**Expected Duration**: < 10 seconds

---

### Test Case 2: Auto-Generate Missing Explanations

**Test Name**: `test_get_session_explanations_auto_generate`

**Setup**:
1. Create user with JWT token
2. Create test session (round 1, 5 questions)
3. Create 5 questions
4. Create 5 attempt answers (all answered)
5. **DO NOT create AnswerExplanation records** (missing explanations)
6. Mark session as "completed"

**Test Action**:
```python
headers = {"Authorization": f"Bearer {valid_jwt_token}"}
response = client.get(
    f"/questions/explanations/session/{session_id}",
    headers=headers
)
```

**Assertions**:
- Status code: **200 OK**
- Response contains all 5 explanations
- Each explanation:
  - `is_fallback`: Could be true or false depending on generation success
  - `explanation_text`: >= 200 chars
  - `reference_links`: list with >= 3 items
  - `created_at`: timestamp close to current time
- **Verify auto-generation occurred**: Either by checking `is_fallback=false` with valid explanation OR `is_fallback=true` with error_message

**Expected Duration**: < 10 seconds (includes LLM generation time)

---

### Test Case 3: Mixed Scenario - Some Explanations Exist, Some Auto-Generate

**Test Name**: `test_get_session_explanations_mixed`

**Setup**:
1. Create user with JWT token
2. Create test session (round 1, 5 questions)
3. Create 5 questions
4. Create 5 attempt answers
5. Create AnswerExplanation for **only 3 questions** (cached)
6. **Omit explanations for 2 questions** (to be generated)
7. Mark session as "completed"

**Test Action**:
```python
headers = {"Authorization": f"Bearer {valid_jwt_token}"}
response = client.get(
    f"/questions/explanations/session/{session_id}",
    headers=headers
)
```

**Assertions**:
- Status code: **200 OK**
- Response contains all 5 explanations
- First 3 explanations: `is_fallback=false`, `created_at` from past
- Last 2 explanations: `created_at` close to current time
- All explanations have valid content and reference links

---

### Test Case 4A: Authentication - Missing JWT Token

**Test Name**: `test_get_session_explanations_no_token`

**Setup**:
1. Create test session (any valid session)
2. **DO NOT provide Authorization header**

**Test Action**:
```python
response = client.get(
    f"/questions/explanations/session/{session_id}"
)
```

**Assertions**:
- Status code: **401 Unauthorized**
- Response detail: error message indicating missing/invalid token

---

### Test Case 4B: Authentication - Invalid JWT Token

**Test Name**: `test_get_session_explanations_invalid_token`

**Setup**:
1. Create valid session
2. Prepare invalid JWT token (expired, tampered, wrong signature)

**Test Action**:
```python
headers = {"Authorization": "Bearer invalid.token.here"}
response = client.get(
    f"/questions/explanations/session/{session_id}",
    headers=headers
)
```

**Assertions**:
- Status code: **401 Unauthorized**
- Response detail: error message

---

### Test Case 4C: Authorization - User Accessing Another User's Session

**Test Name**: `test_get_session_explanations_unauthorized_access`

**Setup**:
1. Create **User A** and User A's test session with answers
2. Create **User B** and User B's JWT token
3. User B tries to access User A's session

**Test Action**:
```python
user_b_headers = {"Authorization": f"Bearer {user_b_jwt_token}"}
response = client.get(
    f"/questions/explanations/session/{user_a_session_id}",
    headers=user_b_headers
)
```

**Assertions**:
- Status code: **401 Unauthorized** (or **403 Forbidden**)
- Response detail: error message indicating access denied

---

### Test Case 5A: Error - Non-Existent Session ID

**Test Name**: `test_get_session_explanations_not_found`

**Setup**:
1. Create user with JWT token
2. Use non-existent session ID (valid UUID format but doesn't exist in DB)

**Test Action**:
```python
headers = {"Authorization": f"Bearer {valid_jwt_token}"}
fake_session_id = "00000000-0000-0000-0000-000000000000"
response = client.get(
    f"/questions/explanations/session/{fake_session_id}",
    headers=headers
)
```

**Assertions**:
- Status code: **404 Not Found**
- Response detail: "Session not found" or similar

---

### Test Case 5B: Error - Invalid Session ID Format

**Test Name**: `test_get_session_explanations_invalid_format`

**Setup**:
1. Create user with JWT token
2. Use invalid session ID format (not a UUID)

**Test Action**:
```python
headers = {"Authorization": f"Bearer {valid_jwt_token}"}
response = client.get(
    f"/questions/explanations/session/invalid-id-format",
    headers=headers
)
```

**Assertions**:
- Status code: **422 Unprocessable Entity**
- Response detail: validation error message

---

### Test Case 5C: Edge Case - Session with Zero Answers

**Test Name**: `test_get_session_explanations_empty_session`

**Setup**:
1. Create user with JWT token
2. Create test session (round 1, 5 questions)
3. Create 5 questions
4. **DO NOT create any attempt answers**
5. Mark session as "completed"

**Test Action**:
```python
headers = {"Authorization": f"Bearer {valid_jwt_token}"}
response = client.get(
    f"/questions/explanations/session/{session_id}",
    headers=headers
)
```

**Assertions**:
- Status code: **200 OK** (or **400 Bad Request** - implementation choice)
- Response contains:
  - `session_id`: matches request
  - `answered_count`: 0
  - `total_questions`: 5
  - `explanations`: empty list `[]`

---

### Test Case 6: Performance - Retrieve + Generate < 10 Seconds

**Test Name**: `test_get_session_explanations_performance`

**Setup**:
1. Create user with JWT token
2. Create test session with 10 questions
3. Create 10 attempt answers (5 with explanations, 5 without)

**Test Action**:
```python
import time
headers = {"Authorization": f"Bearer {valid_jwt_token}"}
start = time.time()
response = client.get(
    f"/questions/explanations/session/{session_id}",
    headers=headers
)
elapsed = time.time() - start
```

**Assertions**:
- Status code: **200 OK**
- `elapsed < 10.0` seconds
- Response contains all 10 explanations

---

## Test Implementation Checklist

- [ ] Create pytest fixtures for user, session, questions, answers, explanations
- [ ] Import required models: User, TestSession, Question, AttemptAnswer, AnswerExplanation
- [ ] Import TestClient and HTTPException
- [ ] Mock JWT token generation for authenticated requests
- [ ] Implement database seeding helper functions
- [ ] Test Case 1: Happy path (all explanations pre-generated)
- [ ] Test Case 2: Auto-generate all missing explanations
- [ ] Test Case 3: Mixed scenario (partial generation)
- [ ] Test Case 4A: No JWT token → 401
- [ ] Test Case 4B: Invalid JWT token → 401
- [ ] Test Case 4C: Different user access → 401/403
- [ ] Test Case 5A: Non-existent session → 404
- [ ] Test Case 5B: Invalid session ID format → 422
- [ ] Test Case 5C: Empty session → 200 with empty list
- [ ] Test Case 6: Performance validation < 10 seconds
- [ ] Verify response schema matches ExplanationResponse model
- [ ] Verify reference_links contain title and url fields
- [ ] Verify explanation_sections contain title and content
- [ ] Add docstrings with REQ-B-B3-Explain-2 reference to each test

---

## Fixtures Required

```python
@pytest.fixture
def test_session(db_session: Session, user_fixture: User) -> TestSession:
    """Create a test session for testing."""
    # Implementation in conftest.py

@pytest.fixture
def questions_with_answers(db_session: Session, test_session: TestSession) -> list[tuple[Question, AttemptAnswer]]:
    """Create 5 questions with 5 answers."""
    # Implementation in conftest.py

@pytest.fixture
def questions_with_explanations(db_session: Session, questions_with_answers) -> list[AnswerExplanation]:
    """Create explanations for all answers."""
    # Implementation in conftest.py
```

---

## Expected Response Format

```json
{
  "session_id": "uuid-string",
  "status": "completed",
  "round": 1,
  "answered_count": 5,
  "total_questions": 5,
  "explanations": [
    {
      "question_id": "uuid",
      "user_answer": {"choice": "A"},
      "is_correct": true,
      "score": 100,
      "explanation": {
        "id": "uuid",
        "explanation_text": "...",
        "explanation_sections": [
          {"title": "...", "content": "..."},
          {"title": "...", "content": "..."}
        ],
        "reference_links": [
          {"title": "...", "url": "https://..."},
          {"title": "...", "url": "https://..."},
          {"title": "...", "url": "https://..."}
        ],
        "user_answer_summary": {
          "user_answer_text": "...",
          "correct_answer_text": "...",
          "question_type": "multiple_choice"
        },
        "problem_statement": "...",
        "is_correct": true,
        "created_at": "2025-11-24T10:40:00Z",
        "is_fallback": false,
        "error_message": null
      }
    }
  ]
}
```

---

## Summary

**Total Test Cases**: 9
- 1 Happy Path
- 1 Auto-generation
- 1 Mixed
- 3 Authentication/Authorization
- 2 Error cases
- 1 Edge case
- 1 Performance

**Expected Test Coverage**: 95%+
**Estimated Test Duration**: 30-45 seconds total
**Implementation Duration**: 2-3 hours

---

## Acceptance Criteria

- [ ] All 9 test cases pass
- [ ] Code coverage >= 90%
- [ ] Authentication properly enforced
- [ ] Auto-generation triggered when needed
- [ ] Performance requirement met (< 10 seconds)
- [ ] Error responses correct HTTP status codes
- [ ] Response schema matches ExplanationResponse exactly
