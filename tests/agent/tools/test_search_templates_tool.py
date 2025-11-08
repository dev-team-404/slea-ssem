"""Tests for Search Question Templates Tool (REQ-A-Mode1-Tool2).

REQ: REQ-A-Mode1-Tool2
Tests for search_question_templates() function that retrieves question templates.
"""

import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from src.agent.tools.search_templates_tool import _search_question_templates_impl


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def valid_search_params() -> dict[str, Any]:
    """Generate valid search parameters."""
    return {
        "interests": ["LLM", "RAG", "Agent Architecture"],
        "difficulty": 7,
        "category": "technical",
    }


@pytest.fixture
def mock_templates() -> list[MagicMock]:
    """Create sample QuestionTemplate objects."""
    templates = []
    template_data = [
        {
            "id": "tmpl_550e8400_e29b_41d4_a716_446655440001",
            "stem": "What is RAG?",
            "type": "short_answer",
            "choices": None,
            "correct_answer": "A technique combining retrieval and generation",
            "correct_rate": 0.85,
            "usage_count": 50,
            "avg_difficulty_score": 7.3,
            "domain": "RAG",
        },
        {
            "id": "tmpl_550e8400_e29b_41d4_a716_446655440002",
            "stem": "Explain Transformer architecture",
            "type": "short_answer",
            "choices": None,
            "correct_answer": "Neural network using attention mechanisms",
            "correct_rate": 0.78,
            "usage_count": 45,
            "avg_difficulty_score": 7.2,
            "domain": "LLM",
        },
    ]

    for data in template_data:
        template = MagicMock()
        for key, value in data.items():
            setattr(template, key, value)
        templates.append(template)

    return templates


@pytest.fixture
def mock_db() -> MagicMock:
    """Create a mock database session."""
    return MagicMock(spec=Session)


# ============================================================================
# Happy Path Tests
# ============================================================================


class TestSearchTemplatesHappyPath:
    """Tests for successful template search."""

    def test_search_templates_found_with_all_fields(
        self,
        valid_search_params: dict[str, Any],
        mock_templates: list[MagicMock],
        mock_db: MagicMock,
    ) -> None:
        """Test retrieving templates with all fields populated.

        REQ: REQ-A-Mode1-Tool2, AC1

        Given: Valid search parameters
        When: search_question_templates() is called
        Then: Returns list of templates sorted by correct_rate
        """
        # Setup
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_templates

        # Execute
        with patch(
            "src.agent.tools.search_templates_tool.get_db",
            return_value=iter([mock_db]),
        ):
            result = _search_question_templates_impl(
                valid_search_params["interests"],
                valid_search_params["difficulty"],
                valid_search_params["category"],
            )

        # Assert
        assert result is not None
        assert isinstance(result, list)
        assert len(result) <= 10
        assert all(isinstance(item, dict) for item in result)
        if len(result) > 0:
            assert "id" in result[0]
            assert "stem" in result[0]
            assert "type" in result[0]
            assert "correct_answer" in result[0]
            assert "correct_rate" in result[0]
            assert "usage_count" in result[0]
            assert "avg_difficulty_score" in result[0]

    def test_search_templates_found_multiple_candidates(
        self,
        valid_search_params: dict[str, Any],
        mock_db: MagicMock,
    ) -> None:
        """Test that maximum 10 templates are returned.

        REQ: REQ-A-Mode1-Tool2, AC1

        Given: 25 matching templates in database
        When: search_question_templates() is called
        Then: Returns only top 10 sorted by correct_rate
        """
        # Setup: Create 25 templates sorted by correct_rate descending
        mock_templates = []
        for i in range(25):
            template = MagicMock()
            template.id = f"tmpl_{i:03d}"
            template.stem = f"Question {i}"
            template.type = "multiple_choice"
            template.choices = ["A", "B", "C", "D"]
            template.correct_answer = "A"
            template.correct_rate = 0.90 - (i * 0.01)  # Descending
            template.usage_count = 100 - i
            template.avg_difficulty_score = 7.0
            template.domain = "LLM"
            mock_templates.append(template)

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_templates[:10]  # Only return top 10

        # Execute
        with patch(
            "src.agent.tools.search_templates_tool.get_db",
            return_value=iter([mock_db]),
        ):
            result = _search_question_templates_impl(
                valid_search_params["interests"],
                valid_search_params["difficulty"],
                valid_search_params["category"],
            )

        # Assert
        assert len(result) == 10
        for i in range(len(result) - 1):
            assert result[i]["correct_rate"] >= result[i + 1]["correct_rate"]

    def test_search_templates_with_multiple_interests(
        self,
        mock_db: MagicMock,
    ) -> None:
        """Test search with multiple interests.

        REQ: REQ-A-Mode1-Tool2

        Given: Multiple interests provided
        When: search_question_templates() is called
        Then: Returns templates matching any of the interests
        """
        # Setup
        mock_template1 = MagicMock()
        mock_template1.id = "tmpl_001"
        mock_template1.stem = "FastAPI question"
        mock_template1.domain = "FastAPI"
        mock_template1.correct_rate = 0.80
        mock_template1.usage_count = 30
        mock_template1.avg_difficulty_score = 6.0

        mock_template2 = MagicMock()
        mock_template2.id = "tmpl_002"
        mock_template2.stem = "Kubernetes question"
        mock_template2.domain = "Kubernetes"
        mock_template2.correct_rate = 0.75
        mock_template2.usage_count = 20
        mock_template2.avg_difficulty_score = 7.5

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_template1, mock_template2]

        interests = ["FastAPI", "DevOps", "Kubernetes"]

        # Execute
        with patch(
            "src.agent.tools.search_templates_tool.get_db",
            return_value=iter([mock_db]),
        ):
            result = _search_question_templates_impl(interests, 6, "technical")

        # Assert
        assert len(result) == 2
        assert result[0]["id"] == "tmpl_001"
        assert result[1]["id"] == "tmpl_002"

    def test_search_templates_with_difficulty_range(
        self,
        mock_db: MagicMock,
    ) -> None:
        """Test that difficulty filtering works (difficulty ± 1.5).

        REQ: REQ-A-Mode1-Tool2, AC4

        Given: difficulty=7 requested
        When: search_question_templates() is called
        Then: All results have avg_difficulty_score between 5.5-8.5
        """
        # Setup: Create templates with various difficulties
        difficulties = [3.0, 5.5, 7.0, 7.5, 8.5, 10.0]
        mock_templates = []
        for diff in difficulties:
            template = MagicMock()
            template.avg_difficulty_score = diff
            template.correct_rate = 0.80
            template.usage_count = 10
            mock_templates.append(template)

        # DB returns only those within range (5.5-8.5)
        filtered_templates = [t for t in mock_templates if 5.5 <= t.avg_difficulty_score <= 8.5]

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = filtered_templates

        # Execute
        with patch(
            "src.agent.tools.search_templates_tool.get_db",
            return_value=iter([mock_db]),
        ):
            result = _search_question_templates_impl(["LLM"], 7, "technical")

        # Assert
        for item in result:
            assert 5.5 <= item["avg_difficulty_score"] <= 8.5


