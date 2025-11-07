# REQ-B-B2-Adapt: 2차 적응형 난이도 조정 (2nd Round Adaptive Difficulty Adjustment)

**Developer**: bwyoon (Backend)
**Status**: ✅ Phase 4 (Done - Ready for Merge)
**Completion Date**: 2025-11-07

---

## 📋 Requirement Summary

Analyze Round 1 test results (score, wrong-answer categories) and generate Round 2 questions with intelligently adjusted difficulty levels. Prioritize weak categories (≥50% of Round 2 questions) while respecting difficulty tier constraints.

**REQ Components**:

- REQ-B-B2-Adapt-1: Generate Round 2 test session with adaptive parameters
- REQ-B-B2-Adapt-2: Adjust difficulty tier based on Round 1 score
- REQ-B-B2-Adapt-3: Extract weak categories and prioritize them in Round 2
- REQ-B-B2-Adapt-4: Return adaptive parameters in response for analysis

---

## 🎯 Implementation Approach

### **Adaptive Difficulty Algorithm**

1. **Score → Tier Mapping** (REQ-B-B2-Adapt-2)
   - 0-40%: "low" tier → decrease difficulty or maintain
   - 40-70%: "medium" tier → maintain or slight increase
   - 70%+: "high" tier → increase difficulty

2. **Tier → Difficulty Adjustment**
   - Low: `round1_avg_difficulty - 1` (min 1.0)
   - Medium: `round1_avg_difficulty + 0.5`
   - High: `round1_avg_difficulty + 2` (max 10.0)

3. **Weak Category Prioritization** (REQ-B-B2-Adapt-3)
   - Extract categories with wrong answers from Round 1
   - Allocate ≥50% of Round 2 questions to weak categories
   - Distribute remaining slots evenly across other categories
   - If no other categories exist, overflow to weak categories

4. **Integrated Parameters** (REQ-B-B2-Adapt-1 & 4)
   - Return difficulty_tier, adjusted_difficulty, weak_categories, priority_ratio
   - Enable frontend to display adaptive reasoning to users

---

## 📦 Files Created/Modified

### **New Files Created**

| File | Purpose | Lines |
|------|---------|-------|
| `src/backend/models/test_result.py` | Store round scores & category analysis | 66 |
| `src/backend/models/attempt_answer.py` | Store individual user responses | 82 |
| `src/backend/services/adaptive_difficulty_service.py` | Difficulty adjustment logic | 239 |
| `src/backend/services/scoring_service.py` | Round score calculation | 147 |
| `tests/backend/test_adaptive_difficulty_service.py` | Service unit tests | 254 |
| `tests/backend/test_scoring_service.py` | Scoring service tests | 159 |
| `tests/backend/test_adaptive_questions_endpoint.py` | API integration tests | 277 |

### **Modified Files**

| File | Changes |
|------|---------|
| `src/backend/services/question_gen_service.py` | Added `generate_questions_adaptive()` method for Round 2 generation |
| `src/backend/api/questions.py` | Added `POST /questions/score` and `POST /questions/generate-adaptive` endpoints |
| `src/backend/models/__init__.py` | Added TestResult, AttemptAnswer exports |
| `src/backend/api/__init__.py` | Ensured questions_router export |
| `tests/conftest.py` | Added TestResult, AttemptAnswer imports and 6 fixture definitions |

---

## 🏗️ Architecture

### **ORM Models**

**TestResult** (`test_results` table)
- `id` (UUID, PK): Result identifier
- `session_id` (FK): Links to test_sessions
- `round` (1-3): Which test round
- `score` (0-100): Percentage score
- `total_points` (int): Points earned
- `correct_count` (int): Number correct
- `total_count` (int): Total questions
- `wrong_categories` (JSON, nullable): `{category: wrong_count}`
- `created_at`: Recording timestamp

**AttemptAnswer** (`attempt_answers` table)
- `id` (UUID, PK): Answer identifier
- `session_id` (FK): Links to test_sessions
- `question_id` (FK): Links to questions
- `user_answer` (JSON): User's response
- `is_correct` (bool): Correctness
- `score` (0-100): Partial credit (%)
- `response_time_ms` (int): Time taken
- `saved_at`: Timestamp

### **Service Layer**

**ScoringService**
```python
def calculate_round_score(session_id: str, round_num: int) -> dict
    # Returns: score, total_points, correct_count, total_count, wrong_categories

def save_round_result(session_id: str, round_num: int) -> TestResult
    # Persists calculated result to database
```

**AdaptiveDifficultyService**
```python
def get_difficulty_tier(score: float) -> str
    # Maps score → tier ("low", "medium", "high")

def calculate_round2_difficulty(round1_avg: float, score: float) -> float
    # Applies tier-based adjustment

def get_weak_categories(session_id: str) -> dict[str, int]
    # Extracts wrong answer categories

def get_category_priority_ratio(weak_categories: dict, total_questions: int) -> dict
    # Allocates questions ensuring ≥50% weak category coverage

def get_adaptive_generation_params(session_id: str) -> dict[str, Any]
    # Aggregates all parameters for Round 2 generation
```

**QuestionGenerationService** (extended)
```python
def generate_questions_adaptive(
    user_id: int, session_id: str, round_num: int = 2
) -> dict[str, Any]
    # Creates Round 2 session with:
    # - Adjusted difficulty (from AdaptiveDifficultyService)
    # - Weak category prioritization (≥50% coverage)
    # - Returns: session_id, questions[], adaptive_params
```

### **API Endpoints**

