"""
Tests for autosave service.

REQ: REQ-B-B2-Plus
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from src.backend.models.attempt_answer import AttemptAnswer
from src.backend.models.question import Question
from src.backend.models.test_session import TestSession
from src.backend.services.autosave_service import AutosaveService


class TestSaveAnswer:
    """REQ-B-B2-Plus-1: Auto-save individual answer in real-time."""

    def test_save_single_answer_success(self, db_session: Session, test_session_in_progress: TestSession) -> None:
        """Save single answer successfully creates AttemptAnswer record."""
        service = AutosaveService(db_session)

        # Create a question
        question = Question(
            session_id=test_session_in_progress.id,
            item_type="multiple_choice",
            stem="Test question",
            choices=["A", "B", "C", "D"],
            answer_schema={"correct_key": "A", "explanation": "Test"},
            difficulty=5,
            category="LLM",
            round=1,
        )
        db_session.add(question)
        db_session.commit()

        # Save answer
        answer = service.save_answer(
            session_id=test_session_in_progress.id,
            question_id=question.id,
            user_answer={"selected_key": "B"},
            response_time_ms=5000,
        )

        assert answer.session_id == test_session_in_progress.id
        assert answer.question_id == question.id
        assert answer.user_answer == {"selected_key": "B"}
        assert answer.response_time_ms == 5000
        assert answer.saved_at is not None

    def test_save_sets_started_at_on_first_answer(
        self, db_session: Session, test_session_in_progress: TestSession
    ) -> None:
        """First answer saves sets started_at timestamp."""
        service = AutosaveService(db_session)

        # Ensure started_at is None initially
        test_session_in_progress.started_at = None
        db_session.commit()

        # Create question
        question = Question(
            session_id=test_session_in_progress.id,
            item_type="multiple_choice",
            stem="Test",
            choices=["A", "B"],
            answer_schema={"correct_key": "A", "explanation": "Test"},
            difficulty=5,
            category="LLM",
            round=1,
        )
        db_session.add(question)
        db_session.commit()

        # Save answer
        service.save_answer(
            session_id=test_session_in_progress.id,
            question_id=question.id,
            user_answer={"selected_key": "A"},
            response_time_ms=3000,
        )

        # Refresh session
        db_session.refresh(test_session_in_progress)
        assert test_session_in_progress.started_at is not None

    def test_idempotent_save_updates_existing(self, db_session: Session, test_session_in_progress: TestSession) -> None:
        """Saving same answer twice updates existing record."""
        service = AutosaveService(db_session)

        question = Question(
            session_id=test_session_in_progress.id,
            item_type="multiple_choice",
            stem="Test",
            choices=["A", "B"],
            answer_schema={"correct_key": "A", "explanation": "Test"},
            difficulty=5,
            category="LLM",
            round=1,
        )
        db_session.add(question)
        db_session.commit()

        # First save
        answer1 = service.save_answer(
            session_id=test_session_in_progress.id,
            question_id=question.id,
            user_answer={"selected_key": "A"},
            response_time_ms=3000,
        )

        # Second save (update)
        answer2 = service.save_answer(
            session_id=test_session_in_progress.id,
            question_id=question.id,
            user_answer={"selected_key": "B"},  # Changed answer
            response_time_ms=5000,
        )

        # Same ID (updated, not created)
        assert answer1.id == answer2.id
        assert answer2.user_answer == {"selected_key": "B"}
        assert answer2.response_time_ms == 5000

        # Only one record in DB
        count = db_session.query(AttemptAnswer).filter_by(session_id=test_session_in_progress.id).count()
        assert count == 1

    def test_save_invalid_session_raises_error(self, db_session: Session) -> None:
        """Saving to non-existent session raises ValueError."""
        service = AutosaveService(db_session)

        with pytest.raises(ValueError, match="not found"):
            service.save_answer(
                session_id="invalid_session_id",
                question_id="q1",
                user_answer={"text": "answer"},
                response_time_ms=1000,
            )

    def test_save_invalid_question_raises_error(
        self, db_session: Session, test_session_in_progress: TestSession
    ) -> None:
        """Saving to non-existent question raises ValueError."""
        service = AutosaveService(db_session)

        with pytest.raises(ValueError, match="not found"):
            service.save_answer(
                session_id=test_session_in_progress.id,
                question_id="invalid_question_id",
                user_answer={"text": "answer"},
                response_time_ms=1000,
            )

    def test_save_to_completed_session_raises_error(
        self, db_session: Session, test_session_in_progress: TestSession
    ) -> None:
        """Cannot save to completed session."""
        service = AutosaveService(db_session)

        # Mark session as completed
        test_session_in_progress.status = "completed"
        db_session.commit()

        question = Question(
            session_id=test_session_in_progress.id,
            item_type="multiple_choice",
            stem="Test",
            choices=["A", "B"],
            answer_schema={"correct_key": "A", "explanation": "Test"},
            difficulty=5,
            category="LLM",
            round=1,
        )
        db_session.add(question)
        db_session.commit()

        with pytest.raises(ValueError, match="already completed"):
            service.save_answer(
                session_id=test_session_in_progress.id,
                question_id=question.id,
                user_answer={"selected_key": "A"},
                response_time_ms=1000,
            )


class TestTimeLimitCheck:
    """REQ-B-B2-Plus-2: Check if session exceeded time limit."""

    def test_check_time_limit_not_exceeded(self, db_session: Session, test_session_in_progress: TestSession) -> None:
        """Time limit not exceeded when within 20 minutes."""
        service = AutosaveService(db_session)

        # Set started_at to 10 minutes ago
        test_session_in_progress.started_at = datetime.now(UTC) - timedelta(minutes=10)
        test_session_in_progress.time_limit_ms = 1200000  # 20 minutes
        db_session.commit()

        result = service.check_time_limit(test_session_in_progress.id)

        assert result["exceeded"] is False
        assert result["elapsed_ms"] < 1200000
        assert result["remaining_ms"] > 0

    def test_check_time_limit_exceeded(self, db_session: Session, test_session_in_progress: TestSession) -> None:
        """Time limit exceeded after 20 minutes."""
        service = AutosaveService(db_session)

        # Set started_at to 21 minutes ago
        test_session_in_progress.started_at = datetime.now(UTC) - timedelta(minutes=21)
        test_session_in_progress.time_limit_ms = 1200000  # 20 minutes
        db_session.commit()

        result = service.check_time_limit(test_session_in_progress.id)

        assert result["exceeded"] is True
        assert result["elapsed_ms"] > 1200000
        assert result["remaining_ms"] == 0

    def test_check_time_limit_not_started(self, db_session: Session, test_session_in_progress: TestSession) -> None:
        """Time limit check when session not started yet."""
        service = AutosaveService(db_session)

        # Ensure started_at is None
        test_session_in_progress.started_at = None
        test_session_in_progress.time_limit_ms = 1200000
        db_session.commit()

        result = service.check_time_limit(test_session_in_progress.id)

        assert result["exceeded"] is False
        assert result["elapsed_ms"] == 0
        assert result["remaining_ms"] == 1200000


class TestPauseSession:
    """REQ-B-B2-Plus-2: Pause session on timeout."""

    def test_pause_session_success(self, db_session: Session, test_session_in_progress: TestSession) -> None:
        """Pause session successfully updates status."""
        service = AutosaveService(db_session)

        paused = service.pause_session(test_session_in_progress.id, reason="time_limit")

        assert paused.status == "paused"
        assert paused.paused_at is not None

    def test_pause_completed_session_raises_error(
        self, db_session: Session, test_session_in_progress: TestSession
    ) -> None:
        """Cannot pause completed session."""
        service = AutosaveService(db_session)

        test_session_in_progress.status = "completed"
        db_session.commit()

        with pytest.raises(ValueError, match="Cannot pause completed"):
            service.pause_session(test_session_in_progress.id)


class TestSessionState:
    """REQ-B-B2-Plus-3: Get session state for resumption."""

    def test_get_session_state_partial_answers(
        self, db_session: Session, test_session_in_progress: TestSession
    ) -> None:
        """Get session state with partial answers."""
        service = AutosaveService(db_session)

        # Create 5 questions
        for i in range(5):
            q = Question(
                session_id=test_session_in_progress.id,
                item_type="multiple_choice",
                stem=f"Q{i + 1}",
                choices=["A", "B"],
                answer_schema={"correct_key": "A", "explanation": "Test"},
                difficulty=5,
                category="LLM",
                round=1,
            )
            db_session.add(q)
        db_session.commit()

        # Answer only 3 questions
        questions = db_session.query(Question).filter_by(session_id=test_session_in_progress.id).limit(3).all()
        for q in questions:
            service.save_answer(
                session_id=test_session_in_progress.id,
                question_id=q.id,
                user_answer={"selected_key": "A"},
                response_time_ms=1000,
            )

        state = service.get_session_state(test_session_in_progress.id)

        assert state["answered_count"] == 3
        assert state["total_questions"] == 5
        assert state["next_question_index"] == 3  # 0-indexed, next is 3


class TestResumeSession:
    """REQ-B-B2-Plus-3: Resume paused session."""

    def test_resume_paused_session(self, db_session: Session, test_session_in_progress: TestSession) -> None:
        """Resume paused session successfully."""
        service = AutosaveService(db_session)

        # Pause first
        test_session_in_progress.status = "paused"
        test_session_in_progress.paused_at = datetime.now(UTC)
        db_session.commit()

        # Resume
        resumed = service.resume_session(test_session_in_progress.id)

        assert resumed.status == "in_progress"
        assert resumed.paused_at is None

    def test_resume_non_paused_raises_error(self, db_session: Session, test_session_in_progress: TestSession) -> None:
        """Cannot resume non-paused session."""
        service = AutosaveService(db_session)

        # Session is in_progress
        with pytest.raises(ValueError, match="not paused"):
            service.resume_session(test_session_in_progress.id)