# ============================================================================
# Data Not Found Tests
# ============================================================================


class TestSearchTemplatesNotFound:
    """Tests for when no templates match criteria."""

    def test_search_templates_not_found(
        self,
        valid_search_params: dict[str, Any],
        mock_db: MagicMock,
    ) -> None:
        """Test when no templates match search criteria.

        REQ: REQ-A-Mode1-Tool2, AC2

        Given: No templates match the criteria
        When: search_question_templates() is called
        Then: Returns empty list, no exception raised
        """
        # Setup
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []  # No results

        # Execute
        with patch(
            "src.agent.tools.search_templates_tool.get_db",
            return_value=iter([mock_db]),
        ):
            result = _search_question_templates_impl(
                ["VeryRareKeyword123"],
                valid_search_params["difficulty"],
                valid_search_params["category"],
            )

        # Assert
        assert result == []
        assert isinstance(result, list)


# ============================================================================
# Input Validation Tests
# ============================================================================


class TestSearchTemplatesInputValidation:
    """Tests for input validation."""

    def test_search_templates_invalid_interests_type(self) -> None:
        """Test rejection of invalid interests type.

        REQ: REQ-A-Mode1-Tool2, AC3

        Given: interests is not a list
        When: search_question_templates() is called
        Then: TypeError is raised
        """
        # Execute & Assert
        with pytest.raises(TypeError):
            _search_question_templates_impl("LLM", 7, "technical")

    def test_search_templates_invalid_difficulty(self) -> None:
        """Test rejection of difficulty out of range.

        REQ: REQ-A-Mode1-Tool2, AC3

        Given: difficulty=11 (out of range)
        When: search_question_templates() is called
        Then: ValueError is raised
        """
        # Execute & Assert
        with pytest.raises(ValueError):
            _search_question_templates_impl(["LLM"], 11, "technical")

    def test_search_templates_invalid_category(self) -> None:
        """Test rejection of unsupported category.

        REQ: REQ-A-Mode1-Tool2, AC3

        Given: category="unknown" (not supported)
        When: search_question_templates() is called
        Then: ValueError is raised
        """
        # Execute & Assert
        with pytest.raises(ValueError):
            _search_question_templates_impl(["LLM"], 7, "unknown")


