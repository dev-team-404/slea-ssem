"""
Tests for ANSWER_SCHEMA_FORMATS.md documentation accuracy.

REQ: REQ-REFACTOR-SOLID-3 (Answer Schema Formats Documentation)

This test suite verifies that:
1. All format examples in the documentation are valid and work correctly
2. Transformation pipeline examples work end-to-end
3. All code examples in docs are copy-paste ready
4. Validation rules in docs match actual implementation
5. Documentation is accessible and complete

Test Cases:
- TestFormatExamples: Verify each format example in docs is valid
- TestTransformationFlow: Verify transformation pipeline examples work
- TestValidationRules: Verify validation rules match implementation
- TestDocumentation: Verify docs structure and completeness
"""

import pytest
from datetime import datetime
from src.backend.models.answer_schema import (
    AnswerSchema,
    AnswerSchemaTransformer,
    AgentResponseTransformer,
    MockDataTransformer,
    TransformerFactory,
    ValidationError,
    UnknownFormatError,
)


class TestFormatExamples:
    """Verify all format examples from documentation are valid."""

    def test_agent_response_format_example_basic(self) -> None:
        """Agent Response Format - Example 1: Basic keyword matching."""
        # From docs: Agent Response Format section
        raw_agent_response = {
            "correct_keywords": ["리튬이온", "배터리"],
            "explanation": "리튬이온 배터리는 높은 에너지 밀도를 가진다.",
        }

        transformer = AgentResponseTransformer()
        result = transformer.transform(raw_agent_response)

        assert result["type"] == "keyword_match"
        assert result["keywords"] == ["리튬이온", "배터리"]
        assert result["explanation"] == "리튬이온 배터리는 높은 에너지 밀도를 가진다."
        assert result["source_format"] == "agent_response"

    def test_agent_response_format_example_multiple_keywords(self) -> None:
        """Agent Response Format - Example 2: Multiple acceptable keywords."""
        raw_agent_response = {
            "correct_keywords": ["battery", "cell", "accumulator"],
            "explanation": "A battery is an electrochemical energy storage device.",
        }

        transformer = AgentResponseTransformer()
        result = transformer.transform(raw_agent_response)

        assert result["type"] == "keyword_match"
        assert len(result["keywords"]) == 3
        assert "battery" in result["keywords"]
        assert "cell" in result["keywords"]

    def test_agent_response_format_example_unicode(self) -> None:
        """Agent Response Format - Example 3: Unicode/multilingual support."""
        raw_agent_response = {
            "correct_keywords": ["전자기파", "電磁波", "💡"],
            "explanation": "전자기파는 에너지를 전달하는 파동이다.",
        }

        transformer = AgentResponseTransformer()
        result = transformer.transform(raw_agent_response)

        assert "전자기파" in result["keywords"]
        assert len(result["keywords"]) == 3

    def test_mock_data_format_example_basic(self) -> None:
        """Mock Data Format - Example 1: Simple multiple choice."""
        # From docs: Mock Data Format section
        raw_mock_data = {
            "correct_key": "B",
            "explanation": "Option B is the correct answer because...",
        }

        transformer = MockDataTransformer()
        result = transformer.transform(raw_mock_data)

        assert result["type"] == "exact_match"
        assert result["correct_answer"] == "B"
        assert result["explanation"] == "Option B is the correct answer because..."
        assert result["source_format"] == "mock_data"

    def test_mock_data_format_example_numeric_answer(self) -> None:
        """Mock Data Format - Example 2: Numeric answer (as string)."""
        raw_mock_data = {
            "correct_key": "42",
            "explanation": "The answer to life, universe, and everything is 42.",
        }

        transformer = MockDataTransformer()
        result = transformer.transform(raw_mock_data)

        assert result["correct_answer"] == "42"
        assert result["type"] == "exact_match"

    def test_mock_data_format_example_complex_answer(self) -> None:
        """Mock Data Format - Example 3: Complex answer (formatted text)."""
        raw_mock_data = {
            "correct_key": "F(x) = x^2 + 2x + 1",
            "explanation": "This is a quadratic function.",
        }

        transformer = MockDataTransformer()
        result = transformer.transform(raw_mock_data)

        assert result["correct_answer"] == "F(x) = x^2 + 2x + 1"


