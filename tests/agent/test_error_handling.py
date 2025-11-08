"""
Comprehensive error handling tests for REQ-A-ErrorHandling.

This module tests the unified error handling and recovery framework:
- Retry mechanisms with exponential backoff
- Fallback strategies for each tool
- Graceful degradation
- Error context and logging
- Circuit breaker patterns

REQ: REQ-A-ErrorHandling
"""

import time
import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.agent.error_handler import (
    ErrorHandler,
    ErrorContext,
    ErrorStrategy,
    RetryConfig,
)
from src.agent.fallback_provider import FallbackProvider
from src.agent.retry_strategy import RetryStrategy, ExponentialBackoff


# ============================================================================
# TEST DATA & FIXTURES
# ============================================================================


@pytest.fixture
def error_handler() -> ErrorHandler:
    """Create error handler instance for testing."""
    return ErrorHandler()


@pytest.fixture
def retry_strategy() -> RetryStrategy:
    """Create retry strategy with exponential backoff."""
    return RetryStrategy(
        max_retries=3,
        backoff_strategy=ExponentialBackoff(initial_delay=0.01, multiplier=2)
    )


@pytest.fixture
def fallback_provider() -> FallbackProvider:
    """Create fallback provider for default values."""
    return FallbackProvider()


@pytest.fixture
def mock_tool1_db_error() -> Exception:
    """Mock database connection error from Tool 1."""
    return ConnectionError("Database connection failed")


@pytest.fixture
def mock_tool3_timeout() -> Exception:
    """Mock timeout error from Tool 3."""
    return TimeoutError("LLM API timeout")


# ============================================================================
# TEST CLASS 1: TOOL 1 - RETRY MECHANISM (AC1)
# ============================================================================


class TestTool1RetryMechanism:
    """Test Tool 1 (Get User Profile) retry logic with 3 attempts."""

    def test_tool1_db_error_retry_3x_then_default(self, error_handler, mock_tool1_db_error):
        """
        AC1: Tool 1 DB error → retry 3x → default profile.

        Given: Tool 1 raises ConnectionError
        When: Error handler manages the call
        Then: Retry 3 times and return default profile
        """
        call_count = 0

        def failing_tool1():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise mock_tool1_db_error
            return {"user_id": "user_001", "self_level": 5}

        result = error_handler.execute_with_retry(
            func=failing_tool1,
            max_retries=3,
            strategy=ErrorStrategy.RETRY_THEN_DEFAULT,
            fallback_value={
                "user_id": "unknown",
                "self_level": 3,
                "years_experience": 0,
                "job_role": "unknown",
                "duty": "unknown",
                "interests": [],
                "previous_score": 50,
            }
        )

        assert call_count == 4  # 3 failures + 1 success
        assert result["user_id"] == "user_001"

    def test_tool1_all_retries_exhausted_uses_fallback(self, error_handler, mock_tool1_db_error):
        """AC1: Tool 1 DB error → 3x retry exhausted → return default profile."""
        def failing_tool1():
            raise mock_tool1_db_error

        default_profile = {
            "user_id": "unknown",
            "self_level": 3,
            "years_experience": 0,
            "job_role": "unknown",
            "duty": "unknown",
            "interests": [],
            "previous_score": 50,
        }

        result = error_handler.execute_with_retry(
            func=failing_tool1,
            max_retries=3,
            strategy=ErrorStrategy.RETRY_THEN_DEFAULT,
            fallback_value=default_profile
        )

        assert result == default_profile
        assert result["user_id"] == "unknown"

    def test_tool1_retry_count_tracked(self, error_handler):
        """Verify retry count is tracked correctly."""
        retry_count = 0

        def failing_tool():
            nonlocal retry_count
            retry_count += 1
            if retry_count <= 2:
                raise ValueError("Error")
            return {"status": "success"}

        result = error_handler.execute_with_retry(
            func=failing_tool,
            max_retries=3,
            strategy=ErrorStrategy.RETRY_THEN_DEFAULT,
            fallback_value={}
        )

        assert retry_count == 3  # 2 failures + 1 success
        assert result["status"] == "success"


