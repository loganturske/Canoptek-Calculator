from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DatasheetAbilityInterpretation(Base):
    __tablename__ = "datasheet_ability_interpretations"
    __table_args__ = (
        UniqueConstraint(
            "datasheet_id",
            "ability_line",
            name="uq_datasheet_ability_interpretation",
        ),
    )

    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datasheet_id: Mapped[str] = mapped_column(
        ForeignKey("datasheets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ability_line: Mapped[int] = mapped_column(Integer, nullable=False)
    ability_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ability_type: Mapped[str | None] = mapped_column(String(100))
    is_simulation_relevant: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    interpreted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    interpreter_kind: Mapped[str | None] = mapped_column(String(64))
    confidence: Mapped[float | None] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(Text)


class DatasheetStructuredEffect(Base):
    __tablename__ = "datasheet_structured_effects"
    __table_args__ = (
        UniqueConstraint("datasheet_id", "effect_id", name="uq_datasheet_structured_effect"),
    )

    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datasheet_id: Mapped[str] = mapped_column(
        ForeignKey("datasheets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ability_line: Mapped[int] = mapped_column(Integer, nullable=False)
    ability_name: Mapped[str] = mapped_column(String(255), nullable=False)
    effect_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    effect_type: Mapped[str] = mapped_column(String(64), nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False, default="any")
    numeric_value: Mapped[int | None] = mapped_column(Integer)
    text_value: Mapped[str | None] = mapped_column(String(100))
    selectable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    enabled_by_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    interpreter_kind: Mapped[str | None] = mapped_column(String(64))
    confidence: Mapped[float | None] = mapped_column(Float)
