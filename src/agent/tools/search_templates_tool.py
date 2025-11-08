"""
Search Question Templates Tool - Find templates by interests and difficulty.

REQ: REQ-A-Mode1-Tool2
Tool 2 for Mode 1 pipeline: Search question templates for few-shot examples.
"""

import logging
from typing import Any

from langchain_core.tools import tool
from sqlalchemy.orm import Session

from src.backend.database import get_db

logger = logging.getLogger(__name__)

# Supported categories
SUPPORTED_CATEGORIES = {"technical", "business", "general"}
DIFFICULTY_MIN = 1
DIFFICULTY_MAX = 10
DIFFICULTY_RANGE = 1.5  # difficulty ± 1.5
MAX_RESULTS = 10


def _validate_inputs(interests: list[str], difficulty: int, category: str) -> None:
    """
    Validate search parameters.

    Args:
        interests: List of interest keywords
        difficulty: Difficulty level (1-10)
        category: Category ("technical", "business", or "general")

    Raises:
        TypeError: If inputs have wrong types
        ValueError: If inputs have invalid values

    """
    # Validate interests
    if not isinstance(interests, list):
        raise TypeError(f"interests must be list, got {type(interests)}")
    if len(interests) == 0:
        raise ValueError("interests cannot be empty")
    for item in interests:
        if not isinstance(item, str):
            raise TypeError(f"Each interest must be string, got {type(item)}")
        if len(item) == 0 or len(item) > 50:
            raise ValueError(f"Each interest must be 1-50 characters, got {len(item)}")

    # Validate difficulty
    if not isinstance(difficulty, int):
        if isinstance(difficulty, float) and difficulty.is_integer():
            difficulty = int(difficulty)
        else:
            raise TypeError(f"difficulty must be int, got {type(difficulty)}")
    if difficulty < DIFFICULTY_MIN or difficulty > DIFFICULTY_MAX:
        raise ValueError(f"difficulty must be {DIFFICULTY_MIN}-{DIFFICULTY_MAX}, got {difficulty}")

    # Validate category
    if not isinstance(category, str):
        raise TypeError(f"category must be string, got {type(category)}")
    category_lower = category.lower()
    if category_lower not in SUPPORTED_CATEGORIES:
        raise ValueError(f"category must be one of {SUPPORTED_CATEGORIES}, got {category}")


def _search_templates_from_db(
    db: Session, interests: list[str], difficulty: int, category: str
) -> list[dict[str, Any]]:
    """
    Query database for matching templates.

    Args:
        db: SQLAlchemy session
        interests: List of interest keywords
        difficulty: Difficulty level
        category: Category

    Returns:
        List of matching templates (dicts)

    """
    try:
        # Import here to avoid circular imports
        from src.backend.models.question_template import QuestionTemplate

        # Calculate difficulty range
        min_difficulty = difficulty - DIFFICULTY_RANGE
        max_difficulty = difficulty + DIFFICULTY_RANGE

        # Build query with filters
        query = (
            db.query(QuestionTemplate)
            .filter(QuestionTemplate.category == category)
            .filter(QuestionTemplate.domain.in_(interests))
            .filter(QuestionTemplate.avg_difficulty_score.between(min_difficulty, max_difficulty))
            .filter(QuestionTemplate.usage_count > 0)
            .filter(QuestionTemplate.is_active == True)  # noqa: E712
            .order_by(QuestionTemplate.correct_rate.desc(), QuestionTemplate.usage_count.desc())
            .limit(MAX_RESULTS)
        )

        results = query.all()

        # Convert to dicts
        output = []
        for template in results:
            output.append(
                {
                    "id": str(template.id),
                    "stem": template.stem,
                    "type": template.type,
                    "choices": template.choices or [],
                    "correct_answer": template.correct_answer,
                    "correct_rate": float(template.correct_rate),
                    "usage_count": int(template.usage_count),
                    "avg_difficulty_score": float(template.avg_difficulty_score),
                }
            )

        return output

    except Exception as e:
        logger.warning(f"Database query error: {e}")
        return []


def _search_question_templates_impl(interests: list[str], difficulty: int, category: str) -> list[dict[str, Any]]:
    """
    Implement search_question_templates (without @tool decorator).

    This is the actual function that can be tested.
    The @tool decorator wraps this function.

    Args:
        interests: List of interest keywords (1-10 items, 1-50 chars each)
        difficulty: Difficulty level (1-10)
        category: Category ("technical", "business", or "general")

    Returns:
        list: Up to 10 matching templates, sorted by correct_rate descending

    Raises:
        ValueError: If inputs are invalid
        TypeError: If inputs have wrong types

    """
    logger.info(f"Tool 2: Searching templates for interests={interests}, difficulty={difficulty}")

    # Validate inputs
    try:
        _validate_inputs(interests, difficulty, category)
    except (ValueError, TypeError) as e:
        logger.error(f"Input validation failed: {e}")
        raise

    # Get database session
    db = next(get_db())
    try:
        # Search templates
        results = _search_templates_from_db(db, interests, difficulty, category)

        if len(results) == 0:
            logger.info(f"No templates found for interests={interests}, difficulty={difficulty}")
        else:
            logger.info(f"Found {len(results)} templates")

        return results

    except Exception as e:
        logger.error(f"Error searching templates: {e}")
        # Graceful degradation: return empty list
        return []
    finally:
        db.close()


@tool
def search_question_templates(interests: list[str], difficulty: int, category: str) -> list[dict[str, Any]]:
    """
    Search for question templates matching interests and difficulty.

    REQ: REQ-A-Mode1-Tool2

    This tool searches for existing question templates that match the user's
    interests and difficulty level. These templates are used as few-shot
    examples to improve the quality of generated questions.

    Args:
        interests: List of interest keywords (1-10 items, each 1-50 chars)
                   Examples: ["LLM", "RAG", "Agent Architecture"]
        difficulty: Difficulty level (1-10 range)
                    1-3: Beginner, 4-6: Intermediate, 7-9: Advanced, 10: Expert
        category: Question category ("technical", "business", or "general")

    Returns:
        list: Up to 10 matching templates, each with:
            - id: Template UUID
            - stem: Question text
            - type: "multiple_choice", "true_false", or "short_answer"
            - choices: List of choices (for MC/TF) or empty list
            - correct_answer: Correct answer key or text
            - correct_rate: 0.0-1.0, success rate of this template
            - usage_count: How many times this template was used
            - avg_difficulty_score: 1.0-10.0, average difficulty

    Raises:
        ValueError: If difficulty not in 1-10 or category not recognized
        TypeError: If inputs have wrong types

    Example:
        >>> results = search_question_templates(
        ...     interests=["LLM", "RAG"],
        ...     difficulty=7,
        ...     category="technical"
        ... )
        >>> len(results)
        5
        >>> results[0]["stem"]
        "What is RAG?"

    """
    return _search_question_templates_impl(interests, difficulty, category)
