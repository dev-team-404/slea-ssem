"""
AnswerSchemaTransformer pattern for normalizing diverse answer_schema formats.

REQ: REQ-REFACTOR-SOLID-1
Implementation: Transformer Pattern + Factory Pattern

This module provides a SOLID-based approach to handling multiple answer_schema
formats from different sources (LLM Agent, Mock data, etc.) without modifying
existing code when new formats are added.

SOLID Principles:
- Single Responsibility: Each transformer handles one format
- Open/Closed: New formats extend abstract class, existing code unchanged
- Liskov Substitution: All transformers implement same interface
- Interface Segregation: Factory provides minimal interface
- Dependency Inversion: Depends on abstract interface, not concrete classes

Classes:
- AnswerSchemaTransformer: Abstract base class defining interface
- AgentResponseTransformer: Converts Agent LLM format to standard
- MockDataTransformer: Converts Mock test data format to standard
- TransformerFactory: Creates appropriate transformer by format type
"""

from abc import ABC, abstractmethod
from typing import Any

# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================


class TransformerError(Exception):
    """Base exception for transformer operations."""

    pass


class UnknownFormatError(TransformerError):
    """Raised when format type is not recognized."""

    pass


class ValidationError(TransformerError):
    """Raised when validation of input data fails."""

    pass


# ============================================================================
# ABSTRACT BASE CLASS
# ============================================================================


