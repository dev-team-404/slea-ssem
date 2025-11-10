"""Backend services."""

from typing import Any


# Lazy imports to avoid circular dependencies and import errors
def __getattr__(name: str) -> Any:  # noqa: ANN401
    """Lazy load services on demand."""
    if name == "AuthService":
        from src.backend.services.auth_service import AuthService

        return AuthService
    if name == "HistoryService":
        from src.backend.services.history_service import HistoryService

        return HistoryService
    if name == "ProfileService":
        from src.backend.services.profile_service import ProfileService

        return ProfileService
    if name == "SurveyService":
        from src.backend.services.survey_service import SurveyService

        return SurveyService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["AuthService", "ProfileService", "SurveyService", "HistoryService"]
