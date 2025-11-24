"""
Comprehensive unit tests for AnswerSchemaTransformer pattern.

REQ: REQ-REFACTOR-SOLID-1
Phase 3: Implementation + Tests

Test coverage:
- AnswerSchemaTransformer (abstract base class)
- AgentResponseTransformer (correct_keywords → keywords)
- MockDataTransformer (correct_key → correct_answer)
- TransformerFactory (format type selection)

Test categories:
1. Happy path (valid transformations)
2. Input validation (missing/invalid fields)
3. Edge cases (null, empty, unicode)
4. Type validation (expected types)
5. Factory pattern tests
6. Integration tests

Total: 37 comprehensive test cases
"""

import pytest
from typing import Any, Dict

from src.backend.models.answer_schema import (
    AnswerSchemaTransformer,
    AgentResponseTransformer,
    MockDataTransformer,
    TransformerFactory,
    ValidationError,
    UnknownFormatError,
)


class TestAnswerSchemaTransformerInterface:
    """Test AnswerSchemaTransformer abstract base class."""

    def test_abstract_class_cannot_be_instantiated(self) -> None:
        """Cannot instantiate abstract AnswerSchemaTransformer directly."""
        with pytest.raises(TypeError):
            AnswerSchemaTransformer()  # type: ignore

    def test_subclass_must_implement_transform(self) -> None:
        """Subclass without transform() raises TypeError."""
        class IncompleteTransformer(AnswerSchemaTransformer):
            """Transformer without transform() implementation."""
            pass

        with pytest.raises(TypeError):
            IncompleteTransformer()  # type: ignore


class TestAgentResponseTransformer:
    """Test AgentResponseTransformer for Agent LLM response format."""

    # Happy Path Tests
    def test_basic_agent_response_transformation(self) -> None:
        """TC-1: Transform basic agent response with correct_keywords."""
        transformer = AgentResponseTransformer()
        raw_data = {
            "correct_keywords": ["battery", "lithium"],
            "explanation": "Lithium-ion batteries store energy..."
        }

        result = transformer.transform(raw_data)

        assert result["type"] == "keyword_match"
        assert result["keywords"] == ["battery", "lithium"]
        assert result["explanation"] == "Lithium-ion batteries store energy..."
        assert result["source_format"] == "agent_response"

    def test_agent_response_with_single_keyword(self) -> None:
        """TC-2: Transform agent response with single keyword in list."""
        transformer = AgentResponseTransformer()
        raw_data = {
            "correct_keywords": ["single_key"],
            "explanation": "Only one keyword"
        }

        result = transformer.transform(raw_data)

        assert result["keywords"] == ["single_key"]
        assert len(result["keywords"]) == 1

    def test_agent_response_with_unicode_keywords(self) -> None:
        """TC-3: Transform agent response with Korean/Unicode keywords."""
        transformer = AgentResponseTransformer()
        raw_data = {
            "correct_keywords": ["배터리", "리튬이온"],
            "explanation": "리튬이온 배터리는..."
        }

        result = transformer.transform(raw_data)

        assert result["keywords"] == ["배터리", "리튬이온"]
        assert result["explanation"] == "리튬이온 배터리는..."

    def test_agent_response_with_very_long_explanation(self) -> None:
        """TC-4: Transform agent response with lengthy explanation (5000+ chars)."""
        transformer = AgentResponseTransformer()
        long_explanation = "This is a very long explanation. " * 200
        raw_data = {
            "correct_keywords": ["key1", "key2"],
            "explanation": long_explanation
        }

        result = transformer.transform(raw_data)

        assert result["explanation"] == long_explanation
        assert len(result["explanation"]) > 5000

    # Input Validation Tests
    def test_agent_response_missing_correct_keywords(self) -> None:
        """TC-5: Error when correct_keywords field missing."""
        transformer = AgentResponseTransformer()
        raw_data = {
            "explanation": "Missing keywords field"
        }

        with pytest.raises(ValidationError, match="correct_keywords"):
            transformer.transform(raw_data)

    def test_agent_response_missing_explanation(self) -> None:
        """TC-6: Error when explanation field missing."""
        transformer = AgentResponseTransformer()
        raw_data = {
            "correct_keywords": ["key1"]
        }

        with pytest.raises(ValidationError, match="explanation"):
            transformer.transform(raw_data)

    def test_agent_response_empty_keywords_list(self) -> None:
        """TC-7: Error when keywords list is empty."""
        transformer = AgentResponseTransformer()
        raw_data = {
            "correct_keywords": [],
            "explanation": "..."
        }

        with pytest.raises(ValidationError, match="empty"):
            transformer.transform(raw_data)

    def test_agent_response_null_keywords(self) -> None:
        """TC-8: Error when keywords is None."""
        transformer = AgentResponseTransformer()
        raw_data = {
            "correct_keywords": None,
            "explanation": "..."
        }

        with pytest.raises(TypeError):
            transformer.transform(raw_data)

    def test_agent_response_keywords_not_list(self) -> None:
        """TC-9: Error when keywords is string instead of list."""
        transformer = AgentResponseTransformer()
        raw_data = {
            "correct_keywords": "not a list",
            "explanation": "..."
        }

        with pytest.raises(TypeError, match="list"):
            transformer.transform(raw_data)

    def test_agent_response_empty_explanation(self) -> None:
        """TC-10: Error when explanation is empty string."""
        transformer = AgentResponseTransformer()
        raw_data = {
            "correct_keywords": ["key"],
            "explanation": ""
        }

        with pytest.raises(ValidationError):
            transformer.transform(raw_data)

    def test_agent_response_extra_fields_ignored(self) -> None:
        """TC-11: Extra fields in input are ignored."""
        transformer = AgentResponseTransformer()
        raw_data = {
            "correct_keywords": ["key"],
            "explanation": "Valid explanation",
            "extra_field": "should be ignored",
            "another_field": 123
        }

        result = transformer.transform(raw_data)

        assert "extra_field" not in result
        assert "another_field" not in result
        assert result["keywords"] == ["key"]


