"""
Tests for profile survey retrieval endpoint.

REQ: REQ-B-A2-Prof-4, REQ-B-A2-Prof-5, REQ-B-A2-Prof-6
"""

import time
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.backend.models.user import User
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

    def test_get_profile_survey_without_jwt_token(self) -> None:
        """
        TC-4: GET /profile/survey - No JWT token should return 401 or 403.

        REQ: REQ-B-A2-Prof-4 (Authentication required)

        Note: Status code may be 401 (Unauthorized) or 403 (Forbidden) depending
        on middleware implementation. Both indicate failed authentication.
        """
        from src.backend.main import app

        unauthenticated_client = TestClient(app)
        # Don't include authorization header
        response = unauthenticated_client.get("/profile/survey")

        # Accept both 401 (Unauthorized) and 403 (Forbidden) as auth failures
        assert response.status_code in (401, 403)
        data = response.json()
        assert "detail" in data

    def test_get_profile_survey_null_fields_are_truly_null(self, client: TestClient, db_session: Session) -> None:
        """
        TC-9: Null fields must be None, not empty strings or other falsy values.

        REQ: REQ-B-A2-Prof-5
        """
        # Don't create any survey - all fields should be null
        response = client.get("/profile/survey")

        assert response.status_code == 200
        data = response.json()

        # Verify each field is explicitly None
        assert data["level"] is None
        assert data["career"] is None
        assert data["job_role"] is None
        assert data["duty"] is None
        assert data["interests"] is None

        # Ensure they are not empty strings
        assert data["level"] != ""
        assert data["job_role"] != ""
        assert data["duty"] != ""
        assert data["interests"] != []

    def test_get_profile_survey_response_structure(self, client: TestClient) -> None:
        """
        TC-7: Response structure must have all 5 expected fields.

        REQ: REQ-B-A2-Prof-5
        """
        response = client.get("/profile/survey")

        assert response.status_code == 200
        data = response.json()

        # Verify all 5 fields are present
        expected_fields = ["level", "career", "job_role", "duty", "interests"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

        # Verify no extra fields
        assert len(data) == 5, f"Expected 5 fields, got {len(data)}: {list(data.keys())}"

    def test_get_profile_survey_most_recent_by_submitted_at(
        self, client: TestClient, authenticated_user: User, db_session: Session
    ) -> None:
        """
        TC-8: With multiple surveys, return the most recent by submitted_at.

        REQ: REQ-B-A2-Prof-4, REQ-B-A2-Prof-5
        """
        # Create first survey with old timestamp
        old_time = datetime.now(UTC) - timedelta(days=10)
        survey1 = UserProfileSurvey(
            user_id=authenticated_user.id,
            self_level="Beginner",
            years_experience=1,
            job_role="Junior Dev",
            duty="Code writing",
            interests=["Python"],
            submitted_at=old_time,
        )

        # Create second survey with recent timestamp
        recent_time = datetime.now(UTC)
        survey2 = UserProfileSurvey(
            user_id=authenticated_user.id,
            self_level="Advanced",
            years_experience=5,
            job_role="Senior Engineer",
            duty="System Design",
            interests=["Architecture"],
            submitted_at=recent_time,
        )

        db_session.add(survey1)
        db_session.add(survey2)
        db_session.commit()

        # Should return the most recent survey (survey2)
        response = client.get("/profile/survey")

        assert response.status_code == 200
        data = response.json()
        assert data["level"] == "Advanced"
        assert data["career"] == 5
        assert data["job_role"] == "Senior Engineer"
        assert data["duty"] == "System Design"
        assert data["interests"] == ["Architecture"]

    def test_get_profile_survey_partial_null_fields(
        self, client: TestClient, authenticated_user: User, db_session: Session
    ) -> None:
        """
        TC-2: Survey with some null fields should return actual values + null.

        REQ: REQ-B-A2-Prof-5
        """
        # Create survey with some fields null (if allowed by schema)
        survey = UserProfileSurvey(
            user_id=authenticated_user.id,
            self_level="Intermediate",
            years_experience=3,
            job_role=None,  # This field is null
            duty="Development",
            interests=None,  # This field is null
        )
        db_session.add(survey)
        db_session.commit()

        response = client.get("/profile/survey")

        assert response.status_code == 200
        data = response.json()
        # Verify actual values are returned
        assert data["level"] == "Intermediate"
        assert data["career"] == 3
        assert data["duty"] == "Development"
        # Verify null fields remain null
        assert data["job_role"] is None
        assert data["interests"] is None
