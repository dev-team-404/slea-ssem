"""
User badge model for storing awarded badges.

REQ: REQ-B-B4-Plus-1, REQ-B-B4-Plus-2, REQ-B-B4-Plus-3
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.models.user import Base


class UserBadge(Base):
    """
    User badge model for storing awarded badges.

    REQ: REQ-B-B4-Plus-1, REQ-B-B4-Plus-2, REQ-B-B4-Plus-3

    Design principle:
    - One record per badge awarded to user
    - Tracks badge name, type (grade/specialist), and award date
    - Used to display badges in user profile API
    - Supports multiple badges per user (grade badge + specialist badges)

    Attributes:
        id: Primary key (UUID)
        user_id: Foreign key to users table
        badge_name: Badge name (e.g., "시작자 배지", "Agent Specialist 배지")
        badge_type: Type of badge (grade, specialist)
        awarded_at: When the badge was awarded
        created_at: Record creation timestamp

    """

    __tablename__ = "user_badges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    badge_name: Mapped[str] = mapped_column(String(255), nullable=False)
    badge_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'grade', 'specialist'
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        """Return string representation of UserBadge."""
        return f"<UserBadge(id='{self.id}', user_id={self.user_id}, badge_name='{self.badge_name}')>"