class TestMockDataTransformer:
    """Test MockDataTransformer for mock test data format."""

    # Happy Path Tests
    def test_basic_mock_data_transformation(self) -> None:
        """TC-12: Transform basic mock data with correct_key."""
        transformer = MockDataTransformer()
        raw_data = {
            "correct_key": "B",
            "explanation": "Answer B is correct because..."
        }

        result = transformer.transform(raw_data)

        assert result["type"] == "exact_match"
        assert result["correct_answer"] == "B"
        assert result["explanation"] == "Answer B is correct because..."
        assert result["source_format"] == "mock_data"

    def test_mock_data_with_longer_key(self) -> None:
        """TC-13: Transform mock data with longer answer key (e.g., 'true', 'false')."""
        transformer = MockDataTransformer()
        raw_data = {
            "correct_key": "true",
            "explanation": "Statement is true"
        }

        result = transformer.transform(raw_data)

        assert result["type"] == "exact_match"
        assert result["correct_answer"] == "true"

    def test_mock_data_with_numeric_string_key(self) -> None:
        """TC-14: Transform mock data with numeric string key."""
        transformer = MockDataTransformer()
        raw_data = {
            "correct_key": "3",
            "explanation": "Answer is 3"
        }

        result = transformer.transform(raw_data)

        assert result["correct_answer"] == "3"
        assert isinstance(result["correct_answer"], str)

    def test_mock_data_with_unicode_explanation(self) -> None:
        """TC-15: Transform mock data with Korean explanation."""
        transformer = MockDataTransformer()
        raw_data = {
            "correct_key": "답",
            "explanation": "이것이 정답입니다"
        }

        result = transformer.transform(raw_data)

        assert result["correct_answer"] == "답"
        assert result["explanation"] == "이것이 정답입니다"

    # Input Validation Tests
    def test_mock_data_missing_correct_key(self) -> None:
        """TC-16: Error when correct_key field missing."""
        transformer = MockDataTransformer()
        raw_data = {
            "explanation": "No correct_key"
        }

        with pytest.raises(ValidationError, match="correct_key"):
            transformer.transform(raw_data)

    def test_mock_data_missing_explanation(self) -> None:
        """TC-17: Error when explanation field missing."""
        transformer = MockDataTransformer()
        raw_data = {
            "correct_key": "B"
        }

        with pytest.raises(ValidationError, match="explanation"):
            transformer.transform(raw_data)

    def test_mock_data_empty_dict(self) -> None:
        """TC-18: Error when input is empty dict."""
        transformer = MockDataTransformer()
        raw_data: Dict[str, Any] = {}

        with pytest.raises(ValidationError):
            transformer.transform(raw_data)

    def test_mock_data_null_correct_key(self) -> None:
        """TC-19: Error when correct_key is None."""
        transformer = MockDataTransformer()
        raw_data = {
            "correct_key": None,
            "explanation": "..."
        }

        with pytest.raises(TypeError):
            transformer.transform(raw_data)

    def test_mock_data_empty_correct_key(self) -> None:
        """TC-20: Error when correct_key is empty string."""
        transformer = MockDataTransformer()
        raw_data = {
            "correct_key": "",
            "explanation": "..."
        }

        with pytest.raises(ValidationError):
            transformer.transform(raw_data)

    def test_mock_data_correct_key_not_string(self) -> None:
        """TC-21: Error when correct_key is not string (e.g., list)."""
        transformer = MockDataTransformer()
        raw_data = {
            "correct_key": ["A", "B"],
            "explanation": "..."
        }

        with pytest.raises(TypeError):
            transformer.transform(raw_data)

    def test_mock_data_empty_explanation(self) -> None:
        """TC-22: Error when explanation is empty."""
        transformer = MockDataTransformer()
        raw_data = {
            "correct_key": "B",
            "explanation": ""
        }

        with pytest.raises(ValidationError):
            transformer.transform(raw_data)


