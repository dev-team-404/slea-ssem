# REQ-F-A1-2: SSO 콜백 페이지 구현

**날짜**: 2025-11-10
**담당자**: Claude Code
**우선순위**: M (Must)
**상태**: ✅ 완료

---

## 📋 요구사항

### 요약
SSO 콜백 페이지를 구현하여 토큰을 안전하게 저장하고 적절한 페이지로 리다이렉트

### 수용 기준
- ✅ "로그인 성공 후 3초 내 대시보드로 이동한다."
- ✅ "로그인 실패 시, 에러 메시지와 함께 '계정 정보 확인', '관리자 문의' 두 링크가 표시된다."

### 관련 문서
- `docs/feature_requirement_mvp1.md` - REQ-F-A1-2
- `docs/user_scenarios_mvp1.md` - 시나리오 0 (사용자 가입)

---

## 🎯 Phase 1: Specification

### Intent
Samsung AD SSO 인증 후 사용자 정보를 받아 백엔드 API를 호출하고, JWT 토큰을 안전하게 저장한 뒤 사용자를 적절한 페이지로 리다이렉트:
- 신규 사용자 → `/signup` (회원가입 페이지)
- 기존 사용자 → `/dashboard`

### 구현 위치
- `src/frontend/src/pages/CallbackPage.tsx` - SSO 콜백 처리 페이지
- `src/frontend/src/pages/CallbackPage.css` - 스타일
- `src/frontend/src/utils/auth.ts` - 토큰 관리 유틸리티
- `src/frontend/src/App.tsx` - 라우트 추가

### 주요 기능
1. URL params에서 사용자 정보 추출 (knox_id, name, dept, business_unit, email)
2. Mock 모드 지원 (개발/테스트용)
3. 백엔드 `/api/auth/login` API 호출
4. JWT 토큰을 localStorage에 저장
5. is_new_user에 따라 적절한 페이지로 리다이렉트
6. 에러 처리 및 헬프 링크 표시

---

## 🧪 Phase 2: Test Design

### 테스트 파일
1. **`src/frontend/src/pages/__tests__/CallbackPage.test.tsx`** (8 tests)
   - Happy Path: 신규/기존 사용자 로그인 성공
   - Edge Cases: API 실패, 필수 파라미터 누락
   - Acceptance Criteria: 에러 링크, Mock 모드, 3초 이내 리다이렉트

2. **`src/frontend/src/utils/__tests__/auth.test.ts`** (7 tests)
   - saveToken, getToken, removeToken 함수 검증
   - 토큰 lifecycle 테스트

### 테스트 커버리지
- ✅ 신규 사용자 → /signup 리다이렉트
- ✅ 기존 사용자 → /dashboard 리다이렉트
- ✅ API 호출 실패 시 에러 메시지
- ✅ 헬프 링크 표시 (계정 정보 확인, 관리자 문의)
- ✅ Mock 모드 동작
- ✅ 3초 이내 리다이렉트
- ✅ 로딩 스피너 표시

---

## 💻 Phase 3: Implementation

### 생성된 파일

#### 1. `src/frontend/src/utils/auth.ts`
**목적**: JWT 토큰 관리 유틸리티

```typescript
export const saveToken = (token: string): void
export const getToken = (): string | null
export const removeToken = (): void
```

**주요 기능**:
- localStorage를 사용한 토큰 저장/조회/삭제
- 토큰 키: `slea_ssem_token`

---

#### 2. `src/frontend/src/pages/CallbackPage.tsx`
**목적**: SSO 콜백 처리 및 인증 완료 후 리다이렉트

**주요 로직**:
```typescript
1. URL params 또는 mock 데이터에서 사용자 정보 추출
2. 필수 파라미터 검증 (knox_id, name, dept, business_unit, email)
3. POST /api/auth/login 호출
4. 응답에서 JWT 토큰 추출 및 저장
5. is_new_user에 따라 리다이렉트:
   - true: /signup
   - false: /dashboard
6. 에러 처리 및 헬프 링크 표시
```

**상태 관리**:
- `loading`: 로딩 상태 (로딩 스피너 표시)
- `error`: 에러 메시지 (에러 화면 표시)

---

#### 3. `src/frontend/src/pages/CallbackPage.css`
**목적**: CallbackPage 스타일링

**주요 스타일**:
- 중앙 정렬 레이아웃
- 로딩 스피너 애니메이션
- 에러 메시지 스타일
- 헬프 링크 버튼 스타일

---

#### 4. `src/frontend/src/App.tsx` (수정)
**변경 사항**: CallbackPage 라우트 추가

```typescript
<Route path="/auth/callback" element={<CallbackPage />} />
```

---

### 수정된 문서 파일

