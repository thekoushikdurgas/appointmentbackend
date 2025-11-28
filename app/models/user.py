"""SQLAlchemy models for user authentication and profiles."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, JSON, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum

from app.db.base import Base
from app.db.types import EnumValue

if TYPE_CHECKING:  # pragma: no cover
    pass


class UserHistoryEventType(str, enum.Enum):
    """Event types for user history."""
    REGISTRATION = "registration"
    LOGIN = "login"


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        Text,
        primary_key=True,
        default=lambda: str(uuid4()),
        nullable=False
    )
    uuid: Mapped[str] = mapped_column(
        Text,
        unique=True,
        index=True,
        nullable=False,
        default=lambda: str(uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    last_sign_in_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now()
    )

    profile: Mapped[Optional["UserProfile"]] = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    history: Mapped[list["UserHistory"]] = relationship(
        "UserHistory",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_id", "id"),
        Index("idx_users_uuid", "uuid"),
    )


class UserProfile(Base):
    """User profile model with additional user information."""

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("users.uuid", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    job_title: Mapped[Optional[str]] = mapped_column(String(255))
    bio: Mapped[Optional[str]] = mapped_column(Text)
    timezone: Mapped[Optional[str]] = mapped_column(String(100))
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)
    notifications: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    role: Mapped[Optional[str]] = mapped_column(String(50), default="Member")
    # Billing fields
    credits: Mapped[int] = mapped_column(default=0, nullable=False)
    subscription_plan: Mapped[Optional[str]] = mapped_column(String(50), default="free")
    subscription_period: Mapped[Optional[str]] = mapped_column(String(20), default="monthly")  # monthly, quarterly, yearly
    subscription_status: Mapped[Optional[str]] = mapped_column(String(50), default="active")
    subscription_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    subscription_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now()
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="profile"
    )

    __table_args__ = (
        Index("idx_user_profiles_user_id", "user_id"),
    )


class UserHistory(Base):
    """
    User history model for tracking registration and login events with IP geolocation.
    
    Note: user_id must be a valid UUID format (stored as text).
    """

    __tablename__ = "user_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # User UUID (UUID format stored as text)
    user_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("users.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    event_type: Mapped[str] = mapped_column(
        EnumValue(UserHistoryEventType, "user_history_event_type"),
        nullable=False,
        index=True
    )
    ip: Mapped[Optional[str]] = mapped_column(String(45))  # IPv6 max length
    # Geolocation fields
    continent: Mapped[Optional[str]] = mapped_column(String(50))
    continent_code: Mapped[Optional[str]] = mapped_column(String(2))
    country: Mapped[Optional[str]] = mapped_column(String(100))
    country_code: Mapped[Optional[str]] = mapped_column(String(2))
    region: Mapped[Optional[str]] = mapped_column(String(10))
    region_name: Mapped[Optional[str]] = mapped_column(String(100))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    district: Mapped[Optional[str]] = mapped_column(String(100))
    zip: Mapped[Optional[str]] = mapped_column(String(20))
    lat: Mapped[Optional[float]] = mapped_column(Numeric(10, 7))
    lon: Mapped[Optional[float]] = mapped_column(Numeric(10, 7))
    timezone: Mapped[Optional[str]] = mapped_column(String(100))
    currency: Mapped[Optional[str]] = mapped_column(String(10))
    isp: Mapped[Optional[str]] = mapped_column(String(255))
    org: Mapped[Optional[str]] = mapped_column(String(255))
    asname: Mapped[Optional[str]] = mapped_column(String(255))
    reverse: Mapped[Optional[str]] = mapped_column(String(255))
    device: Mapped[Optional[str]] = mapped_column(Text)  # User-Agent string
    proxy: Mapped[Optional[bool]] = mapped_column(default=False)
    hosting: Mapped[Optional[bool]] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="history"
    )

    __table_args__ = (
        Index("idx_user_history_user_id", "user_id"),
        Index("idx_user_history_event_type", "event_type"),
        Index("idx_user_history_created_at", "created_at"),
    )