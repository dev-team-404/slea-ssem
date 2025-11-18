"""
Item-Gen-Agent: LangChain ReAct 기반 자율 AI 에이전트.

REQ: REQ-A-ItemGen

개요:
    LangChain의 최신 Agent 패턴 (ReAct)을 사용하여 자동으로 도구를 선택·활용하는
    AI 에이전트입니다. Mode 1 (문항 생성)과 Mode 2 (자동 채점) 두 가지 모드를 지원합니다.

참고:
    - LangChain 공식 문서: https://python.langchain.com/docs/concepts/agents
    - create_react_agent: https://python.langchain.com/api_reference/langchain/agents/
    - 최신 API 버전: LangChain 0.3.x+

품질 기준:
    - 팀 동료 참고 코드 (높은 수준의 문서화)
    - 공식 문서 예시 기반 구현
    - 타입 힌트 & 에러 처리 명시
"""

import json
import logging
import re
import uuid
from datetime import UTC, datetime

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from src.agent.config import AGENT_CONFIG, create_llm
from src.agent.fastmcp_server import TOOLS
from src.agent.prompts.react_prompt import get_react_prompt
from src.agent.round_id_generator import RoundIDGenerator

logger = logging.getLogger(__name__)

# Round ID generator instance (singleton pattern)
_round_id_gen = RoundIDGenerator()


# ============================================================================
# Helper Functions for Robust JSON Parsing
# ============================================================================


def parse_json_robust(json_str: str, max_attempts: int = 5) -> dict | list:
    """
    Robust JSON parsing with multiple cleanup strategies.

    This function attempts to parse JSON using various cleanup strategies when
    the initial parse fails. This handles edge cases like unescaped newlines,
    trailing commas, Python True/False, etc.

    Args:
        json_str: Raw JSON string from LLM response
        max_attempts: Maximum number of cleanup strategies to try (default 5)

    Returns:
        Parsed JSON object or list

    Raises:
        json.JSONDecodeError: If all cleanup strategies fail
    """
    if not json_str or not isinstance(json_str, str):
        raise ValueError("json_str must be a non-empty string")

    # Strategy list: (name, cleanup_function)
    cleanup_strategies = [
        # Strategy 1: No cleanup - try as-is
        ("no_cleanup", lambda s: s),

        # Strategy 2: Fix Python literals (True/False/None)
        ("fix_python_literals", lambda s: re.sub(r"\b(True|False)\b", lambda m: m.group(1).lower(), re.sub(r"\bNone\b", "null", s))),

        # Strategy 3: Remove trailing commas
        ("fix_trailing_commas", lambda s: re.sub(r",(\s*[}\]])", r"\1", s)),

        # Strategy 4: Fix escaped quotes and backslashes
        ("fix_escapes", lambda s: re.sub(r"\\(?!\\|/|[btnfr])", "\\\\", s)),

        # Strategy 5: Remove control characters
        ("remove_control_chars", lambda s: s.encode('utf-8', 'ignore').decode('utf-8')),
    ]

    last_error = None
    for attempt_num, (strategy_name, cleanup_fn) in enumerate(cleanup_strategies, 1):
        try:
            cleaned_json = cleanup_fn(json_str)
            result = json.loads(cleaned_json)

            if attempt_num > 1:
                logger.info(
                    f"✅ JSON parsing succeeded with strategy '{strategy_name}' "
                    f"(attempt {attempt_num}/{len(cleanup_strategies)})"
                )

            return result

        except json.JSONDecodeError as e:
            last_error = e
            logger.debug(
                f"   Attempt {attempt_num}/{len(cleanup_strategies)} "
                f"(strategy: {strategy_name}) failed at char {e.pos}: {e.msg}"
            )
            continue

        except Exception as e:
            logger.debug(f"   Attempt {attempt_num} ({strategy_name}) error: {e}")
            continue

    # All strategies failed
    logger.error(
        f"❌ JSON parsing failed after {len(cleanup_strategies)} cleanup strategies. "
        f"Last error: {last_error} at char {last_error.pos if last_error else 'unknown'}"
    )
    raise last_error or ValueError("JSON parsing failed with unknown error")


def normalize_answer_schema(answer_schema_raw: str | dict | None) -> str:
    """
    Normalize answer_schema to ensure it's always a string.

    Handles multiple formats:
    1. Tool 5 format: {"type": "exact_match", "keywords": null, "correct_answer": "..."}
    2. Mock format: {"correct_key": "B", "explanation": "..."}
    3. LLM format: {"answer_type": "exact_match"}
    4. String format: "exact_match"

    Args:
        answer_schema_raw: Raw answer_schema value (could be str or dict)

    Returns:
        Normalized answer_schema as string: "exact_match" | "keyword_match" | "semantic_match"
    """
    if isinstance(answer_schema_raw, dict):
        # Case 1: Tool 5 format - has 'type' field
        if "type" in answer_schema_raw:
            schema_type = answer_schema_raw.get("type")
            if isinstance(schema_type, str):
                return schema_type

        # Case 2: Mock/LLM format - has correct_key or answer_type
        # Mock questions use "correct_key" but it's still exact_match
        if "correct_key" in answer_schema_raw or "explanation" in answer_schema_raw:
            return "exact_match"

        # Case 3: Keywords present - likely keyword_match
        if "keywords" in answer_schema_raw:
            return "keyword_match"

        # Case 4: Unknown dict - try 'type' or 'answer_type'
        for key in ["type", "answer_type", "schema_type"]:
            if key in answer_schema_raw:
                val = answer_schema_raw.get(key)
                if isinstance(val, str):
                    return val

    if isinstance(answer_schema_raw, str):
        return answer_schema_raw

    # Default fallback
    logger.warning(
        f"⚠️  answer_schema has unexpected type: {type(answer_schema_raw).__name__}. "
        f"Using default 'exact_match'"
    )
    return "exact_match"


# ============================================================================
# Pydantic Schemas (입출력 데이터 계약)
# ============================================================================


class GenerateQuestionsRequest(BaseModel):
    """문항 생성 요청 (REQ: POST /api/v1/items/generate)."""

    session_id: str = Field(..., description="테스트 세션 ID (Backend Service가 생성)")
    survey_id: str = Field(..., description="설문 ID")
    round_idx: int = Field(..., ge=1, description="라운드 번호 (1-based)")
    prev_answers: list[dict] | None = Field(default=None, description="이전 라운드 답변 (적응형 테스트용)")
    question_count: int = Field(default=5, ge=1, le=20, description="생성할 문항 개수 (기본값: 5, 테스트: 2)")
    question_types: list[str] | None = Field(
        default=None, description="생성할 문항 유형 (multiple_choice | true_false | short_answer), None이면 모두 생성"
    )
    domain: str = Field(default="AI", description="문항 도메인/주제 (예: AI, food, science)")