# ============================================================================
# Database Error Tests
# ============================================================================


class TestSearchTemplatesDatabaseErrors:
    """Tests for database error handling."""

    def test_search_templates_db_connection_error(
        self,
        valid_search_params: dict[str, Any],
        mock_db: MagicMock,
    ) -> None:
        """Test handling of database connection errors.

        REQ: REQ-A-Mode1-Tool2, AC5

        Given: Database connection fails
        When: search_question_templates() is called
        Then: Returns empty list, no exception raised
        """
        # Setup
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.side_effect = OperationalError("Connection failed", None, None)

        # Execute
        with patch(
            "src.agent.tools.search_templates_tool.get_db",
            return_value=iter([mock_db]),
        ):
            result = _search_question_templates_impl(
                valid_search_params["interests"],
                valid_search_params["difficulty"],
                valid_search_params["category"],
            )

        # Assert
        assert isinstance(result, list)
        assert result == []

    def test_search_templates_query_timeout(
        self,
        valid_search_params: dict[str, Any],
        mock_db: MagicMock,
    ) -> None:
        """Test handling of query timeouts.

        REQ: REQ-A-Mode1-Tool2, AC5

        Given: Database query times out
        When: search_question_templates() is called
        Then: Returns empty list, no exception raised
        """
        # Setup
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.side_effect = Exception("Query timeout")

        # Execute
        with patch(
            "src.agent.tools.search_templates_tool.get_db",
            return_value=iter([mock_db]),
        ):
            result = _search_question_templates_impl(
                valid_search_params["interests"],
                valid_search_params["difficulty"],
                valid_search_params["category"],
            )

        # Assert
        assert isinstance(result, list)
        assert result == []


# ============================================================================
# Edge Cases Tests
# ============================================================================


class TestSearchTemplatesEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_search_templates_with_empty_interests_list(self) -> None:
        """Test rejection of empty interests list.

        REQ: REQ-A-Mode1-Tool2

        Given: interests=[] (empty list)
        When: search_question_templates() is called
        Then: ValueError is raised
        """
        # Execute & Assert
        with pytest.raises(ValueError):
            _search_question_templates_impl([], 7, "technical")

    def test_search_templates_with_unicode_characters(
        self,
        mock_db: MagicMock,
    ) -> None:
        """Test handling of unicode characters in template data.

        REQ: REQ-A-Mode1-Tool2

        Given: Template contains Korean text
        When: search_question_templates() is called
        Then: Unicode is properly preserved and returned
        """
        # Setup
        mock_template = MagicMock()
        mock_template.id = "tmpl_unicode_001"
        mock_template.stem = "머신러닝의 주요 개념은?"
        mock_template.type = "short_answer"
        mock_template.choices = None
        mock_template.correct_answer = "학습 알고리즘"
        mock_template.correct_rate = 0.82
        mock_template.usage_count = 25
        mock_template.avg_difficulty_score = 7.0
        mock_template.domain = "머신러닝"

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_template]

        # Execute
        with patch(
            "src.agent.tools.search_templates_tool.get_db",
            return_value=iter([mock_db]),
        ):
            result = _search_question_templates_impl(["머신러닝"], 7, "technical")

        # Assert
        assert len(result) >= 1
        assert result[0]["stem"] == "머신러닝의 주요 개념은?"
        assert result[0]["correct_answer"] == "학습 알고리즘"

    def test_search_templates_sorting_by_correct_rate(
        self,
        mock_db: MagicMock,
    ) -> None:
        """Test that results are sorted by correct_rate descending.

        REQ: REQ-A-Mode1-Tool2, AC1

        Given: Multiple templates with different correct_rates
        When: search_question_templates() is called
        Then: Results are sorted by correct_rate descending
        """
        # Setup
        templates = []
        rates = [0.50, 0.90, 0.70]
        for i, rate in enumerate(rates):
            template = MagicMock()
            template.id = f"tmpl_{i}"
            template.correct_rate = rate
            template.usage_count = 10
            template.avg_difficulty_score = 7.0
            templates.append(template)

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        # DB returns already sorted
        mock_query.all.return_value = [templates[1], templates[2], templates[0]]

        # Execute
        with patch(
            "src.agent.tools.search_templates_tool.get_db",
            return_value=iter([mock_db]),
        ):
            result = _search_question_templates_impl(["LLM"], 7, "technical")

        # Assert
        assert result[0]["correct_rate"] == 0.90
        assert result[1]["correct_rate"] == 0.70
        assert result[2]["correct_rate"] == 0.50
