# Answer Schema Formats Guide

**REQ**: REQ-REFACTOR-SOLID-3
**Last Updated**: 2025-11-24
**Status**: Complete

## Table of Contents

1. [Introduction](#introduction)
2. [Agent Response Format](#agent-response-format)
3. [Mock Data Format](#mock-data-format)
4. [Database Storage Format](#database-storage-format)
5. [API Response Format](#api-response-format)
6. [Transformation Pipeline](#transformation-pipeline)
7. [Validation Rules](#validation-rules)
8. [Code Examples](#code-examples)
9. [Adding New Formats](#adding-new-formats)
10. [File References](#file-references)
11. [Troubleshooting](#troubleshooting)

---

## 1. Introduction

### Purpose

This guide documents how answer schema data flows through the system across different formats and transformations. It serves as a central reference for:
- Understanding the 4 formats (Agent Response, Mock Data, Database, API Response)
- Implementing new answer schema sources
- Debugging format-related issues
- Maintaining consistency across the codebase

### Audience

- **Backend Developers**: Implementing new LLM agent responses or data sources
- **API Clients**: Understanding answer_schema structure in API responses
- **QA/Testing**: Creating mock data and understanding validation rules
- **DevOps/Database**: Understanding the storage format for answer_schema column

### The Problem

Before standardization, each LLM response format had different field names:
- Agent A: `correct_keywords` (list)
- Agent B: `correct_key` (string)
- Agent C: Custom format with different structure

This inconsistency required:
- Manual transformation logic in each service
- Repeated null checks (leading to bugs)
- Modifications to multiple files when adding new formats
- Inconsistent error handling

### The Solution

The **Transformer Pattern + Value Object** approach standardizes all formats:

```
Source Format (LLM/Mock) → Transformer → AnswerSchema Value Object → DB/API
                                          (immutable, validated)
```

Benefits:
- Single transformation layer (SRP)
- New formats require no existing code changes (OCP)
- Type-safe, immutable objects (no null bugs)
- Consistent validation everywhere
- Clear data flow contracts

---

## 2. Agent Response Format

### What Is It?

The format returned by the LLM Agent when generating questions with answer schemas. This is the raw output from the language model.

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `correct_keywords` | `list[str]` | Yes | Acceptable keywords for short-answer validation |
| `explanation` | `str` | Yes | Why this answer is correct |

### Format Structure

```json
{
  "question_id": "q_001",
  "question_text": "무엇이 배터리의 핵심 구성 요소인가?",
  "answer_schema": {
    "correct_keywords": ["리튬이온", "배터리"],
    "explanation": "리튬이온 배터리는 높은 에너지 밀도와 긴 수명을 가진 충전식 배터리이다."
  }
}
```

### Example 1: Basic Keyword Matching

**Raw LLM Response**:
```json
{
  "correct_keywords": ["배터리", "리튬"],
  "explanation": "리튬이온 배터리는 고에너지 밀도를 가진다."
}
```

**After Transformation**:
```python
AnswerSchema(
    type="keyword_match",
    keywords=["배터리", "리튬"],
    explanation="리튬이온 배터리는 고에너지 밀도를 가진다.",
    source_format="agent_response",
    created_at=datetime.now()
)
```

### Example 2: Multiple Acceptable Keywords

**Raw LLM Response**:
```json
{
  "correct_keywords": ["battery", "cell", "accumulator", "power source"],
  "explanation": "A battery is an electrochemical energy storage device that converts stored chemical energy into electrical energy."
}
```

**After Transformation**:
```python
AnswerSchema(
    type="keyword_match",
    keywords=["battery", "cell", "accumulator", "power source"],
    explanation="A battery is an electrochemical energy storage device...",
    source_format="agent_response"
)
```

### Example 3: Multilingual Keywords

**Raw LLM Response**:
```json
{
  "correct_keywords": ["전자기파", "electromagnetic wave", "EM wave"],
  "explanation": "전자기파는 진동하는 전기장과 자기장으로 이루어진 파동이다."
}
```

**After Transformation**:
```python
AnswerSchema(
    type="keyword_match",
    keywords=["전자기파", "electromagnetic wave", "EM wave"],
    explanation="전자기파는 진동하는 전기장과 자기장으로 이루어진 파동이다.",
    source_format="agent_response"
)
```

### Transformation Rules

| Source Field | Target Field | Transformation | Notes |
|--------------|--------------|-----------------|-------|
| `correct_keywords` | `keywords` | No change (list) | Type: keyword_match |
| `explanation` | `explanation` | No change (string) | Validated non-empty |
| N/A | `type` | Set to "keyword_match" | Inferred from format |
| N/A | `source_format` | Set to "agent_response" | Metadata for tracing |
| N/A | `created_at` | Set to current datetime | Timestamp for auditing |

---

## 3. Mock Data Format

### What Is It?

Test data format used for fallback scenarios when the LLM is unavailable or for unit testing. Simpler structure than agent responses.

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `correct_key` | `str` | Yes | The single correct answer (for multiple choice) |
| `explanation` | `str` | Yes | Why this answer is correct |

### Format Structure

```json
{
  "question_id": "q_002",
  "question_text": "다음 중 정답은?",
  "answer_schema": {
    "correct_key": "B",
    "explanation": "B 선택지가 정답이다. 왜냐하면..."
  }
}
```

### Example 1: Multiple Choice Question

**Raw Mock Data**:
```json
{
  "correct_key": "B",
  "explanation": "Option B is the correct answer because it accurately describes the process."
}
```

**After Transformation**:
```python
AnswerSchema(
    type="exact_match",
    correct_answer="B",
    explanation="Option B is the correct answer because...",
    source_format="mock_data"
)
```

### Example 2: True/False Question

**Raw Mock Data**:
```json
{
  "correct_key": "True",
  "explanation": "The statement is true. Living organisms require energy to survive."
}
```

**After Transformation**:
```python
AnswerSchema(
    type="exact_match",
    correct_answer="True",
    explanation="The statement is true...",
    source_format="mock_data"
)
```

### Example 3: Numeric or Formula Answer

**Raw Mock Data**:
```json
{
  "correct_key": "F(x) = 2x + 3",
  "explanation": "This linear function has slope 2 and y-intercept 3."
}
```

**After Transformation**:
```python
AnswerSchema(
    type="exact_match",
    correct_answer="F(x) = 2x + 3",
    explanation="This linear function has slope 2 and y-intercept 3.",
    source_format="mock_data"
)
```

### Transformation Rules

| Source Field | Target Field | Transformation | Notes |
|--------------|--------------|-----------------|-------|
| `correct_key` | `correct_answer` | No change (string) | Type: exact_match |
| `explanation` | `explanation` | No change (string) | Validated non-empty |
| N/A | `type` | Set to "exact_match" | Inferred from format |
| N/A | `source_format` | Set to "mock_data" | Metadata for tracing |
| N/A | `created_at` | Set to current datetime | Timestamp for auditing |

---

## 4. Database Storage Format

### What Is It?

The normalized format stored in the PostgreSQL database `test_questions.answer_schema` JSON column. This is the canonical representation that all formats transform into.

### Database Schema

**Table**: `test_questions`

**Column**: `answer_schema` (JSONB)

### Storage Structure

```python
{
    "type": "keyword_match" or "exact_match",
    "keywords": ["keyword1", "keyword2"] or None,
    "correct_answer": "answer_str" or None,
    "explanation": "detailed explanation",
    "source_format": "agent_response" or "mock_data",
    "created_at": "2025-11-24T10:30:00.123456"
}
```

### Constraints

1. **type** (required): One of:
   - `"keyword_match"` - Short answer with acceptable keywords
   - `"exact_match"` - Multiple choice or exact answer matching
   - `"true_false"` - Boolean answer (stored as "True"/"False")
   - `"multiple_choice"` - MC question with option key

2. **keywords vs correct_answer** (exactly one required):
   - For `keyword_match` type: `keywords` must be list[str], `correct_answer` must be None
   - For `exact_match` type: `correct_answer` must be string, `keywords` must be None
   - ❌ NEVER both present
   - ❌ NEVER both None

3. **explanation** (required): Non-empty string

4. **source_format** (required): Source of the data (for auditing)

5. **created_at** (required): ISO 8601 datetime string

### Example 1: Agent Response Stored

**Original Agent Response**:
```json
{
  "correct_keywords": ["배터리", "리튬"],
  "explanation": "리튬이온 배터리는..."
}
```

**Stored in DB** (answer_schema column):
```json
{
  "type": "keyword_match",
  "keywords": ["배터리", "리튬"],
  "correct_answer": null,
  "explanation": "리튬이온 배터리는...",
  "source_format": "agent_response",
  "created_at": "2025-11-24T10:30:00.123456"
}
```

### Example 2: Mock Data Stored

**Original Mock Data**:
```json
{
  "correct_key": "B",
  "explanation": "B는 정답이다."
}
```

**Stored in DB** (answer_schema column):
```json
{
  "type": "exact_match",
  "keywords": null,
  "correct_answer": "B",
  "explanation": "B는 정답이다.",
  "source_format": "mock_data",
  "created_at": "2025-11-24T10:30:00.123456"
}
```

### Database SQL Example

```sql
-- Insert a question with answer_schema
INSERT INTO test_questions (
    question_text,
    answer_schema,
    created_at
) VALUES (
    '배터리의 정의는?',
    '{"type":"keyword_match","keywords":["배터리","리튬"],"correct_answer":null,"explanation":"배터리는...","source_format":"agent_response","created_at":"2025-11-24T10:30:00Z"}'::jsonb,
    NOW()
);

-- Query by answer type
SELECT * FROM test_questions
WHERE answer_schema->>'type' = 'keyword_match';

-- Query by source format (to find mock vs agent)
SELECT * FROM test_questions
WHERE answer_schema->>'source_format' = 'agent_response';
```

---

## 5. API Response Format

### What Is It?

The format returned to API clients when requesting question details. Excludes internal metadata like `source_format` and `created_at`.

### Exposed Fields

| Field | Type | Included | Reason |
|-------|------|----------|--------|
| `type` | `str` | Yes | Client needs to know question type |
| `keywords` | `list[str] \| null` | Yes | Used for answer matching |
| `correct_answer` | `str \| null` | Yes | Used for scoring |
| `explanation` | `str` | Yes | Shown to user after answer |
| `source_format` | `str` | No | Internal implementation detail |
| `created_at` | `datetime` | No | Internal audit trail |

### Response Structure

```python
{
    "id": "q_001",
    "question_text": "배터리의 핵심은?",
    "answer_schema": {
        "type": "keyword_match",
        "keywords": ["배터리", "리튬"],
        "correct_answer": null,
        "explanation": "배터리는 화학 에너지를..."
    }
}
```

### Example 1: Short Answer Response

**API Response** (GET /api/questions/q_001):
```json
{
    "id": "q_001",
    "question_text": "무엇이 배터리의 핵심 구성 요소인가?",
    "answer_schema": {
        "type": "keyword_match",
        "keywords": ["리튬이온", "배터리"],
        "correct_answer": null,
        "explanation": "리튬이온 배터리는 높은 에너지 밀도를 가진다."
    }
}
```

### Example 2: Multiple Choice Response

**API Response** (GET /api/questions/q_002):
```json
{
    "id": "q_002",
    "question_text": "정답을 선택하세요",
    "options": ["A", "B", "C", "D"],
    "answer_schema": {
        "type": "exact_match",
        "keywords": null,
        "correct_answer": "B",
        "explanation": "Option B is the correct answer because..."
    }
}
```

### Implementation in Code

```python
# In service layer:
def get_question(question_id: str) -> dict:
    question = db.query(TestQuestion).get(question_id)

    # answer_schema comes from DB with all fields
    # But we only expose selected fields to client
    return {
        "id": question.id,
        "question_text": question.question_text,
        "answer_schema": {
            "type": question.answer_schema["type"],
            "keywords": question.answer_schema.get("keywords"),
            "correct_answer": question.answer_schema.get("correct_answer"),
            "explanation": question.answer_schema["explanation"]
            # Note: source_format and created_at NOT included
        }
    }
```

---

## 6. Transformation Pipeline

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA SOURCE                               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  LLM Agent Response         Mock Data         Custom Format  │
│  ─────────────────         ─────────         ──────────────  │
│  {                         {                 {               │
│    correct_keywords:       correct_key:      custom_field:   │
│    [...],                  "B",              ...             │
│    explanation: "..."      explanation: "..."  explanation:  │
│  }                         }                 }               │
│                                                               │
└──────────────────────┬──────────────────────┬────────────────┘
                       │                      │
                       ▼                      ▼
             ┌─────────────────────────────────┐
             │   TRANSFORMER LAYER             │
             ├─────────────────────────────────┤
             │                                 │
             │  AgentResponseTransformer       │
             │  MockDataTransformer            │
             │  CustomTransformer              │
             │  TransformerFactory             │
             │                                 │
             └──────────────┬──────────────────┘
                            │
                            ▼
        ┌──────────────────────────────────────┐
        │  STANDARD DICT (Normalized)           │
        ├──────────────────────────────────────┤
        │  {                                   │
        │    "type": "keyword_match",          │
        │    "keywords": [...],                │
        │    "correct_answer": null,           │
        │    "explanation": "...",             │
        │    "source_format": "agent_response" │
        │  }                                   │
        └──────────┬───────────────────────────┘
                   │
                   ▼
    ┌───────────────────────────────────────────┐
    │  VALUE OBJECT LAYER (AnswerSchema)        │
    ├───────────────────────────────────────────┤
    │  AnswerSchema(                            │
    │    type="keyword_match",                  │
    │    keywords=[...],                        │
    │    explanation="...",                     │
    │    source_format="agent_response",        │
    │    created_at=datetime.now()              │
    │  )                                        │
    │                                           │
    │  Properties:                              │
    │  • Immutable (frozen=True)                │
    │  • Validated (__post_init__)              │
    │  • Hashable and comparable                │
    └───────────────┬──────────────────────────┘
                    │
        ┌───────────┴──────────┐
        ▼                      ▼
   ┌─────────────┐      ┌──────────────┐
   │   TO DB     │      │  TO API      │
   ├─────────────┤      ├──────────────┤
   │ .to_db_     │      │ .to_response │
   │ dict()      │      │ _dict()      │
   │             │      │              │
   │ Includes:   │      │ Excludes:    │
   │ • All       │      │ • source_    │
   │   fields    │      │   format     │
   │ • created_at│      │ • created_at │
   │ • source_   │      │              │
   │   format    │      │ Only what    │
   │             │      │ client needs │
   └──────┬──────┘      └──────┬───────┘
          ▼                     ▼
    ┌──────────┐          ┌────────────┐
    │ Database │          │ API Client │
    │ Storage  │          │ Response   │
    │ (JSONB)  │          │            │
    └──────────┘          └────────────┘
```

### Step-by-Step Flow: Agent Response

**Step 1: Agent generates response**
```python
llm_response = {
    "correct_keywords": ["답1", "답2"],
    "explanation": "설명"
}
```

**Step 2: Select appropriate transformer**
```python
factory = TransformerFactory()
transformer = factory.get_transformer("agent_response")
# Returns: AgentResponseTransformer instance
```

**Step 3: Transform to standard dict**
```python
transformed = transformer.transform(llm_response)
# Returns: {
#   "type": "keyword_match",
#   "keywords": ["답1", "답2"],
#   "explanation": "설명",
#   "source_format": "agent_response"
# }
```

**Step 4: Create immutable Value Object**
```python
answer_schema = AnswerSchema(
    type=transformed["type"],
    keywords=transformed.get("keywords"),
    correct_answer=transformed.get("correct_answer"),
    explanation=transformed.get("explanation"),
    source_format=transformed.get("source_format")
)
```

**Step 5: Store in database**
```python
db_dict = answer_schema.to_db_dict()
question.answer_schema = db_dict
session.commit()
# Stored in DB as JSONB
```

**Step 6: Return to API client**
```python
api_dict = answer_schema.to_response_dict()
return {
    "question_id": question.id,
    "answer_schema": api_dict
}
# Client receives: {"type", "keywords", "correct_answer", "explanation"}
```

### Validation Points

Validation occurs at two critical points:

1. **Transformer Level** (AgentResponseTransformer, MockDataTransformer):
   - Checks required fields exist
   - Validates field types
   - Ensures non-empty values
   - Validates list/string formats

2. **Value Object Level** (AnswerSchema.__post_init__):
   - Re-validates all constraints
   - Ensures immutability
   - Prevents invalid state

```python
# Example: Double validation
raw_data = {
    "correct_keywords": "",  # INVALID: empty
    "explanation": "test"
}

# Transformer catches it first:
transformer.transform(raw_data)  # Raises ValidationError

# Even if somehow invalid dict passed:
AnswerSchema(**invalid_dict)  # __post_init__ catches it again
```

### Error Handling Flow

```
Invalid Input
     │
     ├─► Transformer catches immediately
     │   └─► Raises ValidationError/TypeError
     │       └─► Service logs error, returns 400 Bad Request
     │
     └─► IF transformer passed (shouldn't happen)
         └─► AnswerSchema.__post_init__ catches
             └─► Raises ValidationError/TypeError
                 └─► Development error (caught in tests)
```

---

## 7. Validation Rules

### AnswerSchema Field Constraints

#### 1. `type` Field

**Requirement**: Non-empty string

**Valid Values**:
- `"keyword_match"` - Short answer with acceptable keywords
- `"exact_match"` - Multiple choice or exact answer
- `"true_false"` - Boolean question
- `"multiple_choice"` - MC with option keys

**Invalid Values**:
```python
# ❌ Wrong: empty string
AnswerSchema(type="", keywords=["a"], explanation="x")
# Raises: ValidationError("type cannot be empty")

# ❌ Wrong: not a string
AnswerSchema(type=123, keywords=["a"], explanation="x")  # type: ignore
# Raises: TypeError("type must be str")

# ✅ Correct
AnswerSchema(type="keyword_match", keywords=["a"], explanation="x")
```

#### 2. `keywords` Field

**Requirement**: `list[str] | None`

**Constraints**:
- If present: Must be non-empty list of strings
- If absent: Must be None
- Cannot be empty list (would indicate validation failure)

**Valid Values**:
```python
# ✅ Present
AnswerSchema(
    type="keyword_match",
    keywords=["답1", "답2"],
    explanation="설명"
)

# ✅ Absent (None)
AnswerSchema(
    type="exact_match",
    keywords=None,
    correct_answer="B",
    explanation="설명"
)
```

**Invalid Values**:
```python
# ❌ Wrong: string instead of list
AnswerSchema(
    type="keyword_match",
    keywords="답",  # type: ignore
    explanation="설명"
)
# Raises: TypeError("keywords must be list")

# ❌ Wrong: dict instead of list
AnswerSchema(
    type="keyword_match",
    keywords={"key": "value"},  # type: ignore
    explanation="설명"
)
# Raises: TypeError("keywords must be list")

# ❌ Wrong: non-string items
AnswerSchema(
    type="keyword_match",
    keywords=["답1", 123],  # type: ignore
    explanation="설명"
)
# Raises: TypeError("All items in keywords must be strings")
```

#### 3. `correct_answer` Field

**Requirement**: `str | None`

**Constraints**:
- If present: Must be non-empty string
- If absent: Must be None
- Cannot be empty string (would indicate validation failure)

**Valid Values**:
```python
# ✅ Present
AnswerSchema(
    type="exact_match",
    correct_answer="B",
    explanation="설명"
)

# ✅ Absent (None)
AnswerSchema(
    type="keyword_match",
    keywords=["답"],
    correct_answer=None,
    explanation="설명"
)
```

**Invalid Values**:
```python
# ❌ Wrong: list instead of string
AnswerSchema(
    type="exact_match",
    correct_answer=["B"],  # type: ignore
    explanation="설명"
)
# Raises: TypeError("correct_answer must be str")

# ❌ Wrong: empty string
AnswerSchema(
    type="exact_match",
    correct_answer="",
    explanation="설명"
)
# This may be allowed (application logic), but validates as string

# ❌ Wrong: both keywords and correct_answer present
AnswerSchema(
    type="keyword_match",
    keywords=["답"],
    correct_answer="B",  # Both set!
    explanation="설명"
)
# Allowed at AnswerSchema level (not explicitly validated)
# but violates semantic constraint (should be only one)
```

#### 4. `explanation` Field

**Requirement**: Non-empty string (required)

**Constraints**:
- Must be string
- Cannot be empty
- Cannot be whitespace-only

**Valid Values**:
```python
# ✅ Correct
AnswerSchema(
    type="keyword_match",
    keywords=["답"],
    explanation="이것이 정답이다"
)
```

**Invalid Values**:
```python
# ❌ Wrong: empty string
AnswerSchema(
    type="keyword_match",
    keywords=["답"],
    explanation=""
)
# Raises: ValidationError("explanation cannot be empty")

# ❌ Wrong: whitespace-only
AnswerSchema(
    type="keyword_match",
    keywords=["답"],
    explanation="   "
)
# Raises: ValidationError("explanation cannot be empty or whitespace-only")

# ❌ Wrong: not a string
AnswerSchema(
    type="keyword_match",
    keywords=["답"],
    explanation=123  # type: ignore
)
# Raises: TypeError("explanation must be str")
```

#### 5. `keywords` vs `correct_answer` Mutual Exclusivity

**Core Rule**: Exactly one must be present (not both, not neither)

**Valid Combinations**:
```python
# ✅ Case 1: keywords present, correct_answer absent
AnswerSchema(
    type="keyword_match",
    keywords=["답1", "답2"],
    correct_answer=None,
    explanation="설명"
)

# ✅ Case 2: keywords absent, correct_answer present
AnswerSchema(
    type="exact_match",
    keywords=None,
    correct_answer="B",
    explanation="설명"
)
```

**Invalid Combinations**:
```python
# ❌ Case 1: Both None
AnswerSchema(
    type="keyword_match",
    keywords=None,
    correct_answer=None,
    explanation="설명"
)
# Raises: ValidationError("AnswerSchema must have either keywords or correct_answer (not both None)")

# ✅ Case 2: Both present (technically allowed, but violates semantics)
# This is NOT caught by AnswerSchema validation
# But transformer prevents it by design
```

#### 6. `source_format` Field

**Requirement**: Non-empty string

**Valid Values**:
```python
# ✅ From Agent
AnswerSchema(
    ...,
    source_format="agent_response"
)

# ✅ From Mock
AnswerSchema(
    ...,
    source_format="mock_data"
)

# ✅ Custom
AnswerSchema(
    ...,
    source_format="my_custom_format"
)
```

**Invalid Values**:
```python
# ❌ Wrong: empty
AnswerSchema(..., source_format="")
# Raises: TypeError (depends on implementation)

# ❌ Wrong: None
AnswerSchema(..., source_format=None)  # type: ignore
# Raises: TypeError
```

#### 7. `created_at` Field

**Requirement**: `datetime | None` (auto-set if None)

**Behavior**:
- If not provided or None: Automatically set to `datetime.now()`
- If provided: Used as-is

**Valid Values**:
```python
from datetime import datetime

# ✅ Auto-set (recommended)
schema = AnswerSchema(..., created_at=None)
assert schema.created_at is not None  # Auto-set to now

# ✅ Explicit timestamp
schema = AnswerSchema(
    ...,
    created_at=datetime(2025, 11, 24, 10, 30, 0)
)
assert schema.created_at == datetime(2025, 11, 24, 10, 30, 0)
```

### Transformer Input Validation

#### AgentResponseTransformer

**Required Fields**:
- `correct_keywords`: `list[str]` (non-empty)
- `explanation`: `str` (non-empty)

**Validation Rules**:

| Condition | Error | Code |
|-----------|-------|------|
| Missing `correct_keywords` | `ValidationError` | Missing field |
| `correct_keywords` is not list | `TypeError` | Type mismatch |
| `correct_keywords` is empty | `ValidationError` | Empty list |
| Item in `correct_keywords` not string | `TypeError` | List item type |
| Missing `explanation` | `ValidationError` | Missing field |
| `explanation` is not string | `TypeError` | Type mismatch |
| `explanation` is empty/whitespace | `ValidationError` | Empty string |

**Example Validations**:

```python
transformer = AgentResponseTransformer()

# ❌ Missing correct_keywords
with pytest.raises(ValidationError):
    transformer.transform({"explanation": "test"})

# ❌ Correct_keywords not a list
with pytest.raises(TypeError):
    transformer.transform({
        "correct_keywords": "string",
        "explanation": "test"
    })

# ❌ List item not string
with pytest.raises(TypeError):
    transformer.transform({
        "correct_keywords": ["답", 123],
        "explanation": "test"
    })

# ❌ Empty keywords
with pytest.raises(ValidationError):
    transformer.transform({
        "correct_keywords": [],
        "explanation": "test"
    })

# ✅ Valid
result = transformer.transform({
    "correct_keywords": ["답1", "답2"],
    "explanation": "설명"
})
assert result["type"] == "keyword_match"
```

#### MockDataTransformer

**Required Fields**:
- `correct_key`: `str` (non-empty)
- `explanation`: `str` (non-empty)

**Validation Rules**:

| Condition | Error | Code |
|-----------|-------|------|
| Missing `correct_key` | `ValidationError` | Missing field |
| `correct_key` is not string | `TypeError` | Type mismatch |
| `correct_key` is empty/whitespace | `ValidationError` | Empty string |
| Missing `explanation` | `ValidationError` | Missing field |
| `explanation` is not string | `TypeError` | Type mismatch |
| `explanation` is empty/whitespace | `ValidationError` | Empty string |

**Example Validations**:

```python
transformer = MockDataTransformer()

# ❌ Missing correct_key
with pytest.raises(ValidationError):
    transformer.transform({"explanation": "test"})

# ❌ Correct_key not a string
with pytest.raises(TypeError):
    transformer.transform({
        "correct_key": 123,
        "explanation": "test"
    })

# ❌ Empty correct_key
with pytest.raises(ValidationError):
    transformer.transform({
        "correct_key": "",
        "explanation": "test"
    })

# ✅ Valid
result = transformer.transform({
    "correct_key": "B",
    "explanation": "설명"
})
assert result["type"] == "exact_match"
```

---

## 8. Code Examples

### Creating from Agent Response (Recommended Pattern)

**Step 1: Use factory method** (simplest)
```python
raw_data = {
    "correct_keywords": ["답1", "답2"],
    "explanation": "설명"
}

answer_schema = AnswerSchema.from_agent_response(raw_data)
# Result: Validated, immutable AnswerSchema object
```

**Step 2: Or use transformer + factory**
```python
factory = TransformerFactory()
transformer = factory.get_transformer("agent_response")

transformed = transformer.transform(raw_data)
answer_schema = AnswerSchema(
    type=transformed["type"],
    keywords=transformed.get("keywords"),
    correct_answer=transformed.get("correct_answer"),
    explanation=transformed.get("explanation", ""),
    source_format=transformed.get("source_format", "agent_response"),
)
```

### Creating from Mock Data (Recommended Pattern)

```python
raw_data = {
    "correct_key": "B",
    "explanation": "설명"
}

answer_schema = AnswerSchema.from_mock_data(raw_data)
# Result: Validated AnswerSchema with correct_answer="B"
```

### Using TransformerFactory (for extensibility)

```python
# Get transformer by format type
factory = TransformerFactory()
transformer = factory.get_transformer("agent_response")

# Transform raw data
transformed = transformer.transform(raw_agent_response)

# Create Value Object
answer_schema = AnswerSchema(
    type=transformed["type"],
    keywords=transformed.get("keywords"),
    explanation=transformed.get("explanation", ""),
    source_format=transformed.get("source_format", "agent_response"),
)

# Store in database
db_dict = answer_schema.to_db_dict()
question.answer_schema = db_dict
session.commit()
```

### Error Handling

```python
from src.backend.models.answer_schema import (
    ValidationError,
    UnknownFormatError,
)

try:
    # Attempt transformation
    transformer = factory.get_transformer(format_type)
    transformed = transformer.transform(raw_data)
    answer_schema = AnswerSchema(...)

except ValidationError as e:
    # Input validation failed
    logger.warning(f"Invalid answer schema: {e}")
    return {"error": "Invalid answer schema", "details": str(e)}

except UnknownFormatError as e:
    # Unknown format type
    logger.error(f"Unknown format: {e}")
    return {"error": "Unsupported format", "details": str(e)}

except TypeError as e:
    # Type mismatch
    logger.error(f"Type error: {e}")
    return {"error": "Type validation failed", "details": str(e)}
```

### In Service Layer (Question Generation)

```python
class QuestionGenerationService:
    def process_agent_response(self, agent_response: dict) -> list[AnswerSchema]:
        """Convert agent responses to AnswerSchema Value Objects."""

        factory = TransformerFactory()
        schemas = []

        for question in agent_response.get("questions", []):
            try:
                # Use factory method for simple cases
                schema = AnswerSchema.from_agent_response(
                    question.get("answer_schema", {})
                )
                schemas.append(schema)

            except ValidationError as e:
                logger.warning(f"Invalid schema for {question['id']}: {e}")
                # Use fallback or skip
                continue

        return schemas
```

### Converting for Database Storage

```python
# Create AnswerSchema from LLM response
answer_schema = AnswerSchema.from_agent_response(llm_data)

# Convert to database format (includes all metadata)
db_dict = answer_schema.to_db_dict()
# Output:
# {
#     "type": "keyword_match",
#     "keywords": [...],
#     "correct_answer": null,
#     "explanation": "...",
#     "source_format": "agent_response",
#     "created_at": datetime.now()
# }

# Store in database
question.answer_schema = db_dict
session.add(question)
session.commit()
```

### Converting for API Response

```python
# Retrieve question from database
question = session.query(TestQuestion).get(question_id)

# Convert to API response format (excludes internal fields)
api_dict = answer_schema.to_response_dict()
# Output:
# {
#     "type": "keyword_match",
#     "keywords": [...],
#     "correct_answer": null,
#     "explanation": "..."
# }

# Return to client
return {
    "id": question.id,
    "question_text": question.question_text,
    "answer_schema": api_dict
}
```

### Value Object Immutability

```python
answer_schema = AnswerSchema.from_agent_response({
    "correct_keywords": ["답"],
    "explanation": "설명"
})

# ✅ Read-only access
keywords = answer_schema.keywords  # ["답"]
explanation = answer_schema.explanation  # "설명"

# ❌ Cannot modify (frozen=True)
try:
    answer_schema.keywords = ["새로운 답"]  # type: ignore
except Exception as e:
    print(f"Cannot modify: {e}")  # FrozenInstanceError or AttributeError
```

### Using in Collections (Value Object)

```python
# AnswerSchema is hashable and comparable
schema1 = AnswerSchema.from_agent_response({"correct_keywords": ["a"], "explanation": "x"})
schema2 = AnswerSchema.from_agent_response({"correct_keywords": ["a"], "explanation": "x"})

# Equality by value
assert schema1 == schema2

# Can use in sets
schemas_set = {schema1, schema2}
assert len(schemas_set) == 1  # Duplicates removed

# Can use as dict keys
schema_map = {schema1: "value"}
assert schema_map[schema2] == "value"  # schema2 is same as schema1
```

---

## 9. Adding New Formats

### When to Add a New Format

Add a new format when:
1. New LLM provider has different response structure
2. New data source requires transformation
3. Existing formats don't fit the data structure

**DO NOT** modify existing transformers if data mostly fits.

### Step-by-Step Checklist

#### Step 1: Define the Raw Format

Document the new format structure:

```markdown
### CustomProvider Format

Input:
```json
{
    "answer_text": "The correct answer is...",
    "synonyms": ["also accept this", "or this"],
    "confidence": 0.95
}
```

Target: Keyword matching (use keywords field)
```

#### Step 2: Create New Transformer Class

```python
from src.backend.models.answer_schema import AnswerSchemaTransformer

class CustomProviderTransformer(AnswerSchemaTransformer):
    """Transform CustomProvider format to standard format."""

    def transform(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        Transform CustomProvider response to standard format.

        Args:
            raw_data: CustomProvider response dict

        Returns:
            Normalized dict with standard fields
        """
        # Validation
        if "answer_text" not in raw_data:
            raise ValidationError("Missing 'answer_text'")

        if "synonyms" not in raw_data:
            raise ValidationError("Missing 'synonyms'")

        answer_text = raw_data["answer_text"]
        synonyms = raw_data["synonyms"]

        if not isinstance(synonyms, list):
            raise TypeError("'synonyms' must be list")

        # Combine main answer + synonyms into keywords
        keywords = [answer_text] + synonyms

        return {
            "type": "keyword_match",
            "keywords": keywords,
            "explanation": f"Accepts: {', '.join(keywords)}",
            "source_format": "custom_provider",
        }
```

#### Step 3: Register with Factory

```python
from src.backend.models.answer_schema import TransformerFactory

# In your initialization code:
TransformerFactory.register_transformer(
    "custom_provider",
    CustomProviderTransformer
)

# Now available:
factory = TransformerFactory()
transformer = factory.get_transformer("custom_provider")
# Returns: CustomProviderTransformer instance
```

#### Step 4: Write Tests

```python
def test_custom_provider_transformer():
    """Test CustomProvider format transformation."""
    raw_data = {
        "answer_text": "정답",
        "synonyms": ["answer", "response"],
        "confidence": 0.95
    }

    transformer = CustomProviderTransformer()
    result = transformer.transform(raw_data)

    assert result["type"] == "keyword_match"
    assert "정답" in result["keywords"]
    assert "answer" in result["keywords"]
    assert result["source_format"] == "custom_provider"
```

#### Step 5: Update Documentation

Add to this guide:
1. New section under "Formats" with examples
2. Update transformation diagram (optional)
3. Add to troubleshooting if special handling needed

#### Step 6: Verify No Existing Code Breaks

- Run full test suite
- Check service layers don't reference specific transformers
- Ensure factory pattern used everywhere

### Checklist Summary

- [ ] New raw format documented (input/output examples)
- [ ] New transformer class created extending AnswerSchemaTransformer
- [ ] Implements transform() method with proper validation
- [ ] Registered with TransformerFactory.register_transformer()
- [ ] Unit tests covering happy path + error cases
- [ ] Integration tests with service layer
- [ ] Documentation updated with examples
- [ ] No existing code modified (Open/Closed principle)
- [ ] All tests passing
- [ ] Code review approved

---

## 10. File References

### Core Implementation Files

| File | Purpose | Key Classes |
|------|---------|-------------|
| `src/backend/models/answer_schema.py` | Core implementation | AnswerSchemaTransformer, AgentResponseTransformer, MockDataTransformer, TransformerFactory, AnswerSchema |
| `src/backend/services/question_gen_service.py` | Uses AnswerSchema | QuestionGenerationService (generates questions with answer schemas) |
| `src/backend/services/scoring_service.py` | Uses AnswerSchema | ScoringService (validates user answers against answer_schema) |

### Test Files

| File | Purpose | Test Coverage |
|------|---------|---|
| `tests/backend/test_answer_schema_transformers.py` | Transformer tests | AgentResponseTransformer, MockDataTransformer, TransformerFactory, validation |
| `tests/backend/test_answer_schema_value_object.py` | Value Object tests | AnswerSchema creation, validation, immutability, conversions |
| `tests/backend/test_answer_schema_formats_doc.py` | Documentation tests | Format examples, transformation flow, validation rules, documentation accuracy |

### Documentation Files

| File | Purpose |
|------|---------|
| `docs/ANSWER_SCHEMA_FORMATS.md` | This guide (comprehensive format reference) |
| `docs/SOLID_REFACTOR_REQUIREMENTS.md` | REQ definitions for SOLID refactoring phases |

### Database Schema

```sql
-- PostgreSQL table storing questions with answer schemas

CREATE TABLE test_questions (
    id UUID PRIMARY KEY,

    -- Answer schema as JSONB (stored in standard DB format)
    answer_schema JSONB NOT NULL,
    -- Structure:
    -- {
    --   "type": "keyword_match|exact_match",
    --   "keywords": [list of strings] OR null,
    --   "correct_answer": "string" OR null,
    --   "explanation": "string",
    --   "source_format": "agent_response|mock_data|...",
    --   "created_at": "ISO 8601 datetime"
    -- }

    created_at TIMESTAMP DEFAULT NOW()
);

-- Useful queries
-- Find all keyword-match questions
SELECT * FROM test_questions WHERE answer_schema->>'type' = 'keyword_match';

-- Find questions from Agent
SELECT * FROM test_questions WHERE answer_schema->>'source_format' = 'agent_response';

-- Find by keyword
SELECT * FROM test_questions
WHERE answer_schema->'keywords' @> '["keyword"]'::jsonb;
```

---

## 11. Troubleshooting

### Issue: "Missing 'correct_keywords' in agent response"

**Symptom**: ValidationError when transforming agent response

**Cause**: Agent response missing required `correct_keywords` field

**Solution**:
```python
# Check input has correct_keywords
raw_data = agent_response.get("answer_schema", {})
if "correct_keywords" not in raw_data:
    logger.error(f"Agent response missing correct_keywords: {raw_data}")
    # Use fallback or skip
else:
    schema = AnswerSchema.from_agent_response(raw_data)
```

---

### Issue: "keywords field is None after transformation"

**Symptom**: answer_schema.keywords is None when expecting keywords

**Cause**: Transformer selected wrong type or format detected incorrectly

**Solution**:
```python
# Wrong: Using mock transformer for agent data
transformer = factory.get_transformer("mock_data")  # WRONG
# Result: correct_answer set, keywords = None

# Correct: Use agent transformer
transformer = factory.get_transformer("agent_response")
```

---

### Issue: "AnswerSchema must have either keywords or correct_answer"

**Symptom**: ValidationError during AnswerSchema creation

**Cause**: Both keywords and correct_answer are None or both were provided

**Solution**:
```python
# Problem: Both None
AnswerSchema(
    type="keyword_match",
    keywords=None,  # ❌ Both are None
    correct_answer=None,  # ❌ Both are None
    explanation="test"
)
# Fix: Provide one or the other
AnswerSchema(
    type="keyword_match",
    keywords=["答"],  # ✅ One provided
    correct_answer=None,
    explanation="test"
)
```

---

### Issue: "Unknown format type 'custom'"

**Symptom**: UnknownFormatError when getting transformer

**Cause**: Custom format not registered with factory

**Solution**:
```python
# Register custom format before using
TransformerFactory.register_transformer(
    "custom",
    CustomTransformer
)

# Now works
factory = TransformerFactory()
transformer = factory.get_transformer("custom")
```

---

### Issue: "Field 'explanation' cannot be empty"

**Symptom**: ValidationError on empty explanation

**Cause**: LLM returned empty or whitespace-only explanation

**Solution**:
```python
# Validate before transformation
raw_data = agent_response.get("answer_schema", {})

if not raw_data.get("explanation", "").strip():
    logger.warning("Empty explanation in agent response")
    # Use fallback explanation or skip
    raw_data["explanation"] = "See correct keywords for answer"

schema = AnswerSchema.from_agent_response(raw_data)
```

---

### Issue: "Cannot modify frozen AnswerSchema"

**Symptom**: AttributeError or FrozenInstanceError when trying to modify

**Cause**: AnswerSchema is immutable (frozen dataclass)

**Solution**: This is intentional. Create new instance instead:
```python
# Wrong: Try to modify
schema.keywords = ["new"]  # ❌ FrozenInstanceError

# Correct: Create new instance
schema = AnswerSchema(
    type=schema.type,
    keywords=["new"],  # New keywords
    explanation=schema.explanation,
    source_format=schema.source_format
)
```

---

### Issue: "Type mismatch: correct_keywords must be list, got str"

**Symptom**: TypeError during transformation

**Cause**: LLM returned correct_keywords as string instead of list

**Solution**:
```python
# Validate and fix before transformation
raw_data = agent_response.get("answer_schema", {})

if isinstance(raw_data.get("correct_keywords"), str):
    # Convert string to list
    raw_data["correct_keywords"] = [raw_data["correct_keywords"]]

schema = AnswerSchema.from_agent_response(raw_data)
```

---

### Issue: "Database query returns dict, not AnswerSchema object"

**Symptom**: answer_schema from DB is dict, not AnswerSchema

**Cause**: Database stores JSONB, need to reconstruct AnswerSchema

**Solution**:
```python
# When loading from DB:
question = session.query(TestQuestion).get(question_id)

# answer_schema from DB is dict (JSONB)
db_dict = question.answer_schema  # type: dict

# Reconstruct AnswerSchema if needed:
answer_schema = AnswerSchema.from_dict(
    db_dict,
    source=db_dict.get("source_format", "unknown")
)

# Or just use db_dict directly for DB operations
```

---

### Issue: "source_format or created_at missing from API response"

**Symptom**: API returns full schema including internal fields

**Cause**: Using to_db_dict() instead of to_response_dict()

**Solution**:
```python
# Wrong: Includes internal fields
api_dict = schema.to_db_dict()  # ❌ Includes source_format, created_at

# Correct: Only user-facing fields
api_dict = schema.to_response_dict()  # ✅ Excludes internal metadata

return {
    "question_id": question.id,
    "answer_schema": api_dict
}
```

---

### Issue: "All tests passing, but docs are outdated"

**Symptom**: Code examples in docs don't match implementation

**Cause**: Manual documentation not kept in sync with code

**Solution**:
1. Run documentation tests regularly:
   ```bash
   pytest tests/backend/test_answer_schema_formats_doc.py -v
   ```

2. Use automated doctest if adding doc examples:
   ```python
   def transform(self, raw_data):
       """
       Example:
           >>> transformer = AgentResponseTransformer()
           >>> result = transformer.transform({
           ...     "correct_keywords": ["a"],
           ...     "explanation": "test"
           ... })
           >>> result["type"]
           'keyword_match'
       """
       ...
   ```

---

## Summary

This guide provides a complete reference for answer_schema format handling:

- **4 Formats**: Agent Response → Mock Data → Database → API Response
- **2 Transformers**: AgentResponseTransformer, MockDataTransformer
- **1 Value Object**: AnswerSchema (immutable, validated)
- **1 Factory**: TransformerFactory (extensible to new formats)
- **Validation**: Double-checked (transformer + __post_init__)
- **Immutability**: frozen=True prevents accidental modifications
- **Extensibility**: New formats require no changes to existing code

For questions or issues, refer to the troubleshooting section or check the test files for working examples.

---

**Document Version**: 1.0
**REQ**: REQ-REFACTOR-SOLID-3
**Files Updated**: `docs/ANSWER_SCHEMA_FORMATS.md`
**Last Reviewed**: 2025-11-24
