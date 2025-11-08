"""
Tests for autosave API endpoints.

REQ: REQ-B-B2-Plus
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.backend.models.attempt_answer import AttemptAnswer
from src.backend.models.question import Question
from src.backend.models.test_session import TestSession


class TestAutosaveEndpoint:
    """POST /questions/autosave endpoint tests."""

    def test_autosave_answer_success(
        self, client: TestClient, db_session: Session, test_session_in_progress: TestSession
    ) -> None:
        """POST /questions/autosave - Save answer successfully."""
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

        response = client.post(
            "/questions/autosave",
            json={
                "session_id": test_session_in_progress.id,
                "question_id": question.id,
                "user_answer": {"selected_key": "B"},
                "response_time_ms": 5000,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["saved"] is True
        assert data["session_id"] == test_session_in_progress.id
        assert data["question_id"] == question.id
        assert "saved_at" in data

    def test_autosave_multiple_choice_answer(
        self, client: TestClient, db_session: Session, test_session_in_progress: TestSession
    ) -> None:
        """Autosave multiple choice answer with selected_key."""
        question = Question(
            session_id=test_session_in_progress.id,
            item_type="multiple_choice",
            stem="What is 2+2?",
            choices=["A: 3", "B: 4", "C: 5", "D: 6"],
            answer_schema={"correct_key": "B", "explanation": "2+2=4"},
            difficulty=5,
            category="LLM",
            round=1,
        )
        db_session.add(question)
        db_session.commit()

        response = client.post(
            "/questions/autosave",
            json={
                "session_id": test_session_in_progress.id,
                "question_id": question.id,
                "user_answer": {"selected_key": "B"},
                "response_time_ms": 3000,
            },
        )

        assert response.status_code == 200

        # Verify in database
        answer = db_session.query(AttemptAnswer).filter_by(question_id=question.id).first()
        assert answer.user_answer == {"selected_key": "B"}

    def test_autosave_true_false_answer(
        self, client: TestClient, db_session: Session, test_session_in_progress: TestSession
    ) -> None:
        """Autosave true/false answer with selected_value."""
        question = Question(
            session_id=test_session_in_progress.id,
            item_type="true_false",
            stem="True or False: 2+2=4",
            choices=["True", "False"],
            answer_schema={"correct_value": True, "explanation": "Correct"},
            difficulty=5,
            category="LLM",
            round=1,
        )
        db_session.add(question)
        db_session.commit()

        response = client.post(
            "/questions/autosave",
            json={
                "session_id": test_session_in_progress.id,
                "question_id": question.id,
                "user_answer": {"selected_value": True},
                "response_time_ms": 2000,
            },
        )

        assert response.status_code == 200

    def test_autosave_short_answer(
        self, client: TestClient, db_session: Session, test_session_in_progress: TestSession
    ) -> None:
        """Autosave short answer with text field."""
        question = Question(
            session_id=test_session_in_progress.id,
            item_type="short_answer",
            stem="What is LLM?",
            choices=None,
            answer_schema={"keywords": ["language", "model"], "explanation": "Test"},
            difficulty=5,
            category="LLM",
            round=1,
        )
        db_session.add(question)
        db_session.commit()

        response = client.post(
            "/questions/autosave",
            json={
                "session_id": test_session_in_progress.id,
                "question_id": question.id,
                "user_answer": {"text": "Large Language Model"},
                "response_time_ms": 8000,
            },
        )

        assert response.status_code == 200

    def test_autosave_invalid_session(self, client: TestClient) -> None:
        """Autosave with invalid session returns 404."""
        response = client.post(
            "/questions/autosave",
            json={
                "session_id": "invalid_session_id",
                "question_id": "q1",
                "user_answer": {"text": "answer"},
                "response_time_ms": 1000,
            },
        )

        assert response.status_code == 404

    def test_autosave_invalid_question(self, client: TestClient, test_session_in_progress: TestSession) -> None:
        """Autosave with invalid question returns 404."""
        response = client.post(
            "/questions/autosave",
            json={
                "session_id": test_session_in_progress.id,
                "question_id": "invalid_question_id",
                "user_answer": {"text": "answer"},
                "response_time_ms": 1000,
            },
        )

        assert response.status_code == 404

    def test_autosave_completed_session_returns_409(
        self, client: TestClient, db_session: Session, test_session_in_progress: TestSession
    ) -> None:
        """Autosave to completed session returns 409 Conflict."""
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

        response = client.post(
            "/questions/autosave",
            json={
                "session_id": test_session_in_progress.id,
                "question_id": question.id,
                "user_answer": {"selected_key": "A"},
                "response_time_ms": 1000,
            },
        )

        assert response.status_code == 409

    def test_autosave_triggers_pause_on_timeout(
        self, client: TestClient, db_session: Session, test_session_in_progress: TestSession
    ) -> None:
        """Autosave auto-pauses session when time limit exceeded."""
        test_session_in_progress.started_at = datetime.now(UTC) - timedelta(minutes=21)
        test_session_in_progress.time_limit_ms = 1200000  # 20 minutes
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

        response = client.post(
            "/questions/autosave",
            json={
                "session_id": test_session_in_progress.id,
                "question_id": question.id,
                "user_answer": {"selected_key": "A"},
                "response_time_ms": 1000,
            },
        )

        # Answer should save successfully
        assert response.status_code == 200

        # Session should be paused
        db_session.refresh(test_session_in_progress)
        assert test_session_in_progress.status == "paused"


class TestResumeEndpoint:
    """GET /questions/resume endpoint tests."""

    def test_resume_session_success(
        self, client: TestClient, db_session: Session, test_session_in_progress: TestSession
    ) -> None:
        """GET /questions/resume - Resume paused session."""
        # Pause session
        test_session_in_progress.status = "paused"
        test_session_in_progress.paused_at = datetime.now(UTC)
        db_session.commit()

        # Create questions
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

        response = client.get(f"/questions/resume?session_id={test_session_in_progress.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == test_session_in_progress.id
        assert data["status"] == "in_progress"  # Resumed
        assert data["total_questions"] == 5

    def test_resume_with_previous_answers(
        self, client: TestClient, db_session: Session, test_session_in_progress: TestSession
    ) -> None:
        """Resume includes all previous answers with metadata."""
        # Create questions and answers
        for i in range(3):
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

        questions = db_session.query(Question).filter_by(session_id=test_session_in_progress.id).all()
        for q in questions:
            answer = AttemptAnswer(
                session_id=test_session_in_progress.id,
                question_id=q.id,
                user_answer={"selected_key": "A"},
                is_correct=False,
                score=0.0,
                response_time_ms=5000,
            )
            db_session.add(answer)
        db_session.commit()

        response = client.get(f"/questions/resume?session_id={test_session_in_progress.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["previous_answers"]) == 3
        assert all("question_id" in ans for ans in data["previous_answers"])
        assert all("response_time_ms" in ans for ans in data["previous_answers"])

    def test_resume_invalid_session(self, client: TestClient) -> None:
        """Resume invalid session returns 404."""
        response = client.get("/questions/resume?session_id=invalid_session_id")

        assert response.status_code == 404

    def test_resume_next_question_index(
        self, client: TestClient, db_session: Session, test_session_in_progress: TestSession
    ) -> None:
        """Resume returns correct next_question_index."""
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

        # Answer first 2 questions
        questions = db_session.query(Question).filter_by(session_id=test_session_in_progress.id).limit(2).all()
        for q in questions:
            answer = AttemptAnswer(
                session_id=test_session_in_progress.id,
                question_id=q.id,
                user_answer={"selected_key": "A"},
                is_correct=False,
                score=0.0,
                response_time_ms=5000,
            )
            db_session.add(answer)
        db_session.commit()

        response = client.get(f"/questions/resume?session_id={test_session_in_progress.id}")

        data = response.json()
        assert data["answered_count"] == 2
        assert data["next_question_index"] == 2  # Next is index 2 (3rd question)


class TestSessionStatusEndpoint:
    """PUT /questions/session/{session_id}/status endpoint tests."""

    def test_pause_session(
        self, client: TestClient, db_session: Session, test_session_in_progress: TestSession
    ) -> None:
        """PUT /questions/session/{id}/status - Pause session."""
        response = client.put(
            f"/questions/session/{test_session_in_progress.id}/status?status=paused",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"
        assert data["paused_at"] is not None

    def test_resume_session_via_status(
        self, client: TestClient, db_session: Session, test_session_in_progress: TestSession
    ) -> None:
        """PUT /questions/session/{id}/status - Resume session."""
        # Pause first
        test_session_in_progress.status = "paused"
        test_session_in_progress.paused_at = datetime.now(UTC)
        db_session.commit()

        response = client.put(
            f"/questions/session/{test_session_in_progress.id}/status?status=in_progress",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"
        assert data["paused_at"] is None

    def test_invalid_status_returns_422(self, client: TestClient, test_session_in_progress: TestSession) -> None:
        """Invalid status returns 422."""
        response = client.put(
            f"/questions/session/{test_session_in_progress.id}/status?status=invalid_status",
        )

        assert response.status_code == 422

    def test_resume_non_paused_returns_409(self, client: TestClient, test_session_in_progress: TestSession) -> None:
        """Resume non-paused session returns 409."""
        response = client.put(
            f"/questions/session/{test_session_in_progress.id}/status?status=in_progress",
        )

        assert response.status_code == 409


class TestTimeStatusEndpoint:
    """GET /questions/session/{session_id}/time-status endpoint tests."""

    def test_check_time_status_within_limit(
        self, client: TestClient, db_session: Session, test_session_in_progress: TestSession
    ) -> None:
        """Check time status within limit."""
        test_session_in_progress.started_at = datetime.now(UTC) - timedelta(minutes=10)
        test_session_in_progress.time_limit_ms = 1200000
        db_session.commit()

        response = client.get(f"/questions/session/{test_session_in_progress.id}/time-status")

        assert response.status_code == 200
        data = response.json()
        assert data["exceeded"] is False
        assert data["remaining_ms"] > 0

    def test_check_time_status_exceeded(
        self, client: TestClient, db_session: Session, test_session_in_progress: TestSession
    ) -> None:
        """Check time status exceeded."""
        test_session_in_progress.started_at = datetime.now(UTC) - timedelta(minutes=21)
        test_session_in_progress.time_limit_ms = 1200000
        db_session.commit()

        response = client.get(f"/questions/session/{test_session_in_progress.id}/time-status")

        assert response.status_code == 200
        data = response.json()
        assert data["exceeded"] is True
        assert data["remaining_ms"] == 0

    def test_check_time_status_invalid_session(self, client: TestClient) -> None:
        """Check time status with invalid session returns 404."""
        response = client.get("/questions/session/invalid_session_id/time-status")

        assert response.status_code == 404
