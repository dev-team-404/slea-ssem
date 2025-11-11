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
import uuid
from datetime import UTC, datetime

from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from src.agent.config import AGENT_CONFIG, create_llm
from src.agent.fastmcp_server import TOOLS
from src.agent.prompts.react_prompt import get_react_prompt

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Schemas (입출력 데이터 계약)
# ============================================================================


class GenerateQuestionsRequest(BaseModel):
    """문항 생성 요청 (REQ: POST /api/v1/items/generate)."""

    survey_id: str = Field(..., description="설문 ID")
    round_idx: int = Field(..., ge=1, description="라운드 번호 (1-based)")
    prev_answers: list[dict] | None = Field(default=None, description="이전 라운드 답변 (적응형 테스트용)")


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
    error_message: str | None = Field(default=None, description="에러 메시지")


class ScoreAnswerRequest(BaseModel):
    """자동 채점 요청 (단일 처리, Phase 1)."""

    round_id: str = Field(..., description="라운드 ID")
    item_id: str = Field(..., description="문항 ID")
    user_answer: str = Field(..., description="응시자의 답변")
    response_time_ms: int = Field(default=0, ge=0, description="응답 시간 (밀리초)")


class ScoreAnswerResponse(BaseModel):
    """자동 채점 응답 (단일 처리, Phase 1)."""

    item_id: str = Field(..., description="문항 ID")
    correct: bool = Field(..., description="정답 여부")
    score: float = Field(..., ge=0, le=100, description="점수 (0~100)")
    explanation: str = Field(..., description="정답 해설")
    feedback: str | None = Field(default=None, description="부분 정답 피드백")
    extracted_keywords: list[str] = Field(default_factory=list, description="추출된 키워드 (주관식)")
    graded_at: str = Field(..., description="채점 시간")


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
            # 라운드 ID 생성
            round_id = f"round_{request.survey_id}_{request.round_idx}_{uuid.uuid4().hex[:8]}"

            # 에이전트 입력 구성
            agent_input = f"""
Generate high-quality exam questions for the following survey.
Survey ID: {request.survey_id}
Round: {request.round_idx}
Previous Answers: {json.dumps(request.prev_answers) if request.prev_answers else "None (First round)"}

Follow these steps:
1. Get survey context and user profile (Tool 1)
2. Search question templates for similar items (Tool 2) if available
3. Get keywords for adaptive difficulty (Tool 3)
4. Generate new questions with appropriate difficulty
5. Validate each question (Tool 4)
6. Save validated questions (Tool 5) with round_id={round_id}

Important:
- Generate questions with appropriate answer_schema (exact_match, keyword_match, or semantic_match)
- Each question must include: id, type, stem, choices (if MC), answer_schema, difficulty, category
- Return all saved questions with validation scores
"""

            # 에이전트 실행 (Tool Calling 루프)
            # AgentExecutor가 다음을 자동으로 수행:
            # - Agent Thought: 에이전트 추론
            # - Action: 도구 선택 및 호출
            # - Observation: 도구 결과
            # - 반복 또는 종료
            result = await self.executor.ainvoke({"input": agent_input})

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
        logger.info(f"📋 자동 채점 시작: round_id={request.round_id}, item_id={request.item_id}")

        try:
            # 에이전트 입력 구성
            agent_input = f"""
Score and explain the following answer:

Round ID: {request.round_id}
Item ID: {request.item_id}
User Answer: {request.user_answer}
Response Time (ms): {request.response_time_ms}

Use Tool 6 (score_and_explain) to:
1. Score the answer (0~100)
2. Generate explanation
3. Provide feedback if needed
4. Extract keywords if applicable (for short answer)

Return: correct (boolean), score (0-100), explanation, feedback, extracted_keywords
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

            # 1. 각 답변을 순차 채점 (병렬화는 Phase 3)
            for answer in request.answers:
                try:
                    # 단일 채점 메서드 활용
                    single_request = ScoreAnswerRequest(
                        round_id=request.round_id,
                        item_id=answer.item_id,
                        user_answer=answer.user_answer,
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
            result: AgentExecutor의 출력
            round_id: 라운드 ID

        Returns:
            GenerateQuestionsResponse

        로직:
            1. result["intermediate_steps"]에서 모든 도구 호출 추출
            2. name이 "save_generated_question"인 호출에서 question 데이터 파싱
            3. 각 question을 GeneratedItem으로 변환
            4. 성공/실패 개수 집계

        참고:
            - AgentExecutor 출력: {"output": "...", "intermediate_steps": [(tool_name, tool_output), ...]}
            - intermediate_steps는 (tool_name: str, tool_output: str) 튜플의 리스트
            - Tool 출력은 대부분 JSON 문자열 형태

        """
        logger.info(f"문항 생성 결과 파싱 중... round_id={round_id}")

        try:
            # 1. intermediate_steps 추출 (도구 호출 히스토리)
            intermediate_steps = result.get("intermediate_steps", [])
            agent_steps = len(intermediate_steps)
            logger.info(f"도구 호출 {agent_steps}개 발견")

            # 2. save_generated_question 도구 결과 파싱
            items: list[GeneratedItem] = []
            failed_count = 0
            error_messages: list[str] = []

            for tool_name, tool_output_str in intermediate_steps:
                if tool_name != "save_generated_question":
                    continue

                if not tool_output_str:
                    failed_count += 1
                    continue

                # JSON 파싱
                try:
                    tool_output = json.loads(tool_output_str) if isinstance(tool_output_str, str) else tool_output_str
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
                    # answer_schema 구성
                    answer_schema = AnswerSchema(
                        type=tool_output.get("answer_type", "exact_match"),
                        keywords=tool_output.get("correct_keywords"),
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
                    logger.info(f"✓ 문항 파싱 성공: {item.id}")

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
                error_message=f"Parsing error: {str(e)}",
            )

    def _parse_agent_output_score(self, result: dict, item_id: str) -> ScoreAnswerResponse:
        """
        Parse agent output for auto-grading (REQ-A-LangChain).

        Args:
            result: AgentExecutor의 출력
            item_id: 문항 ID

        Returns:
            ScoreAnswerResponse

        로직:
            1. result["intermediate_steps"]에서 tool_name="score_and_explain" 호출 찾기
            2. Tool 출력을 JSON으로 파싱
            3. correct, score, explanation, feedback, extracted_keywords 추출
            4. ScoreAnswerResponse로 변환

        참고:
            - AgentExecutor 출력: {"output": "...", "intermediate_steps": [(tool_name, tool_output), ...]}
            - Tool 6 (score_and_explain) 출력 구조:
              {
                "correct": bool,
                "score": float (0-100),
                "explanation": str,
                "extracted_keywords": list[str] (optional),
                "feedback": str (optional)
              }

        """
        logger.info(f"채점 결과 파싱 중... item_id={item_id}")

        try:
            # 1. intermediate_steps에서 score_and_explain 호출 찾기
            intermediate_steps = result.get("intermediate_steps", [])
            if not intermediate_steps:
                logger.warning("intermediate_steps가 비어있음")
                return ScoreAnswerResponse(
                    item_id=item_id,
                    correct=False,
                    score=0.0,
                    explanation="No tool steps found",
                    graded_at=datetime.now(UTC).isoformat(),
                )

            # 2. score_and_explain 도구 호출 찾기
            score_tool_output = None
            for tool_name, tool_output_str in intermediate_steps:
                if tool_name == "score_and_explain":
                    score_tool_output = tool_output_str
                    break

            if not score_tool_output:
                logger.warning("score_and_explain 도구 호출을 찾을 수 없음")
                return ScoreAnswerResponse(
                    item_id=item_id,
                    correct=False,
                    score=0.0,
                    explanation="score_and_explain tool not executed",
                    graded_at=datetime.now(UTC).isoformat(),
                )

            # 3. JSON 파싱
            try:
                tool_output = json.loads(score_tool_output) if isinstance(score_tool_output, str) else score_tool_output
            except json.JSONDecodeError as e:
                logger.warning(f"JSON 파싱 실패: {str(score_tool_output)[:100]}")
                return ScoreAnswerResponse(
                    item_id=item_id,
                    correct=False,
                    score=0.0,
                    explanation=f"JSON decode error: {str(e)}",
                    graded_at=datetime.now(UTC).isoformat(),
                )

            # 4. ScoreAnswerResponse 생성
            response = ScoreAnswerResponse(
                item_id=item_id,
                correct=tool_output.get("correct", False),
                score=float(tool_output.get("score", 0)),
                explanation=tool_output.get("explanation", ""),
                feedback=tool_output.get("feedback"),
                extracted_keywords=tool_output.get("extracted_keywords", []),
                graded_at=tool_output.get("graded_at", datetime.now(UTC).isoformat()),
            )

            logger.info(f"✅ 채점 파싱 완료: correct={response.correct}, score={response.score}")
            return response

        except Exception as e:
            logger.error(f"❌ 채점 파싱 중 오류: {e}")
            return ScoreAnswerResponse(
                item_id=item_id,
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