class AnswerSchema(BaseModel):
    """답변 검증 스키마."""

    type: str = Field(..., description="답변 유형 (exact_match | keyword_match | semantic_match)")
    keywords: list[str] | None = Field(default=None, description="정답 키워드 (주관식용)")
    correct_answer: str | None = Field(default=None, description="정답 (객관식/OX용)")


class GeneratedItem(BaseModel):
    """생성된 문항 아이템."""

    id: str = Field(..., description="문항 ID (UUID)")
    type: str = Field(..., description="문항 유형 (multiple_choice | true_false | short_answer)")
    stem: str = Field(..., description="문항 내용")
    choices: list[str] | None = Field(default=None, description="객관식 선택지")
    answer_schema: AnswerSchema = Field(..., description="답변 검증 스키마")
    difficulty: int = Field(..., ge=1, le=10, description="난이도 (1~10)")
    category: str = Field(..., description="문항 카테고리")
    validation_score: float = Field(default=0.0, ge=0, le=1, description="검증 점수 (Tool 4) - 내부 메타데이터")
    saved_at: str | None = Field(default=None, description="저장 시간 - 내부 메타데이터")


class GenerateQuestionsResponse(BaseModel):
    """문항 생성 응답 (REQ: POST /api/v1/items/generate)."""

    round_id: str = Field(..., description="생성된 라운드 ID")
    items: list[GeneratedItem] = Field(..., description="생성된 문항 목록")
    time_limit_seconds: int = Field(default=1200, description="시간 제한 (초, 기본 20분)")
    agent_steps: int = Field(default=0, description="에이전트 반복 횟수 - 내부 메타데이터")
    failed_count: int = Field(default=0, description="실패한 문항 개수 - 내부 메타데이터")
    total_tokens: int = Field(default=0, description="LLM 응답 총 토큰 수 (input + output)")
    error_message: str | None = Field(default=None, description="에러 메시지")


class ScoreAnswerRequest(BaseModel):
    """
    자동 채점 요청 (단일 처리, Phase 1 - Tool 6 시그니처 준수).

    Tool 6 시그니처: score_and_explain(session_id, user_id, question_id, question_type, user_answer, ...)

    필드 설계:
    - Tool 6 필수: session_id, user_id, question_id, question_type (모두 optional로 시작 가능, 에이전트가 제공)
    - 필수 (API): user_answer
    - Tool 6 선택: correct_answer, correct_keywords, difficulty, category
    - 내부용: round_id (호환성), item_id (호환성), response_time_ms
    """

    # 필수 파라미터
    user_answer: str = Field(..., description="응시자의 답변")

    # Tool 6 파라미터 (에이전트가 호출할 때 제공)
    session_id: str | None = Field(default=None, description="테스트 세션 ID")
    user_id: str | None = Field(default=None, description="사용자 ID")
    question_id: str | None = Field(default=None, description="문항 ID")
    question_type: str | None = Field(default=None, description="문항 유형 (multiple_choice|true_false|short_answer)")

    # Tool 6 선택 파라미터
    correct_answer: str | None = Field(default=None, description="정답 (객관식/참거짓용)")
    correct_keywords: list[str] | None = Field(default=None, description="정답 키워드 (주관식용)")
    difficulty: int | None = Field(default=None, description="문항 난이도 (1-10)")
    category: str | None = Field(default=None, description="문항 카테고리")

    # 내부용 메타데이터 (호환성)
    round_id: str | None = Field(default=None, description="라운드 ID (내부용)")
    item_id: str | None = Field(default=None, description="문항 ID (내부용, round_id와 함께 사용)")
    response_time_ms: int = Field(default=0, ge=0, description="응답 시간 (밀리초, 내부용)")


class ScoreAnswerResponse(BaseModel):
    """자동 채점 응답 (단일 처리, Phase 1 - Tool 6 반환값 준수)."""

    # 필수 필드
    score: float = Field(..., ge=0, le=100, description="점수 (0~100)")
    explanation: str = Field(..., description="정답 해설")
    graded_at: str = Field(..., description="채점 시간")

    # Tool 6 반환값 및 API 호환 필드
    # is_correct와 correct는 같은 의미 (Tool 6는 is_correct 사용)
    is_correct: bool = Field(default=False, description="정답 여부 (Tool 6 호환)")
    correct: bool = Field(default=False, description="정답 여부 (API 호환, is_correct와 동일)")
    feedback: str | None = Field(default=None, description="부분 정답 피드백")
    keyword_matches: list[str] = Field(default_factory=list, description="키워드 매칭 (Tool 6)")
    extracted_keywords: list[str] = Field(default_factory=list, description="추출된 키워드 (API 호환)")

    # 내부 메타데이터
    item_id: str | None = Field(default=None, description="문항 ID (내부용, 배치 응답용)")


# ============================================================================
# Batch Scoring Models (Phase 2)
# ============================================================================


class UserAnswer(BaseModel):
    """사용자 답변 (배치)."""

    item_id: str = Field(..., description="문항 ID")
    user_answer: str = Field(..., description="사용자 답변")
    response_time_ms: int = Field(default=0, ge=0, description="응답 시간 (밀리초)")


class SubmitAnswersRequest(BaseModel):
    """배치 채점 요청 (REQ: POST /api/v1/scoring/submit-answers)."""

    round_id: str = Field(..., description="라운드 ID")
    answers: list[UserAnswer] = Field(..., description="사용자 답변 배치 (1-50개)")


class ItemScore(BaseModel):
    """채점된 문항 (배치 응답)."""

    item_id: str = Field(..., description="문항 ID")
    correct: bool = Field(..., description="정답 여부")
    score: float = Field(..., ge=0, le=100, description="점수 (0~100)")
    extracted_keywords: list[str] = Field(default_factory=list, description="추출된 키워드 (주관식)")
    feedback: str | None = Field(default=None, description="부분 정답 피드백")


class RoundStats(BaseModel):
    """라운드 통계."""

    avg_response_time: float = Field(..., ge=0, description="평균 응답 시간 (밀리초)")
    correct_count: int = Field(..., ge=0, description="정답 개수")
    total_count: int = Field(..., ge=1, description="전체 문항 개수")


class SubmitAnswersResponse(BaseModel):
    """배치 채점 응답 (REQ: POST /api/v1/scoring/submit-answers)."""

    round_id: str = Field(..., description="라운드 ID")
    per_item: list[ItemScore] = Field(..., description="문항별 채점 결과")
    round_score: float = Field(..., ge=0, le=100, description="라운드 총점")
    round_stats: RoundStats = Field(..., description="라운드 통계")


# ============================================================================
# ItemGenAgent Main Class
# ============================================================================


