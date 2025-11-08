"""Tests for User Profile Tool (REQ-A-Mode1-Tool1).

REQ: REQ-A-Mode1-Tool1
Tests for _get_user_profile_impl() function that retrieves user self-assessment data.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from src.backend.models.user_profile import UserProfileSurvey
from src.agent.tools.user_profile_tool import _get_user_profile_impl


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def valid_user_id() -> str:
    """Generate a valid UUID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def valid_profile_data(valid_user_id: str) -> dict[str, Any]:
    """Return sample user profile data."""
    return {
        "user_id": valid_user_id,
        "self_level": "intermediate",
        "years_experience": 5,
        "job_role": "Senior Backend Engineer",
        "duty": "System design and API development",
        "interests": ["LLM", "RAG", "Agent Architecture"],
        "previous_score": 75,
    }


@pytest.fixture
def mock_profile_model(valid_profile_data: dict[str, Any]) -> MagicMock:
    """Create a mock UserProfileSurvey model instance."""
    profile = MagicMock(spec=UserProfileSurvey)
    profile.user_id = valid_profile_data["user_id"]
    profile.self_level = valid_profile_data["self_level"]
    profile.years_experience = valid_profile_data["years_experience"]
    profile.job_role = valid_profile_data["job_role"]
    profile.duty = valid_profile_data["duty"]
    profile.interests = valid_profile_data["interests"]
    profile.previous_score = valid_profile_data["previous_score"]
    profile.submitted_at = datetime.utcnow()
    return profile


@pytest.fixture
def mock_db() -> MagicMock:
    """Create a mock database session."""
    return MagicMock(spec=Session)


# ============================================================================
# Happy Path Tests
# ============================================================================


class TestGetUserProfileHappyPath:
    """Tests for successful user profile retrieval."""

    def test_get_user_profile_found_full_data(
        self,
        valid_user_id: str,
        mock_profile_model: MagicMock,
        mock_db: MagicMock,
    ) -> None:
        """Test retrieving a complete user profile.

        REQ: REQ-A-Mode1-Tool1, AC1

        Given: User profile exists with all fields populated
        When: _get_user_profile_impl(valid_user_id) is called
        Then: Returns dict with all profile fields
        """
        # Setup
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = mock_profile_model

        # Execute
        with patch("src.agent.tools.user_profile_tool.get_db", return_value=iter([mock_db])):
            result = _get_user_profile_impl(valid_user_id)

        # Assert
        assert result is not None
        assert isinstance(result, dict)
        assert result["user_id"] == valid_user_id
        assert result["self_level"] == "intermediate"
        assert result["years_experience"] == 5
        assert result["job_role"] == "Senior Backend Engineer"
        assert result["duty"] == "System design and API development"
        assert result["interests"] == ["LLM", "RAG", "Agent Architecture"]
        assert result["previous_score"] == 75

    def test_get_user_profile_found_partial_data(
        self,
        valid_user_id: str,
        mock_db: MagicMock,
    ) -> None:
        """Test profile with some NULL fields.

        REQ: REQ-A-Mode1-Tool1

        Given: User profile has some NULL fields
        When: _get_user_profile_impl(valid_user_id) is called
        Then: Returns dict with defaults for NULL fields
        """
        # Setup
        partial_profile = MagicMock(spec=UserProfileSurvey)
        partial_profile.user_id = valid_user_id
        partial_profile.self_level = "beginner"
        partial_profile.years_experience = 1
        partial_profile.job_role = None  # NULL
        partial_profile.duty = None  # NULL
        partial_profile.interests = None  # NULL
        partial_profile.submitted_at = datetime.utcnow()

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = partial_profile

        # Execute
        with patch("src.agent.tools.user_profile_tool.get_db", return_value=iter([mock_db])):
            result = _get_user_profile_impl(valid_user_id)

        # Assert
        assert result is not None
        assert result["self_level"] == "beginner"
        assert result["years_experience"] == 1
        # NULL fields should be filled with defaults
        assert "job_role" in result
        assert "duty" in result
        assert "interests" in result
        assert result["interests"] == [] or result["interests"] is None

    def test_get_user_profile_found_with_interests(
        self,
        valid_user_id: str,
        mock_db: MagicMock,
    ) -> None:
        """Test that interests list is properly returned.

        REQ: REQ-A-Mode1-Tool1

        Given: User profile with interest categories
        When: _get_user_profile_impl(valid_user_id) is called
        Then: Returns dict with interests list intact
        """
        # Setup
        interests = ["LLM", "FastAPI", "DevOps"]
        profile = MagicMock(spec=UserProfileSurvey)
        profile.user_id = valid_user_id
        profile.self_level = "advanced"
        profile.years_experience = 8
        profile.job_role = "Staff Engineer"
        profile.duty = "Architecture"
        profile.interests = interests
        profile.submitted_at = datetime.utcnow()

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = profile

        # Execute
        with patch("src.agent.tools.user_profile_tool.get_db", return_value=iter([mock_db])):
            result = _get_user_profile_impl(valid_user_id)

        # Assert
        assert result is not None
        assert result["interests"] == interests
        assert len(result["interests"]) == 3
        assert "LLM" in result["interests"]