class TestTransformerFactory:
    """Test TransformerFactory for format type selection."""

    def test_factory_get_agent_response_transformer(self) -> None:
        """TC-23: Factory returns AgentResponseTransformer for 'agent_response'."""
        factory = TransformerFactory()
        transformer = factory.get_transformer("agent_response")

        assert isinstance(transformer, AgentResponseTransformer)

    def test_factory_get_mock_data_transformer(self) -> None:
        """TC-24: Factory returns MockDataTransformer for 'mock_data'."""
        factory = TransformerFactory()
        transformer = factory.get_transformer("mock_data")

        assert isinstance(transformer, MockDataTransformer)

    def test_factory_unknown_format_type_raises_error(self) -> None:
        """TC-25: Factory raises error for unknown format type."""
        factory = TransformerFactory()

        with pytest.raises(UnknownFormatError, match="format"):
            factory.get_transformer("unknown_format")

    def test_factory_case_insensitive_format_type(self) -> None:
        """TC-26: Factory handles case variations (case-insensitive)."""
        factory = TransformerFactory()

        t1 = factory.get_transformer("AGENT_RESPONSE")
        t2 = factory.get_transformer("Agent_Response")
        t3 = factory.get_transformer("agent_response")

        assert isinstance(t1, AgentResponseTransformer)
        assert isinstance(t2, AgentResponseTransformer)
        assert isinstance(t3, AgentResponseTransformer)

    def test_factory_returns_new_instance_each_call(self) -> None:
        """TC-27: Each factory.get_transformer() call returns new instance."""
        factory = TransformerFactory()
        t1 = factory.get_transformer("agent_response")
        t2 = factory.get_transformer("agent_response")

        assert t1 is not t2

    def test_factory_returned_transformer_works_correctly(self) -> None:
        """TC-28: Transformer returned by factory works correctly."""
        factory = TransformerFactory()
        transformer = factory.get_transformer("agent_response")
        raw_data = {
            "correct_keywords": ["key1", "key2"],
            "explanation": "Test explanation"
        }

        result = transformer.transform(raw_data)

        assert result["type"] == "keyword_match"
        assert result["keywords"] == ["key1", "key2"]


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_transformer_with_special_characters_in_keywords(self) -> None:
        """TC-29: Handle special characters in keywords (@, #, $, etc)."""
        transformer = AgentResponseTransformer()
        raw_data = {
            "correct_keywords": ["@python", "#hashtag", "$dollar"],
            "explanation": "Special chars..."
        }

        result = transformer.transform(raw_data)

        assert result["keywords"] == ["@python", "#hashtag", "$dollar"]

    def test_transformer_with_very_long_keyword_list(self) -> None:
        """TC-30: Handle large number of keywords (50+ items)."""
        transformer = AgentResponseTransformer()
        raw_data = {
            "correct_keywords": [f"keyword_{i}" for i in range(50)],
            "explanation": "Many keywords..."
        }

        result = transformer.transform(raw_data)

        assert len(result["keywords"]) == 50

    def test_transformer_with_whitespace_in_keywords(self) -> None:
        """TC-31: Handle keywords with leading/trailing whitespace."""
        transformer = AgentResponseTransformer()
        raw_data = {
            "correct_keywords": ["  key1  ", "\tkey2\t", "\nkey3\n"],
            "explanation": "Whitespace keywords..."
        }

        result = transformer.transform(raw_data)

        # Preserves whitespace as-is (doesn't trim)
        assert result["keywords"] == ["  key1  ", "\tkey2\t", "\nkey3\n"]

    def test_transformer_with_newlines_in_explanation(self) -> None:
        """TC-32: Handle multi-line explanation text."""
        transformer = AgentResponseTransformer()
        raw_data = {
            "correct_keywords": ["key"],
            "explanation": "Line 1\nLine 2\nLine 3\n\nMultiple newlines"
        }

        result = transformer.transform(raw_data)

        assert "\n" in result["explanation"]
        assert result["explanation"] == "Line 1\nLine 2\nLine 3\n\nMultiple newlines"

    def test_transformer_with_json_in_explanation(self) -> None:
        """TC-33: Handle JSON-like content in explanation (escaped)."""
        transformer = AgentResponseTransformer()
        raw_data = {
            "correct_keywords": ["key"],
            "explanation": 'Example: {"field": "value", "array": [1, 2, 3]}'
        }

        result = transformer.transform(raw_data)

        assert result["explanation"] == 'Example: {"field": "value", "array": [1, 2, 3]}'


