"""
Tests for profile survey retrieval endpoint.

REQ: REQ-B-A2-Prof-4, REQ-B-A2-Prof-5, REQ-B-A2-Prof-6
"""

import time
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from src.backend.models.user_profile import UserProfileSurvey


class TestProfileSurveyRetrieval:
    """REQ-B-A2-Prof-4, 5, 6: Profile survey retrieval endpoint."""

    def test_get_profile_survey_no_survey_exists(self, client: TestClient) -> None:
        """TC-3: GET /profile/survey - No survey exists, return all null."""
        # Don't create any survey for this user
        response = client.get("/profile/survey")

        assert response.status_code == 200
        data = response.json()
        assert data["level"] is None
        assert data["career"] is None
        assert data["job_role"] is None
        assert data["duty"] is None
        assert data["interests"] is None

    def test_get_profile_survey_success_with_all_fields(
        self, client: TestClient, user_profile_survey_fixture: UserProfileSurvey
    ) -> None:
        """TC-1: GET /profile/survey - Success with all fields populated."""
        # user_profile_survey_fixture already has all fields populated
        response = client.get("/profile/survey")

        assert response.status_code == 200
        data = response.json()
        assert data["level"] == "Intermediate"
        assert data["career"] == 3
        assert data["job_role"] == "Senior Engineer"
        assert data["duty"] == "ML Model Development"
        assert data["interests"] == ["LLM", "RAG"]

    def test_get_profile_survey_response_time_under_1_second(
        self, client: TestClient, user_profile_survey_fixture: UserProfileSurvey
    ) -> None:
        """TC-6: GET /profile/survey - Response within 1 second."""
        # Measure response time
        start_time = time.time()
        response = client.get("/profile/survey")
        elapsed_time = time.time() - start_time

        assert response.status_code == 200
        assert elapsed_time < 1.0  # Must respond within 1 second
