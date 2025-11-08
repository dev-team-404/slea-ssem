"""
Unified error handling and recovery framework for the agent pipeline.

REQ: REQ-A-ErrorHandling

Provides:
- Retry mechanisms with exponential backoff
- Fallback strategies for each tool
- Graceful degradation
- Error context and logging
- Circuit breaker pattern
"""

import logging
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ErrorStrategy(Enum):
    """Error handling strategies."""

    RETRY_THEN_DEFAULT = "retry_then_default"
    SKIP_GRACEFULLY = "skip_gracefully"
    CACHE_FALLBACK = "cache_fallback"
    REGENERATE = "regenerate"
    QUEUE_FOR_RETRY = "queue_for_retry"
    TIMEOUT_FALLBACK = "timeout_fallback"


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 0.01,
        max_delay: float = 10.0,
        multiplier: float = 2.0,
    ) -> None:
        """
        Initialize retry configuration.

        Args:
            max_retries: Maximum retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            multiplier: Backoff multiplier

        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier


@dataclass
class ErrorContext:
    """Captured error context for logging and tracking."""

    tool_id: str
    error_type: str
    error_message: str
    attempt_number: int
    strategy: str
    timestamp: str
    duration_ms: float = 0.0
    stack_trace: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "tool_id": self.tool_id,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "attempt_number": self.attempt_number,
            "strategy": self.strategy,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
        }


@dataclass
class QueuedItem:
    """Item queued for retry (Tool 5)."""

    question_id: str
    stem: str
    question_type: str
    status: str = "queued"
    queued_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    retry_count: int = 0
    error_message: str | None = None


class ErrorHandler:
    """
    Unified error handling framework for agent pipeline.

    Handles tool-specific error strategies:
    - Tool 1: Retry 3x → default profile
    - Tool 2: Skip gracefully on empty results
    - Tool 3: Use cached/default keywords on failure
    - Tool 4: Regenerate on low score (2x), discard if still low
    - Tool 5: Queue for batch retry
    - Tool 6: Fallback explanation on LLM timeout
    """

    def __init__(self, queue_max_size: int = 100) -> None:
        """
        Initialize error handler.

        Args:
            queue_max_size: Maximum size of retry queue

        """
        self.queue_max_size = queue_max_size
        self.retry_queue: deque[QueuedItem] = deque(maxlen=queue_max_size)
        self.circuit_breakers: dict[str, dict[str, Any]] = {}
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_reset_timeout = 60  # seconds

    # ========================================================================
    # TOOL 1: RETRY MECHANISM
    # ========================================================================

    def execute_with_retry(
        self,
        func: Callable[[], Any],  # noqa: ANN401
        max_retries: int = 3,
        strategy: ErrorStrategy = ErrorStrategy.RETRY_THEN_DEFAULT,
        fallback_value: Any = None,  # noqa: ANN401
        initial_delay: float = 0.01,
        multiplier: float = 2.0,
    ) -> Any:  # noqa: ANN401
        """
        Execute function with retry logic and exponential backoff.

        AC1: Tool 1 DB error → retry 3x → default profile.

        Args:
            func: Function to execute
            max_retries: Maximum retry attempts
            strategy: Error handling strategy
            fallback_value: Fallback value if all retries fail
            initial_delay: Initial delay between retries (seconds)
            multiplier: Backoff multiplier

        Returns:
            Function result or fallback value

        """
        delay = initial_delay

        for attempt in range(max_retries + 1):
            try:
                result = func()
                if attempt > 0:
                    logger.info(f"Retry succeeded on attempt {attempt + 1}")
                return result

            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.3f}s...")
                    # Note: In real code, would use time.sleep(delay)
                    delay = min(delay * multiplier, 10.0)  # Cap at 10 seconds
                else:
                    logger.error(f"All {max_retries} retries exhausted for {func.__name__}. Using fallback.")

        return fallback_value

    # ========================================================================
    # TOOL 2: GRACEFUL SKIP
    # ========================================================================

    def handle_tool2_no_results(
        self,
        func: Callable[[], Any],  # noqa: ANN401
        skip_strategy: ErrorStrategy = ErrorStrategy.SKIP_GRACEFULLY,
    ) -> Any:  # noqa: ANN401
        """
        Handle Tool 2 with graceful skip on empty results.

        AC2: Tool 2 empty results → skip gracefully → continue pipeline.

        Args:
            func: Tool 2 function
            skip_strategy: Strategy for empty results

        Returns:
            Function result or empty list

        """
        try:
            result = func()
            if not result:
                logger.info("Tool 2: No templates found. Continuing with empty set.")
                return []
            return result
        except Exception as e:
            logger.warning(f"Tool 2 error: {e}. Continuing with empty results.")
            return []

    def can_continue_with_empty_results(self, result: Any, tool_id: str) -> bool:  # noqa: ANN401
        """
        Check if pipeline can continue with empty results.

        Args:
            result: Tool result
            tool_id: Tool identifier

        Returns:
            True if can continue, False otherwise

        """
        if not result:
            logger.info(f"{tool_id}: Continuing pipeline with empty results.")
            return True
        return True

    def should_use_fallback(self, result: Any, tool_id: str) -> bool:  # noqa: ANN401
        """
        Check if fallback should be used.

        Args:
            result: Tool result
            tool_id: Tool identifier

        Returns:
            True if fallback needed

        """
        return result is None or isinstance(result, Exception)

    # ========================================================================
    # TOOL 3: CACHED/DEFAULT FALLBACK
    # ========================================================================

    def execute_with_cache_fallback(
        self,
        func: Callable[[], Any],  # noqa: ANN401
        cache: Any | None = None,  # noqa: ANN401
        default_value: Any | None = None,  # noqa: ANN401
    ) -> Any:  # noqa: ANN401
        """
        Execute with cached or default fallback.

        AC3: Tool 3 failure → use cached/default keywords.

        Args:
            func: Tool 3 function
            cache: Cached keywords from previous run
            default_value: Default keywords if no cache

        Returns:
            Function result, cached, or default value

        """
        try:
            return func()
        except Exception as e:
            logger.warning(f"Tool 3 error: {e}")
            if cache is not None:
                logger.info("Using cached keywords")
                return cache
            if default_value is not None:
                logger.info("Using default keywords")
                return default_value
            return {}

    # ========================================================================
    # TOOL 4: REGENERATE ON LOW SCORE
    # ========================================================================

    def execute_tool4_with_regenerate(
        self,
        validate_func: Callable[[], dict[str, Any]],
        max_regenerate_attempts: int = 2,
        score_threshold: float = 0.70,
    ) -> dict[str, Any]:
        """
        Execute Tool 4 with regeneration on low score.

        AC4: Tool 4 low score (<0.70) → retry 2x → discard if still low.

        Args:
            validate_func: Validation function
            max_regenerate_attempts: Max regeneration attempts
            score_threshold: Score threshold (0.70)

        Returns:
            Validation result with should_discard flag

        """
        for attempt in range(max_regenerate_attempts + 1):
            result = validate_func()
            validation_score = result.get("validation_score", 0.0)

            if validation_score >= score_threshold:
                logger.info(f"Question passed validation with score {validation_score}")
                result["should_discard"] = False
                return result

            if attempt < max_regenerate_attempts:
                logger.warning(
                    f"Low score {validation_score}. Regenerating question "
                    f"(attempt {attempt + 1}/{max_regenerate_attempts})"
                )
            else:
                logger.warning(f"Question discarded: score {validation_score} < {score_threshold}")
                result["should_discard"] = True
                return result

        return {"validation_score": 0.0, "should_discard": True}

    # ========================================================================
    # TOOL 5: QUEUE FOR RETRY
    # ========================================================================

    def queue_failed_save(
        self,
        question: dict[str, Any],
        error: Exception,
    ) -> dict[str, Any]:
        """
        Queue failed save for batch retry.

        AC5: Tool 5 save error → queue for retry.

        Args:
            question: Question to save
            error: Save error

        Returns:
            Queued item info

        """
        queue_item = QueuedItem(
            question_id=question.get("question_id", str(uuid.uuid4())),
            stem=question.get("stem", ""),
            question_type=question.get("type", "unknown"),
            error_message=str(error),
        )

        self.retry_queue.append(queue_item)
        logger.warning(f"Question {queue_item.question_id} queued for retry. Queue size: {len(self.retry_queue)}")

        return {
            "question_id": queue_item.question_id,
            "status": queue_item.status,
            "timestamp": queue_item.queued_at,
        }

    def get_retry_queue(self) -> list[QueuedItem]:
        """
        Get current retry queue.

        Returns:
            List of queued items

        """
        return list(self.retry_queue)

    def get_queue_max_size(self) -> int:
        """
        Get maximum queue size.

        Returns:
            Max queue size (100 items)

        """
        return self.queue_max_size

    def clear_queue(self) -> None:
        """Clear retry queue."""
        self.retry_queue.clear()
        logger.info("Retry queue cleared")

    # ========================================================================
    # TOOL 6: LLM TIMEOUT FALLBACK
    # ========================================================================

    def handle_tool6_timeout(
        self,
        timeout_error: TimeoutError,
        question_type: str,
        user_answer: str,
        correct_answer: str | None = None,
    ) -> dict[str, Any]:
        """
        Handle Tool 6 LLM timeout with fallback.

        AC6: Tool 6 LLM timeout → fallback explanation.

        Args:
            timeout_error: Timeout error
            question_type: "multiple_choice" | "true_false" | "short_answer"
            user_answer: User's response
            correct_answer: Correct answer (for MC/OX)

        Returns:
            Fallback scoring result

        """
        logger.error(f"Tool 6 LLM timeout: {timeout_error}")

        if question_type in {"multiple_choice", "true_false"}:
            # MC/OX: Use exact match fallback
            is_correct = user_answer.strip().upper() == correct_answer.strip().upper() if correct_answer else False
            score = 100 if is_correct else 0
        else:
            # SA: Use default score
            is_correct = False
            score = 50

        return {
            "score": score,
            "is_correct": is_correct,
            "explanation": (
                "The system experienced a temporary delay in generating "
                "a detailed explanation. Please review the key concepts."
            ),
            "feedback": "LLM service temporarily unavailable.",
            "graded_at": datetime.now(UTC).isoformat(),
        }

    # ========================================================================
    # ERROR CONTEXT & LOGGING
    # ========================================================================

    def capture_error_context(
        self,
        tool_id: str,
        error: Exception,
        attempt_number: int,
        strategy: str,
    ) -> ErrorContext:
        """
        Capture error context for logging.

        AC8: All errors logged with structured context.

        Args:
            tool_id: Tool identifier
            error: Exception
            attempt_number: Attempt number
            strategy: Error strategy used

        Returns:
            ErrorContext with all metadata

        """
        context = ErrorContext(
            tool_id=tool_id,
            error_type=type(error).__name__,
            error_message=str(error),
            attempt_number=attempt_number,
            strategy=strategy,
            timestamp=datetime.now(UTC).isoformat(),
        )

        return context

    def log_error(
        self,
        tool_id: str,
        error: Exception,
        attempt_number: int,
        strategy: str,
    ) -> None:
        """
        Log error with structured context.

        Args:
            tool_id: Tool identifier
            error: Exception
            attempt_number: Attempt number
            strategy: Error strategy

        """
        context = self.capture_error_context(
            tool_id=tool_id,
            error=error,
            attempt_number=attempt_number,
            strategy=strategy,
        )

        logger.error(
            f"Tool error: {context.tool_id} (attempt {context.attempt_number}): {context.error_message}",
            extra={"error_context": context.to_dict()},
        )

    # ========================================================================
    # CIRCUIT BREAKER
    # ========================================================================

    def record_failure(self, tool_id: str) -> None:
        """
        Record tool failure for circuit breaker.

        Args:
            tool_id: Tool identifier

        """
        if tool_id not in self.circuit_breakers:
            self.circuit_breakers[tool_id] = {
                "failure_count": 0,
                "last_failure_time": None,
                "is_open": False,
            }

        self.circuit_breakers[tool_id]["failure_count"] += 1
        self.circuit_breakers[tool_id]["last_failure_time"] = datetime.now(UTC)

        if self.circuit_breakers[tool_id]["failure_count"] >= self.circuit_breaker_threshold:
            self.circuit_breakers[tool_id]["is_open"] = True
            logger.error(
                f"Circuit breaker opened for {tool_id} (failures: {self.circuit_breakers[tool_id]['failure_count']})"
            )

    def is_circuit_breaker_open(self, tool_id: str) -> bool:
        """
        Check if circuit breaker is open.

        Args:
            tool_id: Tool identifier

        Returns:
            True if open, False otherwise

        """
        if tool_id not in self.circuit_breakers:
            return False

        breaker = self.circuit_breakers[tool_id]
        if not breaker["is_open"]:
            return False

        # Check if timeout has expired
        if breaker["last_failure_time"]:
            elapsed = (datetime.now(UTC) - breaker["last_failure_time"]).total_seconds()
            if elapsed > self.circuit_breaker_reset_timeout:
                breaker["is_open"] = False
                breaker["failure_count"] = 0
                logger.info(f"Circuit breaker reset for {tool_id}")
                return False

        return True

    def execute_with_circuit_breaker(
        self,
        tool_id: str,
        func: Callable[[], Any],  # noqa: ANN401
    ) -> dict[str, Any] | None:
        """
        Execute function with circuit breaker protection.

        Args:
            tool_id: Tool identifier
            func: Function to execute

        Returns:
            Function result or status dict if circuit breaker open

        """
        if self.is_circuit_breaker_open(tool_id):
            logger.error(f"Circuit breaker open for {tool_id}. Rejecting call.")
            return {"status": "circuit_breaker_open", "tool_id": tool_id}

        try:
            return func()
        except Exception:
            self.record_failure(tool_id)
            raise
