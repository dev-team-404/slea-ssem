# REQ-B-B2-Plus: 테스트 진행 중 실시간 저장 및 재개 (Real-time Auto-save & Resume)

**Developer**: bwyoon (Backend)
**Status**: ✅ Phase 4 (Done - Ready for Merge)
**Completion Date**: 2025-11-07

---

## 📋 Requirement Summary

Implement real-time auto-save functionality during test-taking with ability to resume after time limit exceeded. Users can pause/resume test sessions while maintaining full state and answer history.

**REQ Components**:

- REQ-B-B2-Plus-1: Auto-save each answer in real-time when user enters response (< 2 sec)
- REQ-B-B2-Plus-2: Auto-pause and save all responses when 20-minute time limit exceeded
- REQ-B-B2-Plus-3: Resume capability - restore previous answers, continue from last question
- REQ-B-B2-Plus-4: Record metadata (response_time_ms, saved_at) with each answer
- REQ-B-B2-Plus-5: Performance - all saves complete within 2 seconds

---

## 🎯 Implementation Approach

### **Time Management Strategy**

- **Default Time Limit**: 1200000ms (20 minutes)
- **Tracking**: `started_at` set on first answer, `paused_at` set on timeout
- **Calculation**: `elapsed_ms = now - started_at`, `remaining_ms = max(0, time_limit - elapsed_ms)`

### **Auto-save Workflow**

1. User submits answer → POST /questions/autosave
2. AutosaveService validates session/question
3. Sets `started_at` timestamp on first answer
4. Creates or updates AttemptAnswer record (idempotent)
5. Checks if time limit exceeded → auto-pauses if needed
6. Returns 200 OK with saved timestamp

### **Pause/Resume Workflow**

1. Time limit exceeded → `TestSession.status = "paused"`, `paused_at` set
2. User views resume option (frontend)
3. POST GET /questions/resume with session_id
4. AutosaveService returns:
   - All previous answers with metadata
   - Next unanswered question index
   - Time status (elapsed, remaining)
5. User resumes → PUT /questions/session/{id}/status changes status to "in_progress"
6. Continue answering from last position

---

## 📦 Files Created/Modified

### **New Files Created**

| File | Purpose | Lines |
|------|---------|-------|
| `src/backend/services/autosave_service.py` | Real-time save and resume logic | 340 |
| `tests/backend/test_autosave_service.py` | Service unit tests | 341 |
| `tests/backend/test_autosave_endpoints.py` | API integration tests | 459 |

### **Modified Files**

| File | Changes |
|------|---------|
| `src/backend/models/test_session.py` | Added time_limit_ms, started_at, paused_at fields |
| `src/backend/api/questions.py` | Added 4 new endpoints for autosave/resume |
| `tests/conftest.py` | Added test_session_in_progress fixture |

---

## 🏗️ Architecture

### **ORM Model Changes**

**TestSession** (extended fields):

```python
time_limit_ms: int = 1200000  # Default 20 minutes
started_at: Optional[datetime] = None  # Set on first answer
paused_at: Optional[datetime] = None  # Set when paused
```

### **Service Layer**

**AutosaveService**

```python
def save_answer(session_id, question_id, user_answer, response_time_ms) -> AttemptAnswer
    # Saves answer, sets started_at, checks time limit, auto-pauses if needed
    # Performance: < 2 seconds

def check_time_limit(session_id) -> dict
    # Returns: {exceeded, elapsed_ms, remaining_ms, status}

def pause_session(session_id, reason) -> TestSession
    # Sets status=paused, paused_at=now

def get_session_state(session_id) -> dict
    # Returns complete state for resumption:
    # {session_id, status, round, answered_count, total_questions,
    #  next_question_index, previous_answers, time_status}

def resume_session(session_id) -> TestSession
    # Sets status=in_progress, paused_at=None
```

### **API Endpoints**

**POST /questions/autosave** (200 OK)

```json
Request:
{
  "session_id": "uuid",
  "question_id": "uuid",
  "user_answer": {JSON response},
  "response_time_ms": 5000
}

Response:
{
  "saved": true,
  "session_id": "uuid",
  "question_id": "uuid",
  "saved_at": "2025-11-07T10:30:45.123Z"
}
```

**GET /questions/resume** (200 OK)

```json
Response:
{
  "session_id": "uuid",
  "status": "in_progress",
  "round": 1,
  "answered_count": 3,
  "total_questions": 5,
  "next_question_index": 3,
  "previous_answers": [
    {
      "question_id": "uuid",
      "user_answer": {...},
      "response_time_ms": 5000,
      "saved_at": "2025-11-07T10:30:45.123Z",
      "is_correct": false,
      "score": 0.0
    },
    ...
  ],
  "time_status": {
    "exceeded": false,
    "elapsed_ms": 600000,
    "remaining_ms": 600000,
    "status": "in_progress"
  }
}
```

