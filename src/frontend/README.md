# SLEA-SSEM Frontend

React + Vite 기반의 프론트엔드 애플리케이션

## Tech Stack

- **Framework**: React 18.2
- **Build Tool**: Vite 5.0
- **Language**: TypeScript 5.3
- **Router**: React Router DOM 6.20
- **Testing**: Vitest + Testing Library

## Quick Start

### 개발 서버 시작

```bash
cd src/frontend
npm run dev
```

개발 서버가 실행되면 `http://localhost:5173`에서 접속 가능합니다.

### 패키지 설치 (필요 시)

```bash
npm install
```

## Available Scripts

### `npm run dev`

개발 서버를 시작합니다. (기본 포트: 5173)

### `npm run build`

프로덕션 빌드를 생성합니다.

```bash
npm run build
```

- TypeScript 컴파일 후 Vite 빌드 실행
- 결과물은 `dist/` 디렉토리에 생성됩니다

### `npm run preview`

빌드된 결과물을 로컬 서버에서 미리보기합니다.

```bash
npm run preview
```

### `npm run test`

Vitest 테스트를 실행합니다.

```bash
npm run test
```

### `npm run test:ui`

Vitest UI 모드로 테스트를 실행합니다.

```bash
npm run test:ui
```

## 프론트엔드 + 백엔드 동시 실행

프로젝트를 풀스택으로 실행하려면 두 개의 터미널이 필요합니다:

```bash
# 터미널 1: 백엔드 (FastAPI)
./tools/dev.sh up              # http://localhost:8000

# 터미널 2: 프론트엔드 (React + Vite)
cd src/frontend
npm run dev                     # http://localhost:5173
```

## 프로젝트 구조

```text
src/frontend/
├── src/
│   ├── main.tsx           # 애플리케이션 진입점
│   ├── App.tsx            # 루트 컴포넌트
│   ├── index.css          # 글로벌 스타일
│   ├── pages/             # 페이지 컴포넌트
│   │   ├── LoginPage.tsx
│   │   └── LoginPage.css
│   └── test/
│       └── setup.ts       # 테스트 설정
├── index.html             # HTML 템플릿
├── vite.config.ts         # Vite 설정
├── tsconfig.json          # TypeScript 설정
└── package.json           # 의존성 관리
```

## 개발 가이드

### TypeScript 사용

모든 컴포넌트는 TypeScript로 작성되어야 합니다:

```tsx
// 타입 정의 예시
interface Props {
  title: string;
  onSubmit: () => void;
}

const Component: React.FC<Props> = ({ title, onSubmit }) => {
  // ...
}
```

### 테스트 작성

컴포넌트 테스트는 Testing Library를 사용합니다:

```tsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'

describe('Component', () => {
  it('renders correctly', () => {
    render(<Component />)
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })
})
```

## 환경 설정

### Vite 환경 변수

`.env` 파일을 생성하여 환경 변수를 설정할 수 있습니다:

```bash
VITE_API_URL=http://localhost:8000
```

코드에서 사용:

```tsx
const apiUrl = import.meta.env.VITE_API_URL
```

## 트러블슈팅

### 포트가 이미 사용 중인 경우

```bash
# 다른 포트로 실행
PORT=3000 npm run dev
```

또는 `vite.config.ts`에서 포트 변경:

```typescript
export default defineConfig({
  server: {
    port: 3000
  }
})
```

### 타입 에러

```bash
# TypeScript 타입 체크
npx tsc --noEmit
```

## 참고 문서

- [Vite Documentation](https://vitejs.dev/)
- [React Documentation](https://react.dev/)
- [Vitest Documentation](https://vitest.dev/)
- [React Router Documentation](https://reactrouter.com/)