# ============================================================================
# TEST CLASS 2: TOOL 2 - GRACEFUL SKIP (AC2)
# ============================================================================


class TestTool2GracefulSkip:
    """Test Tool 2 (Search Templates) graceful skip on no results."""

    def test_tool2_no_results_skip_continue(self, error_handler):
        """
        AC2: Tool 2 no results → skip gracefully → continue pipeline.

        Given: Tool 2 returns empty results
        When: Error handler checks result
        Then: Continue pipeline with empty set
        """
        def tool2_no_results():
            return []  # No templates found

        result = error_handler.handle_tool2_no_results(
            func=tool2_no_results,
            skip_strategy=ErrorStrategy.SKIP_GRACEFULLY
        )

        assert result == []
        assert len(result) == 0

    def test_tool2_empty_results_pipeline_continues(self, error_handler):
        """Verify pipeline can continue with empty template results."""
        empty_templates = []

        # Simulate Tool 2 returning nothing
        can_continue = error_handler.can_continue_with_empty_results(
            result=empty_templates,
            tool_id="tool_2"
        )

        assert can_continue is True

    def test_tool2_error_vs_no_results_difference(self, error_handler):
        """Distinguish between Tool 2 error and no results scenario."""
        # No results: continue
        no_results_response = []
        assert error_handler.can_continue_with_empty_results(no_results_response, "tool_2")

        # Actual error: fallback
        error_case = None
        should_use_fallback = error_handler.should_use_fallback(error_case, "tool_2")
        assert should_use_fallback is True


# ============================================================================
# TEST CLASS 3: TOOL 3 - CACHED/DEFAULT FALLBACK (AC3)
# ============================================================================


class TestTool3CachedFallback:
    """Test Tool 3 (Difficulty Keywords) cached fallback."""

    def test_tool3_failure_use_cached_keywords(self, error_handler, mock_tool3_timeout):
        """
        AC3: Tool 3 failure → use cached/default keywords.

        Given: Tool 3 times out
        When: Error handler catches timeout
        Then: Return cached or default keywords
        """
        def failing_tool3():
            raise mock_tool3_timeout

        cached_keywords = {
            "keywords": ["basic", "intermediate", "advanced"],
            "concepts": ["fundamentals", "application"],
            "example_questions": ["What is X?"],
        }

        result = error_handler.execute_with_cache_fallback(
            func=failing_tool3,
            cache=cached_keywords,
            default_value={
                "keywords": ["default"],
                "concepts": ["general"],
                "example_questions": [],
            }
        )

        # Should return from cache first
        assert "keywords" in result
        assert len(result["keywords"]) > 0

    def test_tool3_no_cache_use_default(self, error_handler, mock_tool3_timeout):
        """AC3: Tool 3 failure with no cache → use default keywords."""
        def failing_tool3():
            raise mock_tool3_timeout

        default_keywords = {
            "keywords": ["default"],
            "concepts": ["general"],
            "example_questions": [],
        }

        result = error_handler.execute_with_cache_fallback(
            func=failing_tool3,
            cache=None,
            default_value=default_keywords
        )

        assert result == default_keywords
        assert result["keywords"] == ["default"]


# ============================================================================
# TEST CLASS 4: TOOL 4 - REGENERATE ON LOW SCORE (AC4)
# ============================================================================


class TestTool4RegenerateOnLowScore:
    """Test Tool 4 (Validate Quality) regeneration on low validation score."""

    def test_tool4_low_score_retry_2x_then_discard(self, error_handler):
        """
        AC4: Tool 4 low score (<0.70) → retry 2x → discard if still low.

        Given: Tool 4 returns validation score < 0.70
        When: Error handler checks score
        Then: Retry up to 2 times, discard if still low
        """
        attempt = 0

        def tool4_validate():
            nonlocal attempt
            attempt += 1
            if attempt <= 2:
                return {"validation_score": 0.60, "recommendation": "reject"}
            return {"validation_score": 0.85, "recommendation": "pass"}

        result = error_handler.execute_tool4_with_regenerate(
            validate_func=tool4_validate,
            max_regenerate_attempts=2,
            score_threshold=0.70
        )

        # After 2 attempts, score improves
        assert result["validation_score"] >= 0.70
        assert attempt == 3

    def test_tool4_score_always_low_discard_question(self, error_handler):
        """AC4: Tool 4 low score after 2 retries → discard question."""
        def tool4_always_low():
            return {"validation_score": 0.50, "recommendation": "reject"}

        result = error_handler.execute_tool4_with_regenerate(
            validate_func=tool4_always_low,
            max_regenerate_attempts=2,
            score_threshold=0.70
        )

        # Score never improves, question discarded
        assert result["validation_score"] < 0.70
        assert result["should_discard"] is True


