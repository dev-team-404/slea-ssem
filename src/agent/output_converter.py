"""
Agent Output Converter: Structured parsing of LangChain Agent responses.

REQ: REQ-A-OutputConverter

개요:
    LangChain ReAct Agent의 다양한 출력 형식(ReAct 텍스트, structured JSON)을
    일관되고 구조화된 GeneratedItem/ScoreResult로 변환합니다.

    주요 기능:
    - Final Answer JSON 추출 및 파싱
    - 다양한 answer_schema 형식 정규화
    - 타입별 데이터 변환 (MC vs Short Answer)
    - 검증 및 에러 처리

설계 원칙:
    - Single Responsibility: 파싱만 담당
    - Dependency Inversion: Pydantic 모델과만 의존
    - Composition: 작은 메서드 조합
    - Testability: 각 메서드 독립적 테스트 가능
"""

import json
import logging
import re
import uuid
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Data Contracts (출력 스키마)
# ============================================================================


class AnswerSchema(BaseModel):
    """정규화된 answer_schema 구조."""

    type: str = Field(..., description="exact_match, keyword_match, or semantic_match")
    keywords: list[str] | None = Field(None, description="Short answer keywords (Optional)")
    correct_answer: str | None = Field(None, description="Correct answer (Optional)")


class GeneratedItem(BaseModel):
    """생성된 문항."""

    id: str
    type: str  # multiple_choice, true_false, short_answer
    stem: str
    choices: list[str] | None = None
    answer_schema: AnswerSchema
    difficulty: int
    category: str
    validation_score: float = 0.0


# ============================================================================
# AgentOutputConverter: 핵심 클래스
# ============================================================================


