"""
Question Template model for managing reusable question templates.

REQ: REQ-A-Mode1-Tool2, REQ-A-Mode1-Tool4
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.models.user import Base


class QuestionTemplate(Base):
    """
    Question Template model for storing reusable question templates.

    REQ: REQ-A-Mode1-Tool2, REQ-A-Mode1-Tool4

    Design principle:
    - Templates are used as few-shot examples for LLM-based question generation
    - Stores template metadata: stem, choices, correct answer, difficulty, category
    - Tracks usage statistics: correct_rate, usage_count, avg_difficulty_score
    - Links to domains/categories for searching by interest

    Attributes:
        id: Primary key (UUID)
        category: Top-level category (technical, business, general)
        domain: Specific domain/interest area (LLM, RAG, FastAPI, etc.)
        stem: Question content/text
        type: Question type (multiple_choice, true_false, short_answer)
        choices: JSON array of choices (for multiple_choice/true_false)
        correct_answer: Correct answer key or text
        correct_rate: 0.0-1.0, success rate of this template
        usage_count: How many times this template was used
        avg_difficulty_score: 1.0-10.0, average difficulty rating
        is_active: Whether this template is active and searchable
        created_at: Template creation timestamp
        updated_at: Last update timestamp

    """

    __tablename__ = "question_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    stem: Mapped[str] = mapped_column(String(2000), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    choices: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    correct_answer: Mapped[str] = mapped_column(String(500), nullable=False)
    correct_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_difficulty_score: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        """Return string representation of QuestionTemplate."""
        return (
            f"<QuestionTemplate(id='{self.id}', category='{self.category}', "
            f"domain='{self.domain}', type='{self.type}')>"
        )