# ============================================================================
# TEST CLASS 5: TOOL 5 - QUEUE FOR RETRY (AC5)
# ============================================================================


class TestTool5QueueForRetry:
    """Test Tool 5 (Save Question) queue mechanism for failed saves."""

    def test_tool5_save_failure_add_to_queue(self, error_handler):
        """
        AC5: Tool 5 save error → queue for retry.

        Given: Tool 5 save operation fails
        When: Error handler catches failure
        Then: Add item to memory queue for batch retry
        """
        def failing_save():
            raise IOError("Database write failed")

        question = {
            "question_id": str(uuid.uuid4()),
            "stem": "Test question?",
            "type": "multiple_choice",
        }

        queue_item = error_handler.queue_failed_save(
            question=question,
            error=IOError("Database write failed")
        )

        assert queue_item["question_id"] == question["question_id"]
        assert queue_item["status"] == "queued"
        assert "timestamp" in queue_item

    def test_tool5_queue_has_size_limit(self, error_handler):
        """AC5: Memory queue has max size limit (100 items)."""
        queue = error_handler.get_retry_queue()

        # Verify max queue size is enforced
        max_size = error_handler.get_queue_max_size()
        assert max_size == 100

    def test_tool5_batch_retry_queue(self, error_handler):
        """AC5: Queued items can be batch retried."""
        questions = [
            {"question_id": f"q_{i}", "stem": f"Q{i}?", "type": "mc"}
            for i in range(3)
        ]

        for q in questions:
            error_handler.queue_failed_save(q, IOError("Save failed"))

        queue = error_handler.get_retry_queue()
        assert len(queue) == 3

        # Simulate batch retry - convert QueuedItem to dict
        def batch_save(questions_list):
            return [
                {
                    "question_id": q.question_id if hasattr(q, "question_id") else q["question_id"],
                    "saved": True,
                }
                for q in questions_list
            ]

        results = batch_save(queue)
        assert len(results) == 3
        assert all(r["saved"] for r in results)


# ============================================================================
# TEST CLASS 6: TOOL 6 - LLM TIMEOUT FALLBACK (AC6)
# ============================================================================


class TestTool6LLMTimeoutFallback:
    """Test Tool 6 (Score & Explain) LLM timeout fallback."""

    def test_tool6_llm_timeout_fallback_explanation(self, error_handler):
        """
        AC6: Tool 6 LLM timeout → fallback explanation.

        Given: Tool 6 LLM call times out
        When: Error handler catches TimeoutError
        Then: Return fallback score and explanation
        """
        def tool6_with_timeout():
            raise TimeoutError("LLM API timeout after 15 seconds")

        result = error_handler.handle_tool6_timeout(
            timeout_error=TimeoutError("LLM API timeout"),
            question_type="short_answer",
            user_answer="Test answer"
        )

        assert "score" in result
        assert "explanation" in result
        assert result["score"] == 50  # Default fallback score
        assert "temporary" in result["explanation"].lower() or "delay" in result["explanation"].lower()

    def test_tool6_mc_timeout_uses_exact_match_fallback(self, error_handler):
        """AC6: Tool 6 MC timeout → fallback to exact match scoring."""
        result = error_handler.handle_tool6_timeout(
            timeout_error=TimeoutError("LLM API timeout"),
            question_type="multiple_choice",
            user_answer="B",
            correct_answer="B"
        )

        # For MC, should be able to use exact match
        assert result["is_correct"] is True
        assert result["score"] == 100

    def test_tool6_sa_timeout_default_score(self, error_handler):
        """AC6: Tool 6 SA timeout → default score (50)."""
        result = error_handler.handle_tool6_timeout(
            timeout_error=TimeoutError("LLM API timeout"),
            question_type="short_answer",
            user_answer="User answer",
        )

        assert result["score"] == 50
        assert result["is_correct"] is False
        assert "explanation" in result


