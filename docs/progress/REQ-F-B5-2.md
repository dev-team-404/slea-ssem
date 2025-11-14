# REQ-F-B5-2: 레벨 테스트 재응시 버튼

**REQ ID**: REQ-F-B5-2
**Priority**: M (Medium)
**Status**: ✅ Completed
**Date**: 2025-11-14

---

## Phase 1: Specification

### Requirements
대시보드 또는 결과 페이지에 "레벨 테스트 재응시" 버튼을 제공해야 한다.

### Acceptance Criteria
- "재응시 버튼 클릭 시 이전 정보가 미리 로드된다."
- 결과 페이지에서 사용자가 쉽게 재응시를 시작할 수 있음

### Implementation Specification

**Objective**:
TestResultsPage에 "재응시하기" 버튼을 추가하여 사용자가 테스트 완료 후 즉시 재응시할 수 있도록 함

**Location**:
- `src/frontend/src/components/TestResults/ActionButtons.tsx` - "재응시하기" 버튼 컴포넌트
- `src/frontend/src/pages/TestResultsPage.tsx` - onRetake handler 구현

**Signature**:
```typescript
// ActionButtons Component
interface ActionButtonsProps {
  onGoHome: () => void
  onRetake: () => void
}

// TestResultsPage onRetake handler
onRetake: () => void
```

**Behavior**:
1. TestResultsPage에 ActionButtons 컴포넌트 렌더링
2. ActionButtons는 2개의 버튼 표시:
   - "홈화면으로 이동" (primary button)
   - "재응시하기" (secondary button)
3. "재응시하기" 클릭 시:
   - surveyId를 state 또는 localStorage에서 조회
   - surveyId를 localStorage에 저장 (REQ-F-B5-3 연동)
   - /profile-review 페이지로 이동
4. /profile-review에서 이전 정보 자동 로드 (REQ-F-B5-3)

**Dependencies**:
- REQ-F-B4-1 (TestResultsPage 기본 기능)
- REQ-F-B5-3 (재응시 시 이전 정보 자동 입력)

**Non-functional**:
- 버튼 스타일: primary vs secondary 구분
- 명확한 액션 라벨 ("재응시하기", "홈화면으로 이동")
- 모바일/데스크톱 반응형 디자인

---

## Phase 2: Test Design

### Test Cases

**Test Locations**:
- `src/frontend/src/pages/__tests__/TestResultsPage.test.tsx` (5 tests)
- ActionButtons 컴포넌트는 단순 UI이므로 통합 테스트로 검증

#### TestResultsPage Integration Tests (5 tests)

**Test 1**: `"재응시하기" 버튼 클릭 시 /profile-review로 이동`
- Given: TestResultsPage with surveyId = 'survey_abc'
- When: User clicks "재응시하기" button
- Then:
  - surveyId saved to localStorage
  - navigate('/profile-review') called
- **Status**: ✅ PASS

**Test 2**: `surveyId를 state에서 localStorage로 저장`
- Given: state.surveyId = 'survey_xyz'
- When: "재응시하기" clicked
- Then: localStorage.getItem('lastSurveyId') === 'survey_xyz'
- **Status**: ✅ PASS

**Test 3**: `state에 surveyId 없을 때 localStorage에서 조회`
- Given: state has no surveyId, localStorage has 'saved_survey_123'
- When: "재응시하기" clicked
- Then:
  - navigate('/profile-review') called
  - localStorage still has 'saved_survey_123'
- **Status**: ✅ PASS

**Test 4**: `surveyId가 전혀 없어도 /profile-review로 이동`
- Given: No surveyId in state or localStorage
- When: "재응시하기" clicked
- Then: navigate('/profile-review') called (fallback behavior)
- **Status**: ✅ PASS

**Test 5**: `"홈화면으로 이동" 버튼 클릭 시 /home으로 이동`
- Given: TestResultsPage loaded
- When: User clicks "홈화면으로 이동" button
- Then: navigate('/home') called
- **Status**: ✅ PASS

---

## Phase 3: Implementation

### Modified/Created Files

#### 1. `src/frontend/src/components/TestResults/ActionButtons.tsx`
**Lines**: 1-25 (NEW FILE)
**Changes**: "재응시하기" 및 "홈화면으로 이동" 버튼 컴포넌트 생성

```typescript
// REQ: REQ-F-B4-1
import React from 'react'

interface ActionButtonsProps {
  onGoHome: () => void
  onRetake: () => void
}

/**
 * Action Buttons Component
 * Displays navigation buttons for home and retake actions
 */
export const ActionButtons: React.FC<ActionButtonsProps> = ({ onGoHome, onRetake }) => {
  return (
    <div className="action-buttons">
      <button type="button" className="primary-button" onClick={onGoHome}>
        홈화면으로 이동
      </button>
      <button type="button" className="secondary-button" onClick={onRetake}>
        재응시하기
      </button>
    </div>
  )
}
```