**POST /questions/score** (200 OK)
```json
Request:
  ?session_id=uuid

Response:
{
  "session_id": "uuid",
  "round": 1,
  "score": 20.0,
  "total_points": 20,
  "correct_count": 1,
  "total_count": 5,
  "wrong_categories": {"RAG": 2, "Robotics": 1, "LLM": 1}
}
```

**POST /questions/generate-adaptive** (201 Created)
```json
Request:
{
  "previous_session_id": "uuid",
  "round": 2
}

Response:
{
  "session_id": "new-uuid",
  "questions": [...],
  "adaptive_params": {
    "difficulty_tier": "low",
    "adjusted_difficulty": 4.0,
    "weak_categories": {"RAG": 2, "Robotics": 1, "LLM": 1},
    "priority_ratio": {"RAG": 3, "Robotics": 2},
    "score": 20.0,
    "correct_count": 1,
    "total_count": 5
  }
}
```

---

## 🧪 Test Coverage (41 tests, 100% pass rate)

### **Difficulty Tier Mapping** (5 tests)
- Score 0-40% → "low" tier
- Score 40-70% → "medium" tier
- Score 70%+ → "high" tier
- Invalid scores raise ValueError
- Boundary conditions verified

### **Difficulty Adjustment** (5 tests)
- Low tier: decrease by 1 (min 1.0)
- Medium tier: increase by 0.5
- High tier: increase by 2 (max 10.0)
- Clamping at min/max verified

### **Weak Category Extraction** (4 tests)
- Single weak category extraction
- Multiple weak categories
- No weak categories (all correct)
- Missing Round 1 result error handling

### **Category Prioritization** (4 tests)
- Single category gets ≥50% (3 of 5 questions)
- Multiple categories distributed fairly
- No categories returns empty ratio
- Ratio sums correctly

### **Scoring Service** (9 tests)
- All correct: 100% score
- Partial correct: proper calculation
- All wrong: 0% score
- Wrong category identification
- Multiple weak categories
- Save to database
- Query from database

### **API Endpoints** (11 tests)
- Score endpoint success with weak category detection
- Invalid session handling
- Generate adaptive success
- Response structure validation
- Adaptive parameters included
- Weak category prioritization verified (≥50%)
- Difficulty adjustment respected
- Invalid previous session error (404)
- Invalid round validation (422)
- End-to-end Round 1 → Round 2 flow

**Results**: ✅ All 41 tests passing (100%)

---

## 🔄 Integration Points

### **Dependencies**
- `TestSession`, `Question` models (from REQ-B-B2-Gen)
- `User`, `UserProfileSurvey` models (from REQ-B-A1, REQ-B-B1)
- `AttemptAnswer` model (new, pairs questions with responses)
- FastAPI/SQLAlchemy ORM

### **Data Flow**

```
Round 1:
  user → POST /questions/generate → TestSession created
       → answer questions
       → POST /questions/score → TestResult saved + wrong_categories extracted

Round 2:
  user → POST /questions/generate-adaptive
       → AdaptiveDifficultyService analyzes Round 1 TestResult
       → QuestionGenerationService creates new TestSession with:
         - Difficulty adjusted per tier
         - Questions prioritize weak categories (≥50%)
       → Return new session + adaptive_params for user feedback
```

### **Future Enhancements**
- Implement actual round_avg_difficulty calculation from Question records
- Add dynamic category constraints per user
- Support 3-round testing with cumulative adaptation
- LLM-based prompt generation with adaptive difficulty parameters

---

## ✅ Acceptance Criteria Met

| Criteria | Status | Evidence |
|----------|--------|----------|
| Adjust difficulty per tier | ✅ | Tests verify low(-1), medium(+0.5), high(+2) |
| Extract weak categories | ✅ | Tests extract and count wrong answers by category |
| Prioritize weak (≥50%) | ✅ | Tests verify at least 3 of 5 from weak categories |
| Return adaptive params | ✅ | Endpoint response includes all 4 parameter types |
| Clamp difficulty (1-10) | ✅ | Tests verify min 1.0 and max 10.0 |
| API integration | ✅ | Both endpoints tested with valid/invalid inputs |
| Input validation | ✅ | Invalid sessions/rounds return 404/422 |
| DB persistence | ✅ | TestResult and AttemptAnswer records created |

---

## 📝 Code Quality

- **Ruff linting**: ✅ All checks pass (46 ANN001 errors fixed with type annotations)
- **Type hints**: ✅ All functions have complete type annotations
- **Docstrings**: ✅ All public APIs documented with REQ references
- **Line length**: ✅ ≤ 120 chars throughout

---

## 🚀 Next Steps

1. **REQ-B-B3-Score**: Implement scoring service for MC/TF (exact match) and short answers (LLM-based)
2. **Round 3 Support**: Extend adaptive logic for 3-round testing
3. **LLM Integration**: Replace mock questions with actual LLM-generated content using adaptive parameters
4. **User Ranking**: Implement ranking calculation after all rounds complete

---

## 📚 Related Documentation

- Specification: `docs/feature_requirement_mvp1.md` (REQ-B-B2-Adapt-1 through 4)
- Data Schema: `docs/PROJECT_SETUP_PROMPT.md`
- Previous Phase: `docs/progress/REQ-B-B2-Gen.md` (1st Round Question Generation)

---

## 🔗 Commit Information

- **Branch**: main
- **Commit SHA**: (pending - will be set after merge)
- **Message**: `feat: Implement REQ-B-B2-Adapt 2nd round adaptive difficulty adjustment`
- **Files Changed**: 12 files (+1,225 lines, -42 lines)
