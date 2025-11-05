# 기여 가이드

이 프로젝트에 관심을 가져주셔서 감사합니다! 버그 제보, 기능 제안, 문서 개선, 코드 기여 등 모든 형태의 기여를 환영합니다.

---

## 기여 방법

### 1. 저장소 포크(Fork)

- 저장소 페이지 우측 상단의 "Fork" 버튼을 클릭해 본인 계정으로 복사본을 만듭니다.

### 2. 포크한 저장소 클론(Clone)

- 포크한 저장소를 로컬로 복제합니다:

  ```bash
  git clone https://github.com/your-username/python-project-template.git
  cd python-project-template
  ```

### 3. 새 브랜치 생성

- 기능 추가나 버그 수정을 위한 브랜치를 만듭니다:

  ```bash
  git checkout -b feature/기능-이름
  # 또는
  git checkout -b fix/버그-이름
  ```

### 4. 의존성 설치

- 가상환경을 만들고 의존성을 설치합니다:

  ```bash
  python -m venv .venv
  source .venv/bin/activate  # Linux/macOS
  # .venv\Scripts\activate    # Windows PowerShell
  pip install --upgrade pip setuptools wheel
  pip install tox
  ```

### 5. 변경사항 반영

- 기능 추가, 버그 수정, 문서 업데이트 등 필요한 작업을 진행합니다.
- 아래 코드 스타일 및 가이드라인을 준수해 주세요.

### 6. 검사 도구 실행

- 변경사항을 제출하기 전, 모든 검사가 통과하는지 확인합니다:

  ```bash
  tox
  ```

- 포맷팅, 린트, 타입 체크가 자동으로 실행됩니다.

### 7. 커밋 및 푸시

- 명확한 메시지로 커밋 후 원격 저장소에 푸시합니다:

  ```bash
  git add .
  git commit -m "변경 내용을 명확히 작성"
  git push origin 브랜치-이름
  ```

### 8. Pull Request 생성

- 원본 저장소에서 "New Pull Request"를 클릭합니다.
- 본인 브랜치를 선택하고 변경 내용을 명확히 설명해 주세요.
- 관련 이슈가 있다면 함께 언급해 주세요.

---

## 코드 스타일 & 가이드라인

- [PEP 8](https://pep8.org/) 스타일 가이드를 기본으로 합니다.
- 코드 포맷팅과 임포트 정리는 `black`과 `isort`를 사용합니다.
- 명확하고 간결한 커밋 메시지를 작성해 주세요.
- 새로운 기능 추가나 버그 수정 시 테스트 코드도 함께 추가/수정해 주세요.
- 문서도 필요에 따라 업데이트해 주세요.

---

## 이슈 제보

- [Issues](https://github.com/yourusername/python-project-template/issues) 탭에서 버그 제보나 기능 제안을 남겨주세요.
- 재현 방법, 기대 동작, 스크린샷 등 최대한 자세히 작성해 주세요.

---

## 행동 강령

- 모든 커뮤니케이션에서 서로를 존중해 주세요.
- 자세한 내용은 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) 파일을 참고해 주세요(존재하는 경우).

---

프로젝트 발전에 기여해 주셔서 감사합니다! 궁금한 점이 있으면 이슈를 남기거나 Pull Request에서 질문해 주세요.
