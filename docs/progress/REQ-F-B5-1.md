# REQ-F-B5-1: 이전 응시 정보 비교 섹션

**REQ ID**: REQ-F-B5-1
**Priority**: S (High)
**Status**: ✅ Completed
**Date**: 2025-11-14

---

## Phase 1: Specification

### Requirements
결과 페이지에 "이전 응시 정보 비교" 섹션을 표시하고, 이전 등급/점수와 현재 정보를 간단한 차트/텍스트로 비교해야 한다.

### Acceptance Criteria
- "이전 결과 vs 현재 결과 비교가 시각적으로 표시된다."

### Implementation Specification

**Objective**:
TestResultsPage에 사용자의 이전 테스트 결과와 현재 결과를 비교하는 섹션을 추가하여, 등급/점수 변화를 시각적으로 표시

**Location**:
- `src/frontend/src/pages/TestResultsPage.tsx` - 비교 섹션 통합
- `src/frontend/src/components/TestResults/ComparisonSection.tsx` - 비교 섹션 컴포넌트
- `src/frontend/src/services/resultService.ts` - 이전 결과 조회 API
- `src/frontend/src/lib/transport/mockTransport.ts` - Mock API

**Signature**:
```typescript
// Types
interface PreviousResult {
  grade: Grade
  score: number
  test_date: string  // ISO date string
}

// Service
resultService.getPreviousResult(): Promise<PreviousResult | null>

// Component
interface ComparisonSectionProps {
  currentGrade: Grade
  currentScore: number
  previousResult: PreviousResult | null
}
```

**Behavior**:
1. TestResultsPage 로드 시 사용자의 이전 테스트 결과 조회
2. 이전 결과가 있으면:
   - 등급 비교 (예: "Beginner → Intermediate")
   - 점수 비교 (예: "65점 → 75점 (+10점)")
   - 개선/하락 아이콘 (↑ 상승, ↓ 하락, → 변동없음)
   - 이전 테스트 날짜 표시
   - 요약 메시지 (예: "이전보다 10점 향상되었습니다!")
3. 이전 결과가 없으면:
   - "첫 응시입니다" 메시지
   - 현재 등급/점수만 표시

**Dependencies**:
- Backend API: `/api/results/previous` (Mock으로 구현)
- REQ-F-B4-1 (TestResultsPage 기본 기능)

**Non-functional**:
- 이전 결과는 가장 최근 1개만 표시
- Loading state 처리
- Error handling (API 실패 시 gracefully degrade)
- 시각적으로 명확한 비교 표시 (색상, 아이콘 사용)

---

## Phase 2: Test Design

### Test Cases

**Test Locations**:
- `src/frontend/src/components/TestResults/__tests__/ComparisonSection.test.tsx` (6 tests)
- `src/frontend/src/pages/__tests__/TestResultsPage.test.tsx` (3 tests added)

#### ComparisonSection Component Tests (6 tests)

**Test 1**: `점수/등급 상승 시 개선 표시`
- Given: previousResult = {grade: 'Beginner', score: 65}, current = {grade: 'Intermediate', score: 75}
- When: Component renders
- Then: "Beginner → Intermediate", "65점 → 75점 (+10점)", ↑ 아이콘, "10점 향상되었습니다!" 표시
- **Status**: ✅ PASS

**Test 2**: `점수/등급 하락 시 하락 표시`
- Given: previousResult = {grade: 'Intermediate', score: 75}, current = {grade: 'Beginner', score: 65}
- When: Component renders
- Then: ↓ 아이콘, "(-10점)", "10점 낮아졌습니다" 표시
- **Status**: ✅ PASS

**Test 3**: `변동 없음`
- Given: previousResult = {grade: 'Intermediate', score: 75}, current = same
- When: Component renders
- Then: "Intermediate (변동 없음)", "75점 (변동 없음)", → 아이콘, "이전과 동일한 성적입니다" 표시
- **Status**: ✅ PASS

**Test 4**: `이전 결과 없음 (첫 응시)`
- Given: previousResult = null
- When: Component renders
- Then: "첫 응시입니다" 메시지, 현재 등급/점수만 표시, 비교 정보 없음
- **Status**: ✅ PASS

**Test 5**: `이전 테스트 날짜 표시`
- Given: previousResult with test_date = '2025-01-10T10:00:00Z'
- When: Component renders
- Then: "이전 테스트: 2025년 1월 10일" 형식으로 표시
- **Status**: ✅ PASS

**Test 6**: `등급은 같지만 점수만 상승`
- Given: previousResult = {grade: 'Intermediate', score: 70}, current = {grade: 'Intermediate', score: 75}
- When: Component renders
- Then: 등급 "(변동 없음)", 점수 "70점 → 75점 (+5점)", ↑ 아이콘 1개만, "5점 향상되었습니다!" 표시
- **Status**: ✅ PASS