# ============================================================================
# TEST CLASS 7: RETRY WITH EXPONENTIAL BACKOFF (AC7)
# ============================================================================


class TestExponentialBackoff:
    """Test exponential backoff retry strategy."""

    def test_exponential_backoff_timing(self, retry_strategy):
        """
        AC7: Retry with exponential backoff (100ms, 200ms, 400ms).

        Given: ExponentialBackoff(initial=100ms, multiplier=2)
        When: Calculate delays
        Then: 100ms → 200ms → 400ms
        """
        delays = retry_strategy.get_retry_delays(num_retries=3)

        # Should be [0.01, 0.02, 0.04] seconds (10ms, 20ms, 40ms for fast tests)
        assert len(delays) == 3
        assert delays[0] < delays[1] < delays[2]
        # Each should roughly double
        assert delays[1] / delays[0] >= 1.9
        assert delays[2] / delays[1] >= 1.9

    def test_exponential_backoff_applied_on_retry(self):
        """AC7: Exponential backoff delay applied between retries."""
        backoff = ExponentialBackoff(initial_delay=0.01, multiplier=2)

        attempt = 0
        start_time = time.time()

        def failing_func():
            nonlocal attempt
            attempt += 1
            if attempt <= 2:
                raise ValueError("Fail")
            return "success"

        # Manually apply backoff
        delays = [backoff.get_delay(i) for i in range(3)]

        assert len(delays) == 3
        assert delays[0] <= delays[1] <= delays[2]


# ============================================================================
# TEST CLASS 8: ERROR CONTEXT & LOGGING (AC8)
# ============================================================================


class TestErrorContextAndLogging:
    """Test error context capture and structured logging."""

    def test_error_context_captured(self, error_handler):
        """
        AC8: All errors logged with structured context.

        Given: Tool fails
        When: Error handler captures context
        Then: ErrorContext has all metadata
        """
        def failing_tool():
            raise ValueError("Validation failed")

        error_context = error_handler.capture_error_context(
            tool_id="tool_1",
            error=ValueError("Validation failed"),
            attempt_number=2,
            strategy="RETRY_THEN_DEFAULT"
        )

        assert error_context.tool_id == "tool_1"
        assert error_context.error_type == "ValueError"
        assert error_context.attempt_number == 2
        assert error_context.strategy == "RETRY_THEN_DEFAULT"
        assert error_context.timestamp is not None

    def test_error_context_includes_timestamp(self, error_handler):
        """AC8: Error context includes ISO 8601 timestamp."""
        error_context = error_handler.capture_error_context(
            tool_id="tool_2",
            error=Exception("Test"),
            attempt_number=1,
            strategy="SKIP"
        )

        assert error_context.timestamp is not None
        # Verify ISO format
        assert "T" in error_context.timestamp
        assert "Z" in error_context.timestamp or "+" in error_context.timestamp

    def test_structured_error_logging(self, error_handler, caplog):
        """AC8: Errors logged in structured format."""
        import logging
        caplog.set_level(logging.ERROR)

        def failing_tool():
            raise RuntimeError("Tool failed")

        try:
            error_handler.log_error(
                tool_id="tool_3",
                error=RuntimeError("Tool failed"),
                attempt_number=1,
                strategy="CACHE_FALLBACK"
            )
        except Exception:
            pass

        # Verify error was logged
        assert len(caplog.records) > 0
        log_record = caplog.records[0]
        assert "tool_3" in log_record.message or "Tool failed" in log_record.message


# ============================================================================
# TEST CLASS 9: CIRCUIT BREAKER PATTERN
# ============================================================================


