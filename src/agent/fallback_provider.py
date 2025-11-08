"""
Fallback data provider for error recovery.

REQ: REQ-A-ErrorHandling

Provides default values when tools fail:
- Default user profiles
- Default keywords
- Default scoring results
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class FallbackProvider:
    """Provides fallback/default values for tool failures."""

    # ========================================================================
    # TOOL 1: DEFAULT USER PROFILE
    # ========================================================================

    @staticmethod
    def get_default_user_profile() -> dict[str, Any]:
        """
        Get default user profile for Tool 1 failure.

        Returns:
            Default profile with conservative settings

        """
        return {
            "user_id": "unknown",
            "self_level": 3,  # Intermediate
            "years_experience": 0,
            "job_role": "unknown",
            "duty": "unknown",
            "interests": [],
            "previous_score": 50,
        }

    # ========================================================================
    # TOOL 2: EMPTY TEMPLATES
    # ========================================================================

    @staticmethod
    def get_default_templates() -> list[dict[str, Any]]:
        """
        Get default templates for Tool 2 failure.

        Returns:
            Empty list (skip to next tool)

        """
        return []

    # ========================================================================
    # TOOL 3: DEFAULT KEYWORDS
    # ========================================================================

    @staticmethod
    def get_default_keywords() -> dict[str, Any]:
        """
        Get default difficulty keywords for Tool 3 failure.

        Returns:
            Generic keywords that work for any question type

        """
        return {
            "keywords": [
                "basics",
                "fundamentals",
                "application",
                "analysis",
                "synthesis",
            ],
            "concepts": [
                "definition",
                "explanation",
                "example",
                "practice",
            ],
            "example_questions": [
                "What are the key concepts?",
                "How are these applied?",
                "What is the significance?",
            ],
        }

    # ========================================================================
    # TOOL 4: DISCARD LOGIC
    # ========================================================================

    @staticmethod
    def should_discard_low_score(validation_score: float, threshold: float = 0.70) -> bool:
        """
        Determine if question should be discarded.

        Args:
            validation_score: Validation score (0-1)
            threshold: Discard threshold (default 0.70)

        Returns:
            True if should discard

        """
        return validation_score < threshold

    # ========================================================================
    # TOOL 5: QUEUE MANAGEMENT
    # ========================================================================

    @staticmethod
    def get_queue_max_size() -> int:
        """
        Get maximum retry queue size.

        Returns:
            Max queue size (100 items)

        """
        return 100

    @staticmethod
    def create_queue_item(
        question_id: str,
        stem: str,
        question_type: str,
        error_message: str = "",
    ) -> dict[str, Any]:
        """
        Create queued item for retry.

        Args:
            question_id: Question ID
            stem: Question text
            question_type: Question type
            error_message: Save error message

        Returns:
            Queue item dict

        """
        return {
            "question_id": question_id,
            "stem": stem,
            "type": question_type,
            "status": "queued",
            "error": error_message,
        }

    # ========================================================================
    # TOOL 6: FALLBACK SCORING
    # ========================================================================

    @staticmethod
    def get_default_score_result(
        question_type: str,
        user_answer: str = "",
        correct_answer: str = "",
    ) -> dict[str, Any]:
        """
        Get default scoring result for Tool 6 timeout.

        Args:
            question_type: Type of question
            user_answer: User's response
            correct_answer: Correct answer (for MC/OX)

        Returns:
            Default score result

        """
        if question_type in {"multiple_choice", "true_false"}:
            # MC/OX: Exact match if possible
            is_correct = user_answer.strip().upper() == correct_answer.strip().upper() if correct_answer else False
            score = 100 if is_correct else 0
        else:
            # SA: Default to middle score
            is_correct = False
            score = 50

        return {
            "score": score,
            "is_correct": is_correct,
            "explanation": ("The system experienced a temporary delay. Please review the key concepts."),
            "feedback": "Service temporarily unavailable.",
        }

    @staticmethod
    def get_default_explanation() -> str:
        """
        Get default explanation for timeout.

        Returns:
            Generic explanation text

        """
        return (
            "The system experienced a temporary delay in generating "
            "a detailed explanation. Please review the key concepts "
            "to improve your understanding."
        )