#### TestResultsPage Integration Tests (3 tests)

**Test 7**: `이전 결과 로드 성공 및 ComparisonSection 렌더링`
- Given: API returns previousResult = {grade: 'Beginner', score: 65, test_date: '2025-01-10'}
- When: TestResultsPage loads
- Then: ComparisonSection 렌더링, "성적 비교" 제목, 이전 결과 데이터 표시
- **Status**: ✅ PASS

**Test 8**: `이전 결과 없을 때 (첫 응시)`
- Given: API returns null
- When: TestResultsPage loads
- Then: ComparisonSection 렌더링, "첫 응시입니다" 메시지, 현재 결과만 표시
- **Status**: ✅ PASS

**Test 9**: `이전 결과 API 에러 시 ComparisonSection 숨김`
- Given: API call fails
- When: TestResultsPage loads
- Then: Main results displayed, ComparisonSection shows "첫 응시입니다" (null fallback)
- **Status**: ✅ PASS

---

## Phase 3: Implementation

### Modified/Created Files

#### 1. `src/frontend/src/lib/transport/mockTransport.ts`
**Lines**: 85-89
**Changes**: Mock API 데이터 추가

```typescript
'/results/previous': {
  grade: 'Beginner',
  score: 65,
  test_date: '2025-01-10T10:00:00Z',
}
```

**Rationale**: 개발 환경에서 테스트용 이전 결과 데이터 제공

---

#### 2. `src/frontend/src/services/resultService.ts`
**Lines**: 40-47, 66-81
**Changes**:
- PreviousResult interface 추가
- getPreviousResult() 메서드 추가

```typescript
export interface PreviousResult {
  grade: Grade
  score: number
  test_date: string
}

async getPreviousResult(): Promise<PreviousResult | null> {
  try {
    return await transport.get<PreviousResult>('/api/results/previous')
  } catch (error) {
    // If no previous result exists (404), return null
    return null
  }
}
```

**Rationale**: 이전 결과 조회 API 제공, 에러 시 null 반환하여 첫 응시 처리

---

#### 3. `src/frontend/src/components/TestResults/ComparisonSection.tsx`
**Lines**: 1-135 (NEW FILE)
**Changes**: 비교 섹션 컴포넌트 생성

**Key Features**:
- 첫 응시 vs 재응시 분기 처리
- 등급/점수 변화 계산 로직
- 상승/하락/변동없음 표시 (아이콘, 색상)
- 이전 테스트 날짜 형식 변환 (한국어)
- 요약 메시지 (개선/하락/동일)

**Rationale**: 시각적으로 명확한 비교 정보 제공, 사용자 동기 부여

---

#### 4. `src/frontend/src/components/TestResults/ComparisonSection.css`
**Lines**: 1-168 (NEW FILE)
**Changes**: 비교 섹션 스타일

**Key Styles**:
- improved (녹색): border-color: #28a745, background: #f0fdf4
- declined (빨간색): border-color: #dc3545, background: #fef2f2
- unchanged (회색): border-color: #6c757d, background: #f8f9fa
- 요약 메시지 색상 구분

**Rationale**: 시각적 피드백으로 개선/하락 즉시 인지 가능

---

#### 5. `src/frontend/src/components/TestResults/index.ts`
**Lines**: 1, 6
**Changes**: ComparisonSection export 추가

**Rationale**: 컴포넌트 재사용을 위한 export

---

#### 6. `src/frontend/src/pages/TestResultsPage.tsx`
**Lines**: 1-2, 5-6, 37-56, 147-154
**Changes**:
- useState, useEffect import
- ComparisonSection import
- PreviousResult import
- 이전 결과 fetching 로직 추가
- ComparisonSection 렌더링

```typescript
// State for previous result
const [previousResult, setPreviousResult] = useState<PreviousResult | null>(null)
const [isPreviousLoading, setIsPreviousLoading] = useState(true)

useEffect(() => {
  const fetchPreviousResult = async () => {
    setIsPreviousLoading(true)
    try {
      const result = await resultService.getPreviousResult()
      setPreviousResult(result)
    } catch (err) {
      setPreviousResult(null) // Silently fail
    } finally {
      setIsPreviousLoading(false)
    }
  }
  fetchPreviousResult()
}, [])

// Render ComparisonSection
{!isPreviousLoading && (
  <ComparisonSection
    currentGrade={resultData.grade}
    currentScore={resultData.score}
    previousResult={previousResult}
  />
)}
```

**Rationale**: 결과 페이지에 비교 섹션 통합, API 에러 시에도 페이지 정상 표시

---

#### 7. `src/frontend/src/components/TestResults/__tests__/ComparisonSection.test.tsx`
**Lines**: 1-164 (NEW FILE)
**Changes**: 6개 테스트 케이스 작성