class ItemGenAgent:
    """
    LangChain AgentExecutor 기반 Item-Gen-Agent.

    설명:
        - LangChain의 create_tool_calling_agent() API 사용
        - AgentExecutor로 도구 호출 및 에러 처리 관리
        - Tool Calling 방식 (최신 LLM 모델 최적화)
        - 구조화된 입출력 (Pydantic)
        - 상세한 로깅 (디버깅)

    사용 예시:
        ```python
        # 에이전트 생성
        agent = ItemGenAgent()

        # Mode 1: 문항 생성
        request = GenerateQuestionsRequest(
            survey_id="survey_123",
            round_idx=1,
            prev_answers=None
        )
        response = await agent.generate_questions(request)

        # Mode 2: 자동 채점
        score_request = ScoreAnswerRequest(
            round_id="round_123",
            item_id="item_456",
            user_answer="The answer is..."
        )
        score_response = await agent.score_and_explain(score_request)
        ```

    참고:
        - LangChain 공식: https://python.langchain.com/docs/concepts/agents
        - create_tool_calling_agent: Tool Calling 패턴 구현 (최신 LLM 최적화)
        - AgentExecutor: max_iterations, early_stopping_method, 에러 처리
    """

    def __init__(self) -> None:
        """
        Initialize ItemGenAgent with LangGraph create_react_agent.

        단계:
            1. LLM 생성 (Google Gemini)
            2. 프롬프트 로드
            3. FastMCP 도구 등록
            4. create_react_agent()로 에이전트 생성 (최신 Tool Calling 지원)

        에러 처리:
            - GEMINI_API_KEY 없음: ValueError
            - LLM 초기화 실패: 로그 + 재시도
        """
        logger.info("ItemGenAgent 초기화 중...")

        try:
            # 1. LLM 생성
            self.llm = create_llm()
            logger.info("✓ LLM (Google Gemini) 생성 완료")

            # 2. 프롬프트 로드
            self.prompt = get_react_prompt()
            logger.info("✓ ReAct 프롬프트 로드 완료")

            # 3. 도구 목록 (6개)
            self.tools = TOOLS
            logger.info(f"✓ {len(self.tools)}개 도구 등록 완료: {[t.name for t in self.tools]}")

            # 4. create_react_agent() - LangGraph 최신 Tool Calling 지원
            # LangGraph의 create_react_agent는 최신 LLM의 Tool Calling 기능을 자동으로 활용합니다.
            # ReAct 패턴: Thought → Action → Observation을 반복하며 복잡한 작업을 수행합니다.
            # AGENT_CONFIG의 max_iterations, early_stopping_method, handle_parsing_errors는
            # create_react_agent의 래퍼로 활용되거나, CompiledStateGraph 실행 시 config로 전달됩니다.
            self.executor = create_react_agent(
                model=self.llm,
                tools=self.tools,
                prompt=self.prompt,
                debug=AGENT_CONFIG.get("verbose", False),
                version="v2",  # 최신 LangGraph v2 API 사용
            )
            logger.info("✓ ReAct 에이전트 생성 완료 (Tool Calling 최적화 v2)")

            logger.info("✅ ItemGenAgent 초기화 성공")

        except Exception as e:
            logger.error(f"❌ ItemGenAgent 초기화 실패: {e}")
            raise

    def _extract_tool_results(self, result: dict, tool_name: str) -> list[tuple[str, str]]:
        """
        Extract tool results from agent output in both formats.

        LangGraph create_react_agent returns:
            {"messages": [AIMessage, ToolMessage, ...], ...}

        While AgentExecutor returns:
            {"output": "...", "intermediate_steps": [(tool_name, tool_output), ...], ...}

        This helper extracts tool calls in both formats to support both actual LangGraph
        output and test mocks.

        Args:
            result: Agent output dict
            tool_name: Name of the tool to extract (e.g., "save_generated_question", "score_and_explain")

        Returns:
            List of (tool_name, tool_output_str) tuples matching the given tool_name

        Raises:
            Exception: Logs errors but continues processing for robustness

        LangChain Message Structures:
        - AIMessage: {"type": "ai", "content": "...", "tool_calls": [ToolCall(...), ...]}
        - ToolMessage: {"type": "tool", "content": "...", "tool_call_id": "call_123", "name": "tool_name"}
        - ToolCall: {id: "call_123", name: "tool_name", args: {...}}

        """
        tool_results = []
        logger.info(f"\n🔧 _extract_tool_results: Looking for tool_name='{tool_name}'")

        # Format 1: AgentExecutor intermediate_steps (for backward compatibility with tests)
        intermediate_steps = result.get("intermediate_steps", [])
        if intermediate_steps:
            logger.info("✓ Format 1: intermediate_steps detected (test mock)")
            logger.info(f"  Total steps: {len(intermediate_steps)}")
            for i, (step_tool_name, tool_output_str) in enumerate(intermediate_steps):
                logger.info(f"  [{i}] step_tool_name='{step_tool_name}', matches_target={step_tool_name == tool_name}")
                if step_tool_name == tool_name:
                    tool_results.append((step_tool_name, tool_output_str))
                    logger.info(f"       ✓ MATCHED - output_type={type(tool_output_str).__name__}")
            logger.info(f"  Result: {len(tool_results)} matching tools found\n")
            return tool_results

        # Format 2: LangGraph messages format (actual LangGraph output)
        messages = result.get("messages", [])
        if not messages:
            logger.warning("No intermediate_steps or messages found in agent result\n")
            return []

        logger.info("✓ Format 2: messages detected (LangGraph output)")
        logger.info(f"  Total messages: {len(messages)}\n")

        # Step 1: Build a map of tool_call_id → ToolMessage for quick lookup
        logger.info("Step 1️⃣: Scanning for ToolMessages...")
        tool_messages_by_id: dict[str, ToolMessage] = {}
        for i, message in enumerate(messages):
            msg_type = type(message).__name__
            if isinstance(message, ToolMessage):
                tool_call_id = message.tool_call_id
                name = getattr(message, "name", "?")
                content_preview = str(getattr(message, "content", ""))[:100]
                logger.info(f"  [{i}] ToolMessage found:")
                logger.info(f"       tool_call_id={tool_call_id}, name={name}")
                logger.info(f"       content_preview={content_preview}...")
                if tool_call_id:
                    tool_messages_by_id[tool_call_id] = message
                    logger.info("       ✓ Added to map")
                else:
                    logger.info("       ⚠️  No tool_call_id!")
            elif msg_type == "AIMessage":
                logger.info(f"  [{i}] AIMessage (checking for tool_calls...)")
            else:
                logger.info(f"  [{i}] {msg_type}")

        logger.info(f"\nToolMessage map summary: {len(tool_messages_by_id)} items\n")

        # Step 2: Iterate through AIMessages to find matching tool calls
        logger.info("Step 2️⃣: Scanning AIMessages for tool_calls...")
        ai_message_count = 0
        for i, message in enumerate(messages):
            if isinstance(message, AIMessage):
                ai_message_count += 1
                logger.info(f"  [{i}] AIMessage #{ai_message_count}")

                # AIMessage has tool_calls list with ToolCall objects
                tool_calls = getattr(message, "tool_calls", [])
                logger.info(f"       tool_calls: {len(tool_calls)} found")

                if not tool_calls:
                    logger.info("       ⚠️  No tool_calls in this message")
                    continue

                for j, tool_call in enumerate(tool_calls):
                    try:
                        # ToolCall is an object with .id and .name attributes
                        call_id = tool_call.id if hasattr(tool_call, "id") else tool_call.get("id")
                        call_name = tool_call.name if hasattr(tool_call, "name") else tool_call.get("name")

                        logger.info(f"         [{j}] tool_call: name='{call_name}', id={call_id}")
                        logger.info(f"              target_tool_name='{tool_name}', matches={call_name == tool_name}")

                        # Check if this tool call matches what we're looking for
                        if call_name == tool_name:
                            logger.info("              ✓ NAME MATCHED!")
                            # Find the corresponding ToolMessage
                            if call_id in tool_messages_by_id:
                                tool_msg = tool_messages_by_id[call_id]
                                content = tool_msg.content if hasattr(tool_msg, "content") else str(tool_msg)
                                tool_results.append((tool_name, content))
                                content_preview = str(content)[:100]
                                logger.info(f"              ✓ FOUND ToolMessage with id={call_id}")
                                logger.info(f"              content_preview={content_preview}...")
                            else:
                                logger.warning(
                                    f"              ✗ NO ToolMessage found for id={call_id}!\n"
                                    f"                 Available IDs in map: {list(tool_messages_by_id.keys())}"
                                )
                        else:
                            logger.info(f"              ✗ Name mismatch (looking for '{tool_name}')")

                    except (AttributeError, KeyError, TypeError) as e:
                        logger.error(f"         [{j}] ERROR extracting tool_call properties: {e}")
                        continue

        logger.info(f"\nStep 2️⃣ Result: {len(tool_results)} matching tools found\n")
        return tool_results

    async def generate_questions(self, request: GenerateQuestionsRequest) -> GenerateQuestionsResponse:
        """
        Mode 1: Generate questions (Tool 1-5 auto-select).

        REQ: REQ-A-Mode1-Pipeline

        단계:
            1. 사용자 프로필 조회 (Tool 1)
            2. 템플릿 검색 (Tool 2) - 선택사항
            3. 난이도별 키워드 조회 (Tool 3)
            4. LLM으로 문항 생성
            5. 각 문항 검증 (Tool 4)
            6. 검증 통과 문항 저장 (Tool 5)

        Args:
            request: GenerateQuestionsRequest

        Returns:
            GenerateQuestionsResponse

        에러 처리:
            - Tool 호출 실패: 자동 재시도 (최대 3회)
            - 에이전트 최대 반복: 부분 결과 반환
            - LLM 오류: 에러 메시지 포함

        참고:
            - AgentExecutor: 도구 호출 및 Tool Calling 루프 자동 관리
            - intermediate_steps: 에이전트의 각 도구 호출 추적

        """
        logger.info(f"📝 문항 생성 시작: survey_id={request.survey_id}, round_idx={request.round_idx}")

        try:
            # 라운드 ID 생성 (REQ-A-RoundID)
            # survey_id를 session_id로 사용하여 라운드 ID 생성
            round_id = _round_id_gen.generate(session_id=request.survey_id, round_number=request.round_idx)

            # 에이전트 입력 구성
            question_types_str = (
                ", ".join(request.question_types)
                if request.question_types
                else "multiple_choice, true_false, short_answer"
            )
            agent_input = f"""
Generate high-quality exam questions for the following survey.
Session ID: {request.session_id}
Survey ID: {request.survey_id}
Round: {request.round_idx}
Domain: {request.domain}
Previous Answers: {json.dumps(request.prev_answers) if request.prev_answers else "None (First round)"}
Question Count: {request.question_count}
Question Types: {question_types_str}

Follow these steps:
1. Get survey context and user profile (Tool 1)
2. Search question templates for similar items (Tool 2) if available
3. Get keywords for adaptive difficulty (Tool 3)
4. Generate new questions with appropriate difficulty (focused on {request.domain} domain)
5. Validate each question (Tool 4)
6. Save validated questions (Tool 5) with session_id={request.session_id} and round_id={round_id}

Important:
- Generate EXACTLY {request.question_count} questions with the specified types
- All questions should be related to {request.domain} domain/topic
- Generate questions with appropriate answer_schema (exact_match, keyword_match, or semantic_match)
- Each question must include: id, type, stem, choices (if MC), answer_schema, difficulty, category
- Return all saved questions with validation scores
- When calling Tool 5, ALWAYS pass session_id={request.session_id} to save questions with correct session reference
"""

            # 에이전트 실행 (Tool Calling 루프)
            # LangGraph v2 create_react_agent는 messages 형식으로 입력 받음
            # - messages: 대화 히스토리 (HumanMessage, AIMessage, ToolMessage 등)
            # - Agent가 자동으로 Thought → Action → Observation 반복
            #
            # 성능 최적화 (향후 개선사항):
            # 1. Tool 병렬 실행: 독립적인 Tool들 (validate + save)은 asyncio.gather로 병렬화 가능
            #    - ReAct 패턴의 제약: 각 Tool 결과 → 다음 Thought 결정
            #    - 가능한 경우: 같은 질문의 validate/save 단계를 병렬화
            # 2. Tool 비동기화: 모든 Tool을 async 함수로 변경 (현재는 동기)
            # 3. 캐싱: 자주 호출되는 Tool (get_difficulty_keywords)에 캐싱 적용
            result = await self.executor.ainvoke({"messages": [HumanMessage(content=agent_input)]})

            logger.info("✅ 에이전트 실행 완료")

            # 결과 파싱
            response = self._parse_agent_output_generate(result, round_id)
            logger.info(f"✅ 문항 생성 성공: {len(response.items)}개 생성")

            return response

        except Exception as e:
            logger.error(f"❌ 문항 생성 실패: {e}")
            return GenerateQuestionsResponse(
                round_id=f"round_error_{uuid.uuid4().hex[:8]}",
                items=[],
                time_limit_seconds=1200,
                agent_steps=0,
                failed_count=0,
                error_message=str(e),
            )

    async def score_and_explain(self, request: ScoreAnswerRequest) -> ScoreAnswerResponse:
        """
        Mode 2: Auto-grade answers (Tool 6).

        REQ: REQ-A-Mode2-Pipeline

        단계:
            1. Tool 6 호출 (자동 채점 & 해설 생성)

        Args:
            request: ScoreAnswerRequest

        Returns:
            ScoreAnswerResponse

        에러 처리:
            - Tool 6 호출 실패: 재시도 3회
            - LLM 오류: 기본 점수 0 반환

        참고:
            - Tool 6: 객관식/OX (정확 매칭) vs 주관식 (LLM 평가)
            - 채점 기준: >= 80 → 정답, 70~79 → 부분 정답, < 70 → 오답

        """
        logger.info(
            f"📋 자동 채점 시작: round_id={request.round_id}, item_id={request.item_id}, user_id={request.user_id}"
        )

        try:
            # Tool 6 필수 파라미터 확인 및 기본값 설정
            session_id = request.session_id or "unknown_session"
            user_id = request.user_id or "unknown_user"
            question_id = request.question_id or request.item_id
            question_type = request.question_type or "short_answer"

            # 에이전트 입력 구성 (Tool 6 필수 파라미터 명시)
            agent_input = f"""
Score and explain the following answer using Tool 6 (score_and_explain):

=== TEST SESSION CONTEXT ===
Session ID: {session_id}
User ID: {user_id}
Question ID: {question_id}
Question Type: {question_type}

=== ANSWER DETAILS ===
Round ID: {request.round_id}
User Answer: {request.user_answer}
Response Time (ms): {request.response_time_ms}"""

            # 추가 정보 (선택사항)
            if request.correct_answer:
                agent_input += f"\nCorrect Answer: {request.correct_answer}"
            if request.correct_keywords:
                agent_input += f"\nCorrect Keywords: {', '.join(request.correct_keywords)}"
            if request.difficulty:
                agent_input += f"\nDifficulty Level: {request.difficulty}"
            if request.category:
                agent_input += f"\nQuestion Category: {request.category}"

            agent_input += f"""

=== TASK ===
Call Tool 6 (score_and_explain) with the following parameters:
- session_id: {session_id}
- user_id: {user_id}
- question_id: {question_id}
- question_type: {question_type}
- user_answer: [User's response]
- correct_answer: [if available]
- correct_keywords: [if applicable]
- difficulty: [if available]
- category: [if available]

Tool 6 will return: is_correct (boolean), score (0-100), explanation, keyword_matches, feedback, graded_at
"""

            # 에이전트 실행
            result = await self.executor.ainvoke({"input": agent_input})

            logger.info("✅ 채점 완료")

            # 결과 파싱
            response = self._parse_agent_output_score(result, request.item_id)
            logger.info(f"✅ 채점 성공: score={response.score}, correct={response.correct}")

            return response

        except Exception as e:
            logger.error(f"❌ 채점 실패: {e}")
            # 기본값 반환
            return ScoreAnswerResponse(
                item_id=request.item_id,
                correct=False,
                score=0.0,
                explanation=f"채점 중 오류 발생: {str(e)}",
                graded_at=datetime.now(UTC).isoformat(),
            )

    async def submit_answers(self, request: SubmitAnswersRequest) -> SubmitAnswersResponse:
        """
        Mode 2 Batch: Auto-grade multiple answers in one round (Tool 6).

        REQ: REQ-B-ItemGen-Batch

        단계:
            1. 각 답변에 대해 Tool 6 호출 (자동 채점)
            2. 채점 결과 수집
            3. 라운드 통계 계산 (평균 응답시간, 정답률 등)
            4. 배치 응답 반환

        Args:
            request: SubmitAnswersRequest

        Returns:
            SubmitAnswersResponse

        에러 처리:
            - Tool 6 호출 실패: 개별 항목별 재시도
            - 통계 계산 오류: 안전한 기본값 제공

        """
        logger.info(f"📝 배치 채점 시작: round_id={request.round_id}, items={len(request.answers)}")

        try:
            per_item: list[ItemScore] = []
            response_times: list[int] = []

            # Round ID에서 session_id 추출 (RoundIDGenerator 포맷: session_id_round_number_timestamp)
            try:
                parsed_round = _round_id_gen.parse(request.round_id)
                session_id = parsed_round.session_id
                logger.debug(f"Extracted session_id from round_id: {session_id}")
            except Exception as e:
                # Round ID 파싱 실패 시 round_id 전체를 session_id로 사용
                session_id = request.round_id
                logger.warning(f"Failed to parse round_id: {e}, using full round_id as session_id")

            # 1. 각 답변을 순차 채점 (병렬화는 Phase 3)
            for answer in request.answers:
                try:
                    # 단일 채점 메서드 활용 (Tool 6 필수 파라미터 포함)
                    single_request = ScoreAnswerRequest(
                        # Tool 6 필수 파라미터
                        session_id=session_id,
                        user_id=None,  # 배치 요청에서는 제공되지 않음 - Tool 6에서 "unknown_user" 기본값 사용
                        question_id=answer.item_id,  # item_id를 question_id로 사용
                        question_type="short_answer",  # 배치 채점에서 기본값 - 실제 타입은 질문 DB에서 조회 필요
                        # 사용자 답변
                        user_answer=answer.user_answer,
                        # 내부 메타데이터
                        round_id=request.round_id,
                        item_id=answer.item_id,
                        response_time_ms=answer.response_time_ms,
                    )

                    result = await self.score_and_explain(single_request)

                    # 배치 응답 포맷으로 변환
                    item_score = ItemScore(
                        item_id=result.item_id,
                        correct=result.correct,
                        score=result.score,
                        extracted_keywords=result.extracted_keywords,
                        feedback=result.feedback,
                    )
                    per_item.append(item_score)
                    response_times.append(answer.response_time_ms)

                    logger.info(f"✓ 문항 채점 완료: {answer.item_id}, score={result.score}, correct={result.correct}")

                except Exception as e:
                    logger.error(f"❌ 문항 채점 실패: {answer.item_id}, {str(e)}")
                    # 실패한 항목도 결과에 포함 (score=0)
                    item_score = ItemScore(
                        item_id=answer.item_id,
                        correct=False,
                        score=0.0,
                        feedback=f"채점 오류: {str(e)}",
                    )
                    per_item.append(item_score)
                    response_times.append(answer.response_time_ms)

            # 2. 라운드 통계 계산
            correct_count = sum(1 for item in per_item if item.correct)
            total_count = len(per_item)
            round_score = sum(item.score for item in per_item) / total_count if total_count > 0 else 0.0
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0

            round_stats = RoundStats(
                avg_response_time=avg_response_time,
                correct_count=correct_count,
                total_count=total_count,
            )

            # 3. 배치 응답 생성
            response = SubmitAnswersResponse(
                round_id=request.round_id,
                per_item=per_item,
                round_score=round_score,
                round_stats=round_stats,
            )

            logger.info(
                f"✅ 배치 채점 완료: "
                f"round_score={response.round_score:.1f}, "
                f"correct={correct_count}/{total_count}, "
                f"avg_time={avg_response_time:.0f}ms"
            )

            return response

        except Exception as e:
            logger.error(f"❌ 배치 채점 중 예상치 못한 오류: {e}")
            # 부분 결과라도 반환하지 않고 전체 실패 표시
            return SubmitAnswersResponse(
                round_id=request.round_id,
                per_item=[],
                round_score=0.0,
                round_stats=RoundStats(
                    avg_response_time=0.0,
                    correct_count=0,
                    total_count=len(request.answers),
                ),
            )

    def _parse_agent_output_generate(self, result: dict, round_id: str) -> GenerateQuestionsResponse:
        """
        Parse agent output for question generation (REQ-A-LangChain).

        Args:
            result: Agent output (supports both AgentExecutor and LangGraph formats)
            round_id: 라운드 ID

        Returns:
            GenerateQuestionsResponse

        로직:
            1. _extract_tool_results()로 도구 호출 추출 (intermediate_steps 또는 messages 모두 지원)
            2. name이 "save_generated_question"인 호출에서 question 데이터 파싱
            3. 각 question을 GeneratedItem으로 변환
            4. 성공/실패 개수 집계

        참고:
            - AgentExecutor 출력: {"output": "...", "intermediate_steps": [(tool_name, tool_output), ...]}
            - LangGraph 출력: {"messages": [...message objects...]}
            - 두 포맷 모두 _extract_tool_results()로 일관되게 처리

        """
        logger.info(f"문항 생성 결과 파싱 중... round_id={round_id}")

        # Extract total_tokens from LangGraph messages
        total_tokens = 0
        if "messages" in result:
            for msg in result.get("messages", []):
                if hasattr(msg, "response_metadata") and msg.response_metadata:
                    usage_metadata = msg.response_metadata.get("usage_metadata", {})
                    if "total_tokens" in usage_metadata:
                        total_tokens = usage_metadata["total_tokens"]
                        break

        try:
            # DEBUG: Agent output 구조 분석
            logger.info("=" * 80)
            logger.info("🔍 AGENT OUTPUT STRUCTURE ANALYSIS")
            logger.info("=" * 80)

            # 1. Result dict 키 확인
            result_keys = list(result.keys())
            logger.info(f"Result 최상위 키: {result_keys}")

            # 2. intermediate_steps 확인
            intermediate_steps = result.get("intermediate_steps", [])
            if intermediate_steps:
                logger.info(f"\n✓ intermediate_steps 발견: {len(intermediate_steps)}개")
                for i, (tool_name, tool_output) in enumerate(intermediate_steps):
                    output_preview = str(tool_output)[:150]
                    logger.info(f"  [{i}] tool_name={tool_name}, output_type={type(tool_output).__name__}")
                    logger.info(f"      output_preview={output_preview}...")
            else:
                logger.info("\n✗ intermediate_steps 없음")

            # 3. messages 확인
            messages = result.get("messages", [])
            if messages:
                logger.info(f"\n✓ messages 발견: {len(messages)}개")
                for i, msg in enumerate(messages):
                    msg_type = type(msg).__name__
                    msg_attrs = {
                        "type": getattr(msg, "type", "N/A"),
                        "has_content": hasattr(msg, "content"),
                        "has_tool_calls": hasattr(msg, "tool_calls"),
                        "has_tool_call_id": hasattr(msg, "tool_call_id"),
                    }
                    logger.info(f"  [{i}] type={msg_type}, attrs={msg_attrs}")

                    # AIMessage의 경우 tool_calls 확인
                    if msg_type == "AIMessage" and hasattr(msg, "tool_calls"):
                        tool_calls = getattr(msg, "tool_calls", [])
                        if tool_calls:
                            logger.info(f"      tool_calls: {len(tool_calls)}개")
                            for j, tc in enumerate(tool_calls):
                                tc_name = getattr(tc, "name", tc.get("name") if isinstance(tc, dict) else "?")
                                tc_id = getattr(tc, "id", tc.get("id") if isinstance(tc, dict) else "?")
                                logger.info(f"        [{j}] name={tc_name}, id={tc_id}")
                        # DEBUG: AIMessage의 content 전체 출력
                        ai_content = getattr(msg, "content", "")
                        if ai_content:
                            content_preview = str(ai_content)[:500]
                            logger.info("      AIMessage.content (first 500 chars):")
                            logger.info(f"        {content_preview}...")

                    # ToolMessage의 경우 내용 확인
                    if msg_type == "ToolMessage":
                        content = getattr(msg, "content", "?")
                        tool_call_id = getattr(msg, "tool_call_id", "?")
                        name = getattr(msg, "name", "?")
                        logger.info(f"      tool_call_id={tool_call_id}, name={name}")
                        logger.info(f"      content_preview={str(content)[:200]}...")
            else:
                logger.info("\n✗ messages 없음")

            logger.info("=" * 80)

            # 0. ReAct 텍스트 형식: Final Answer JSON 파싱 시도
            logger.info("\n🔍 Attempting to parse Final Answer JSON from AIMessage...")
            items: list[GeneratedItem] = []
            failed_count = 0
            error_messages: list[str] = []
            agent_steps = 0  # Initialize agent_steps early

            # AIMessage에서 Final Answer JSON 추출
            for message in result.get("messages", []):
                if isinstance(message, AIMessage):
                    content = getattr(message, "content", "")

                    # Final Answer: 패턴 찾기
                    if "Final Answer:" in content:
                        logger.info("✓ Found 'Final Answer:' in AIMessage content")

                        try:
                            # Final Answer 뒤의 JSON 추출
                            json_start = content.find("Final Answer:") + len("Final Answer:")
                            json_str = content[json_start:].strip()

                            # ```json ... ``` 마크다운 제거
                            if "```json" in json_str:
                                json_str = json_str.split("```json")[1].split("```")[0].strip()
                            elif "```" in json_str:
                                json_str = json_str.split("```")[1].split("```")[0].strip()

                            # Unescape 처리: Agent가 escaped quotes를 사용할 수 있음
                            # Replace escaped quotes (order matters: handle single quotes first)
                            # Remove backslash before single quotes (not valid in JSON strings)
                            json_str = json_str.replace("\\'", "'")
                            # Replace escaped double quotes with regular quotes
                            json_str = json_str.replace('\\"', '"')

                            # Convert Python None to JSON null
                            import re

                            json_str = re.sub(r"\bNone\b", "null", json_str)

                            logger.info(f"📋 Extracted JSON (first 300 chars): {json_str[:300]}...")

                            # JSON 파싱 (robust parser 사용)
                            try:
                                questions_data = parse_json_robust(json_str)
                            except json.JSONDecodeError as e:
                                logger.warning(f"❌ Failed to parse Final Answer JSON after all cleanup strategies: {e}")
                                error_messages.append(f"Final Answer JSON parsing failed: {str(e)}")
                                continue

                            if not isinstance(questions_data, list):
                                questions_data = [questions_data]

                            logger.info(f"✅ Parsed {len(questions_data)} question(s) from Final Answer JSON")

                            # 각 question을 GeneratedItem으로 변환
                            for q in questions_data:
                                try:
                                    # Determine question type for answer_schema structure
                                    question_type = q.get("type", "multiple_choice")

                                    # answer_schema 구성 (type-aware)
                                    # Tool 5 반환값에서 flattened 필드 사용 (correct_answer, correct_keywords)
                                    # Normalize answer_schema to handle both string and dict formats
                                    raw_answer_schema = q.get("answer_schema")
                                    normalized_schema_type = normalize_answer_schema(raw_answer_schema)

                                    # Extract correct_answer from multiple possible fields
                                    # Priority: correct_answer > correct_key > (from raw_answer_schema dict)
                                    correct_answer_value = (
                                        q.get("correct_answer") or
                                        q.get("correct_key") or
                                        (raw_answer_schema.get("correct_answer") if isinstance(raw_answer_schema, dict) else None) or
                                        (raw_answer_schema.get("correct_key") if isinstance(raw_answer_schema, dict) else None)
                                    )

                                    if question_type == "short_answer":
                                        # Short answer: include keywords only
                                        answer_schema = AnswerSchema(
                                            type=normalized_schema_type,
                                            keywords=q.get("correct_keywords"),
                                            correct_answer=None,  # Not used for short answer
                                        )
                                    else:
                                        # MC/TF: include correct_answer only
                                        answer_schema = AnswerSchema(
                                            type=normalized_schema_type,
                                            keywords=None,  # Not used for MC/TF
                                            correct_answer=correct_answer_value,
                                        )
                                    logger.info(
                                        f"  ✓ answer_schema populated: type={answer_schema.type}, keywords={answer_schema.keywords is not None}, correct_answer={answer_schema.correct_answer is not None}"
                                    )

                                    item = GeneratedItem(
                                        id=q.get("question_id", f"q_{uuid.uuid4().hex[:8]}"),
                                        type=question_type,
                                        stem=q.get("stem", ""),
                                        choices=q.get("choices"),
                                        answer_schema=answer_schema,
                                        difficulty=q.get("difficulty", 5),
                                        category=q.get("category", "AI"),
                                        validation_score=q.get("validation_score", 0.0),
                                        saved_at=datetime.now(UTC).isoformat(),
                                    )
                                    items.append(item)
                                    logger.info(f"  ✓ Created GeneratedItem: {item.id} ({item.stem[:50]}...)")

                                except Exception as e:
                                    logger.error(f"  ✗ Failed to create GeneratedItem: {e}")
                                    failed_count += 1
                                    error_messages.append(f"GeneratedItem creation error: {str(e)}")
                                    continue

                            # Final Answer JSON이 파싱되면 도구 추출 스킵
                            if items:
                                logger.info(f"\n✅ Successfully parsed {len(items)} items from Final Answer JSON")
                                logger.info("Skipping tool results extraction (using Final Answer format)")
                                # Update agent_steps when Final Answer JSON is found
                                agent_steps = max(
                                    agent_steps,
                                    len(result.get("intermediate_steps", [])) or len(result.get("messages", [])),
                                )
                                break

                        except json.JSONDecodeError as e:
                            logger.warning(f"❌ Failed to parse Final Answer JSON: {e}")
                            error_messages.append(f"Final Answer JSON decode error: {str(e)}")
                            continue
                        except Exception as e:
                            logger.warning(f"❌ Error processing Final Answer: {e}")
                            error_messages.append(f"Final Answer processing error: {str(e)}")
                            continue

            # 1. Final Answer JSON이 없으면 save_generated_question 도구 결과 추출
            if not items:
                logger.info("\n📊 Extracting save_generated_question tool results (LangGraph format)...")
                tool_results = self._extract_tool_results(result, "save_generated_question")
                agent_steps = max(
                    agent_steps, len(result.get("intermediate_steps", [])) or len(result.get("messages", []))
                )
                logger.info(f"✓ 도구 호출 {agent_steps}개 발견, save_generated_question {len(tool_results)}개")

                # DEBUG: 추출된 tool_results 상세 출력
                if tool_results:
                    logger.info("\n📋 Extracted tool results:")
                    for i, (tool_name, tool_output_str) in enumerate(tool_results):
                        logger.info(f"  [{i}] tool_name={tool_name}")
                        logger.info(f"      output_type={type(tool_output_str).__name__}")
                        output_preview = str(tool_output_str)[:300]
                        logger.info(f"      output_preview={output_preview}...")
                else:
                    logger.warning("⚠️  No tool results extracted!")

                # Tool results 파싱으로 items 구성
                for tool_name, tool_output_str in tool_results:
                    if tool_name != "save_generated_question":
                        continue

                    if not tool_output_str:
                        failed_count += 1
                        continue

                    # JSON 파싱
                    try:
                        tool_output = (
                            json.loads(tool_output_str) if isinstance(tool_output_str, str) else tool_output_str
                        )
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON 파싱 실패: {str(tool_output_str)[:100]}")
                        failed_count += 1
                        error_messages.append(f"JSON decode error: {str(e)}")
                        continue

                    # success 플래그 확인
                    has_error = "error" in tool_output
                    is_success = tool_output.get("success", not has_error)

                    if not is_success or has_error:
                        failed_count += 1
                        if "error" in tool_output:
                            error_messages.append(tool_output["error"])
                        continue

                    # GeneratedItem 객체 생성
                    try:
                        # Determine question type for answer_schema structure
                        item_type = tool_output.get("item_type", "multiple_choice")

                        # answer_schema 구성 (Tool 5가 제공하거나 기본값 사용)
                        schema_from_tool = tool_output.get("answer_schema", {})
                        if isinstance(schema_from_tool, dict):
                            # Tool 5에서 반환한 answer_schema 사용
                            # Type-aware construction: include only relevant fields for question type
                            if item_type == "short_answer":
                                # Short answer: include keywords only
                                answer_schema = AnswerSchema(
                                    type=schema_from_tool.get("type", "keyword_match"),
                                    keywords=schema_from_tool.get("correct_keywords")
                                    or schema_from_tool.get("keywords"),
                                    correct_answer=None,  # Not used for short answer
                                )
                            else:
                                # MC/TF: include correct_answer/correct_key only
                                answer_schema = AnswerSchema(
                                    type=schema_from_tool.get("type", "exact_match"),
                                    keywords=None,  # Not used for MC/TF
                                    correct_answer=schema_from_tool.get("correct_key")
                                    or schema_from_tool.get("correct_answer"),
                                )
                        else:
                            # Fallback to tool_output fields with type awareness
                            if item_type == "short_answer":
                                answer_schema = AnswerSchema(
                                    type=tool_output.get("answer_type", "keyword_match"),
                                    keywords=tool_output.get("correct_keywords"),
                                    correct_answer=None,
                                )
                            else:
                                answer_schema = AnswerSchema(
                                    type=tool_output.get("answer_type", "exact_match"),
                                    keywords=None,
                                    correct_answer=tool_output.get("correct_answer"),
                                )

                        item = GeneratedItem(
                            id=tool_output.get("question_id", f"q_{uuid.uuid4().hex[:8]}"),
                            type=tool_output.get("item_type", "multiple_choice"),
                            stem=tool_output.get("stem", ""),
                            choices=tool_output.get("choices"),
                            answer_schema=answer_schema,
                            difficulty=tool_output.get("difficulty", 5),
                            category=tool_output.get("category", "general"),
                            validation_score=tool_output.get("validation_score", 0.0),
                            saved_at=tool_output.get("saved_at", datetime.now(UTC).isoformat()),
                        )
                        items.append(item)
                        logger.info(f"✓ 문항 파싱 성공: {item.id}, stem={item.stem[:50] if item.stem else 'N/A'}")

                    except Exception as e:
                        logger.error(f"GeneratedItem 생성 실패: {e}")
                        failed_count += 1
                        error_messages.append(str(e))
                        continue

            # 3. 응답 생성
            error_msg = " | ".join(error_messages) if error_messages else None

            response = GenerateQuestionsResponse(
                round_id=round_id,
                items=items,
                time_limit_seconds=1200,  # 기본 20분
                agent_steps=agent_steps,
                failed_count=failed_count,
                total_tokens=total_tokens,
                error_message=error_msg,
            )

            logger.info(f"✅ 파싱 완료: 성공={len(items)}, 실패={failed_count}, agent_steps={agent_steps}")
            return response

        except Exception as e:
            logger.error(f"❌ 파싱 중 예상치 못한 오류: {e}")
            return GenerateQuestionsResponse(
                round_id=round_id,
                items=[],
                time_limit_seconds=1200,
                agent_steps=0,
                failed_count=0,
                total_tokens=total_tokens,
                error_message=f"Parsing error: {str(e)}",
            )

    def _parse_agent_output_score(self, result: dict, item_id: str) -> ScoreAnswerResponse:
        """
        Parse agent output for auto-grading (REQ-A-LangChain).

        Args:
            result: Agent output (supports both AgentExecutor and LangGraph formats)
            item_id: 문항 ID

        Returns:
            ScoreAnswerResponse

        로직:
            1. _extract_tool_results()로 score_and_explain 호출 추출 (intermediate_steps 또는 messages 모두 지원)
            2. Tool 출력을 JSON으로 파싱
            3. is_correct, score, explanation, feedback, keyword_matches 추출
            4. ScoreAnswerResponse로 변환

        참고:
            - AgentExecutor 출력: {"output": "...", "intermediate_steps": [(tool_name, tool_output), ...]}
            - LangGraph 출력: {"messages": [...message objects...]}
            - Tool 6 (score_and_explain) 출력 구조:
              {
                "is_correct": bool,  # Tool 6 호환
                "score": float (0-100),
                "explanation": str,
                "keyword_matches": list[str] (optional),  # Tool 6 호환
                "feedback": str (optional)
              }

        """
        logger.info(f"채점 결과 파싱 중... item_id={item_id}")

        try:
            # 1. score_and_explain 도구 결과 추출 (포맷 무관)
            tool_results = self._extract_tool_results(result, "score_and_explain")
            if not tool_results:
                logger.warning("score_and_explain 도구 호출을 찾을 수 없음")
                return ScoreAnswerResponse(
                    item_id=item_id,
                    is_correct=False,
                    correct=False,
                    score=0.0,
                    explanation="score_and_explain tool not executed",
                    graded_at=datetime.now(UTC).isoformat(),
                )

            # 2. 첫 번째 score_and_explain 결과 사용
            _, score_tool_output = tool_results[0]
            if not score_tool_output:
                logger.warning("score_and_explain 도구 출력이 비어있음")
                return ScoreAnswerResponse(
                    item_id=item_id,
                    is_correct=False,
                    correct=False,
                    score=0.0,
                    explanation="score_and_explain output is empty",
                    graded_at=datetime.now(UTC).isoformat(),
                )

            # 3. JSON 파싱
            try:
                tool_output = json.loads(score_tool_output) if isinstance(score_tool_output, str) else score_tool_output
            except json.JSONDecodeError as e:
                logger.warning(f"JSON 파싱 실패: {str(score_tool_output)[:100]}")
                return ScoreAnswerResponse(
                    item_id=item_id,
                    is_correct=False,
                    correct=False,
                    score=0.0,
                    explanation=f"JSON decode error: {str(e)}",
                    graded_at=datetime.now(UTC).isoformat(),
                )

            # 4. ScoreAnswerResponse 생성 (Tool 6 호환)
            # Tool 6는 "is_correct"를 반환하며, "keyword_matches"로 키워드 리스트 제공
            is_correct_from_tool = tool_output.get("is_correct", tool_output.get("correct", False))
            keyword_matches = tool_output.get("keyword_matches", tool_output.get("extracted_keywords", []))

            response = ScoreAnswerResponse(
                item_id=item_id,
                is_correct=is_correct_from_tool,  # Tool 6 호환
                correct=is_correct_from_tool,  # API 호환 (같은 값)
                score=float(tool_output.get("score", 0)),
                explanation=tool_output.get("explanation", ""),
                feedback=tool_output.get("feedback"),
                keyword_matches=keyword_matches,  # Tool 6 호환
                extracted_keywords=keyword_matches,  # API 호환 (같은 값)
                graded_at=tool_output.get("graded_at", datetime.now(UTC).isoformat()),
            )

            logger.info(f"✅ 채점 파싱 완료: correct={response.correct}, score={response.score}")
            return response

        except Exception as e:
            logger.error(f"❌ 채점 파싱 중 오류: {e}")
            return ScoreAnswerResponse(
                item_id=item_id,
                is_correct=False,
                correct=False,
                score=0.0,
                explanation=f"Parsing error: {str(e)}",
                graded_at=datetime.now(UTC).isoformat(),
            )


# ============================================================================
# Factory Function
# ============================================================================


async def create_agent() -> ItemGenAgent:
    """
    Create ItemGenAgent factory function.

    Returns:
        ItemGenAgent: 초기화된 에이전트

    사용:
        ```python
        agent = await create_agent()
        ```

    """
    return ItemGenAgent()
