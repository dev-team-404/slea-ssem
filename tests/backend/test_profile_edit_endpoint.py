"""
Tests for profile edit endpoints.

REQ: REQ-B-A2-Edit-1, REQ-B-A2-Edit-2, REQ-B-A2-Edit-3, REQ-B-A2-Edit-4
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.backend.models.user import User


class TestEditNicknameEndpoint:
    """REQ-B-A2-Edit-1, 2: Edit nickname endpoint tests."""

    def test_put_profile_nickname_success(self, client: TestClient, db_session: Session) -> None:
        """Integration test: PUT /profile/nickname - successful edit."""
        # Create a user with id=1 (endpoint uses hardcoded user_id=1)
        user = User(
            knox_id="edit_test_user",
            name="Edit Test User",
            dept="Test",
            business_unit="Test",
            email="edit@example.com",
            nickname="old_nickname",
        )
        db_session.add(user)
        db_session.commit()

        payload = {"nickname": "new_nickname"}
        response = client.put("/profile/nickname", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["new_nickname"] == "new_nickname"
        assert "user_id" in data
        assert "updated_at" in data

    def test_put_profile_nickname_self_allowed(self, client: TestClient, db_session: Session) -> None:
        """Edge case: User can edit to their own nickname."""
        # Note: The authenticated_user fixture already has nickname="jwt_test_user"
        # So we're testing if user can change nickname to their own nickname
        payload = {"nickname": "jwt_test_user"}
        response = client.put("/profile/nickname", json=payload)

        # Should succeed (200) because user is changing to their own current nickname
        assert response.status_code == 200
        assert response.json()["new_nickname"] == "jwt_test_user"

    def test_put_profile_nickname_duplicate(self, client: TestClient, db_session: Session) -> None:
        """Edge case: Cannot edit to nickname taken by others."""
        # Create user with id=1 (endpoint uses hardcoded user_id=1)
        user1 = User(
            knox_id="user_1",
            name="User 1",
            dept="Test",
            business_unit="Test",
            email="user1@example.com",
        )
        db_session.add(user1)
        db_session.commit()

        # Create another user with taken nickname
        user2 = User(
            knox_id="user_2",
            name="User 2",
            dept="Test",
            business_unit="Test",
            email="user2@example.com",
            nickname="taken_nickname",
        )
        db_session.add(user2)
        db_session.commit()

        # Try to use user2's nickname
        payload = {"nickname": "taken_nickname"}
        response = client.put("/profile/nickname", json=payload)

        assert response.status_code == 400
        assert "already taken" in response.json()["detail"]

    def test_put_profile_nickname_invalid(self, client: TestClient) -> None:
        """Integration test: PUT /profile/nickname - invalid format."""
        # Test too short (Pydantic returns 422 for validation errors)
        response = client.put("/profile/nickname", json={"nickname": "ab"})
        assert response.status_code == 422

        # Test forbidden word (returns 400 from business logic)
        response = client.put("/profile/nickname", json={"nickname": "admin"})
        assert response.status_code == 400
        assert "prohibited word" in response.json()["detail"]


class TestEditSurveyEndpoint:
    """REQ-B-A2-Edit-3, 4: Edit survey endpoint tests."""

    def test_put_profile_survey_success(self, client: TestClient, db_session: Session) -> None:
        """Integration test: PUT /profile/survey - successful creation."""
        # Create user with id=1
        user = User(
            knox_id="survey_test_user",
            name="Survey Test User",
            dept="Test",
            business_unit="Test",
            email="survey@example.com",
        )
        db_session.add(user)
        db_session.commit()

        payload = {
            "level": "intermediate",
            "career": 3,
            "job_role": "Engineer",
            "duty": "Development",
            "interests": ["AI", "ML"],
        }
        response = client.put("/profile/survey", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert "survey_id" in data
        assert "user_id" in data
        assert "updated_at" in data

    def test_put_profile_survey_partial_fields(self, client: TestClient, db_session: Session) -> None:
        """Happy path: Survey with only some fields."""
        user = User(
            knox_id="partial_survey_user",
            name="Partial Survey User",
            dept="Test",
            business_unit="Test",
            email="partial@example.com",
        )
        db_session.add(user)
        db_session.commit()

        payload = {"level": "beginner"}
        response = client.put("/profile/survey", json=payload)

        assert response.status_code == 201
        assert "survey_id" in response.json()

    def test_put_profile_survey_invalid_level(self, client: TestClient, db_session: Session) -> None:
        """Input validation: Invalid level."""
        # Create user with id=1
        user = User(
            knox_id="invalid_level_user",
            name="Invalid Level User",
            dept="Test",
            business_unit="Test",
            email="invalid_level@example.com",
        )
        db_session.add(user)
        db_session.commit()

        payload = {"level": "expert"}
        response = client.put("/profile/survey", json=payload)

        assert response.status_code == 400
        assert "Invalid self_level" in response.json()["detail"]

    def test_put_profile_survey_invalid_years(self, client: TestClient, db_session: Session) -> None:
        """Input validation: Invalid years_experience."""
        # Create user with id=1
        user = User(
            knox_id="invalid_years_user",
            name="Invalid Years User",
            dept="Test",
            business_unit="Test",
            email="invalid_years@example.com",
        )
        db_session.add(user)
        db_session.commit()

        payload = {"career": -1}
        response = client.put("/profile/survey", json=payload)

        assert response.status_code == 400
        assert "between 0 and 60" in response.json()["detail"]

    def test_put_profile_survey_invalid_interests(self, client: TestClient, db_session: Session) -> None:
        """Input validation: Invalid interests."""
        # Create user with id=1
        user = User(
            knox_id="invalid_interests_user",
            name="Invalid Interests User",
            dept="Test",
            business_unit="Test",
            email="invalid_interests@example.com",
        )
        db_session.add(user)
        db_session.commit()

        payload = {"interests": []}
        response = client.put("/profile/survey", json=payload)

        assert response.status_code == 400
        assert "between 1 and 20 items" in response.json()["detail"]

    def test_put_profile_survey_empty_body(self, client: TestClient, db_session: Session) -> None:
        """Happy path: Empty body (all optional) should succeed."""
        user = User(
            knox_id="empty_survey_user",
            name="Empty Survey User",
            dept="Test",
            business_unit="Test",
            email="empty@example.com",
        )
        db_session.add(user)
        db_session.commit()

        payload = {}
        response = client.put("/profile/survey", json=payload)

        assert response.status_code == 201
        assert "survey_id" in response.json()