**Test Coverage**:
- 점수/등급 상승 ✅
- 점수/등급 하락 ✅
- 변동 없음 ✅
- 첫 응시 ✅
- 이전 테스트 날짜 표시 ✅
- 등급 동일 + 점수만 변동 ✅

**Rationale**: 모든 사용자 시나리오 커버

---

#### 8. `src/frontend/src/pages/__tests__/TestResultsPage.test.tsx`
**Lines**: 1, 154-248
**Changes**: 3개 integration 테스트 추가

**Test Coverage**:
- 이전 결과 로드 성공 ✅
- 이전 결과 없을 때 ✅
- API 에러 처리 ✅

**Rationale**: 페이지 레벨 통합 테스트

---

### Code Quality
- ✅ Type safety: TypeScript interfaces 정의
- ✅ Error handling: try-catch, null fallback
- ✅ Loading state: isPreviousLoading 관리
- ✅ Accessibility: semantic HTML, ARIA labels
- ✅ Responsive design: CSS flexbox
- ✅ Comments: REQ-F-B5-1 참조 주석

---

## Phase 4: Summary

### Test Results
✅ All automated tests passed (9 tests total):
- **ComparisonSection.test.tsx**: 6 tests (all PASS)
- **TestResultsPage.test.tsx**: 3 tests added (all PASS)

**Test Execution**:
```bash
npm test -- ComparisonSection.test.tsx --run
# Result: 6 passed (6)

npm test -- TestResultsPage.test.tsx --run
# Result: 8 passed (5 retake + 3 comparison)
```

**Test Coverage**:
- 등급/점수 상승/하락/변동없음 ✅
- 첫 응시 시나리오 ✅
- 이전 테스트 날짜 표시 ✅
- 등급 동일 + 점수 변동 ✅
- API 에러 처리 ✅
- Integration (page level) ✅

### Traceability

| Requirement | Implementation | Test Coverage |
|-------------|----------------|---------------|
| REQ-F-B5-1: 이전 응시 정보 비교 | ComparisonSection.tsx<br>TestResultsPage.tsx:37-56, 147-154<br>resultService.ts:66-81 | ✅ 9 automated tests |
| 등급/점수 비교 표시 | ComparisonSection.tsx:68-103 | ✅ ComparisonSection.test (Test 1, 2, 3, 6) |
| 첫 응시 처리 | ComparisonSection.tsx:23-42 | ✅ ComparisonSection.test (Test 4) |
| 이전 테스트 날짜 | ComparisonSection.tsx:62-66 | ✅ ComparisonSection.test (Test 5) |
| 시각적 비교 (아이콘, 색상) | ComparisonSection.css | ✅ All tests verify icons/classes |
| API 에러 처리 | resultService.ts:73-79<br>TestResultsPage.tsx:45-50 | ✅ TestResultsPage.test (Test 9) |

### Modified/Created Files
1. `src/frontend/src/lib/transport/mockTransport.ts:85-89`
2. `src/frontend/src/services/resultService.ts:40-47, 66-81`
3. `src/frontend/src/components/TestResults/ComparisonSection.tsx` (NEW, 135 lines)
4. `src/frontend/src/components/TestResults/ComparisonSection.css` (NEW, 168 lines)
5. `src/frontend/src/components/TestResults/index.ts:1, 6`
6. `src/frontend/src/pages/TestResultsPage.tsx:1-2, 5-6, 37-56, 147-154`
7. `src/frontend/src/components/TestResults/__tests__/ComparisonSection.test.tsx` (NEW, 164 lines, 6 tests)
8. `src/frontend/src/pages/__tests__/TestResultsPage.test.tsx:1, 154-248` (3 tests added)

### Related Requirements
- ✅ REQ-F-B4-1: 최종 결과 페이지 (기본 기능)
- ✅ REQ-F-B5-3: 재응시 시 이전 정보 자동 입력 (이미 구현됨)
- 🔄 REQ-F-B5-2: "재응시하기" 버튼 (이미 구현됨)

---

## Notes

**Implementation Decision**: Mock API
- Backend API가 아직 없으므로 mock으로 구현
- 실제 백엔드 연동 시 `/api/results/previous` 엔드포인트만 추가하면 됨

**User Flow**:
1. 테스트 완료 → TestResultsPage
2. 이전 결과 자동 조회 (비동기)
3. 비교 섹션 렌더링:
   - 이전 결과 있음 → 등급/점수 비교 표시
   - 이전 결과 없음 → "첫 응시입니다" 표시

**Visual Design**:
- 개선: 녹색 테두리 + 밝은 녹색 배경
- 하락: 빨간색 테두리 + 밝은 빨간색 배경
- 변동없음: 회색 테두리 + 밝은 회색 배경
- 아이콘: ↑ (상승), ↓ (하락), → (변동없음)

**Future Improvements**:
- 여러 이전 결과 비교 (최근 3개 등)
- 점수 변화 그래프
- 카테고리별 점수 변화
- 개선 추천 메시지
