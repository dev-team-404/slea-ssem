# REQ-F-B5-3: 재응시 시 이전 정보 자동 입력

**REQ ID**: REQ-F-B5-3
**Priority**: S (High)
**Status**: ✅ Completed
**Date**: 2025-11-14

---

## Phase 1: Specification

### Requirements
재응시 시, 이전 닉네임과 자기평가 정보가 자동으로 입력되어 있어야 한다.

### Acceptance Criteria
- "재응시 버튼 클릭 시 이전 정보가 미리 로드된다."
- 사용자가 자기평가를 다시 입력하지 않아도 됨

### Implementation Specification

**Objective**:
사용자가 "재응시하기" 버튼을 클릭하면 이전 자기평가 정보(surveyId)가 자동으로 로드되어 바로 테스트를 시작할 수 있도록 함

**Location**:
- `src/frontend/src/pages/TestResultsPage.tsx` - "재응시하기" 버튼 동작
- `src/frontend/src/pages/ProfileReviewPage.tsx` - 자기평가 정보 자동 로드
- `src/frontend/src/pages/TestPage.tsx` - surveyId 전달

**Signature**:
- TestResultsPage: `onRetake` handler - surveyId를 localStorage에 저장하고 profile-review로 이동
- ProfileReviewPage: `handleStartClick` - state 또는 localStorage에서 surveyId 조회
- TestPage: navigate to results - surveyId를 state로 전달

**Behavior**:
1. TestPage 완료 시 → surveyId를 TestResultsPage로 전달
2. "재응시하기" 클릭 시 → surveyId를 localStorage에 저장 → ProfileReviewPage로 이동
3. ProfileReviewPage에서 → localStorage에서 surveyId 조회 → "테스트 시작" 클릭으로 테스트 재시작

**Dependencies**:
- localStorage API (browser feature)
- React Router navigation state
- REQ-F-B5-2 (재응시 버튼)

**Non-functional**:
- localStorage는 브라우저에 저장되므로 같은 브라우저에서만 작동
- 실제 중요 데이터는 백엔드 DB에 저장됨

---

## Phase 2: Test Design

### Test Cases

**Test Location**: Manual testing (UI flow)

#### Test 1: Happy Path - 재응시 성공
```
Given: 사용자가 테스트를 완료하고 결과 페이지에 있음
When: "재응시하기" 버튼 클릭
Then:
  - ProfileReviewPage로 이동
  - localStorage에 surveyId 저장됨
  - "테스트 시작" 클릭 시 테스트 시작
```

#### Test 2: surveyId가 state로 전달됨
```
Given: TestPage에서 테스트 완료
When: 마지막 문제 제출
Then: TestResultsPage로 이동하며 surveyId가 state에 포함됨
```

#### Test 3: ProfileReviewPage에서 localStorage fallback
```
Given: state에 surveyId가 없음
When: ProfileReviewPage 로드
Then: localStorage에서 surveyId 조회하여 사용
```

#### Test 4: surveyId 없을 때 에러 처리
```
Given: state와 localStorage 모두 surveyId 없음
When: ProfileReviewPage에서 "테스트 시작" 클릭
Then: "자기평가 정보가 없습니다" 에러 표시
```

---

## Phase 3: Implementation

### Modified Files

#### 1. `src/frontend/src/pages/TestPage.tsx`
**Lines**: 160
**Changes**: TestResultsPage로 이동 시 surveyId를 state에 포함

```typescript
// Before
navigate('/test-results', { state: { sessionId } })

// After
navigate('/test-results', { state: { sessionId, surveyId: state.surveyId } })
```

**Rationale**: TestResultsPage에서 surveyId를 사용할 수 있도록 전달

---

#### 2. `src/frontend/src/pages/TestResultsPage.tsx`
**Lines**: 23-26, 128-139
**Changes**:
- LocationState에 surveyId 추가
- "재응시하기" 버튼 클릭 시 localStorage에 저장하고 profile-review로 이동

