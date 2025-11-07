"""
Scoring service for calculating test results and identifying weak areas.

REQ: REQ-B-B3-Score, REQ-B-B2-Adapt
"""

from sqlalchemy.orm import Session

from src.backend.models.attempt_answer import AttemptAnswer
from src.backend.models.question import Question
from src.backend.models.test_result import TestResult


class ScoringService:
    """
    Service for calculating scores and analyzing test performance.

    REQ: REQ-B-B3-Score, REQ-B-B2-Adapt

    Methods:
        calculate_round_score: Calculate score for completed round
        get_wrong_categories: Identify wrong answer categories

    """

    def __init__(self, session: Session) -> None:
        """
        Initialize ScoringService with database session.

        Args:
            session: SQLAlchemy database session

        """
        self.session = session

    def calculate_round_score(self, session_id: str, round_num: int) -> dict:
        """
        Calculate score for a completed test round.

        REQ: REQ-B-B3-Score-1, REQ-B-B3-Score-2

        Calculates total score from all attempt answers in session:
        - Multiple choice / True-False: exact match (1 point if correct, 0 if wrong)
        - Short answer: LLM-based (0-100 scale, stored in score field)

        Args:
            session_id: TestSession ID
            round_num: Round number (1, 2, or 3)

        Returns:
            Dictionary with:
                - score (float): Percentage score (0-100)
                - total_points (int): Total points earned
                - correct_count (int): Number of correct answers
                - total_count (int): Total questions
                - wrong_categories (dict): Category -> wrong count mapping

        """
        # Get all attempt answers for this session
        attempts = self.session.query(AttemptAnswer).filter_by(session_id=session_id).all()

        if not attempts:
            raise ValueError(f"No attempt answers found for session {session_id}")

        total_count = len(attempts)
        correct_count = sum(1 for a in attempts if a.is_correct)
        total_points = sum(a.score for a in attempts)

        # Calculate percentage score
        # For MC/TF: correct answers worth 100 points / total
        # For SA: partial points included in score field
        max_points = total_count * 100  # Each question worth 100 points max
        percentage_score = (total_points / max_points) * 100 if max_points > 0 else 0

        # Get wrong categories
        wrong_categories = self._get_wrong_categories(attempts)

        return {
            "score": round(percentage_score, 2),
            "total_points": int(total_points),
            "correct_count": correct_count,
            "total_count": total_count,
            "wrong_categories": wrong_categories,
        }

    def _get_wrong_categories(self, attempts: list[AttemptAnswer]) -> dict:
        """
        Identify categories where user got wrong answers.

        REQ: REQ-B-B2-Adapt-3

        Args:
            attempts: List of AttemptAnswer records

        Returns:
            Dictionary mapping category -> number of wrong answers
            Example: {"LLM": 1, "RAG": 2}

        """
        wrong_categories = {}

        for attempt in attempts:
            if not attempt.is_correct:
                # Get question to find category
                question = self.session.query(Question).filter_by(id=attempt.question_id).first()
                if question:
                    category = question.category
                    wrong_categories[category] = wrong_categories.get(category, 0) + 1

        return wrong_categories

    def save_round_result(self, session_id: str, round_num: int) -> TestResult:
        """
        Calculate and persist round result to database.

        Args:
            session_id: TestSession ID
            round_num: Round number

        Returns:
            TestResult record created

        """
        score_data = self.calculate_round_score(session_id, round_num)

        result = TestResult(
            session_id=session_id,
            round=round_num,
            score=score_data["score"],
            total_points=score_data["total_points"],
            correct_count=score_data["correct_count"],
            total_count=score_data["total_count"],
            wrong_categories=score_data["wrong_categories"],
        )

        self.session.add(result)
        self.session.commit()
        return result
