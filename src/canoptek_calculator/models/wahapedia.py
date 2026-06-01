from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Faction(Base):
    __tablename__ = "factions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    link: Mapped[str] = mapped_column(Text, nullable=False)

    datasheets: Mapped[list[Datasheet]] = relationship(back_populates="faction")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    edition: Mapped[str | None] = mapped_column(String(32))
    version: Mapped[str | None] = mapped_column(String(32))
    errata_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    errata_link: Mapped[str | None] = mapped_column(Text)

    datasheets: Mapped[list[Datasheet]] = relationship(back_populates="source")


class Detachment(Base):
    __tablename__ = "detachments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    faction_id: Mapped[str | None] = mapped_column(ForeignKey("factions.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    legend: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str | None] = mapped_column(String(100))


class Ability(Base):
    __tablename__ = "abilities"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    legend: Mapped[str | None] = mapped_column(Text)
    faction_id: Mapped[str | None] = mapped_column(ForeignKey("factions.id"), index=True)
    description: Mapped[str | None] = mapped_column(Text)


class Stratagem(Base):
    __tablename__ = "stratagems"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    faction_id: Mapped[str | None] = mapped_column(ForeignKey("factions.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    type: Mapped[str | None] = mapped_column(String(255))
    cp_cost: Mapped[int | None] = mapped_column(Integer)
    legend: Mapped[str | None] = mapped_column(Text)
    turn: Mapped[str | None] = mapped_column(String(100))
    phase: Mapped[str | None] = mapped_column(String(100))
    detachment: Mapped[str | None] = mapped_column(String(255))
    detachment_id: Mapped[str | None] = mapped_column(ForeignKey("detachments.id"), index=True)
    description: Mapped[str | None] = mapped_column(Text)


class Enhancement(Base):
    __tablename__ = "enhancements"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    faction_id: Mapped[str | None] = mapped_column(ForeignKey("factions.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cost: Mapped[int | None] = mapped_column(Integer)
    detachment: Mapped[str | None] = mapped_column(String(255))
    detachment_id: Mapped[str | None] = mapped_column(ForeignKey("detachments.id"), index=True)
    legend: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)


class DetachmentAbility(Base):
    __tablename__ = "detachment_abilities"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    faction_id: Mapped[str | None] = mapped_column(ForeignKey("factions.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    legend: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    detachment: Mapped[str | None] = mapped_column(String(255))
    detachment_id: Mapped[str | None] = mapped_column(ForeignKey("detachments.id"), index=True)


class Datasheet(Base):
    __tablename__ = "datasheets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    faction_id: Mapped[str] = mapped_column(ForeignKey("factions.id"), nullable=False, index=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id"), index=True)
    legend: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str | None] = mapped_column(String(100), index=True)
    loadout: Mapped[str | None] = mapped_column(Text)
    transport: Mapped[str | None] = mapped_column(Text)
    virtual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    leader_head: Mapped[str | None] = mapped_column(Text)
    leader_footer: Mapped[str | None] = mapped_column(Text)
    damaged_w: Mapped[str | None] = mapped_column(String(64))
    damaged_description: Mapped[str | None] = mapped_column(Text)
    link: Mapped[str | None] = mapped_column(Text)

    faction: Mapped[Faction] = relationship(back_populates="datasheets")
    source: Mapped[Source | None] = relationship(back_populates="datasheets")
    abilities: Mapped[list[DatasheetAbility]] = relationship(
        back_populates="datasheet",
        cascade="all, delete-orphan",
        order_by=lambda: DatasheetAbility.line,
    )
    keywords: Mapped[list[DatasheetKeyword]] = relationship(
        back_populates="datasheet",
        cascade="all, delete-orphan",
    )
    models: Mapped[list[DatasheetModel]] = relationship(
        back_populates="datasheet",
        cascade="all, delete-orphan",
        order_by=lambda: DatasheetModel.line,
    )
    options: Mapped[list[DatasheetOption]] = relationship(
        back_populates="datasheet",
        cascade="all, delete-orphan",
        order_by=lambda: DatasheetOption.line,
    )
    wargear: Mapped[list[DatasheetWargear]] = relationship(
        back_populates="datasheet",
        cascade="all, delete-orphan",
        order_by=lambda: (DatasheetWargear.line, DatasheetWargear.line_in_wargear),
    )
    unit_composition: Mapped[list[DatasheetUnitComposition]] = relationship(
        back_populates="datasheet",
        cascade="all, delete-orphan",
        order_by=lambda: DatasheetUnitComposition.line,
    )
    model_costs: Mapped[list[DatasheetModelCost]] = relationship(
        back_populates="datasheet",
        cascade="all, delete-orphan",
        order_by=lambda: DatasheetModelCost.line,
    )


class DatasheetAbility(Base):
    __tablename__ = "datasheet_abilities"
    __table_args__ = (UniqueConstraint("datasheet_id", "line", name="uq_datasheet_ability_line"),)

    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datasheet_id: Mapped[str] = mapped_column(
        ForeignKey("datasheets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line: Mapped[int] = mapped_column(Integer, nullable=False)
    ability_id: Mapped[str | None] = mapped_column(ForeignKey("abilities.id"), index=True)
    model: Mapped[str | None] = mapped_column(String(255))
    name: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str | None] = mapped_column(String(100))
    parameter: Mapped[str | None] = mapped_column(String(100))

    datasheet: Mapped[Datasheet] = relationship(back_populates="abilities")
    ability: Mapped[Ability | None] = relationship()


class DatasheetKeyword(Base):
    __tablename__ = "datasheet_keywords"
    __table_args__ = (
        UniqueConstraint(
            "datasheet_id",
            "keyword",
            "model",
            "is_faction_keyword",
            name="uq_datasheet_keyword",
        ),
    )

    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datasheet_id: Mapped[str] = mapped_column(
        ForeignKey("datasheets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    keyword: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    model: Mapped[str | None] = mapped_column(String(255))
    is_faction_keyword: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    datasheet: Mapped[Datasheet] = relationship(back_populates="keywords")


class DatasheetModel(Base):
    __tablename__ = "datasheet_models"
    __table_args__ = (UniqueConstraint("datasheet_id", "line", name="uq_datasheet_model_line"),)

    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datasheet_id: Mapped[str] = mapped_column(
        ForeignKey("datasheets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    m: Mapped[str | None] = mapped_column("M", String(64))
    t: Mapped[str | None] = mapped_column("T", String(64))
    sv: Mapped[str | None] = mapped_column("Sv", String(64))
    inv_sv: Mapped[str | None] = mapped_column(String(64))
    inv_sv_descr: Mapped[str | None] = mapped_column(Text)
    w: Mapped[str | None] = mapped_column("W", String(64))
    ld: Mapped[str | None] = mapped_column("Ld", String(64))
    oc: Mapped[str | None] = mapped_column("OC", String(64))
    base_size: Mapped[str | None] = mapped_column(String(100))
    base_size_descr: Mapped[str | None] = mapped_column(Text)

    datasheet: Mapped[Datasheet] = relationship(back_populates="models")


class DatasheetOption(Base):
    __tablename__ = "datasheet_options"
    __table_args__ = (UniqueConstraint("datasheet_id", "line", name="uq_datasheet_option_line"),)

    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datasheet_id: Mapped[str] = mapped_column(
        ForeignKey("datasheets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line: Mapped[int] = mapped_column(Integer, nullable=False)
    button: Mapped[str | None] = mapped_column(String(16))
    description: Mapped[str | None] = mapped_column(Text)

    datasheet: Mapped[Datasheet] = relationship(back_populates="options")


class DatasheetWargear(Base):
    __tablename__ = "datasheet_wargear"
    __table_args__ = (
        UniqueConstraint(
            "datasheet_id",
            "line",
            "line_in_wargear",
            name="uq_datasheet_wargear_line",
        ),
    )

    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datasheet_id: Mapped[str] = mapped_column(
        ForeignKey("datasheets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line: Mapped[int] = mapped_column(Integer, nullable=False)
    line_in_wargear: Mapped[int] = mapped_column(Integer, nullable=False)
    dice: Mapped[str | None] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    range: Mapped[str | None] = mapped_column(String(64))
    type: Mapped[str | None] = mapped_column(String(64))
    a: Mapped[str | None] = mapped_column("A", String(64))
    bs_ws: Mapped[str | None] = mapped_column("BS_WS", String(64))
    s: Mapped[str | None] = mapped_column("S", String(64))
    ap: Mapped[str | None] = mapped_column("AP", String(64))
    d: Mapped[str | None] = mapped_column("D", String(64))

    datasheet: Mapped[Datasheet] = relationship(back_populates="wargear")


class DatasheetUnitComposition(Base):
    __tablename__ = "datasheet_unit_composition"
    __table_args__ = (UniqueConstraint("datasheet_id", "line", name="uq_datasheet_unit_comp_line"),)

    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datasheet_id: Mapped[str] = mapped_column(
        ForeignKey("datasheets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    datasheet: Mapped[Datasheet] = relationship(back_populates="unit_composition")


class DatasheetModelCost(Base):
    __tablename__ = "datasheet_model_costs"
    __table_args__ = (
        UniqueConstraint("datasheet_id", "line", name="uq_datasheet_model_cost_line"),
    )

    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datasheet_id: Mapped[str] = mapped_column(
        ForeignKey("datasheets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    cost: Mapped[int | None] = mapped_column(Integer)

    datasheet: Mapped[Datasheet] = relationship(back_populates="model_costs")


class DatasheetStratagem(Base):
    __tablename__ = "datasheet_stratagems"
    __table_args__ = (
        UniqueConstraint("datasheet_id", "stratagem_id", name="uq_datasheet_stratagem"),
    )

    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datasheet_id: Mapped[str] = mapped_column(
        ForeignKey("datasheets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stratagem_id: Mapped[str] = mapped_column(
        ForeignKey("stratagems.id"),
        nullable=False,
        index=True,
    )


class DatasheetEnhancement(Base):
    __tablename__ = "datasheet_enhancements"
    __table_args__ = (
        UniqueConstraint("datasheet_id", "enhancement_id", name="uq_datasheet_enhancement"),
    )

    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datasheet_id: Mapped[str] = mapped_column(
        ForeignKey("datasheets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    enhancement_id: Mapped[str] = mapped_column(
        ForeignKey("enhancements.id"),
        nullable=False,
        index=True,
    )


class DatasheetDetachmentAbility(Base):
    __tablename__ = "datasheet_detachment_abilities"
    __table_args__ = (
        UniqueConstraint(
            "datasheet_id",
            "detachment_ability_id",
            name="uq_datasheet_detachment_ability",
        ),
    )

    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datasheet_id: Mapped[str] = mapped_column(
        ForeignKey("datasheets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    detachment_ability_id: Mapped[str] = mapped_column(
        ForeignKey("detachment_abilities.id"),
        nullable=False,
        index=True,
    )


class DatasheetLeader(Base):
    __tablename__ = "datasheet_leaders"
    __table_args__ = (UniqueConstraint("leader_id", "attached_id", name="uq_datasheet_leader"),)

    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    leader_id: Mapped[str] = mapped_column(
        ForeignKey("datasheets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attached_id: Mapped[str] = mapped_column(
        ForeignKey("datasheets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


class LastUpdate(Base):
    __tablename__ = "last_update"

    singleton_id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    last_update: Mapped[datetime] = mapped_column(DateTime, nullable=False)
