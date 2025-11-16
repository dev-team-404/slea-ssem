"""
Signup API endpoint for unified nickname + profile registration.

REQ: REQ-B-A2-Signup, REQ-F-A2-Signup-6
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.backend.database import get_db
from src.backend.models.user import User
from src.backend.services.profile_service import ProfileService
from src.backend.utils.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["signup"])


class SignupProfilePayload(BaseModel):
    """Nested profile payload for signup request."""

    level: str | None = Field(None, description="Self-assessed level (beginner/intermediate/advanced)")
    career: int | None = Field(None, description="Years of experience (0-60)", ge=0, le=60)
    job_role: str | None = Field(None, description="Job role/title", max_length=100)
    duty: str | None = Field(None, description="Primary responsibility", max_length=500)
    interests: list[str] | None = Field(
        None,
        description="Interest categories (max 20 items)",
        max_length=20,
    )


class SignupRequest(BaseModel):
    """Unified signup request body."""

    nickname: str = Field(..., description="Desired nickname", min_length=3, max_length=30)
    profile: SignupProfilePayload = Field(
        default_factory=SignupProfilePayload,
        description="Profile payload captured from signup form",
    )


class SignupResponse(BaseModel):
    """Unified signup response payload."""

    success: bool = Field(..., description="Signup success flag")
    message: str = Field(..., description="Result message")
    user_id: str = Field(..., description="User's Knox ID")
    nickname: str = Field(..., description="Registered nickname")
    survey_id: str = Field(..., description="Created survey ID")
    updated_at: str = Field(..., description="Timestamp of completion")


def _map_profile_payload(profile: SignupProfilePayload) -> dict[str, Any]:
    """Map API payload fields to ProfileService-compatible keys."""
    service_payload: dict[str, Any] = {}
    if profile.level is not None:
        service_payload["self_level"] = profile.level
    if profile.career is not None:
        service_payload["years_experience"] = profile.career
    if profile.job_role is not None:
        service_payload["job_role"] = profile.job_role
    if profile.duty is not None:
        service_payload["duty"] = profile.duty
    if profile.interests is not None:
        service_payload["interests"] = profile.interests
    return service_payload


@router.post(
    "",
    response_model=SignupResponse,
    status_code=201,
    summary="Complete unified signup",
    description="Registers nickname and profile survey in a single transaction.",
)
def complete_signup(
    request: SignupRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    """
    Complete signup by updating nickname + profile in one transaction.
    """
    profile_service = ProfileService(db)

    try:
        mapped_profile = _map_profile_payload(request.profile)
        result = profile_service.complete_signup(user.id, request.nickname, mapped_profile)
        return {
            "success": True,
            "message": "회원가입 완료",
            "user_id": user.knox_id,
            "nickname": result["nickname"],
            "survey_id": result["survey_id"],
            "updated_at": result["submitted_at"],
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to complete signup")
        raise HTTPException(status_code=500, detail="Failed to complete signup") from exc