**Rationale**:
- 재사용 가능한 버튼 컴포넌트 분리
- primary/secondary 버튼 스타일 구분
- 명확한 액션 라벨

---

#### 2. `src/frontend/src/pages/TestResultsPage.tsx`
**Lines**: 156-172
**Changes**: ActionButtons 컴포넌트 렌더링 및 onRetake handler 구현

```typescript
{/* Action Buttons */}
<ActionButtons
  onGoHome={() => navigate('/home')}
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
/>
```

**Rationale**:
- surveyId 조회 우선순위: state > localStorage (fallback)
- surveyId를 localStorage에 저장하여 REQ-F-B5-3 연동
- /profile-review로 이동하여 사용자가 이전 정보 확인 가능
- surveyId가 없어도 재응시 시작 가능 (graceful fallback)

---

### Code Quality
- ✅ Type safety: TypeScript interfaces 정의
- ✅ Error handling: surveyId 없어도 동작
- ✅ Accessibility: semantic button elements
- ✅ Responsive design: CSS flexbox
- ✅ Comments: REQ-F-B5-2, REQ-F-B5-3 참조 주석

---

## Phase 4: Summary

### Test Results
✅ All automated tests passed (5 tests total):
- **TestResultsPage.test.tsx (REQ-F-B5-3 describe block)**: 5 tests (all PASS)

**Test Execution**:
```bash
npm test -- TestResultsPage --run
# Result: 8 passed (8 total, including REQ-F-B5-1 and REQ-F-B5-3 tests)
```

**Test Coverage**:
- "재응시하기" 버튼 클릭 및 navigation ✅
- surveyId localStorage 저장 ✅
- surveyId fallback (state → localStorage) ✅
- surveyId 없을 때 graceful fallback ✅
- "홈화면으로 이동" 버튼 동작 ✅

### Traceability

| Requirement | Implementation | Test Coverage |
|-------------|----------------|---------------|
| REQ-F-B5-2: "재응시하기" 버튼 제공 | ActionButtons.tsx:13-24<br>TestResultsPage.tsx:156-172 | ✅ 5 automated tests |
| 버튼 클릭 시 재응시 시작 | TestResultsPage.tsx:159-170 | ✅ TestResultsPage.test (Test 1, 4) |
| surveyId 저장 및 전달 | TestResultsPage.tsx:161-166 | ✅ TestResultsPage.test (Test 2, 3) |
| /profile-review 이동 | TestResultsPage.tsx:169 | ✅ TestResultsPage.test (Test 1, 3, 4) |
| "홈화면으로 이동" 버튼 | ActionButtons.tsx:16-18<br>TestResultsPage.tsx:158 | ✅ TestResultsPage.test (Test 5) |

### Modified/Created Files
1. `src/frontend/src/components/TestResults/ActionButtons.tsx` (NEW, 25 lines)
2. `src/frontend/src/pages/TestResultsPage.tsx:156-172` (ActionButtons integration)
3. `src/frontend/src/pages/__tests__/TestResultsPage.test.tsx:54-171` (5 tests)

### Related Requirements
- ✅ REQ-F-B4-1: 최종 결과 페이지 (기본 기능)
- ✅ REQ-F-B5-1: 이전 응시 정보 비교 섹션 (이미 구현됨)
- ✅ REQ-F-B5-3: 재응시 시 이전 정보 자동 입력 (연동됨)

---

## Notes

**Implementation Decision**: ActionButtons 컴포넌트 분리
- 버튼 로직을 재사용 가능한 컴포넌트로 분리
- TestResultsPage는 handler만 제공
- 향후 다른 페이지에서도 재사용 가능

**User Flow**:
1. 테스트 완료 → TestResultsPage
2. 결과 확인 → "재응시하기" 또는 "홈화면으로 이동" 선택
3. "재응시하기" 클릭:
   - surveyId를 localStorage에 저장
   - /profile-review로 이동
   - ProfileReviewPage에서 이전 정보 자동 로드 (REQ-F-B5-3)
   - "테스트 시작" 클릭 → 새 테스트 세션 시작

**Design Decisions**:
- primary button: "홈화면으로 이동" (기본 액션)
- secondary button: "재응시하기" (추가 액션)
- surveyId fallback: state → localStorage → 없어도 진행

**Future Improvements**:
- 재응시 제한 (예: 하루 1회)
- 재응시 전 확인 모달 ("이전 결과가 유지됩니다. 계속하시겠습니까?")
- 재응시 시 이전 결과 비교 미리보기