#### 1. `docs/feature_requirement_mvp1.md`
**변경 사항**:
- "REQ-F-A2: 닉네임 등록 화면" → "REQ-F-A2: 회원가입 화면 (닉네임 등록)"
- Frontend 체크리스트: "닉네임 등록" → "회원가입 (닉네임 등록)"

**이유**: 닉네임 입력이 전체 회원가입 프로세스의 일부임을 명확히 하기 위함

---

#### 2. `docs/user_scenarios_mvp1.md`
**변경 사항** (4곳):
- "가입 안내 페이지" → "회원가입 페이지"

**이유**: 일관된 용어 사용 및 명확성 향상

---

## ✅ Phase 4: Test Results

### 테스트 실행 결과

```
Test Files  3 passed (3)
     Tests  20 passed (20)
  Duration  1.16s

✓ src/pages/__tests__/LoginPage.test.tsx (5 tests)
✓ src/pages/__tests__/CallbackPage.test.tsx (8 tests)
✓ src/utils/__tests__/auth.test.ts (7 tests)
```

**모든 테스트 통과** ✅

---

## 📊 Traceability Matrix

| REQ ID | Specification | Implementation | Test |
|--------|--------------|----------------|------|
| REQ-F-A1-2 | SSO 콜백 페이지 구현 | `CallbackPage.tsx:1-137` | `CallbackPage.test.tsx:1-304` |
| - 토큰 저장 | localStorage에 JWT 저장 | `auth.ts:15-17` | `auth.test.ts:33-49` |
| - 토큰 조회 | localStorage에서 JWT 조회 | `auth.ts:24-26` | `auth.test.ts:51-62` |
| - 토큰 삭제 | localStorage에서 JWT 삭제 | `auth.ts:31-33` | `auth.test.ts:64-75` |
| - 신규 사용자 리다이렉트 | /signup으로 이동 | `CallbackPage.tsx:88-90` | `CallbackPage.test.tsx:67-113` |
| - 기존 사용자 리다이렉트 | /dashboard로 이동 | `CallbackPage.tsx:90-92` | `CallbackPage.test.tsx:115-143` |
| - 에러 처리 | 에러 메시지 + 헬프 링크 | `CallbackPage.tsx:94-97, 122-148` | `CallbackPage.test.tsx:145-196` |
| - Mock 모드 | 개발/테스트용 mock 데이터 | `CallbackPage.tsx:37-47` | `CallbackPage.test.tsx:198-219` |
| - 3초 이내 리다이렉트 | 성능 요구사항 | `CallbackPage.tsx:88-92` | `CallbackPage.test.tsx:221-253` |

---

## 📁 변경된 파일 목록

### 신규 생성 (6개)
- `src/frontend/src/pages/CallbackPage.tsx`
- `src/frontend/src/pages/CallbackPage.css`
- `src/frontend/src/pages/__tests__/CallbackPage.test.tsx`
- `src/frontend/src/utils/auth.ts`
- `src/frontend/src/utils/__tests__/auth.test.ts`
- `docs/progress/REQ-F-A1-2.md`

### 수정 (3개)
- `src/frontend/src/App.tsx` - CallbackPage 라우트 추가
- `docs/feature_requirement_mvp1.md` - 용어 통일 (회원가입 페이지)
- `docs/user_scenarios_mvp1.md` - 용어 통일 (회원가입 페이지)

---

## 🎓 배운 점 & 개선사항

### 성공 요인
1. TDD 접근법으로 테스트 먼저 작성 → 요구사항 명확화
2. Mock 모드 지원으로 개발/테스트 용이성 확보
3. 명확한 에러 처리 및 사용자 안내

### 개선 가능 영역
1. **보안**: localStorage 대신 HttpOnly 쿠키 사용 고려 (XSS 공격 방지)
2. **재시도 로직**: API 호출 실패 시 자동 재시도 추가
3. **로딩 타임아웃**: 무한 로딩 방지를 위한 타임아웃 설정

---

## ✅ Acceptance Criteria 검증

- ✅ "로그인 성공 후 3초 내 대시보드로 이동한다."
  - 검증: `CallbackPage.test.tsx:221-253` (Performance test)

- ✅ "로그인 실패 시, 에러 메시지와 함께 '계정 정보 확인', '관리자 문의' 두 링크가 표시된다."
  - 검증: `CallbackPage.test.tsx:164-196` (Help links test)

---

## 📝 다음 단계

REQ-F-A1-2 구현 완료 후 다음 요구사항:
- **REQ-F-A2-1~5**: 회원가입 화면 (닉네임 등록) 구현
- **REQ-B-A2-1~5**: 닉네임 검증 백엔드 API 구현

---

**구현 완료일**: 2025-11-10
**총 소요 시간**: ~1시간
**상태**: ✅ Done