# ============================================================================
# Not Found Tests
# ============================================================================


class TestGetUserProfileNotFound:
    """Tests for handling non-existent users."""

    def test_get_user_profile_not_found(
        self,
        valid_user_id: str,
        mock_db: MagicMock,
    ) -> None:
        """Test when user doesn't exist.

        REQ: REQ-A-Mode1-Tool1, AC2

        Given: User ID does not exist in database
        When: _get_user_profile_impl(valid_user_id) is called
        Then: Returns default profile values
        """
        # Setup
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None  # User not found

        # Execute
        with patch("src.agent.tools.user_profile_tool.get_db", return_value=iter([mock_db])):
            result = _get_user_profile_impl(valid_user_id)

        # Assert
        assert result is not None
        assert result["user_id"] == valid_user_id
        assert result["self_level"] == "beginner"
        assert result["years_experience"] == 0
        assert result["interests"] == []
        assert result["previous_score"] == 0

    def test_get_user_profile_not_found_returns_defaults(
        self,
        mock_db: MagicMock,
    ) -> None:
        """Test that defaults are safe fallback values.

        REQ: REQ-A-Mode1-Tool1, AC2

        Given: User doesn't exist
        When: _get_user_profile_impl() is called
        Then: All returned fields are safe default values
        """
        # Setup
        nonexistent_id = str(uuid.uuid4())  # Valid but non-existent UUID
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None

        # Execute
        with patch("src.agent.tools.user_profile_tool.get_db", return_value=iter([mock_db])):
            result = _get_user_profile_impl(nonexistent_id)

        # Assert
        assert result is not None
        assert result["self_level"] in ["beginner", "intermediate", "advanced"]
        assert isinstance(result["years_experience"], int)
        assert result["years_experience"] >= 0
        assert isinstance(result["interests"], list)
        assert isinstance(result["previous_score"], int)


# ============================================================================
# Input Validation Tests
# ============================================================================


class TestGetUserProfileInputValidation:
    """Tests for input validation."""

    def test_get_user_profile_invalid_uuid_format(self) -> None:
        """Test rejection of invalid UUID format.

        REQ: REQ-A-Mode1-Tool1, AC3

        Given: Invalid UUID format provided
        When: _get_user_profile_impl(invalid_id) is called
        Then: ValueError is raised or handled gracefully
        """
        # Setup
        invalid_id = "invalid-uuid-format"

        # Execute & Assert
        with pytest.raises((ValueError, TypeError)):
            _get_user_profile_impl(invalid_id)

    def test_get_user_profile_empty_string(self) -> None:
        """Test rejection of empty string input.

        REQ: REQ-A-Mode1-Tool1, AC3

        Given: Empty string as user_id
        When: _get_user_profile_impl("") is called
        Then: ValueError is raised or handled gracefully
        """
        # Execute & Assert
        with pytest.raises((ValueError, TypeError)):
            _get_user_profile_impl("")

    def test_get_user_profile_none_input(self) -> None:
        """Test rejection of None input.

        REQ: REQ-A-Mode1-Tool1, AC3

        Given: None as user_id
        When: _get_user_profile_impl(None) is called
        Then: TypeError is raised or handled gracefully
        """
        # Execute & Assert
        with pytest.raises((TypeError, ValueError)):
            _get_user_profile_impl(None)  # type: ignore


# ============================================================================
# Database Error Tests
# ============================================================================