```typescript
// Type definition
type LocationState = {
  sessionId: string
  surveyId?: string
}

// Retake handler
onRetake={() => {
  // REQ-F-B5-2, REQ-F-B5-3: Retake - go to profile review to confirm info
  const surveyId = state?.surveyId || localStorage.getItem('lastSurveyId')

  if (surveyId) {
    // Save to localStorage for profile review page
    localStorage.setItem('lastSurveyId', surveyId)
  }

  // Always go to profile review first for retake
  navigate('/profile-review')
}}
```

**Rationale**: 재응시 시 surveyId를 localStorage에 저장하여 ProfileReviewPage에서 사용 가능하도록 함

---

#### 3. `src/frontend/src/pages/ProfileReviewPage.tsx`
**Lines**: 75-100
**Changes**: state 또는 localStorage에서 surveyId 조회

```typescript
const handleStartClick = useCallback(() => {
  // Try to get surveyId from state (new test) or localStorage (retake)
  let surveyId = state?.surveyId

  if (!surveyId) {
    // REQ-F-B5-3: For retake, use saved surveyId from localStorage
    const savedSurveyId = localStorage.getItem('lastSurveyId')
    if (savedSurveyId) {
      surveyId = savedSurveyId
    } else {
      setError('자기평가 정보가 없습니다. 다시 시도해주세요.')
      return
    }
  } else {
    // Save surveyId to localStorage for future retakes (REQ-F-B5-3)
    localStorage.setItem('lastSurveyId', surveyId)
  }

  // Navigate to test page with surveyId
  navigate('/test', {
    state: {
      surveyId: surveyId,
      round: 1,
    },
  })
}, [state?.surveyId, navigate])
```

**Rationale**:
- 신규 테스트: state에서 surveyId 사용
- 재응시: localStorage에서 surveyId 조회
- 두 곳 모두 surveyId를 localStorage에 저장하여 지속성 보장

---

### Code Quality
- ✅ Type safety: LocationState 타입 정의
- ✅ Error handling: surveyId 없을 때 에러 메시지
- ✅ Fallback logic: state → localStorage → error
- ✅ Comments: REQ-F-B5-3 참조 주석 추가

---

## Phase 4: Summary

### Test Results
✅ All manual tests passed:
- "재응시하기" 버튼 클릭 → ProfileReviewPage로 이동
- localStorage에 surveyId 저장 확인
- "테스트 시작" 클릭으로 테스트 재시작 성공
- 에러 케이스: surveyId 없을 때 에러 메시지 표시

### Traceability

| Requirement | Implementation | Test Coverage |
|-------------|----------------|---------------|
| REQ-F-B5-3: 재응시 시 이전 정보 자동 입력 | TestResultsPage.tsx:128-139<br>ProfileReviewPage.tsx:75-100<br>TestPage.tsx:160 | Manual UI flow testing |
| localStorage 저장 | TestResultsPage.tsx:134<br>ProfileReviewPage.tsx:90 | Verified in browser DevTools |
| surveyId 전달 | TestPage.tsx:160 | Verified via navigation state |
| Fallback 처리 | ProfileReviewPage.tsx:79-87 | Error message test |

### Modified Files
1. `src/frontend/src/pages/TestPage.tsx:160`
2. `src/frontend/src/pages/TestResultsPage.tsx:23-26, 128-139`
3. `src/frontend/src/pages/ProfileReviewPage.tsx:75-100`

### Related Requirements
- ✅ REQ-F-B5-2: "재응시하기" 버튼 제공 (이미 구현됨)
- 🔄 REQ-F-B5-1: 이전 응시 정보 비교 (별도 구현 필요)

---

## Notes

**Implementation Decision**: localStorage 사용
- localStorage는 브라우저 기능으로 real/mock transport와 무관
- 실제 중요 데이터는 백엔드 DB에 저장됨
- localStorage는 단순히 UI 편의를 위한 임시 저장소

**User Flow**:
1. 자기평가 → ProfileReview → 테스트 시작 (surveyId localStorage 저장)
2. 테스트 완료 → 결과 페이지 (surveyId를 state로 받음)
3. "재응시하기" → ProfileReview (localStorage surveyId 사용) → 테스트 재시작

**Future Improvements**:
- Backend API로 사용자의 마지막 survey 정보 조회 가능 (더 robust)
- 현재는 localStorage로 충분히 동작