class TestTransformationFlow:
    """Verify transformation pipeline examples work end-to-end."""

    def test_transformation_flow_agent_to_db(self) -> None:
        """Agent Response → Transformer → AnswerSchema → DB Format."""
        # Step 1: Agent Response (LLM returns)
        agent_response = {
            "correct_keywords": ["배터리", "리튬"],
            "explanation": "리튬이온 배터리는 고에너지 밀도를 가진다.",
        }

        # Step 2: Transform using factory
        factory = TransformerFactory()
        transformer = factory.get_transformer("agent_response")
        transformed = transformer.transform(agent_response)

        # Step 3: Create AnswerSchema Value Object
        answer_schema = AnswerSchema(
            type=transformed["type"],
            keywords=transformed.get("keywords"),
            correct_answer=transformed.get("correct_answer"),
            explanation=transformed.get("explanation", ""),
            source_format=transformed.get("source_format", "agent_response"),
        )

        # Step 4: Convert to DB format
        db_dict = answer_schema.to_db_dict()

        assert db_dict["type"] == "keyword_match"
        assert db_dict["keywords"] == ["배터리", "리튬"]
        assert "created_at" in db_dict
        assert db_dict["source_format"] == "agent_response"

    def test_transformation_flow_mock_to_db(self) -> None:
        """Mock Data → Transformer → AnswerSchema → DB Format."""
        # Step 1: Mock data
        mock_data = {
            "correct_key": "정답",
            "explanation": "이것이 정답이다.",
        }

        # Step 2: Transform using factory
        factory = TransformerFactory()
        transformer = factory.get_transformer("mock_data")
        transformed = transformer.transform(mock_data)

        # Step 3: Create AnswerSchema
        answer_schema = AnswerSchema(
            type=transformed["type"],
            keywords=transformed.get("keywords"),
            correct_answer=transformed.get("correct_answer"),
            explanation=transformed.get("explanation", ""),
            source_format=transformed.get("source_format", "mock_data"),
        )

        # Step 4: To DB format
        db_dict = answer_schema.to_db_dict()

        assert db_dict["type"] == "exact_match"
        assert db_dict["correct_answer"] == "정답"

    def test_transformation_flow_with_factory_methods(self) -> None:
        """Transformation using factory methods (recommended pattern)."""
        agent_response = {
            "correct_keywords": ["키워드1", "키워드2"],
            "explanation": "설명",
        }

        # Recommended way: use factory method
        answer_schema = AnswerSchema.from_agent_response(agent_response)

        assert answer_schema.type == "keyword_match"
        assert answer_schema.keywords == ["키워드1", "키워드2"]

        # Convert for API response (excludes source_format, created_at)
        api_dict = answer_schema.to_response_dict()
        assert "source_format" not in api_dict
        assert "created_at" not in api_dict
        assert "explanation" in api_dict

    def test_transformation_flow_factory_pattern_agent(self) -> None:
        """Code example from docs: Using TransformerFactory with Agent response."""
        # From ANSWER_SCHEMA_FORMATS.md Section 8: Code Examples
        factory = TransformerFactory()
        transformer = factory.get_transformer("agent_response")

        # Transform raw data
        raw_data = {
            "correct_keywords": ["answer1", "answer2"],
            "explanation": "Explanation text",
        }
        transformed = transformer.transform(raw_data)

        # Create Value Object
        answer_schema = AnswerSchema(
            type=transformed["type"],
            keywords=transformed.get("keywords"),
            explanation=transformed.get("explanation", ""),
            source_format=transformed.get("source_format", "agent_response"),
        )

        # Convert to DB format
        db_dict = answer_schema.to_db_dict()

        assert isinstance(db_dict, dict)
        assert "keywords" in db_dict
        assert "source_format" in db_dict
        assert "created_at" in db_dict

    def test_transformation_flow_factory_pattern_mock(self) -> None:
        """Code example from docs: Using TransformerFactory with Mock data."""
        factory = TransformerFactory()
        transformer = factory.get_transformer("mock_data")

        # Transform raw mock data
        raw_data = {
            "correct_key": "answer",
            "explanation": "Explanation",
        }
        transformed = transformer.transform(raw_data)

        # Create Value Object
        answer_schema = AnswerSchema(
            type=transformed["type"],
            correct_answer=transformed.get("correct_answer"),
            explanation=transformed.get("explanation", ""),
            source_format=transformed.get("source_format", "mock_data"),
        )

        db_dict = answer_schema.to_db_dict()

        assert db_dict["correct_answer"] == "answer"
        assert db_dict["type"] == "exact_match"