class TestGetUserProfileDatabaseErrors:
    """Tests for database error handling."""

    def test_get_user_profile_db_connection_error(
        self,
        valid_user_id: str,
        mock_db: MagicMock,
    ) -> None:
        """Test handling of database connection errors.

        REQ: REQ-A-Mode1-Tool1

        Given: Database connection fails
        When: _get_user_profile_impl(valid_user_id) is called
        Then: Returns default profile or retries gracefully
        """
        # Setup
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.side_effect = OperationalError(
            "Connection timeout", None, None
        )

        # Execute
        with patch("src.agent.tools.user_profile_tool.get_db", return_value=iter([mock_db])):
            result = _get_user_profile_impl(valid_user_id)

        # Assert - should return default profile or None gracefully
        assert result is None or isinstance(result, dict)
        if result is not None:
            assert "user_id" in result

    def test_get_user_profile_db_query_timeout(
        self,
        valid_user_id: str,
        mock_db: MagicMock,
    ) -> None:
        """Test handling of query timeouts.

        REQ: REQ-A-Mode1-Tool1

        Given: Database query times out
        When: _get_user_profile_impl(valid_user_id) is called
        Then: Returns default profile or handles gracefully
        """
        # Setup
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.side_effect = Exception("Query timeout")

        # Execute
        with patch("src.agent.tools.user_profile_tool.get_db", return_value=iter([mock_db])):
            result = _get_user_profile_impl(valid_user_id)

        # Assert
        assert result is None or isinstance(result, dict)


# ============================================================================
# Edge Cases Tests
# ============================================================================


class TestGetUserProfileEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_get_user_profile_multiple_records_returns_latest(
        self,
        valid_user_id: str,
        mock_db: MagicMock,
    ) -> None:
        """Test that only the latest profile is returned.

        REQ: REQ-A-Mode1-Tool1, AC4

        Given: Multiple profile records exist for same user
        When: _get_user_profile_impl(valid_user_id) is called
        Then: Only the most recent (submitted_at DESC) record is returned
        """
        # Setup
        latest_profile = MagicMock(spec=UserProfileSurvey)
        latest_profile.user_id = valid_user_id
        latest_profile.self_level = "advanced"
        latest_profile.years_experience = 10
        latest_profile.job_role = "Principal Engineer"
        latest_profile.duty = "Leadership"
        latest_profile.interests = ["AI", "ML"]
        latest_profile.submitted_at = datetime.utcnow()

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = latest_profile

        # Execute
        with patch("src.agent.tools.user_profile_tool.get_db", return_value=iter([mock_db])):
            result = _get_user_profile_impl(valid_user_id)

        # Assert
        assert result is not None
        assert result["self_level"] == "advanced"  # Latest, not oldest
        assert result["years_experience"] == 10

    def test_get_user_profile_null_fields_filled_with_defaults(
        self,
        valid_user_id: str,
        mock_db: MagicMock,
    ) -> None:
        """Test that NULL fields are filled with defaults.

        REQ: REQ-A-Mode1-Tool1

        Given: All optional fields are NULL
        When: _get_user_profile_impl(valid_user_id) is called
        Then: All NULL fields are replaced with default values
        """
        # Setup
        sparse_profile = MagicMock(spec=UserProfileSurvey)
        sparse_profile.user_id = valid_user_id
        sparse_profile.self_level = None
        sparse_profile.years_experience = None
        sparse_profile.job_role = None
        sparse_profile.duty = None
        sparse_profile.interests = None
        sparse_profile.submitted_at = datetime.utcnow()

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = sparse_profile

        # Execute
        with patch("src.agent.tools.user_profile_tool.get_db", return_value=iter([mock_db])):
            result = _get_user_profile_impl(valid_user_id)

        # Assert
        assert result is not None
        # All None values should be replaced
        assert result["self_level"] is not None
        assert result["years_experience"] is not None
        assert result["job_role"] is not None
        assert result["duty"] is not None
        assert result["interests"] is not None

    def test_get_user_profile_unicode_characters(
        self,
        valid_user_id: str,
        mock_db: MagicMock,
    ) -> None:
        """Test handling of unicode characters in profile.

        REQ: REQ-A-Mode1-Tool1

        Given: Profile contains unicode characters (Korean)
        When: _get_user_profile_impl(valid_user_id) is called
        Then: Unicode is properly preserved and returned
        """
        # Setup
        unicode_profile = MagicMock(spec=UserProfileSurvey)
        unicode_profile.user_id = valid_user_id
        unicode_profile.self_level = "intermediate"
        unicode_profile.years_experience = 5
        unicode_profile.job_role = "데이터 엔지니어"  # Korean
        unicode_profile.duty = "분석 및 모델 개발"  # Korean
        unicode_profile.interests = ["머신러닝", "데이터베이스"]  # Korean
        unicode_profile.submitted_at = datetime.utcnow()

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = unicode_profile

        # Execute
        with patch("src.agent.tools.user_profile_tool.get_db", return_value=iter([mock_db])):
            result = _get_user_profile_impl(valid_user_id)

        # Assert
        assert result is not None
        assert result["job_role"] == "데이터 엔지니어"
        assert result["duty"] == "분석 및 모델 개발"
        assert "머신러닝" in result["interests"]
        assert "데이터베이스" in result["interests"]