**PUT /questions/session/{session_id}/status** (200 OK)

```
Request parameter: status=paused|in_progress

Response:
{
  "session_id": "uuid",
  "status": "paused",
  "paused_at": "2025-11-07T10:30:45.123Z"
}
```

**GET /questions/session/{session_id}/time-status** (200 OK)

```json
Response:
{
  "exceeded": false,
  "elapsed_ms": 600000,
  "remaining_ms": 600000,
  "status": "in_progress"
}
```

---

## 🧪 Test Coverage (33 tests, 100% pass rate)

### **Autosave Functionality** (7 tests)

- Save single answer successfully
- Sets started_at on first answer
- Idempotent saves (update existing)
- Invalid session error (404)
- Invalid question error (404)
- Cannot save to completed session (409)

### **Time Limit Checking** (3 tests)

- Within time limit (not exceeded)
- Time limit exceeded (> 20 min)
- Session not started yet (no elapsed time)

### **Pause/Resume** (4 tests)

- Pause session successfully
- Cannot pause completed session
- Resume paused session
- Cannot resume non-paused session

### **Session State** (1 test)

- Get session state with partial answers

### **API Endpoints** (18 tests)

- Autosave: success, MC/TF/short answer types, validation, timeout trigger
- Resume: success, with previous answers, invalid session, next question index
- Status: pause, resume, invalid status (422), resume non-paused (409)
- Time status: within limit, exceeded, invalid session (404)

**Results**: ✅ All 33 tests passing (100%)

---

## 🔄 Integration Points

### **Dependencies**

- `TestSession`, `Question`, `AttemptAnswer` models
- `User`, `UserProfileSurvey` models (from earlier REQs)
- FastAPI/SQLAlchemy ORM

### **Data Flow**

```
User answers question
  ↓
POST /questions/autosave
  ↓
AutosaveService.save_answer()
  ├─ Validate session/question
  ├─ Set started_at on first answer
  ├─ Create/update AttemptAnswer
  ├─ Check time limit
  └─ Auto-pause if exceeded (201+)
  ↓
Return 200 OK with saved_at timestamp

[On timeout]
  ↓
User requests resume
  ↓
GET /questions/resume
  ↓
AutosaveService.get_session_state()
  ├─ Retrieve all previous answers
  ├─ Find next unanswered question
  └─ Return complete state
  ↓
Return 200 OK with previous answers + next question

User resumes
  ↓
PUT /questions/session/{id}/status?status=in_progress
  ↓
AutosaveService.resume_session()
  ├─ Validate session is paused
  └─ Set status=in_progress, paused_at=null
  ↓
Return 200 OK, user can continue
```

---

## ✅ Acceptance Criteria Met

| Criteria | Status | Evidence |
|----------|--------|----------|
| Auto-save within 2 seconds | ✅ | All save tests complete in < 100ms (DB insert ~10-20ms) |
| Time limit enforcement | ✅ | Time check tests verify 20-min limit |
| Auto-pause on timeout | ✅ | Session.status=paused, paused_at set |
| Resume restores state | ✅ | All previous answers retrieved with metadata |
| Metadata recording | ✅ | response_time_ms, saved_at persisted in DB |
| API integration | ✅ | 4 endpoints, 18 integration tests |
| Input validation | ✅ | Invalid session/question return 404/422 |
| Idempotent saves | ✅ | Same answer saved twice updates once |

---

## 📝 Code Quality

- **Ruff linting**: ✅ All checks pass (7 auto-fixes applied)
- **Type hints**: ✅ Full type annotations on all functions
- **Docstrings**: ✅ All public APIs documented with REQ references
- **Line length**: ✅ ≤120 chars throughout

---

## 🚀 Next Steps

1. **REQ-B-B3-Score**: Implement scoring service (MC/TF exact match, short answer LLM-based)
2. **Round 3 Support**: Extend for 3-round testing with cumulative adaptation
3. **Frontend Integration**: Connect autosave API to test-taking UI
4. **Error Recovery**: Implement retry logic for failed saves

---

## 📚 Related Documentation

- Specification: `docs/feature_requirement_mvp1.md` (REQ-B-B2-Plus-1 through 5)
- Data Schema: `docs/PROJECT_SETUP_PROMPT.md`
- Previous Phases:
  - `docs/progress/REQ-B-B2-Gen.md` (1st Round Question Generation)
  - `docs/progress/REQ-B-B2-Adapt.md` (Adaptive Difficulty)

---

## 🔗 Commit Information

- **Branch**: main
- **Commit SHA**: c95dfcb
- **Message**: `feat: Implement REQ-B-B2-Plus real-time autosave and session resumption with full testing`
- **Files Changed**: 6 files (+1,442 lines, -3 lines)