class TestValidationRules:
    """Verify validation rules from documentation match implementation."""

    def test_validation_type_required(self) -> None:
        """Validation Rule: type must be non-empty string."""
        # Should fail with empty type
        with pytest.raises(ValidationError, match="type.*empty"):
            AnswerSchema(
                type="",
                keywords=["answer"],
                explanation="test",
            )

    def test_validation_keywords_must_be_list(self) -> None:
        """Validation Rule: keywords must be list[str] or None."""
        # Should fail if keywords is string instead of list
        with pytest.raises(TypeError, match="keywords.*must be list"):
            AnswerSchema(
                type="keyword_match",
                keywords="not_a_list",  # type: ignore
                explanation="test",
            )

    def test_validation_correct_answer_must_be_string(self) -> None:
        """Validation Rule: correct_answer must be str or None."""
        # Should fail if correct_answer is list
        with pytest.raises(TypeError, match="correct_answer.*must be str"):
            AnswerSchema(
                type="exact_match",
                correct_answer=["list"],  # type: ignore
                explanation="test",
            )

    def test_validation_explanation_required_non_empty(self) -> None:
        """Validation Rule: explanation must be non-empty string."""
        # Should fail with empty explanation
        with pytest.raises(ValidationError, match="explanation.*empty"):
            AnswerSchema(
                type="keyword_match",
                keywords=["answer"],
                explanation="",
            )

    def test_validation_at_least_one_answer_field(self) -> None:
        """Validation Rule: Either keywords or correct_answer required (not both None)."""
        # Should fail if both are None
        with pytest.raises(ValidationError, match="keywords.*correct_answer.*both None"):
            AnswerSchema(
                type="keyword_match",
                keywords=None,
                correct_answer=None,
                explanation="test",
            )

    def test_validation_source_format_required(self) -> None:
        """Validation Rule: source_format must be non-empty string."""
        # Should fail with empty source_format
        with pytest.raises(TypeError):
            # source_format must be string, not empty
            AnswerSchema(
                type="keyword_match",
                keywords=["answer"],
                explanation="test",
                source_format=None,  # type: ignore
            )

    def test_validation_agent_response_missing_keywords(self) -> None:
        """Validation Rule: Agent response must have correct_keywords field."""
        transformer = AgentResponseTransformer()

        with pytest.raises(ValidationError, match="correct_keywords"):
            transformer.transform({"explanation": "test"})

    def test_validation_agent_response_missing_explanation(self) -> None:
        """Validation Rule: Agent response must have explanation field."""
        transformer = AgentResponseTransformer()

        with pytest.raises(ValidationError, match="explanation"):
            transformer.transform({"correct_keywords": ["answer"]})

    def test_validation_agent_keywords_must_be_list(self) -> None:
        """Validation Rule: Agent correct_keywords must be list."""
        transformer = AgentResponseTransformer()

        with pytest.raises(TypeError, match="correct_keywords.*list"):
            transformer.transform(
                {
                    "correct_keywords": "string_not_list",
                    "explanation": "test",
                }
            )

    def test_validation_agent_keywords_not_empty(self) -> None:
        """Validation Rule: Agent correct_keywords cannot be empty list."""
        transformer = AgentResponseTransformer()

        with pytest.raises(ValidationError, match="cannot be empty"):
            transformer.transform(
                {
                    "correct_keywords": [],
                    "explanation": "test",
                }
            )

    def test_validation_mock_missing_correct_key(self) -> None:
        """Validation Rule: Mock data must have correct_key field."""
        transformer = MockDataTransformer()

        with pytest.raises(ValidationError, match="correct_key"):
            transformer.transform({"explanation": "test"})

    def test_validation_mock_missing_explanation(self) -> None:
        """Validation Rule: Mock data must have explanation field."""
        transformer = MockDataTransformer()

        with pytest.raises(ValidationError, match="explanation"):
            transformer.transform({"correct_key": "B"})

    def test_validation_mock_key_must_be_string(self) -> None:
        """Validation Rule: Mock correct_key must be string."""
        transformer = MockDataTransformer()

        with pytest.raises(TypeError, match="correct_key.*string"):
            transformer.transform(
                {
                    "correct_key": 123,  # type: ignore
                    "explanation": "test",
                }
            )

    def test_validation_mock_key_not_empty(self) -> None:
        """Validation Rule: Mock correct_key cannot be empty."""
        transformer = MockDataTransformer()

        with pytest.raises(ValidationError, match="cannot be empty"):
            transformer.transform(
                {
                    "correct_key": "",
                    "explanation": "test",
                }
            )


