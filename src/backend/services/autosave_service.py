"""
Autosave service for real-time answer saving and session resumption.

REQ: REQ-B-B2-Plus
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from src.backend.models.attempt_answer import AttemptAnswer
from src.backend.models.question import Question
from src.backend.models.test_session import TestSession


class AutosaveService:
    """
    Service for auto-saving user answers and managing session state.

    REQ: REQ-B-B2-Plus-1, 2, 3, 4, 5

    Methods:
        save_answer: Save individual answer in real-time (< 2 sec)
        check_time_limit: Check if session exceeded time limit
        pause_session: Pause session on timeout
        get_session_state: Get current session state for resume
        resume_session: Resume paused session

    """

    def __init__(self, session: Session) -> None:
        """
        Initialize AutosaveService with database session.

        Args:
            session: SQLAlchemy database session

        """
        self.session = session

    def save_answer(
        self,
        session_id: str,
        question_id: str,
        user_answer: dict[str, Any],
        response_time_ms: int,
    ) -> AttemptAnswer:
        """
        Save user's answer to a question in real-time.

        REQ: REQ-B-B2-Plus-1, REQ-B-B2-Plus-4, REQ-B-B2-Plus-5

        Performance requirement: Complete within 2 seconds.

        Args:
            session_id: TestSession ID
            question_id: Question ID
            user_answer: User's response (JSON format)
            response_time_ms: Time taken to answer in milliseconds

        Returns:
            Created or updated AttemptAnswer record

        Raises:
            ValueError: If session or question not found
            ValueError: If session is completed (no further saves allowed)

        """
        # Validate session exists and is saveable
        test_session = self.session.query(TestSession).filter_by(id=session_id).first()
        if not test_session:
            raise ValueError(f"Test session {session_id} not found")

        if test_session.status == "completed":
            raise ValueError(f"Session {session_id} is already completed")

        # Validate question exists and belongs to session
        question = self.session.query(Question).filter_by(id=question_id, session_id=session_id).first()
        if not question:
            raise ValueError(f"Question {question_id} not found in session {session_id}")

        # Set started_at on first answer if not already set
        if not test_session.started_at:
            test_session.started_at = datetime.now(UTC)
            self.session.commit()

        # Check if answer already exists (idempotent update)
        existing = self.session.query(AttemptAnswer).filter_by(session_id=session_id, question_id=question_id).first()

        if existing:
            # Update existing answer
            existing.user_answer = user_answer
            existing.response_time_ms = response_time_ms
            existing.saved_at = datetime.now(UTC)
            self.session.commit()
            self.session.refresh(existing)
            return existing

        # Create new answer
        answer = AttemptAnswer(
            session_id=session_id,
            question_id=question_id,
            user_answer=user_answer,
            is_correct=False,  # Will be set by scoring service
            score=0.0,  # Will be set by scoring service
            response_time_ms=response_time_ms,
            saved_at=datetime.now(UTC),
        )
        self.session.add(answer)
        self.session.commit()
        self.session.refresh(answer)
        return answer

    def check_time_limit(self, session_id: str) -> dict[str, Any]:
        """
        Check if session has exceeded time limit.

        REQ: REQ-B-B2-Plus-2

        Args:
            session_id: TestSession ID

        Returns:
            Dictionary with:
                - exceeded (bool): True if time limit exceeded
                - elapsed_ms (int): Elapsed time in milliseconds
                - remaining_ms (int): Remaining time (0 if exceeded)
                - status (str): Session status

        Raises:
            ValueError: If session not found

        """
        test_session = self.session.query(TestSession).filter_by(id=session_id).first()
        if not test_session:
            raise ValueError(f"Test session {session_id} not found")

        # If not started yet, no time elapsed
        if not test_session.started_at:
            return {
                "exceeded": False,
                "elapsed_ms": 0,
                "remaining_ms": test_session.time_limit_ms,
                "status": test_session.status,
            }

        started_at = test_session.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)

        # Calculate elapsed time
        now = datetime.now(UTC)
        elapsed = now - started_at
        elapsed_ms = int(elapsed.total_seconds() * 1000)

        exceeded = elapsed_ms > test_session.time_limit_ms
        remaining_ms = max(0, test_session.time_limit_ms - elapsed_ms)

        return {
            "exceeded": exceeded,
            "elapsed_ms": elapsed_ms,
            "remaining_ms": remaining_ms,
            "status": test_session.status,
        }

    def pause_session(self, session_id: str, reason: str = "time_limit") -> TestSession:
        """
        Pause session (typically due to timeout).

        REQ: REQ-B-B2-Plus-2

        Args:
            session_id: TestSession ID
            reason: Pause reason (time_limit, manual, etc.)

        Returns:
            Updated TestSession

        Raises:
            ValueError: If session not found or already completed

        """
        test_session = self.session.query(TestSession).filter_by(id=session_id).first()
        if not test_session:
            raise ValueError(f"Test session {session_id} not found")

        if test_session.status == "completed":
            raise ValueError(f"Cannot pause completed session {session_id}")

        test_session.status = "paused"
        test_session.paused_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(test_session)
        return test_session

    def get_session_state(self, session_id: str) -> dict[str, Any]:
        """
        Get complete session state for resumption.

        REQ: REQ-B-B2-Plus-3

        Args:
            session_id: TestSession ID

        Returns:
            Dictionary with:
                - session_id (str): Session ID
                - status (str): Session status
                - round (int): Current round
                - answered_count (int): Number of questions answered
                - total_questions (int): Total questions in session
                - next_question_index (int): Index of next unanswered question
                - previous_answers (list): All previous answers with metadata
                - time_status (dict): Time limit status

        Raises:
            ValueError: If session not found

        """
        test_session = self.session.query(TestSession).filter_by(id=session_id).first()
        if not test_session:
            raise ValueError(f"Test session {session_id} not found")

        # Get all questions for this session
        questions = self.session.query(Question).filter_by(session_id=session_id).order_by(Question.created_at).all()

        # Get all answers
        answers = (
            self.session.query(AttemptAnswer).filter_by(session_id=session_id).order_by(AttemptAnswer.saved_at).all()
        )

        # Build previous answers list
        previous_answers = []
        for answer in answers:
            previous_answers.append(
                {
                    "question_id": answer.question_id,
                    "user_answer": answer.user_answer,
                    "response_time_ms": answer.response_time_ms,
                    "saved_at": answer.saved_at.isoformat() if answer.saved_at else None,
                    "is_correct": answer.is_correct,
                    "score": answer.score,
                }
            )

        # Find next unanswered question
        answered_question_ids = {a.question_id for a in answers}
        next_question_index = 0
        for idx, q in enumerate(questions):
            if q.id not in answered_question_ids:
                next_question_index = idx
                break
        else:
            next_question_index = len(questions)  # All answered

        # Get time status
        time_status = self.check_time_limit(session_id)

        return {
            "session_id": session_id,
            "status": test_session.status,
            "round": test_session.round,
            "answered_count": len(answers),
            "total_questions": len(questions),
            "next_question_index": next_question_index,
            "previous_answers": previous_answers,
            "time_status": time_status,
        }

    def resume_session(self, session_id: str) -> TestSession:
        """
        Resume a paused session.

        REQ: REQ-B-B2-Plus-3

        Args:
            session_id: TestSession ID

        Returns:
            Updated TestSession with status = in_progress

        Raises:
            ValueError: If session not found or not paused

        """
        test_session = self.session.query(TestSession).filter_by(id=session_id).first()
        if not test_session:
            raise ValueError(f"Test session {session_id} not found")

        if test_session.status != "paused":
            raise ValueError(f"Session {session_id} is not paused (status: {test_session.status})")

        test_session.status = "in_progress"
        test_session.paused_at = None
        self.session.commit()
        self.session.refresh(test_session)
        return test_session

    def get_next_unanswered_question(self, session_id: str) -> Question | None:
        """
        Get the next unanswered question in the session.

        Args:
            session_id: TestSession ID

        Returns:
            Next unanswered Question or None if all answered

        Raises:
            ValueError: If session not found

        """
        test_session = self.session.query(TestSession).filter_by(id=session_id).first()
        if not test_session:
            raise ValueError(f"Test session {session_id} not found")

        # Get all questions
        questions = self.session.query(Question).filter_by(session_id=session_id).order_by(Question.created_at).all()

        # Get answered question IDs
        answered_ids = self.session.query(AttemptAnswer.question_id).filter_by(session_id=session_id).all()
        answered_ids_set = {q_id for (q_id,) in answered_ids}

        # Find first unanswered
        for question in questions:
            if question.id not in answered_ids_set:
                return question

        return None
