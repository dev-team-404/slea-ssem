"""
Tests for scoring service.

REQ: REQ-B-B3-Score, REQ-B-B2-Adapt
"""

import pytest
from sqlalchemy.orm import Session

from src.backend.models.attempt_answer import AttemptAnswer
from src.backend.models.test_session import TestSession
from src.backend.services.scoring_service import ScoringService


class TestScoreCalculation:
    """REQ-B-B3-Score: Calculate round score from attempt answers."""

    def test_calculate_round_score_all_correct(
        self,
        db_session: Session,
        test_session_round1_fixture: TestSession,
        attempt_answers_for_session: list[AttemptAnswer],
    ) -> None:
        """Calculate score when user gets all answers correct."""
        # Update attempt answers to all correct
        from src.backend.models.attempt_answer import AttemptAnswer

        answers = db_session.query(AttemptAnswer).filter_by(session_id=test_session_round1_fixture.id).all()

        for answer in answers:
            answer.is_correct = True
            answer.score = 100.0

        db_session.commit()

        service = ScoringService(db_session)
        score_data = service.calculate_round_score(test_session_round1_fixture.id, 1)

        assert score_data["score"] == 100.0
        assert score_data["correct_count"] == 5
        assert score_data["total_count"] == 5

    def test_calculate_round_score_partial_correct(
        self,
        db_session: Session,
        test_session_round1_fixture: TestSession,
        attempt_answers_for_session: list[AttemptAnswer],
    ) -> None:
        """Calculate score with some correct and some wrong answers."""
        service = ScoringService(db_session)
        score_data = service.calculate_round_score(test_session_round1_fixture.id, 1)

        # 1 correct out of 5 = 20%
        assert score_data["score"] == 20.0
        assert score_data["correct_count"] == 1
        assert score_data["total_count"] == 5

    def test_calculate_round_score_all_wrong(
        self,
        db_session: Session,
        test_session_round1_fixture: TestSession,
        attempt_answers_for_session: list[AttemptAnswer],
    ) -> None:
        """Calculate score when user gets all answers wrong."""
        from src.backend.models.attempt_answer import AttemptAnswer

        answers = db_session.query(AttemptAnswer).filter_by(session_id=test_session_round1_fixture.id).all()

        for answer in answers:
            answer.is_correct = False
            answer.score = 0.0

        db_session.commit()

        service = ScoringService(db_session)
        score_data = service.calculate_round_score(test_session_round1_fixture.id, 1)

        assert score_data["score"] == 0.0
        assert score_data["correct_count"] == 0
        assert score_data["total_count"] == 5

    def test_no_attempt_answers_raises_error(
        self, db_session: Session, test_session_round1_fixture: TestSession
    ) -> None:
        """Missing attempt answers raises ValueError."""
        service = ScoringService(db_session)

        with pytest.raises(ValueError, match="No attempt answers found"):
            service.calculate_round_score(test_session_round1_fixture.id, 1)


class TestWeakCategoryIdentification:
    """REQ-B-B2-Adapt-3: Identify weak categories from wrong answers."""

    def test_identify_single_weak_category(
        self,
        db_session: Session,
        test_session_round1_fixture: TestSession,
        attempt_answers_for_session: list[AttemptAnswer],
    ) -> None:
        """Identify single weak category from wrong answers."""
        service = ScoringService(db_session)
        score_data = service.calculate_round_score(test_session_round1_fixture.id, 1)

        # Expected: RAG (2 wrong), Robotics (1 wrong), LLM (1 wrong)
        wrong_cats = score_data["wrong_categories"]

        assert "RAG" in wrong_cats
        assert wrong_cats["RAG"] == 2

    def test_identify_multiple_weak_categories(
        self,
        db_session: Session,
        test_session_round1_fixture: TestSession,
        attempt_answers_for_session: list[AttemptAnswer],
    ) -> None:
        """Identify multiple weak categories."""
        service = ScoringService(db_session)
        score_data = service.calculate_round_score(test_session_round1_fixture.id, 1)

        wrong_cats = score_data["wrong_categories"]

        # Should have multiple weak categories
        assert len(wrong_cats) > 1
        assert "RAG" in wrong_cats
        assert "Robotics" in wrong_cats or "LLM" in wrong_cats

    def test_no_wrong_answers_no_weak_categories(
        self,
        db_session: Session,
        test_session_round1_fixture: TestSession,
        attempt_answers_for_session: list[AttemptAnswer],
    ) -> None:
        """No weak categories when all answers correct."""
        from src.backend.models.attempt_answer import AttemptAnswer

        answers = db_session.query(AttemptAnswer).filter_by(session_id=test_session_round1_fixture.id).all()

        for answer in answers:
            answer.is_correct = True

        db_session.commit()

        service = ScoringService(db_session)
        score_data = service.calculate_round_score(test_session_round1_fixture.id, 1)

        assert score_data["wrong_categories"] == {}


class TestSaveRoundResult:
    """Save calculated result to database as TestResult record."""

    def test_save_round_result_creates_record(
        self,
        db_session: Session,
        test_session_round1_fixture: TestSession,
        attempt_answers_for_session: list[AttemptAnswer],
    ) -> None:
        """Saving round result creates TestResult record in DB."""
        service = ScoringService(db_session)
        result = service.save_round_result(test_session_round1_fixture.id, 1)

        assert result is not None
        assert result.session_id == test_session_round1_fixture.id
        assert result.round == 1
        assert result.score == 20.0

    def test_saved_result_queryable(
        self,
        db_session: Session,
        test_session_round1_fixture: TestSession,
        attempt_answers_for_session: list[AttemptAnswer],
    ) -> None:
        """Saved result can be queried from database."""
        from src.backend.models.test_result import TestResult

        service = ScoringService(db_session)
        service.save_round_result(test_session_round1_fixture.id, 1)

        # Query from DB
        retrieved = db_session.query(TestResult).filter_by(session_id=test_session_round1_fixture.id, round=1).first()

        assert retrieved is not None
        assert retrieved.score == 20.0
        assert retrieved.correct_count == 1
        assert "RAG" in retrieved.wrong_categories