class TestDocumentation:
    """Verify documentation completeness and accessibility."""

    def test_transformer_factory_get_agent_response(self) -> None:
        """Documentation: TransformerFactory supports agent_response format."""
        factory = TransformerFactory()
        transformer = factory.get_transformer("agent_response")
        assert isinstance(transformer, AgentResponseTransformer)

    def test_transformer_factory_get_mock_data(self) -> None:
        """Documentation: TransformerFactory supports mock_data format."""
        factory = TransformerFactory()
        transformer = factory.get_transformer("mock_data")
        assert isinstance(transformer, MockDataTransformer)

    def test_transformer_factory_unknown_format_error(self) -> None:
        """Documentation: TransformerFactory raises error for unknown formats."""
        factory = TransformerFactory()

        with pytest.raises(UnknownFormatError, match="Unknown format type"):
            factory.get_transformer("unknown_format")

    def test_answer_schema_factory_from_agent_response(self) -> None:
        """Documentation: AnswerSchema.from_agent_response() method exists."""
        schema = AnswerSchema.from_agent_response(
            {
                "correct_keywords": ["답"],
                "explanation": "설명",
            }
        )
        assert schema.keywords == ["답"]
        assert schema.source_format == "agent_response"

    def test_answer_schema_factory_from_mock_data(self) -> None:
        """Documentation: AnswerSchema.from_mock_data() method exists."""
        schema = AnswerSchema.from_mock_data(
            {
                "correct_key": "B",
                "explanation": "설명",
            }
        )
        assert schema.correct_answer == "B"
        assert schema.source_format == "mock_data"

    def test_answer_schema_to_db_dict(self) -> None:
        """Documentation: AnswerSchema.to_db_dict() includes all metadata."""
        schema = AnswerSchema.from_agent_response(
            {
                "correct_keywords": ["답"],
                "explanation": "설명",
            }
        )
        db_dict = schema.to_db_dict()

        assert "type" in db_dict
        assert "keywords" in db_dict
        assert "explanation" in db_dict
        assert "source_format" in db_dict
        assert "created_at" in db_dict

    def test_answer_schema_to_response_dict(self) -> None:
        """Documentation: AnswerSchema.to_response_dict() excludes internal metadata."""
        schema = AnswerSchema.from_agent_response(
            {
                "correct_keywords": ["답"],
                "explanation": "설명",
            }
        )
        api_dict = schema.to_response_dict()

        # Should include
        assert "type" in api_dict
        assert "keywords" in api_dict
        assert "explanation" in api_dict

        # Should NOT include
        assert "source_format" not in api_dict
        assert "created_at" not in api_dict

    def test_documentation_example_migration_as_is_to_be(self) -> None:
        """Documentation: Migration example (AS-IS → TO-BE) works correctly."""
        # TO-BE: Using TransformerFactory and AnswerSchema
        factory = TransformerFactory()
        transformer = factory.get_transformer("agent_response")

        answer_schema_data = {
            "correct_keywords": ["배터리"],
            "explanation": "배터리는...",
        }

        transformed = transformer.transform(answer_schema_data)
        answer_schema = AnswerSchema(
            type=transformed["type"],
            keywords=transformed.get("keywords"),
            explanation=transformed.get("explanation", ""),
            source_format=transformed.get("source_format", "agent_response"),
        )

        # Result should always be valid (not None)
        assert answer_schema.keywords is not None
        assert answer_schema.explanation is not None

    def test_immutability_frozen_dataclass(self) -> None:
        """Documentation: AnswerSchema is immutable (frozen dataclass)."""
        schema = AnswerSchema.from_agent_response(
            {
                "correct_keywords": ["답"],
                "explanation": "설명",
            }
        )

        # Should not be able to modify
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            schema.keywords = ["modified"]  # type: ignore

    def test_value_object_equality(self) -> None:
        """Documentation: AnswerSchema Value Objects with same data are equal."""
        from datetime import datetime

        # Use explicit created_at to ensure equality
        now = datetime.now()
        data = {
            "correct_keywords": ["답"],
            "explanation": "설명",
        }

        schema1 = AnswerSchema.from_agent_response(data)
        schema2 = AnswerSchema.from_agent_response(data)

        # Note: created_at is auto-set to now() on each instance, so they will differ
        # Instead, test with explicit created_at for equality
        schema1_explicit = AnswerSchema(
            type="keyword_match",
            keywords=["답"],
            explanation="설명",
            source_format="agent_response",
            created_at=now
        )
        schema2_explicit = AnswerSchema(
            type="keyword_match",
            keywords=["답"],
            explanation="설명",
            source_format="agent_response",
            created_at=now
        )

        # Same data and created_at should be equal
        assert schema1_explicit == schema2_explicit

    def test_value_object_hashable(self) -> None:
        """Documentation: AnswerSchema can be used in sets and as dict keys."""
        schema = AnswerSchema.from_agent_response(
            {
                "correct_keywords": ["답"],
                "explanation": "설명",
            }
        )

        # Should be hashable
        schema_set = {schema}
        assert len(schema_set) == 1

        # Should work as dict key
        schema_dict = {schema: "value"}
        assert schema_dict[schema] == "value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
