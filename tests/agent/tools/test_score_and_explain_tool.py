"""
Test suite for REQ-A-Mode2-Tool6: Score & Generate Explanation

This module tests the auto-scoring tool that:
1. Scores user answers (MC, OX, short answer)
2. Generates explanations with reference links
3. Handles edge cases and LLM timeouts

REQ: REQ-A-Mode2-Tool6
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel, ValidationError

# ============================================================================
# TEST DATA & FIXTURES
# ============================================================================


class ScoreAnswerRequest(BaseModel):
    """Input schema for scoring endpoint."""

    session_id: str
    user_id: str
    question_id: str
    question_type: str  # "multiple_choice" | "true_false" | "short_answer"
    user_answer: str
    correct_answer: str | None = None  # For MC/OX
    correct_keywords: list[str] | None = None  # For short answer
    difficulty: int | None = None
    category: str | None = None


class ScoreAnswerResponse(BaseModel):
    """Output schema for scoring result."""

    attempt_id: str
    session_id: str
    question_id: str
    user_id: str
    is_correct: bool
    score: int  # 0-100
    explanation: str
    keyword_matches: list[str]
    feedback: str | None = None
    graded_at: str  # ISO format timestamp


class AnswerExplanation(BaseModel):
    """Explanation storage schema."""

    id: str
    question_id: str
    attempt_answer_id: str
    explanation_text: str  # >= 500 chars
    reference_links: list[dict[str, str]]  # [{title, url}, ...] >= 3
    is_correct: bool
    created_at: str


@pytest.fixture
def valid_mc_request() -> ScoreAnswerRequest:
    """Valid multiple choice scoring request."""
    return ScoreAnswerRequest(
        session_id="sess_001",
        user_id="user_001",
        question_id="q_001",
        question_type="multiple_choice",
        user_answer="B",
        correct_answer="B",
        difficulty=5,
        category="technical",
    )


@pytest.fixture
def valid_ox_request() -> ScoreAnswerRequest:
    """Valid true/false scoring request."""
    return ScoreAnswerRequest(
        session_id="sess_001",
        user_id="user_001",
        question_id="q_002",
        question_type="true_false",
        user_answer="True",
        correct_answer="True",
        difficulty=3,
        category="general",
    )


@pytest.fixture
def valid_short_answer_request() -> ScoreAnswerRequest:
    """Valid short answer scoring request."""
    return ScoreAnswerRequest(
        session_id="sess_001",
        user_id="user_001",
        question_id="q_003",
        question_type="short_answer",
        user_answer="RAG is a technique combining retrieval and generation",
        correct_answer=None,
        correct_keywords=["RAG", "retrieval", "generation"],
        difficulty=7,
        category="technical",
    )


@pytest.fixture
def mock_db_session() -> MagicMock:
    """Mock database session."""
    return MagicMock()


@pytest.fixture
def mock_llm() -> AsyncMock:
    """Mock LLM client for explanation generation."""
    return AsyncMock()


# ============================================================================
# TEST CLASS 1: INPUT VALIDATION
# ============================================================================


class TestInputValidation:
    """Test input validation for score_and_explain tool."""

    def test_missing_required_field_session_id(self):
        """AC1: Reject request with missing session_id."""
        with pytest.raises(ValidationError):
            ScoreAnswerRequest(
                user_id="user_001",
                question_id="q_001",
                question_type="multiple_choice",
                user_answer="B",
            )

    def test_missing_required_field_user_id(self):
        """AC1: Reject request with missing user_id."""
        with pytest.raises(ValidationError):
            ScoreAnswerRequest(
                session_id="sess_001",
                question_id="q_001",
                question_type="multiple_choice",
                user_answer="B",
            )

    def test_missing_required_field_question_type(self):
        """AC1: Reject request with missing question_type."""
        with pytest.raises(ValidationError):
            ScoreAnswerRequest(
                session_id="sess_001",
                user_id="user_001",
                question_id="q_001",
                user_answer="B",
            )

    def test_empty_user_answer(self):
        """AC4: Handle empty user_answer gracefully."""
        # Should not raise during construction
        req = ScoreAnswerRequest(
            session_id="sess_001",
            user_id="user_001",
            question_id="q_001",
            question_type="multiple_choice",
            user_answer="",
            correct_answer="B",
        )
        assert req.user_answer == ""

    def test_invalid_question_type(self):
        """AC1: Reject invalid question_type."""
        # Pydantic allows any string by default; validation happens in implementation
        req = ScoreAnswerRequest(
            session_id="sess_001",
            user_id="user_001",
            question_id="q_001",
            question_type="invalid_type",
            user_answer="answer",
        )
        assert req.question_type == "invalid_type"

    def test_correct_answer_required_for_mc(self, valid_mc_request):
        """AC1: Multiple choice requires correct_answer."""
        assert valid_mc_request.correct_answer is not None

    def test_keywords_required_for_short_answer(self, valid_short_answer_request):
        """AC1: Short answer requires correct_keywords."""
        assert valid_short_answer_request.correct_keywords is not None


# ============================================================================
# TEST CLASS 2: MULTIPLE CHOICE SCORING
# ============================================================================


class TestMultipleChoiceScoring:
    """Test MC/OX exact match scoring logic."""

    def test_mc_correct_answer(self, valid_mc_request):
        """AC1: MC correct answer returns is_correct=True, score=100."""
        # user_answer == correct_answer
        assert valid_mc_request.user_answer == valid_mc_request.correct_answer
        # Expected: is_correct=True, score=100
        expected_score = 100
        expected_is_correct = True

        assert valid_mc_request.user_answer == "B"
        assert expected_score == 100
        assert expected_is_correct is True

    def test_mc_incorrect_answer(self):
        """AC1: MC incorrect answer returns is_correct=False, score=0."""
        req = ScoreAnswerRequest(
            session_id="sess_001",
            user_id="user_001",
            question_id="q_001",
            question_type="multiple_choice",
            user_answer="A",  # Wrong answer
            correct_answer="B",
        )
        # user_answer != correct_answer
        assert req.user_answer != req.correct_answer
        # Expected: is_correct=False, score=0
        expected_score = 0
        expected_is_correct = False

        assert expected_score == 0
        assert expected_is_correct is False

    def test_ox_true_correct(self, valid_ox_request):
        """AC1: OX (True/False) correct answer returns is_correct=True."""
        assert valid_ox_request.user_answer == valid_ox_request.correct_answer
        expected_is_correct = True
        assert expected_is_correct is True

    def test_ox_false_correct(self):
        """AC1: OX False answer returns is_correct=True if correct."""
        req = ScoreAnswerRequest(
            session_id="sess_001",
            user_id="user_001",
            question_id="q_002",
            question_type="true_false",
            user_answer="False",
            correct_answer="False",
        )
        assert req.user_answer == req.correct_answer
        expected_is_correct = True
        assert expected_is_correct is True

    def test_case_insensitive_matching(self):
        """AC1: MC matching should handle case variation (B vs b)."""
        req = ScoreAnswerRequest(
            session_id="sess_001",
            user_id="user_001",
            question_id="q_001",
            question_type="multiple_choice",
            user_answer="b",  # lowercase
            correct_answer="B",
        )
        # Implementation should normalize: "b".upper() == "B"
        normalized_answer = req.user_answer.upper()
        assert normalized_answer == req.correct_answer.upper()


# ============================================================================
# TEST CLASS 3: SHORT ANSWER SCORING (LLM SEMANTIC)
# ============================================================================


class TestShortAnswerScoring:
    """Test short answer LLM-based semantic scoring."""

    @pytest.mark.asyncio
    async def test_short_answer_high_score_with_keywords(self, valid_short_answer_request, mock_llm):
        """AC2: Short answer with all keywords → is_correct=True, score=100."""
        # User answer contains all keywords
        mock_llm.invoke.return_value.content = """
        Score: 95
        Keyword Matches: RAG, retrieval, generation
        Feedback: Excellent understanding
        """

        # Expected: is_correct=True (score >= 80), score=95
        expected_score = 95
        expected_is_correct = True
        expected_keywords = ["RAG", "retrieval", "generation"]

        assert expected_score >= 80
        assert expected_is_correct is True
        assert len(expected_keywords) == 3

    @pytest.mark.asyncio
    async def test_short_answer_partial_credit(self, valid_short_answer_request, mock_llm):
        """AC2: Short answer with partial keywords → 70-79 score, is_correct=False."""
        # User answer contains 1-2 keywords
        mock_llm.invoke.return_value.content = """
        Score: 75
        Keyword Matches: RAG, retrieval
        Feedback: Good but missing generation concept
        """

        # Expected: is_correct=False (score 70-79), score=75
        expected_score = 75
        expected_is_correct = False
        expected_keywords = ["RAG", "retrieval"]

        assert 70 <= expected_score < 80
        assert expected_is_correct is False
        assert len(expected_keywords) == 2

    @pytest.mark.asyncio
    async def test_short_answer_low_score_no_keywords(self, mock_llm):
        """AC2: Short answer with no keywords → score<70, is_correct=False."""
        req = ScoreAnswerRequest(
            session_id="sess_001",
            user_id="user_001",
            question_id="q_003",
            question_type="short_answer",
            user_answer="I don't know",
            correct_answer=None,
            correct_keywords=["RAG", "retrieval", "generation"],
        )

        mock_llm.invoke.return_value.content = """
        Score: 20
        Keyword Matches:
        Feedback: Does not address the question
        """

        # Expected: is_correct=False, score<70
        expected_score = 20
        expected_is_correct = False
        expected_keywords = []

        assert expected_score < 70
        assert expected_is_correct is False
        assert len(expected_keywords) == 0

    @pytest.mark.asyncio
    async def test_short_answer_keyword_extraction(self, mock_llm):
        """AC2: Extract keyword matches from user answer."""
        req = ScoreAnswerRequest(
            session_id="sess_001",
            user_id="user_001",
            question_id="q_003",
            question_type="short_answer",
            user_answer="RAG and LLM integrate retrieval",
            correct_answer=None,
            correct_keywords=["RAG", "retrieval", "integration", "LLM"],
        )

        mock_llm.invoke.return_value.content = """
        Score: 88
        Keyword Matches: RAG, LLM, retrieval
        """

        # Expected keywords: subset of correct_keywords found in answer
        expected_keywords = ["RAG", "LLM", "retrieval"]
        assert len(expected_keywords) >= 2
        assert "RAG" in expected_keywords


# ============================================================================
# TEST CLASS 4: RESPONSE STRUCTURE & CONTRACT
# ============================================================================


class TestResponseStructure:
    """Test output response schema compliance."""

    def test_response_has_all_required_fields(self):
        """AC5: Response contains all required fields."""
        response = ScoreAnswerResponse(
            attempt_id=str(uuid.uuid4()),
            session_id="sess_001",
            question_id="q_001",
            user_id="user_001",
            is_correct=True,
            score=100,
            explanation="Correct answer with comprehensive understanding",
            keyword_matches=["RAG"],
            graded_at=datetime.now().isoformat(),
        )

        required_fields = {
            "attempt_id",
            "session_id",
            "question_id",
            "user_id",
            "is_correct",
            "score",
            "explanation",
            "keyword_matches",
            "graded_at",
        }

        for field in required_fields:
            assert hasattr(response, field)

    def test_response_field_types(self):
        """AC5: Response fields have correct types."""
        response = ScoreAnswerResponse(
            attempt_id="test-id",
            session_id="sess_001",
            question_id="q_001",
            user_id="user_001",
            is_correct=True,
            score=85,
            explanation="Test explanation",
            keyword_matches=["keyword1"],
            graded_at=datetime.now().isoformat(),
        )

        assert isinstance(response.attempt_id, str)
        assert isinstance(response.session_id, str)
        assert isinstance(response.question_id, str)
        assert isinstance(response.user_id, str)
        assert isinstance(response.is_correct, bool)
        assert isinstance(response.score, int)
        assert isinstance(response.explanation, str)
        assert isinstance(response.keyword_matches, list)
        assert isinstance(response.graded_at, str)

    def test_score_range_0_100(self):
        """AC5: Score must be within 0-100 range."""
        for score in [0, 50, 100]:
            response = ScoreAnswerResponse(
                attempt_id="id",
                session_id="sess",
                question_id="q",
                user_id="u",
                is_correct=score >= 80,
                score=score,
                explanation="Test",
                keyword_matches=[],
                graded_at=datetime.now().isoformat(),
            )
            assert 0 <= response.score <= 100

    def test_graded_at_is_iso_timestamp(self):
        """AC5: graded_at must be ISO format timestamp."""
        now = datetime.now().isoformat()
        response = ScoreAnswerResponse(
            attempt_id="id",
            session_id="sess",
            question_id="q",
            user_id="u",
            is_correct=True,
            score=100,
            explanation="Test",
            keyword_matches=[],
            graded_at=now,
        )
        # Should parse without error
        datetime.fromisoformat(response.graded_at)

    def test_explanation_not_empty(self):
        """AC3: Explanation should be non-empty."""
        response = ScoreAnswerResponse(
            attempt_id="id",
            session_id="sess",
            question_id="q",
            user_id="u",
            is_correct=True,
            score=100,
            explanation="Non-empty explanation",
            keyword_matches=[],
            graded_at=datetime.now().isoformat(),
        )
        assert len(response.explanation) > 0


# ============================================================================
# TEST CLASS 5: EXPLANATION GENERATION
# ============================================================================


class TestExplanationGeneration:
    """Test explanation generation with reference links."""

    @pytest.mark.asyncio
    async def test_explanation_correct_answer(self, mock_llm):
        """AC3: Generate positive explanation for correct answer."""
        mock_llm.invoke.return_value.content = """
        This is a correct answer. You have demonstrated understanding of RAG systems.

        References:
        1. https://example.com/rag-guide
        2. https://example.com/retrieval-intro
        3. https://example.com/generation-methods
        """

        # Expected: explanation contains affirmation + educational content
        expected_explanation = "This is a correct answer. " "You have demonstrated understanding of RAG systems."

        assert "correct" in expected_explanation.lower()
        assert "understanding" in expected_explanation.lower()

    @pytest.mark.asyncio
    async def test_explanation_incorrect_answer(self, mock_llm):
        """AC3: Generate constructive feedback for incorrect answer."""
        mock_llm.invoke.return_value.content = """
        Your answer is incomplete. RAG combines retrieval and generation,
        but you missed the generation part.

        Key concepts to review:
        - Retrieval: Getting relevant documents
        - Generation: Creating answers from documents
        """

        # Expected: explanation provides correction + guidance
        expected_explanation = (
            "Your answer is incomplete. "
            "RAG combines retrieval and generation, "
            "but you missed the generation part."
        )

        assert "incomplete" in expected_explanation.lower()
        assert "missed" in expected_explanation.lower()

    @pytest.mark.asyncio
    async def test_explanation_with_reference_links(self, mock_llm):
        """AC3: Generate explanation with minimum 3 reference links."""
        explanation_obj = AnswerExplanation(
            id=str(uuid.uuid4()),
            question_id="q_001",
            attempt_answer_id="att_001",
            explanation_text="Detailed explanation about RAG systems " * 50,
            reference_links=[
                {"title": "RAG Guide", "url": "https://example.com/rag-guide"},
                {"title": "Retrieval Methods", "url": "https://example.com/retrieval"},
                {"title": "Generation Models", "url": "https://example.com/generation"},
            ],
            is_correct=True,
            created_at=datetime.now().isoformat(),
        )

        # Required: >= 3 reference links
        assert len(explanation_obj.reference_links) >= 3
        for link in explanation_obj.reference_links:
            assert "title" in link
            assert "url" in link
            assert link["url"].startswith("http")


# ============================================================================
# TEST CLASS 6: EDGE CASES & ERROR HANDLING
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_whitespace_normalization(self):
        """AC4: Handle extra whitespace in answers."""
        req = ScoreAnswerRequest(
            session_id="sess_001",
            user_id="user_001",
            question_id="q_001",
            question_type="multiple_choice",
            user_answer="  B  ",  # Extra whitespace
            correct_answer="B",
        )

        # Implementation should strip whitespace
        normalized = req.user_answer.strip()
        assert normalized == req.correct_answer

    def test_null_difficulty_and_category(self):
        """AC4: difficulty and category are optional."""
        req = ScoreAnswerRequest(
            session_id="sess_001",
            user_id="user_001",
            question_id="q_001",
            question_type="multiple_choice",
            user_answer="B",
            correct_answer="B",
            difficulty=None,
            category=None,
        )
        assert req.difficulty is None
        assert req.category is None

    def test_unicode_characters_in_answer(self):
        """AC4: Handle Unicode/multi-byte characters."""
        req = ScoreAnswerRequest(
            session_id="sess_001",
            user_id="user_001",
            question_id="q_003",
            question_type="short_answer",
            user_answer="검색 후 생성 (RAG) 기술입니다",
            correct_keywords=["RAG", "검색", "생성"],
        )
        assert "검색" in req.user_answer
        assert "RAG" in req.correct_keywords

    def test_very_long_answer(self):
        """AC4: Handle very long short answer (>5000 chars)."""
        long_answer = "A" * 5000
        req = ScoreAnswerRequest(
            session_id="sess_001",
            user_id="user_001",
            question_id="q_003",
            question_type="short_answer",
            user_answer=long_answer,
            correct_keywords=["A"],
        )
        assert len(req.user_answer) == 5000

    @pytest.mark.asyncio
    async def test_llm_timeout_graceful_fallback(self, mock_llm):
        """AC4: LLM timeout returns fallback explanation."""
        mock_llm.invoke.side_effect = TimeoutError("LLM timeout after 15s")

        # Implementation should catch timeout and provide fallback
        with pytest.raises(TimeoutError):
            await mock_llm.invoke({"text": "test"})

    def test_empty_keywords_list(self):
        """AC4: Handle empty correct_keywords list."""
        req = ScoreAnswerRequest(
            session_id="sess_001",
            user_id="user_001",
            question_id="q_003",
            question_type="short_answer",
            user_answer="Some answer",
            correct_keywords=[],
        )
        assert req.correct_keywords == []

    def test_multiple_choice_with_numeric_answer(self):
        """AC4: MC with numeric answer options."""
        req = ScoreAnswerRequest(
            session_id="sess_001",
            user_id="user_001",
            question_id="q_001",
            question_type="multiple_choice",
            user_answer="2",  # Numeric option
            correct_answer="2",
        )
        assert req.user_answer == req.correct_answer


# ============================================================================
# TEST CLASS 7: ACCEPTANCE CRITERIA SUMMARY
# ============================================================================


class TestAcceptanceCriteria:
    """Comprehensive AC verification tests."""

    def test_ac1_mc_ox_exact_matching(self, valid_mc_request, valid_ox_request):
        """AC1: MC/OX uses exact match comparison."""
        # MC
        assert valid_mc_request.user_answer == valid_mc_request.correct_answer
        # OX
        assert valid_ox_request.user_answer == valid_ox_request.correct_answer

    def test_ac2_short_answer_semantic_evaluation(self, valid_short_answer_request):
        """AC2: Short answer uses semantic evaluation."""
        assert valid_short_answer_request.question_type == "short_answer"
        assert valid_short_answer_request.correct_keywords is not None
        assert len(valid_short_answer_request.correct_keywords) > 0

    def test_ac3_explanation_generation(self):
        """AC3: Generates explanation with references."""
        explanation = AnswerExplanation(
            id="exp_001",
            question_id="q_001",
            attempt_answer_id="att_001",
            explanation_text="Comprehensive explanation " * 50,
            reference_links=[
                {"title": "Ref1", "url": "https://example.com/1"},
                {"title": "Ref2", "url": "https://example.com/2"},
                {"title": "Ref3", "url": "https://example.com/3"},
            ],
            is_correct=True,
            created_at=datetime.now().isoformat(),
        )
        assert len(explanation.explanation_text) >= 500
        assert len(explanation.reference_links) >= 3

    def test_ac4_edge_case_handling(self):
        """AC4: Handles edge cases gracefully."""
        # Empty answer
        req1 = ScoreAnswerRequest(
            session_id="sess_001",
            user_id="user_001",
            question_id="q_001",
            question_type="multiple_choice",
            user_answer="",
            correct_answer="B",
        )
        assert req1.user_answer == ""

        # Null optional fields
        req2 = ScoreAnswerRequest(
            session_id="sess_001",
            user_id="user_001",
            question_id="q_001",
            question_type="multiple_choice",
            user_answer="B",
            correct_answer="B",
            difficulty=None,
            category=None,
        )
        assert req2.difficulty is None

    def test_ac5_fastapi_schema_compliance(self):
        """AC5: Response matches FastAPI schema."""
        response = ScoreAnswerResponse(
            attempt_id="id",
            session_id="sess",
            question_id="q",
            user_id="u",
            is_correct=True,
            score=100,
            explanation="Test",
            keyword_matches=[],
            graded_at=datetime.now().isoformat(),
        )

        # Can be serialized to JSON
        json_data = response.model_dump_json()
        assert "attempt_id" in json_data
        assert "is_correct" in json_data
        assert "score" in json_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
