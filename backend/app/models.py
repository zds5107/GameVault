from sqlalchemy import (
    Integer, 
    String, 
    DateTime,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Enum as SQLAlchemyEnum
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime, timezone
from enum import Enum


class CollectionStatus(str, Enum):
    OWNED = "owned"
    WISHLIST = "wishlist"

    
class OwnershipType(str, Enum):
    PHYSICAL = "physical"
    DIGITAL = "digital"

class PlayStatus(str, Enum):
    UNPLAYED = "unplayed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"

class Base(DeclarativeBase):
    pass

class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    platform: Mapped[str] = mapped_column(String(100), nullable=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

class CollectionEntry(Base):
    __tablename__ = "collection_entries"

    __table_args__ = (
        UniqueConstraint("user_id", "game_id"),
        CheckConstraint(
            "(collection_status = 'owned' AND ownership_type IS NOT NULL) "
            "OR "
            "(collection_status = 'wishlist' AND ownership_type IS NULL)",
            name="ck_collection_entries_status_ownership",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id"),
        nullable=False,
    )

    collection_status: Mapped[CollectionStatus] = mapped_column(
        SQLAlchemyEnum(
            CollectionStatus,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
    )

    ownership_type: Mapped[OwnershipType | None] = mapped_column(
        SQLAlchemyEnum(
            OwnershipType,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=True,
    )

    play_status: Mapped[PlayStatus] = mapped_column(
        SQLAlchemyEnum(
            PlayStatus,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
    )

    