class AgentOutputConverter:
    """
    LangChain Agent 출력을 구조화된 형식으로 변환.

    지원하는 입력 형식:
    1. ReAct 텍스트: "Final Answer: [...JSON...]"
    2. Structured: "Final Answer: {json_object}"
    3. 마크다운: "Final Answer: ```json\n[...]\n```"

    예제:
        converter = AgentOutputConverter()

        # Final Answer JSON 추출 및 파싱
        questions_data = converter.parse_final_answer_json(ai_message_content)

        # 데이터를 GeneratedItem으로 변환
        items = converter.extract_items_from_questions(
            questions_data,
            question_types=["multiple_choice", "short_answer"]
        )

        # answer_schema 검증
        for item in items:
            assert converter.validate_answer_schema(item.answer_schema)
    """

    # ==========================================================================
    # 1. JSON 추출 및 파싱
    # ==========================================================================

    @staticmethod
    def parse_final_answer_json(content: str, max_attempts: int = 5) -> dict | list:
        """
        ReAct 형식의 AI Message에서 Final Answer JSON을 추출하고 파싱.

        처리 단계:
        1. "Final Answer:" 패턴 탐색
        2. 마크다운 코드블록 제거 (```json ... ```)
        3. Escaped 문자 처리
        4. Robust JSON 파싱 (5가지 cleanup strategy)

        Args:
            content: AI Message의 content (ReAct 텍스트 형식)
            max_attempts: 최대 cleanup 시도 횟수

        Returns:
            파싱된 JSON 객체 또는 배열

        Raises:
            json.JSONDecodeError: 모든 cleanup 시도 실패 시
            ValueError: content가 None이거나 Final Answer 패턴 없을 시
        """
        if not content or not isinstance(content, str):
            raise ValueError("content must be a non-empty string")

        # Step 1: "Final Answer:" 패턴 탐색
        if "Final Answer:" not in content:
            raise ValueError('Content must contain "Final Answer:" pattern')

        json_start = content.find("Final Answer:") + len("Final Answer:")
        json_str = content[json_start:].strip()

        # Step 2: 마크다운 코드블록 제거
        json_str = AgentOutputConverter._remove_markdown_code_blocks(json_str)

        # Step 3: Escaped 문자 처리
        json_str = AgentOutputConverter._unescape_json_string(json_str)

        # Step 4: Robust JSON 파싱
        try:
            parsed = AgentOutputConverter._parse_json_robust(json_str, max_attempts)
            logger.info(f"✅ Successfully parsed Final Answer JSON")
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse Final Answer JSON after {max_attempts} attempts")
            raise

    @staticmethod
    def _remove_markdown_code_blocks(json_str: str) -> str:
        """마크다운 코드블록 (```json ... ```) 제거."""
        if "```json" in json_str:
            return json_str.split("```json")[1].split("```")[0].strip()
        elif "```" in json_str:
            return json_str.split("```")[1].split("```")[0].strip()
        return json_str

    @staticmethod
    def _unescape_json_string(json_str: str) -> str:
        """
        JSON 문자열의 escaped 문자 처리.

        처리 대상:
        - \\' → ' (single quote)
        - \\" → " (double quote)
        - \\bNone\\b → null (Python None)
        """
        # Remove backslash before single quotes
        json_str = json_str.replace("\\'", "'")
        # Replace escaped double quotes
        json_str = json_str.replace('\\"', '"')
        # Convert Python None to JSON null
        json_str = re.sub(r"\bNone\b", "null", json_str)
        return json_str

    @staticmethod
    def _parse_json_robust(json_str: str, max_attempts: int = 5) -> dict | list:
        """
        5가지 cleanup strategy를 순차적으로 적용하는 robust JSON 파싱.

        Strategy 1: 현상태로 파싱
        Strategy 2: Python literals (True/False) 변환
        Strategy 3: Trailing commas 제거
        Strategy 4: Escape 문자 처리
        Strategy 5: Control characters 제거

        Args:
            json_str: Raw JSON 문자열
            max_attempts: 최대 시도 횟수

        Returns:
            파싱된 JSON 객체 또는 배열

        Raises:
            json.JSONDecodeError: 모든 전략 실패 시
        """
        cleanup_strategies = [
            ("no_cleanup", lambda s: s),
            ("fix_python_literals", lambda s: re.sub(r"\b(True|False)\b", lambda m: m.group(1).lower(), s)),
            ("fix_trailing_commas", lambda s: re.sub(r",(\s*[}\]])", r"\1", s)),
            ("fix_escapes", lambda s: re.sub(r"\\(?!\\|/|[btnfr])", "\\\\", s)),
            ("remove_control_chars", lambda s: s.encode("utf-8", "ignore").decode("utf-8")),
        ]

        last_error = None
        for attempt_num, (strategy_name, cleanup_fn) in enumerate(cleanup_strategies, 1):
            try:
                cleaned_json = cleanup_fn(json_str)
                result = json.loads(cleaned_json)

                if attempt_num > 1:
                    logger.debug(
                        f"✅ JSON parsing succeeded with strategy '{strategy_name}' "
                        f"(attempt {attempt_num}/{len(cleanup_strategies)})"
                    )
                return result

            except json.JSONDecodeError as e:
                last_error = e
                logger.debug(f"⚠️  Strategy '{strategy_name}' failed: {str(e)[:100]}")
                if attempt_num >= max_attempts:
                    break

        raise last_error

    # ==========================================================================
    # 2. 데이터 변환: 질문 데이터 → GeneratedItem
    # ==========================================================================

    @staticmethod
    def extract_items_from_questions(
        questions_data: dict | list,
        question_types: list[str] | None = None,
    ) -> list[GeneratedItem]:
        """
        파싱된 JSON 데이터를 GeneratedItem 리스트로 변환.

        입력 데이터 구조:
        [
            {
                "question_id": "...",
                "type": "multiple_choice",
                "stem": "...",
                "choices": [...],
                "answer_schema": {...} or "exact_match",
                "difficulty": 5,
                "category": "AI",
                "correct_answer": "B" (optional, from Tool 5),
                "validation_score": 0.9
            },
            ...
        ]

        Args:
            questions_data: 파싱된 JSON (list 또는 dict)
            question_types: 기대하는 질문 타입 (필터링용, optional)

        Returns:
            list[GeneratedItem]: 변환된 문항 리스트

        Raises:
            ValueError: 필수 필드 부족 시
        """
        if not isinstance(questions_data, list):
            questions_data = [questions_data]

        items: list[GeneratedItem] = []

        for q_dict in questions_data:
            try:
                item = AgentOutputConverter._convert_question_to_item(q_dict)
                items.append(item)
            except ValueError as e:
                logger.warning(f"⚠️  Skipped invalid question: {str(e)}")
                continue

        logger.info(f"✅ Extracted {len(items)} valid items from questions data")
        return items

    @staticmethod
    def _convert_question_to_item(q_dict: dict) -> GeneratedItem:
        """
        단일 질문 dict를 GeneratedItem으로 변환.

        필수 필드:
        - type: "multiple_choice" | "true_false" | "short_answer"
        - stem: 질문 텍스트

        선택 필드:
        - question_id: UUID (없으면 자동 생성)
        - choices: 선택지 (MC/TF에 필요)
        - answer_schema: dict 또는 string (정규화됨)
        - difficulty: 1-10 (기본값 5)
        - category: 문항 카테고리 (기본값 "AI")
        - validation_score: 검증 점수 (기본값 0.0)

        Raises:
            ValueError: 필수 필드 부족 시
        """
        # 필수 필드 검증
        if "type" not in q_dict or "stem" not in q_dict:
            raise ValueError(f"Missing required fields: type or stem in {q_dict}")

        question_type = q_dict.get("type", "multiple_choice")
        stem = q_dict.get("stem", "")

        if not stem:
            raise ValueError("stem cannot be empty")

        # Answer schema 정규화
        raw_answer_schema = q_dict.get("answer_schema")
        normalized_schema_type = AgentOutputConverter.normalize_schema_type(raw_answer_schema)

        # Correct answer 추출 (다중 필드 지원)
        correct_answer_value = (
            q_dict.get("correct_answer")
            or q_dict.get("correct_key")
            or (raw_answer_schema.get("correct_answer") if isinstance(raw_answer_schema, dict) else None)
            or (raw_answer_schema.get("correct_key") if isinstance(raw_answer_schema, dict) else None)
        )

        # Type별 answer_schema 구성
        if question_type == "short_answer":
            answer_schema = AnswerSchema(
                type=normalized_schema_type,
                keywords=q_dict.get("correct_keywords"),
                correct_answer=None,
            )
        else:
            answer_schema = AnswerSchema(
                type=normalized_schema_type,
                keywords=None,
                correct_answer=correct_answer_value,
            )

        item = GeneratedItem(
            id=q_dict.get("question_id", f"q_{uuid.uuid4().hex[:8]}"),
            type=question_type,
            stem=stem,
            choices=q_dict.get("choices"),
            answer_schema=answer_schema,
            difficulty=int(q_dict.get("difficulty", 5)),
            category=q_dict.get("category", "AI"),
            validation_score=float(q_dict.get("validation_score", 0.0)),
        )

        return item

    # ==========================================================================
    # 3. Answer Schema 정규화
    # ==========================================================================

    @staticmethod
    def normalize_schema_type(answer_schema_raw: str | dict | None) -> str:
        """
        다양한 형식의 answer_schema를 표준 타입 문자열로 정규화.

        지원하는 입력 형식:
        1. Tool 5 형식: {"type": "exact_match", ...}
        2. Mock 형식: {"correct_key": "B", "explanation": "..."}
        3. Keyword 형식: {"keywords": [...]}
        4. 문자열: "exact_match"
        5. List: [...] (keyword_match로 추론)

        반환값:
        - "exact_match" (MC, TF 기본)
        - "keyword_match" (Short answer)
        - "semantic_match" (고급 채점)

        Args:
            answer_schema_raw: Raw answer_schema 값

        Returns:
            정규화된 타입 문자열
        """
        if isinstance(answer_schema_raw, dict):
            # Case 1: Tool 5 형식 - 명시적 'type' 필드
            if "type" in answer_schema_raw:
                schema_type = answer_schema_raw.get("type")
                if isinstance(schema_type, str):
                    return schema_type

            # Case 2: Mock 형식 - "correct_key" 또는 "explanation"
            if "correct_key" in answer_schema_raw or "explanation" in answer_schema_raw:
                return "exact_match"

            # Case 3: Keywords 포함 - keyword_match
            if "keywords" in answer_schema_raw and answer_schema_raw.get("keywords"):
                return "keyword_match"

            # Case 4: 기타 'type' 필드
            for key in ["type", "answer_type", "schema_type"]:
                if key in answer_schema_raw:
                    val = answer_schema_raw.get(key)
                    if isinstance(val, str):
                        return val

        if isinstance(answer_schema_raw, str):
            return answer_schema_raw

        if isinstance(answer_schema_raw, list):
            return "keyword_match"

        # 기본값
        logger.warning(
            f"⚠️  answer_schema has unexpected type: {type(answer_schema_raw).__name__}. "
            f"Defaulting to 'exact_match'"
        )
        return "exact_match"

    # ==========================================================================
    # 4. 검증
    # ==========================================================================

    @staticmethod
    def validate_answer_schema(answer_schema: AnswerSchema) -> bool:
        """
        AnswerSchema의 일관성을 검증.

        규칙:
        1. type은 항상 필수
        2. short_answer: keywords는 있고, correct_answer는 None
        3. MC/TF: correct_answer는 있고, keywords는 None
        4. type은 유효한 값 ("exact_match", "keyword_match", "semantic_match")

        Args:
            answer_schema: 검증할 AnswerSchema

        Returns:
            bool: 유효하면 True, 아니면 False
        """
        if not answer_schema.type:
            logger.warning("❌ answer_schema.type is missing")
            return False

        valid_types = ["exact_match", "keyword_match", "semantic_match"]
        if answer_schema.type not in valid_types:
            logger.warning(f"❌ answer_schema.type '{answer_schema.type}' not in {valid_types}")
            return False

        return True

    @staticmethod
    def validate_generated_item(item: GeneratedItem) -> bool:
        """
        GeneratedItem의 모든 필드 검증.

        검사 항목:
        1. id: 유효한 UUID 형식
        2. type: 유효한 질문 타입
        3. stem: 비어있지 않음
        4. answer_schema: 유효함
        5. difficulty: 1-10 범위
        6. category: 비어있지 않음

        Args:
            item: 검증할 GeneratedItem

        Returns:
            bool: 유효하면 True
        """
        # Type 검증
        valid_types = ["multiple_choice", "true_false", "short_answer"]
        if item.type not in valid_types:
            logger.warning(f"❌ Invalid item type: {item.type}")
            return False

        # Stem 검증
        if not item.stem or not isinstance(item.stem, str):
            logger.warning("❌ Invalid or missing stem")
            return False

        # Answer schema 검증
        if not AgentOutputConverter.validate_answer_schema(item.answer_schema):
            return False

        # Difficulty 검증
        if not (1 <= item.difficulty <= 10):
            logger.warning(f"❌ difficulty out of range: {item.difficulty}")
            return False

        # Category 검증
        if not item.category:
            logger.warning("❌ category is empty")
            return False

        return True
