from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class ArmyList(Base):
    __tablename__ = "army_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    faction_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    faction_name: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
        index=True,
    )

    entries: Mapped[list[ArmyListEntry]] = relationship(
        back_populates="army_list",
        cascade="all, delete-orphan",
        order_by=lambda: (ArmyListEntry.sort_order.asc(), ArmyListEntry.id.asc()),
    )


class ArmyListEntry(Base):
    __tablename__ = "army_list_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    army_list_id: Mapped[int] = mapped_column(
        ForeignKey("army_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    datasheet_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    datasheet_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_line: Mapped[int | None] = mapped_column(Integer)
    model_name: Mapped[str | None] = mapped_column(String(255))
    unit_size: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    points_each: Mapped[int | None] = mapped_column(Integer)
    cost_label: Mapped[str | None] = mapped_column(String(255))
    nickname: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    army_list: Mapped[ArmyList] = relationship(back_populates="entries")
