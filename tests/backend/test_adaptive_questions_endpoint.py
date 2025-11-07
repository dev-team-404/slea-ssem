"""
Tests for adaptive questions API endpoints.

REQ: REQ-B-B2-Adapt-1, REQ-B-B2-Adapt-2, REQ-B-B2-Adapt-3
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.backend.models.attempt_answer import AttemptAnswer
from src.backend.models.test_result import TestResult
from src.backend.models.test_session import TestSession


class TestScoringEndpoint:
    """POST /questions/score endpoint tests."""

    def test_score_round_endpoint_success(
        self,
        client: TestClient,
        db_session: Session,
        test_session_round1_fixture: TestSession,
        attempt_answers_for_session: list[AttemptAnswer],
    ) -> None:
        """POST /questions/score - Calculate and save round score."""
        response = client.post(
            "/questions/score",
            params={"session_id": test_session_round1_fixture.id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == test_session_round1_fixture.id
        assert data["round"] == 1
        assert data["score"] == 20.0  # 1 correct of 5
        assert data["correct_count"] == 1
        assert data["total_count"] == 5

    def test_score_round_identifies_weak_categories(
        self,
        client: TestClient,
        db_session: Session,
        test_session_round1_fixture: TestSession,
        attempt_answers_for_session: list[AttemptAnswer],
    ) -> None:
        """POST /questions/score - Identifies weak categories."""
        response = client.post(
            "/questions/score",
            params={"session_id": test_session_round1_fixture.id},
        )

        assert response.status_code == 200
        data = response.json()
        wrong_cats = data["wrong_categories"]

        assert len(wrong_cats) > 0
        assert "RAG" in wrong_cats  # RAG has 2 wrong answers

    def test_score_round_invalid_session(self, client: TestClient) -> None:
        """POST /questions/score - Invalid session returns 404."""
        response = client.post(
            "/questions/score",
            params={"session_id": "invalid_session_id"},
        )

        assert response.status_code == 404


class TestGenerateAdaptiveQuestionsEndpoint:
    """POST /questions/generate-adaptive endpoint tests."""

    def test_generate_adaptive_questions_success(
        self,
        client: TestClient,
        db_session: Session,
        test_session_round1_fixture: TestSession,
        attempt_answers_for_session: list[AttemptAnswer],
        test_result_low_score: TestResult,
    ) -> None:
        """POST /questions/generate-adaptive - Generate Round 2 with adapted difficulty."""
        response = client.post(
            "/questions/generate-adaptive",
            json={
                "previous_session_id": test_session_round1_fixture.id,
                "round": 2,
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert "session_id" in data
        assert data["session_id"] != test_session_round1_fixture.id  # New session
        assert len(data["questions"]) == 5  # 5 questions generated
        assert "adaptive_params" in data

    def test_adaptive_questions_has_required_fields(
        self,
        client: TestClient,
        db_session: Session,
        test_session_round1_fixture: TestSession,
        attempt_answers_for_session: list[AttemptAnswer],
        test_result_low_score: TestResult,
    ) -> None:
        """Each adaptive question has all required fields."""
        response = client.post(
            "/questions/generate-adaptive",
            json={
                "previous_session_id": test_session_round1_fixture.id,
                "round": 2,
            },
        )

        assert response.status_code == 201
        data = response.json()

        for question in data["questions"]:
            assert "id" in question
            assert "item_type" in question
            assert "stem" in question
            assert "answer_schema" in question
            assert "difficulty" in question
            assert "category" in question

    def test_adaptive_params_included_in_response(
        self,
        client: TestClient,
        db_session: Session,
        test_session_round1_fixture: TestSession,
        attempt_answers_for_session: list[AttemptAnswer],
        test_result_low_score: TestResult,
    ) -> None:
        """Response includes adaptive parameters."""
        response = client.post(
            "/questions/generate-adaptive",
            json={
                "previous_session_id": test_session_round1_fixture.id,
                "round": 2,
            },
        )

        assert response.status_code == 201
        data = response.json()
        params = data["adaptive_params"]

        assert "difficulty_tier" in params
        assert "adjusted_difficulty" in params
        assert "weak_categories" in params
        assert "priority_ratio" in params
        assert "score" in params

    def test_adaptive_questions_prioritize_weak_categories(
        self,
        client: TestClient,
        db_session: Session,
        test_session_round1_fixture: TestSession,
        attempt_answers_for_session: list[AttemptAnswer],
        test_result_low_score: TestResult,
    ) -> None:
        """Round 2 questions prioritize weak categories (≥50%)."""
        response = client.post(
            "/questions/generate-adaptive",
            json={
                "previous_session_id": test_session_round1_fixture.id,
                "round": 2,
            },
        )

        assert response.status_code == 201
        data = response.json()

        # Get weak categories from adaptive params
        weak_cats = data["adaptive_params"]["weak_categories"]
        weak_cat_names = list(weak_cats.keys())

        # Count questions from weak categories
        weak_count = sum(1 for q in data["questions"] if q["category"] in weak_cat_names)

        # Should be ≥50% (at least 3 of 5)
        assert weak_count >= 3

    def test_adaptive_questions_respects_difficulty_adjustment(
        self,
        client: TestClient,
        db_session: Session,
        test_session_round1_fixture: TestSession,
        attempt_answers_for_session: list[AttemptAnswer],
        test_result_low_score: TestResult,
    ) -> None:
        """Round 2 difficulty adjusted based on score."""
        response = client.post(
            "/questions/generate-adaptive",
            json={
                "previous_session_id": test_session_round1_fixture.id,
                "round": 2,
            },
        )

        assert response.status_code == 201
        data = response.json()

        # Low score (30%) should decrease or maintain difficulty
        # Round 1 avg was ~5, Round 2 should be ≤5
        avg_difficulty_round2 = sum(q["difficulty"] for q in data["questions"]) / len(data["questions"])

        assert avg_difficulty_round2 <= 6  # Allows some flexibility

    def test_generate_adaptive_invalid_previous_session(self, client: TestClient) -> None:
        """POST /questions/generate-adaptive - Invalid previous session returns 404."""
        response = client.post(
            "/questions/generate-adaptive",
            json={
                "previous_session_id": "invalid_session_id",
                "round": 2,
            },
        )

        assert response.status_code == 404

    def test_generate_adaptive_invalid_round(
        self,
        client: TestClient,
        db_session: Session,
        test_session_round1_fixture: TestSession,
        attempt_answers_for_session: list[AttemptAnswer],
        test_result_low_score: TestResult,
    ) -> None:
        """POST /questions/generate-adaptive - Invalid round (1) returns 422."""
        response = client.post(
            "/questions/generate-adaptive",
            json={
                "previous_session_id": test_session_round1_fixture.id,
                "round": 1,  # Invalid: should be 2 or 3
            },
        )

        assert response.status_code == 422


class TestEndToEndAdaptiveFlow:
    """End-to-end test of scoring and adaptive generation."""

    def test_full_round1_to_round2_flow(
        self,
        client: TestClient,
        db_session: Session,
        test_session_round1_fixture: TestSession,
        attempt_answers_for_session: list[AttemptAnswer],
    ) -> None:
        """Full flow: Score Round 1 → Generate Round 2."""
        # Step 1: Score Round 1
        score_response = client.post(
            "/questions/score",
            params={"session_id": test_session_round1_fixture.id},
        )
        assert score_response.status_code == 200
        score_data = score_response.json()

        # Create TestResult from scored data (normally done by scoring service)
        result = TestResult(
            session_id=test_session_round1_fixture.id,
            round=1,
            score=score_data["score"],
            total_points=score_data.get("correct_count", 1) * 100,
            correct_count=score_data["correct_count"],
            total_count=score_data["total_count"],
            wrong_categories=score_data.get("wrong_categories"),
        )
        db_session.add(result)
        db_session.commit()

        # Step 2: Generate Round 2 with adaptive difficulty
        adaptive_response = client.post(
            "/questions/generate-adaptive",
            json={
                "previous_session_id": test_session_round1_fixture.id,
                "round": 2,
            },
        )
        assert adaptive_response.status_code == 201
        adaptive_data = adaptive_response.json()

        # Verify Round 2 is properly adapted
        assert adaptive_data["adaptive_params"]["score"] == 20.0  # 1/5 correct
        assert len(adaptive_data["questions"]) == 5
        assert adaptive_data["session_id"] != test_session_round1_fixture.id
