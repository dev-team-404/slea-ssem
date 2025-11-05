# python-project-template

**[kr-한국어]** | [en-English](README.en.md)

최소한의 구성으로 표준화된 Python 프로젝트 템플릿으로, `black`, `isort`, `mypy`, `pylint`와 같은 도구들을 `tox`와 통합하여 코드 포맷팅, 린팅, 타입 체크를 위한 필수 설정을 포함해 개발 워크플로우를 간소화해줍니다.

---

## 목적

이 템플릿은 새 Python 프로젝트를 시작할 때마다 매번 설정하는 번거로움을 줄이고, 일관된 코드 스타일과 품질을 유지할 수 있도록 다음을 제공합니다:

- 코드 포맷터: **black**
- 임포트 정리기: **isort**
- 타입 검사기: **mypy**
- 코드 린터: **pylint**
- 통합 테스트 및 린트 자동화 도구: **tox**

`tox`를 통해 위 도구들을 손쉽게 실행하고, 여러 Python 버전에서 테스트할 수 있도록 기본 환경을 구성해 놓았습니다.

---

## 주요 구성 파일

- `tox.ini`  
  각종 린트, 포맷, 타입 검사 도구를 개별 혹은 한꺼번에 실행할 수 있도록 환경별로 정의되어 있습니다.  
  `tox` 명령어 한 번으로 모든 검사 도구를 실행하거나, 특정 도구만 선택 실행 가능하도록 설계되었습니다.

- `pyproject.toml`  
  `black`, `isort`, `mypy`, `pylint` 등 주요 툴의 설정을 통합 관리합니다.  
  일관된 스타일과 규칙을 유지하며, 편리한 도구 설정을 지원합니다.

---

## 사용 방법

### 1. 템플릿 레포지토리 생성

- GitHub에서 [python-project-template](https://github.com/yourusername/python-project-template) 저장소를 템플릿으로 사용  
- 새 프로젝트 생성 시 "Use this template" 버튼 클릭 후 복제

---

### 2. 의존성 설치

프로젝트 루트에서 Python 가상환경을 생성 및 활성화한 뒤:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate    # Windows PowerShell

pip install --upgrade pip setuptools wheel
pip install tox
```

---

### 3. 검사 도구 실행

- **모든 검사 도구 실행 (black, isort, mypy, pylint):**

  ```bash
  tox
  ```

- **개별 도구 실행 예시:**

  ```bash
  tox -e black    # 코드 포맷팅 (black)
  tox -e isort    # 임포트 정리 (isort)
  tox -e mypy     # 타입 검사 (mypy)
  tox -e pylint   # 코드 린트 (pylint)
  tox -e lint     # pylint만 실행하는 단축 명령어
  ```

### 4. 설정 커스터마이징

- `pyproject.toml` 내 `[tool.black]`, `[tool.isort]`, `[tool.mypy]`, `[tool.pylint]` 섹션에서 각 도구의 옵션을 수정하세요.
- 필요 시 `tox.ini`에서 검사 대상 경로나 환경 변수를 조정할 수 있습니다.

---

## 권장 워크플로우

1. 코딩 후 `tox -e black`과 `tox -e isort`로 코드 스타일과 임포트를 정리
2. `tox -e mypy`로 타입 오류 확인
3. `tox -e pylint`로 코드 품질 및 잠재 문제 점검
4. 마지막으로 `tox` 명령어로 전체 검사를 한 번에 수행

---

## 추가 참고

- Python 공식 스타일 가이드: [PEP 8](https://pep8.org/)
- `tox` 공식 문서: [https://tox.readthedocs.io/](https://tox.readthedocs.io/)
- 각 도구 공식 사이트에서 상세 옵션과 사용법 확인 가능

---

## 기여

이 프로젝트는 모든 개발자의 참여를 환영합니다!
버그 제보, 기능 제안, 코드 개선 등 다양한 방식으로 참여하실 수 있습니다.
자세한 기여 방법은 [기여](./CONTRIBUTING.ko.md)  가이드를 참고해 주세요.

---

## 📝 라이선스

[MIT 라이선스](LICENSE)