class TestIntegration:
    """Integration tests with broader system."""

    def test_transformer_output_compatible_with_question_model(self) -> None:
        """TC-34: Transformer output can be stored in Question.answer_schema."""
        transformer = AgentResponseTransformer()
        raw_data = {
            "correct_keywords": ["key1", "key2"],
            "explanation": "Test explanation"
        }

        result = transformer.transform(raw_data)

        # Result should have all required fields for storage in Question.answer_schema
        assert "type" in result
        assert "explanation" in result
        assert "source_format" in result
        assert result["type"] in ["keyword_match", "exact_match"]

    def test_multiple_transformations_same_factory(self) -> None:
        """TC-35: Factory can handle multiple consecutive transformations."""
        factory = TransformerFactory()

        raw_data_agent = {
            "correct_keywords": ["key1"],
            "explanation": "Agent format"
        }
        raw_data_mock = {
            "correct_key": "B",
            "explanation": "Mock format"
        }

        transformer_agent = factory.get_transformer("agent_response")
        result_agent = transformer_agent.transform(raw_data_agent)

        transformer_mock = factory.get_transformer("mock_data")
        result_mock = transformer_mock.transform(raw_data_mock)

        assert result_agent["type"] == "keyword_match"
        assert result_mock["type"] == "exact_match"

    def test_transformer_preserves_all_required_fields(self) -> None:
        """TC-36: Transformer output preserves all required fields for DB storage."""
        agent_transformer = AgentResponseTransformer()
        mock_transformer = MockDataTransformer()

        agent_data = {
            "correct_keywords": ["key"],
            "explanation": "Explanation"
        }
        mock_data = {
            "correct_key": "A",
            "explanation": "Explanation"
        }

        agent_result = agent_transformer.transform(agent_data)
        mock_result = mock_transformer.transform(mock_data)

        # Both should have complete structure
        assert "type" in agent_result
        assert "keywords" in agent_result
        assert "explanation" in agent_result
        assert "source_format" in agent_result

        assert "type" in mock_result
        assert "correct_answer" in mock_result
        assert "explanation" in mock_result
        assert "source_format" in mock_result

    def test_transformer_error_messages_are_helpful(self) -> None:
        """TC-37: Error messages provide actionable guidance."""
        transformer = AgentResponseTransformer()

        # Test that error messages mention expected field names
        with pytest.raises(ValidationError) as exc_info:
            transformer.transform({})

        error_message = str(exc_info.value)
        assert "correct_keywords" in error_message
        assert "explanation" in error_message


# Test data fixtures
@pytest.fixture
def agent_response_data() -> Dict[str, Any]:
    """Sample Agent response format."""
    return {
        "correct_keywords": ["battery", "lithium"],
        "explanation": "Lithium-ion batteries are rechargeable..."
    }


@pytest.fixture
def mock_data() -> Dict[str, Any]:
    """Sample Mock data format."""
    return {
        "correct_key": "B",
        "explanation": "Answer B is correct because..."
    }


@pytest.fixture
def factory() -> TransformerFactory:
    """TransformerFactory instance for tests."""
    return TransformerFactory()
