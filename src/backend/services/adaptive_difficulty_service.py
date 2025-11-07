"""
Adaptive difficulty service for calculating difficulty adjustments.

REQ: REQ-B-B2-Adapt
"""

from typing import Any

from sqlalchemy.orm import Session

from src.backend.models.test_result import TestResult


class AdaptiveDifficultyService:
    """
    Service for adaptive difficulty adjustment based on Round 1 performance.

    REQ: REQ-B-B2-Adapt-2, REQ-B-B2-Adapt-3

    Methods:
        get_difficulty_tier: Map score to difficulty adjustment tier
        calculate_round2_difficulty: Calculate Round 2 difficulty delta
        get_weak_categories: Extract weak categories from Round 1

    """

    def __init__(self, session: Session) -> None:
        """
        Initialize AdaptiveDifficultyService with database session.

        Args:
            session: SQLAlchemy database session

        """
        self.session = session

    def get_difficulty_tier(self, score: float) -> str:
        """
        Map Round 1 score to difficulty tier.

        REQ: REQ-B-B2-Adapt-2

        Tier mapping:
        - 0-40%: "low" (decrease or maintain)
        - 40-70%: "medium" (maintain or slight increase)
        - 70%+: "high" (increase)

        Args:
            score: Round 1 percentage score (0-100)

        Returns:
            Difficulty tier: "low", "medium", or "high"

        Raises:
            ValueError: If score is invalid (< 0 or > 100)

        """
        if not (0 <= score <= 100):
            raise ValueError(f"Invalid score: {score}. Must be between 0 and 100.")

        if score < 40:
            return "low"
        elif score < 70:
            return "medium"
        else:
            return "high"

    def calculate_round2_difficulty(self, round1_avg_difficulty: float, score: float) -> float:
        """
        Calculate adjusted difficulty for Round 2 based on Round 1 score and difficulty.

        REQ: REQ-B-B2-Adapt-2

        Adjustment rules:
        - Low tier (0-40%): avg_difficulty - 1 (or maintain if already low)
        - Medium tier (40-70%): avg_difficulty + 0.5 (slight increase)
        - High tier (70%+): avg_difficulty + 2 (increase)

        Args:
            round1_avg_difficulty: Average difficulty of Round 1 questions (1-10)
            score: Round 1 percentage score (0-100)

        Returns:
            Adjusted difficulty for Round 2 (float, clamped to 1-10 range)

        """
        tier = self.get_difficulty_tier(score)

        if tier == "low":
            # Decrease or maintain: subtract 1, but keep minimum 1
            adjusted = max(1.0, round1_avg_difficulty - 1.0)
        elif tier == "medium":
            # Slight increase
            adjusted = round1_avg_difficulty + 0.5
        else:  # tier == "high"
            # Increase difficulty
            adjusted = round1_avg_difficulty + 2.0

        # Clamp to valid difficulty range (1-10)
        return max(1.0, min(10.0, adjusted))

    def get_weak_categories(self, session_id: str, minimum_threshold: float = 0.0) -> dict[str, int]:
        """
        Get weak categories (categories with wrong answers) for adaptive selection.

        REQ: REQ-B-B2-Adapt-3

        Args:
            session_id: TestSession ID to look up Round 1 results
            minimum_threshold: Minimum wrong count to include (default 0 = all weak categories)

        Returns:
            Dictionary: {category -> wrong_count}
            Example: {"LLM": 1, "RAG": 2}
            Returns empty dict if no weak categories found

        Raises:
            ValueError: If Round 1 TestResult not found

        """
        result = self.session.query(TestResult).filter_by(session_id=session_id, round=1).first()

        if not result:
            raise ValueError(f"Round 1 result not found for session {session_id}")

        if not result.wrong_categories:
            return {}

        # Filter out categories below threshold
        filtered = {cat: count for cat, count in result.wrong_categories.items() if count > minimum_threshold}

        return filtered

    def should_prioritize_categories(self, wrong_categories: dict[str, int]) -> bool:
        """
        Determine if weak categories should be prioritized in Round 2.

        REQ: REQ-B-B2-Adapt-3

        Prioritize if user has any wrong answers.

        Args:
            wrong_categories: Dictionary of categories with wrong counts

        Returns:
            True if categories should be prioritized (user has weak areas)

        """
        return len(wrong_categories) > 0

    def get_category_priority_ratio(
        self, wrong_categories: dict[str, int], total_questions: int = 5
    ) -> dict[str, float]:
        """
        Calculate how many questions should be from weak categories.

        REQ: REQ-B-B2-Adapt-3 (≥50% from weak categories)

        For 5 total questions:
        - If 1 weak category with 2 wrong: allocate ≥3 questions (60%)
        - If 2 weak categories with 2+2 wrong: allocate ≥3 questions (60%) total

        Args:
            wrong_categories: Categories with wrong counts
            total_questions: Total questions in Round 2 (default 5)

        Returns:
            Dictionary: {category -> count} for how many questions to ask
            Example: {"LLM": 3, "RAG": 2}

        """
        if not wrong_categories:
            # No weak categories: use balanced distribution
            return {}

        # Calculate minimum questions needed to satisfy ≥50% from weak categories
        min_weak_questions = max(3, (total_questions + 1) // 2)  # Ensures ≥50%

        # Total weak categories
        total_weak_cats = len(wrong_categories)

        # Distribute weak questions fairly among weak categories
        allocation: dict[str, float] = {}
        remaining = min_weak_questions

        for idx, (cat, _count) in enumerate(wrong_categories.items()):
            # Give each weak category roughly equal share
            cats_left = total_weak_cats - idx
            questions_for_this_cat = remaining // cats_left
            allocation[cat] = questions_for_this_cat
            remaining -= questions_for_this_cat

        return allocation

    def get_adaptive_generation_params(self, session_id: str) -> dict[str, Any]:
        """
        Get all parameters needed for adaptive Round 2 question generation.

        REQ: REQ-B-B2-Adapt-1, 2, 3

        Args:
            session_id: TestSession ID

        Returns:
            Dictionary with:
                - difficulty_tier (str): "low", "medium", "high"
                - adjusted_difficulty (float): Target difficulty for Round 2
                - weak_categories (dict): Categories to prioritize
                - priority_ratio (dict): How many questions per category

        Raises:
            ValueError: If Round 1 result not found

        """
        result = self.session.query(TestResult).filter_by(session_id=session_id, round=1).first()

        if not result:
            raise ValueError(f"Round 1 result not found for session {session_id}")

        # Get Round 1 questions to calculate average difficulty
        # For now, we'll use a default since we need to calculate from Question records
        # In practice, you'd query actual Round 1 questions
        round1_avg_difficulty = 5.0  # Default: will be overridden in real implementation

        tier = self.get_difficulty_tier(result.score)
        adjusted_diff = self.calculate_round2_difficulty(round1_avg_difficulty, result.score)
        weak_cats = self.get_weak_categories(session_id)
        priority = self.get_category_priority_ratio(weak_cats)

        return {
            "difficulty_tier": tier,
            "adjusted_difficulty": adjusted_diff,
            "weak_categories": weak_cats,
            "priority_ratio": priority,
            "score": result.score,
            "correct_count": result.correct_count,
            "total_count": result.total_count,
        }