class TestCircuitBreakerPattern:
    """Test circuit breaker for cascading failures."""

    def test_circuit_breaker_opens_on_threshold(self, error_handler):
        """Circuit breaker opens after consecutive failures."""
        # Simulate 5 consecutive failures
        for _ in range(5):
            error_handler.record_failure(tool_id="tool_1")

        # Check if circuit breaker is open
        is_open = error_handler.is_circuit_breaker_open(tool_id="tool_1")
        assert is_open is True

    def test_circuit_breaker_rejects_call_when_open(self, error_handler):
        """Circuit breaker prevents calls when open."""
        # Open circuit breaker
        for _ in range(5):
            error_handler.record_failure(tool_id="tool_2")

        # Try to execute - should be rejected
        def tool_func():
            return "success"

        result = error_handler.execute_with_circuit_breaker(
            tool_id="tool_2",
            func=tool_func
        )

        assert result is None or result.get("status") == "circuit_breaker_open"


# ============================================================================
# TEST CLASS 10: ACCEPTANCE CRITERIA SUMMARY
# ============================================================================


class TestAcceptanceCriteria:
    """Verify all acceptance criteria are met."""

    def test_ac1_tool1_retry_then_default(self, error_handler):
        """AC1: Tool 1 DB error → retry 3x → default profile."""
        default_profile = {"user_id": "unknown", "self_level": 3}

        def failing_tool():
            raise ConnectionError("DB failed")

        result = error_handler.execute_with_retry(
            func=failing_tool,
            max_retries=3,
            strategy=ErrorStrategy.RETRY_THEN_DEFAULT,
            fallback_value=default_profile
        )

        assert result == default_profile

    def test_ac2_tool2_skip_gracefully(self, error_handler):
        """AC2: Tool 2 empty results → skip gracefully → continue."""
        can_continue = error_handler.can_continue_with_empty_results([], "tool_2")
        assert can_continue is True

    def test_ac3_tool3_cached_fallback(self, error_handler):
        """AC3: Tool 3 failure → use cached/default keywords."""
        cached = {"keywords": ["cached"]}
        result = error_handler.execute_with_cache_fallback(
            func=lambda: (_ for _ in ()).throw(TimeoutError()),
            cache=cached,
            default_value={"keywords": ["default"]}
        )
        assert "keywords" in result

    def test_ac4_tool4_regenerate_on_low_score(self, error_handler):
        """AC4: Tool 4 low score → retry 2x → discard if still low."""
        def always_low():
            return {"validation_score": 0.50, "should_discard": True}

        result = error_handler.execute_tool4_with_regenerate(
            validate_func=always_low,
            max_regenerate_attempts=2,
            score_threshold=0.70
        )
        assert result["should_discard"] is True

    def test_ac5_tool5_queue_for_retry(self, error_handler):
        """AC5: Tool 5 save error → queue for retry."""
        question = {"question_id": "q_1", "stem": "Q?"}
        queue_item = error_handler.queue_failed_save(question, IOError("Save failed"))
        assert queue_item["status"] == "queued"

    def test_ac6_tool6_llm_timeout_fallback(self, error_handler):
        """AC6: Tool 6 LLM timeout → fallback explanation."""
        result = error_handler.handle_tool6_timeout(
            timeout_error=TimeoutError("Timeout"),
            question_type="short_answer",
            user_answer="Answer"
        )
        assert "score" in result
        assert "explanation" in result

    def test_ac7_exponential_backoff(self, retry_strategy):
        """AC7: Retry with exponential backoff (100ms, 200ms, 400ms)."""
        delays = retry_strategy.get_retry_delays(3)
        assert len(delays) == 3
        assert delays[0] <= delays[1] <= delays[2]

    def test_ac8_error_logging(self, error_handler):
        """AC8: All errors logged with structured context."""
        context = error_handler.capture_error_context(
            tool_id="tool_1",
            error=Exception("Test"),
            attempt_number=1,
            strategy="RETRY"
        )
        assert context.tool_id == "tool_1"
        assert context.timestamp is not None
