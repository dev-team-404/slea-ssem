"""
Tests for unified signup endpoint.

REQ: REQ-F-A2-Signup-6, REQ-B-A2-Signup
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.backend.models.user import User
from src.backend.models.user_profile import UserProfileSurvey


@pytest.fixture
def authenticated_user(db_session: Session) -> User:
    """Override authenticated user fixture to simulate a new user without nickname."""
    user = User(
        knox_id="signup_user",
        name="Signup User",
        dept="DX",
        business_unit="S.LSI",
        email="signup_user@samsung.com",
        nickname=None,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_complete_signup_success(
    client: TestClient,
    db_session: Session,
    authenticated_user: User,
) -> None:
    """Happy path: nickname + profile saved and responds with success."""
    payload = {
        "nickname": "new_signup_user",
        "profile": {
            "level": "beginner",
            "career": 1,
            "job_role": "Backend",
            "duty": "API development",
            "interests": ["AI", "Backend"],
        },
    }

    response = client.post("/signup", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["nickname"] == "new_signup_user"
    assert data["survey_id"]

    db_session.refresh(authenticated_user)
    assert authenticated_user.nickname == "new_signup_user"

    surveys = db_session.query(UserProfileSurvey).filter_by(user_id=authenticated_user.id).all()
    assert len(surveys) == 1
    assert surveys[0].self_level == "beginner"


def test_complete_signup_duplicate_nickname_returns_400(
    client: TestClient,
    db_session: Session,
    authenticated_user: User,
) -> None:
    """Duplicate nickname detection returns 400 with error message."""
    existing_user = User(
        knox_id="taken_user",
        name="Taken",
        dept="DX",
        business_unit="S.LSI",
        email="taken@samsung.com",
        nickname="taken_name",
    )
    db_session.add(existing_user)
    db_session.commit()

    payload = {
        "nickname": "taken_name",
        "profile": {"level": "intermediate"},
    }

    response = client.post("/signup", json=payload)

    assert response.status_code == 400
    assert "already taken" in response.json()["detail"]


def test_complete_signup_invalid_profile_rolls_back(
    client: TestClient,
    db_session: Session,
    authenticated_user: User,
) -> None:
    """Invalid profile payload should not persist nickname or survey."""
    payload = {
        "nickname": "rollback_user",
        "profile": {
            "level": "invalid-level",
        },
    }

    response = client.post("/signup", json=payload)

    assert response.status_code == 400
    assert "Invalid self_level" in response.json()["detail"]

    db_session.refresh(authenticated_user)
    assert authenticated_user.nickname is None
    survey_count = db_session.query(UserProfileSurvey).filter_by(user_id=authenticated_user.id).count()
    assert survey_count == 0