class AnswerSchemaTransformer(ABC):
    """
    Abstract base class for answer_schema transformers.

    Defines the interface that all concrete transformers must implement.
    Each transformer is responsible for converting a specific input format
    into a standardized answer_schema dict.

    Concrete implementations:
    - AgentResponseTransformer: Handles Agent LLM response format
    - MockDataTransformer: Handles Mock test data format

    Example:
        >>> transformer = AgentResponseTransformer()
        >>> raw_data = {
        ...     "correct_keywords": ["battery", "lithium"],
        ...     "explanation": "Lithium-ion batteries..."
        ... }
        >>> result = transformer.transform(raw_data)
        >>> result["type"]
        'keyword_match'
        >>> result["keywords"]
        ['battery', 'lithium']

    """

    @abstractmethod
    def transform(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        Transform raw answer_schema data to standard format.

        This method must be implemented by concrete subclasses to handle
        their specific format's transformation logic.

        Args:
            raw_data: Raw answer_schema dictionary from specific source format

        Returns:
            Normalized answer_schema dictionary with standard fields:
            - type: str (e.g., "keyword_match", "exact_match")
            - keywords: list[str] | None (for keyword-based questions)
            - correct_answer: str | None (for exact match questions)
            - explanation: str (explanation of correct answer)

        Raises:
            ValidationError: If required fields are missing or invalid
            TypeError: If data types don't match expectations

        """
        pass


# ============================================================================
# CONCRETE TRANSFORMER 1: AGENT RESPONSE FORMAT
# ============================================================================


class AgentResponseTransformer(AnswerSchemaTransformer):
    """
    Transformer for Agent LLM response format.

    Converts Agent responses with 'correct_keywords' field to standard format
    with 'keywords' field.

    Input Format (from LLM Agent):
        {
            "correct_keywords": ["keyword1", "keyword2"],
            "explanation": "Explanation text"
        }

    Output Format (normalized):
        {
            "type": "keyword_match",
            "keywords": ["keyword1", "keyword2"],
            "explanation": "Explanation text",
            "source_format": "agent_response"
        }

    Transformation Rules:
    - correct_keywords → keywords (rename and validate as list)
    - explanation → explanation (validate non-empty string)
    - Infer type as "keyword_match" (questions with keywords use keyword matching)
    - Add source_format metadata

    Error Handling:
    - Missing correct_keywords → ValidationError
    - Missing explanation → ValidationError
    - Empty keywords list → ValidationError (agent response should have keywords)
    - keywords not a list → TypeError
    - Non-string keywords → TypeError
    - Empty/None explanation → ValidationError
    """

    def transform(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        Transform Agent response format to standard format.

        Args:
            raw_data: Agent response dictionary with 'correct_keywords' and 'explanation'

        Returns:
            Normalized dictionary with 'keywords', 'explanation', 'type', 'source_format'

        Raises:
            ValidationError: If required fields missing or invalid
            TypeError: If data types don't match expectations

        """
        # Validate input is a dict
        if not isinstance(raw_data, dict):
            raise TypeError(f"raw_data must be dict, got {type(raw_data).__name__}")

        # Step 1: Extract and validate correct_keywords
        if "correct_keywords" not in raw_data:
            raise ValidationError(
                "Missing required field 'correct_keywords' in agent response format. "
                "Expected: {'correct_keywords': [...], 'explanation': '...'}"
            )

        correct_keywords = raw_data.get("correct_keywords")

        # Validate correct_keywords is a list
        if not isinstance(correct_keywords, list):
            raise TypeError(
                f"Field 'correct_keywords' must be list, got {type(correct_keywords).__name__}. "
                f"Value: {correct_keywords}"
            )

        # Validate list is not empty
        if len(correct_keywords) == 0:
            raise ValidationError(
                "Field 'correct_keywords' cannot be empty. Agent response must provide at least one keyword."
            )

        # Validate all items in list are strings
        for i, keyword in enumerate(correct_keywords):
            if not isinstance(keyword, str):
                raise TypeError(
                    f"All items in 'correct_keywords' must be strings. Item {i} is {type(keyword).__name__}: {keyword}"
                )

        # Step 2: Extract and validate explanation
        if "explanation" not in raw_data:
            raise ValidationError(
                "Missing required field 'explanation' in agent response format. Explanation is mandatory."
            )

        explanation = raw_data.get("explanation")

        # Validate explanation is a string
        if not isinstance(explanation, str):
            raise TypeError(f"Field 'explanation' must be string, got {type(explanation).__name__}")

        # Validate explanation is not empty
        if len(explanation.strip()) == 0:
            raise ValidationError(
                "Field 'explanation' cannot be empty or whitespace-only. Provide a meaningful explanation."
            )

        # Step 3: Build and return normalized dict
        return {
            "type": "keyword_match",
            "keywords": correct_keywords,
            "explanation": explanation,
            "source_format": "agent_response",
        }


# ============================================================================
# CONCRETE TRANSFORMER 2: MOCK DATA FORMAT
# ============================================================================


class MockDataTransformer(AnswerSchemaTransformer):
    """
    Transformer for Mock test data format.

    Converts Mock data with 'correct_key' field to standard format with
    'correct_answer' field.

    Input Format (from Mock data):
        {
            "correct_key": "B",
            "explanation": "Explanation text"
        }

    Output Format (normalized):
        {
            "type": "exact_match",
            "correct_answer": "B",
            "explanation": "Explanation text",
            "source_format": "mock_data"
        }

    Transformation Rules:
    - correct_key → correct_answer (rename and validate as string)
    - explanation → explanation (validate non-empty string)
    - Infer type as "exact_match" (mock uses exact answer matching)
    - Add source_format metadata

    Error Handling:
    - Missing correct_key → ValidationError
    - Missing explanation → ValidationError
    - Empty/None correct_key → ValidationError
    - correct_key not a string → TypeError
    - Empty/None explanation → ValidationError
    """

    def transform(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        Transform Mock data format to standard format.

        Args:
            raw_data: Mock data dictionary with 'correct_key' and 'explanation'

        Returns:
            Normalized dictionary with 'correct_answer', 'explanation', 'type', 'source_format'

        Raises:
            ValidationError: If required fields missing or invalid
            TypeError: If data types don't match expectations

        """
        # Validate input is a dict
        if not isinstance(raw_data, dict):
            raise TypeError(f"raw_data must be dict, got {type(raw_data).__name__}")

        # Validate dict is not empty
        if len(raw_data) == 0:
            raise ValidationError("Input dictionary is empty. Expected: {'correct_key': '...', 'explanation': '...'}")

        # Step 1: Extract and validate correct_key
        if "correct_key" not in raw_data:
            raise ValidationError(
                "Missing required field 'correct_key' in mock data format. "
                "Expected: {'correct_key': '...', 'explanation': '...'}"
            )

        correct_key = raw_data.get("correct_key")

        # Validate correct_key is a string
        if not isinstance(correct_key, str):
            raise TypeError(
                f"Field 'correct_key' must be string, got {type(correct_key).__name__}. Value: {correct_key}"
            )

        # Validate correct_key is not empty
        if len(correct_key.strip()) == 0:
            raise ValidationError("Field 'correct_key' cannot be empty or whitespace-only. Provide a valid answer key.")

        # Step 2: Extract and validate explanation
        if "explanation" not in raw_data:
            raise ValidationError("Missing required field 'explanation' in mock data format. Explanation is mandatory.")

        explanation = raw_data.get("explanation")

        # Validate explanation is a string
        if not isinstance(explanation, str):
            raise TypeError(f"Field 'explanation' must be string, got {type(explanation).__name__}")

        # Validate explanation is not empty
        if len(explanation.strip()) == 0:
            raise ValidationError(
                "Field 'explanation' cannot be empty or whitespace-only. Provide a meaningful explanation."
            )

        # Step 3: Build and return normalized dict
        return {
            "type": "exact_match",
            "correct_answer": correct_key,
            "explanation": explanation,
            "source_format": "mock_data",
        }


# ============================================================================
# FACTORY PATTERN
# ============================================================================


class TransformerFactory:
    """
    Factory for creating appropriate AnswerSchemaTransformer instances.

    This factory implements the Factory Pattern to encapsulate transformer
    creation logic. It maps format types to their corresponding transformer
    classes, allowing new formats to be added without modifying existing code
    (Open/Closed principle).

    Supported formats:
    - "agent_response": AgentResponseTransformer (for LLM Agent outputs)
    - "mock_data": MockDataTransformer (for test mock data)

    Usage:
        >>> factory = TransformerFactory()
        >>> transformer = factory.get_transformer("agent_response")
        >>> result = transformer.transform(raw_data)

    Adding new formats:
        1. Create new transformer class extending AnswerSchemaTransformer
        2. Add format_type mapping in _get_transformer_class()
        3. No changes needed to existing code (Open/Closed principle)
    """

    # Mapping of format types to transformer classes
    _TRANSFORMERS: dict[str, type[AnswerSchemaTransformer]] = {
        "agent_response": AgentResponseTransformer,
        "mock_data": MockDataTransformer,
    }

    def get_transformer(self, format_type: str) -> AnswerSchemaTransformer:
        """
        Get transformer instance for specified format type.

        Args:
            format_type: Format identifier string (e.g., "agent_response", "mock_data")

        Returns:
            New instance of appropriate transformer class

        Raises:
            UnknownFormatError: If format_type is not recognized

        Example:
            >>> factory = TransformerFactory()
            >>> transformer = factory.get_transformer("agent_response")
            >>> isinstance(transformer, AgentResponseTransformer)
            True

        """
        # Normalize format_type (lowercase, strip whitespace)
        normalized_format = format_type.lower().strip()

        # Check if format type is registered
        if normalized_format not in self._TRANSFORMERS:
            available_formats = ", ".join(self._TRANSFORMERS.keys())
            raise UnknownFormatError(f"Unknown format type '{format_type}'. Supported formats: {available_formats}")

        # Get transformer class and instantiate
        transformer_class = self._TRANSFORMERS[normalized_format]
        return transformer_class()

    @classmethod
    def register_transformer(cls, format_type: str, transformer_class: type[AnswerSchemaTransformer]) -> None:
        """
        Register a new transformer class for a format type (extension point).

        This class method allows registering new transformer implementations
        at runtime, enabling the system to support additional formats without
        modifying the factory code.

        Args:
            format_type: Format identifier string to register
            transformer_class: Class that extends AnswerSchemaTransformer

        Raises:
            TypeError: If transformer_class doesn't extend AnswerSchemaTransformer
            ValueError: If format_type is already registered

        Example:
            >>> class CustomTransformer(AnswerSchemaTransformer):
            ...     def transform(self, raw_data):
            ...         return {"type": "custom", ...}
            >>> factory = TransformerFactory()
            >>> factory.register_transformer("custom", CustomTransformer)
            >>> transformer = factory.get_transformer("custom")

        """
        # Validate transformer class extends AnswerSchemaTransformer
        if not issubclass(transformer_class, AnswerSchemaTransformer):
            raise TypeError(f"transformer_class must extend AnswerSchemaTransformer, got {transformer_class.__name__}")

        # Normalize format type
        normalized_format = format_type.lower().strip()

        # Check if already registered
        if normalized_format in cls._TRANSFORMERS:
            raise ValueError(
                f"Format type '{format_type}' is already registered. Use a different name or unregister first."
            )

        # Register new transformer
        cls._TRANSFORMERS[normalized_format] = transformer_class
