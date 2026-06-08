from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session, selectinload

from ..models import ArmyList, ArmyListEntry, Datasheet, DatasheetModel, Faction
from ..models.army_lists import utcnow
from ..schemas.api import (
    ArmyListCreate,
    ArmyListDetailRead,
    ArmyListEntryCreate,
    ArmyListEntryRead,
    ArmyListEntryUpdate,
    ArmyListSummaryRead,
    ArmyListUpdate,
)


@dataclass(frozen=True)
class ArmyListReferenceContext:
    factions: dict[str, Faction]
    datasheets: dict[str, Datasheet]
    models: dict[tuple[str, int], DatasheetModel]


class ArmyListService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_army_lists(self) -> list[ArmyListSummaryRead]:
        army_lists = self.session.scalars(
            select(ArmyList)
            .options(selectinload(ArmyList.entries))
            .order_by(ArmyList.updated_at.desc(), ArmyList.name.asc())
        ).all()
        context = self._build_reference_context(army_lists)
        return [self._serialize_army_list(army_list, context) for army_list in army_lists]

    def get_army_list_detail(self, army_list_id: int) -> ArmyListDetailRead:
        army_list = self._get_army_list_or_raise(army_list_id)
        context = self._build_reference_context([army_list])
        return self._serialize_army_list_detail(army_list, context)

    def create_army_list(self, payload: ArmyListCreate) -> ArmyListDetailRead:
        faction = self._require_faction(payload.faction_id)
        army_list = ArmyList(
            name=self._clean_required_text(payload.name, "Army list name"),
            faction_id=faction.id,
            faction_name=faction.name,
            notes=self._clean_optional_text(payload.notes),
        )
        self.session.add(army_list)
        self.session.commit()
        self.session.expire_all()
        return self.get_army_list_detail(army_list.id)

    def update_army_list(self, army_list_id: int, payload: ArmyListUpdate) -> ArmyListDetailRead:
        army_list = self._get_army_list_or_raise(army_list_id)

        if "name" in payload.model_fields_set:
            if payload.name is None:
                raise ValueError("Army list name cannot be empty.")
            army_list.name = self._clean_required_text(payload.name, "Army list name")

        if "faction_id" in payload.model_fields_set:
            if payload.faction_id is None:
                raise ValueError("Army list faction cannot be empty.")
            if army_list.entries and payload.faction_id != army_list.faction_id:
                raise ValueError(
                    "Change the faction only after clearing the list entries or create a new list."
                )
            faction = self._require_faction(payload.faction_id)
            army_list.faction_id = faction.id
            army_list.faction_name = faction.name

        if "notes" in payload.model_fields_set:
            army_list.notes = self._clean_optional_text(payload.notes)

        self._touch_list(army_list)
        self.session.commit()
        self.session.expire_all()
        return self.get_army_list_detail(army_list.id)

    def delete_army_list(self, army_list_id: int) -> None:
        army_list = self._get_army_list_or_raise(army_list_id)
        self.session.delete(army_list)
        self.session.commit()

    def add_entry(
        self,
        army_list_id: int,
        payload: ArmyListEntryCreate,
    ) -> ArmyListDetailRead:
        army_list = self._get_army_list_or_raise(army_list_id)
        datasheet = self._require_datasheet_for_list(payload.datasheet_id, army_list)
        model = (
            self._require_model_line(datasheet.id, payload.model_line)
            if payload.model_line is not None
            else None
        )

        entry = ArmyListEntry(
            army_list=army_list,
            datasheet_id=datasheet.id,
            datasheet_name=datasheet.name,
            model_line=model.line if model else None,
            model_name=self._build_model_name(model, datasheet),
            unit_size=payload.unit_size,
            quantity=payload.quantity,
            points_each=payload.points_each,
            cost_label=self._clean_optional_text(payload.cost_label),
            nickname=self._clean_optional_text(payload.nickname),
            notes=self._clean_optional_text(payload.notes),
            sort_order=payload.sort_order
            if payload.sort_order is not None
            else self._next_sort_order(army_list),
        )
        self.session.add(entry)
        self._touch_list(army_list)
        self.session.commit()
        self.session.expire_all()
        return self.get_army_list_detail(army_list.id)

    def update_entry(
        self,
        army_list_id: int,
        entry_id: int,
        payload: ArmyListEntryUpdate,
    ) -> ArmyListDetailRead:
        army_list = self._get_army_list_or_raise(army_list_id)
        entry = self._get_entry_or_raise(army_list, entry_id)

        datasheet = None
        datasheet_changed = False
        if "datasheet_id" in payload.model_fields_set:
            if payload.datasheet_id is None:
                raise ValueError("Unit datasheet cannot be empty.")
            datasheet = self._require_datasheet_for_list(payload.datasheet_id, army_list)
            datasheet_changed = datasheet.id != entry.datasheet_id
            entry.datasheet_id = datasheet.id
            entry.datasheet_name = datasheet.name

        if "model_line" in payload.model_fields_set:
            if payload.model_line is None:
                entry.model_line = None
                entry.model_name = None
            else:
                datasheet = datasheet or self._require_datasheet_for_list(
                    entry.datasheet_id,
                    army_list,
                )
                model = self._require_model_line(datasheet.id, payload.model_line)
                entry.model_line = model.line
                entry.model_name = self._build_model_name(model, datasheet)
        elif datasheet_changed:
            entry.model_line = None
            entry.model_name = None

        if "unit_size" in payload.model_fields_set and payload.unit_size is not None:
            entry.unit_size = payload.unit_size

        if "quantity" in payload.model_fields_set and payload.quantity is not None:
            entry.quantity = payload.quantity

        if "points_each" in payload.model_fields_set:
            entry.points_each = payload.points_each

        if "cost_label" in payload.model_fields_set:
            entry.cost_label = self._clean_optional_text(payload.cost_label)

        if "nickname" in payload.model_fields_set:
            entry.nickname = self._clean_optional_text(payload.nickname)

        if "notes" in payload.model_fields_set:
            entry.notes = self._clean_optional_text(payload.notes)

        if "sort_order" in payload.model_fields_set and payload.sort_order is not None:
            entry.sort_order = payload.sort_order

        self._touch_list(army_list)
        self.session.commit()
        self.session.expire_all()
        return self.get_army_list_detail(army_list.id)

    def delete_entry(self, army_list_id: int, entry_id: int) -> ArmyListDetailRead:
        army_list = self._get_army_list_or_raise(army_list_id)
        entry = self._get_entry_or_raise(army_list, entry_id)
        self.session.delete(entry)
        self._touch_list(army_list)
        self.session.commit()
        self.session.expire_all()
        return self.get_army_list_detail(army_list.id)

    def _get_army_list_or_raise(self, army_list_id: int) -> ArmyList:
        army_list = self.session.scalar(
            select(ArmyList)
            .options(selectinload(ArmyList.entries))
            .where(ArmyList.id == army_list_id)
        )
        if army_list is None:
            raise LookupError(f"Army list {army_list_id} was not found.")
        return army_list

    def _get_entry_or_raise(self, army_list: ArmyList, entry_id: int) -> ArmyListEntry:
        for entry in army_list.entries:
            if entry.id == entry_id:
                return entry
        raise LookupError(f"Army list entry {entry_id} was not found.")

    def _require_faction(self, faction_id: str) -> Faction:
        faction = self.session.get(Faction, faction_id)
        if faction is None:
            raise LookupError(f"Faction {faction_id} was not found.")
        return faction

    def _require_datasheet_for_list(self, datasheet_id: str, army_list: ArmyList) -> Datasheet:
        datasheet = self.session.get(Datasheet, datasheet_id)
        if datasheet is None:
            raise LookupError(f"Datasheet {datasheet_id} was not found.")
        if datasheet.faction_id != army_list.faction_id:
            raise ValueError(
                f"{datasheet.name} belongs to a different faction and cannot be added to this list."
            )
        return datasheet

    def _require_model_line(self, datasheet_id: str, model_line: int) -> DatasheetModel:
        model = self.session.scalar(
            select(DatasheetModel).where(
                DatasheetModel.datasheet_id == datasheet_id,
                DatasheetModel.line == model_line,
            )
        )
        if model is None:
            raise ValueError(
                f"Model line {model_line} does not exist for datasheet {datasheet_id}."
            )
        return model

    def _build_reference_context(
        self,
        army_lists: list[ArmyList],
    ) -> ArmyListReferenceContext:
        faction_ids = {army_list.faction_id for army_list in army_lists}
        datasheet_ids = {
            entry.datasheet_id for army_list in army_lists for entry in army_list.entries
        }
        model_pairs = {
            (entry.datasheet_id, entry.model_line)
            for army_list in army_lists
            for entry in army_list.entries
            if entry.model_line is not None
        }

        factions = (
            self.session.scalars(select(Faction).where(Faction.id.in_(faction_ids))).all()
            if faction_ids
            else []
        )
        datasheets = (
            self.session.scalars(select(Datasheet).where(Datasheet.id.in_(datasheet_ids))).all()
            if datasheet_ids
            else []
        )
        models = (
            self.session.scalars(
                select(DatasheetModel).where(
                    tuple_(DatasheetModel.datasheet_id, DatasheetModel.line).in_(model_pairs)
                )
            ).all()
            if model_pairs
            else []
        )

        return ArmyListReferenceContext(
            factions={faction.id: faction for faction in factions},
            datasheets={datasheet.id: datasheet for datasheet in datasheets},
            models={(model.datasheet_id, model.line): model for model in models},
        )

    def _serialize_army_list(
        self,
        army_list: ArmyList,
        context: ArmyListReferenceContext,
    ) -> ArmyListSummaryRead:
        current_faction = context.factions.get(army_list.faction_id)
        entry_reads = [self._serialize_entry(entry, context) for entry in army_list.entries]

        total_points = 0
        has_unpriced_entries = False
        has_stale_entries = current_faction is None
        total_units = 0
        total_models = 0

        for entry in entry_reads:
            total_units += entry.quantity
            total_models += entry.entry_model_count
            has_stale_entries = has_stale_entries or bool(entry.reference_warning)
            if entry.total_points is None:
                has_unpriced_entries = True
            else:
                total_points += entry.total_points

        return ArmyListSummaryRead(
            id=army_list.id,
            name=army_list.name,
            faction_id=army_list.faction_id,
            faction_name=current_faction.name if current_faction else army_list.faction_name,
            faction_available=current_faction is not None,
            notes=army_list.notes,
            entry_count=len(entry_reads),
            total_units=total_units,
            total_models=total_models,
            total_points=total_points,
            has_unpriced_entries=has_unpriced_entries,
            has_stale_entries=has_stale_entries,
            created_at=army_list.created_at,
            updated_at=army_list.updated_at,
        )

    def _serialize_army_list_detail(
        self,
        army_list: ArmyList,
        context: ArmyListReferenceContext,
    ) -> ArmyListDetailRead:
        summary = self._serialize_army_list(army_list, context)
        return ArmyListDetailRead(
            **summary.model_dump(),
            entries=[self._serialize_entry(entry, context) for entry in army_list.entries],
        )

    def _serialize_entry(
        self,
        entry: ArmyListEntry,
        context: ArmyListReferenceContext,
    ) -> ArmyListEntryRead:
        current_datasheet = context.datasheets.get(entry.datasheet_id)
        current_model = (
            context.models.get((entry.datasheet_id, entry.model_line))
            if entry.model_line is not None
            else None
        )
        datasheet_name = current_datasheet.name if current_datasheet else entry.datasheet_name
        model_name = self._build_model_name(
            current_model,
            current_datasheet,
            fallback=entry.model_name,
        )

        reference_warning = None
        model_available = None
        if current_datasheet is None:
            reference_warning = (
                "This datasheet is no longer available in the current Wahapedia import."
            )
        elif entry.model_line is not None and current_model is None:
            model_available = False
            reference_warning = (
                "The saved model line is no longer available in the current datasheet import."
            )
        elif entry.model_line is not None:
            model_available = True

        total_points = entry.points_each * entry.quantity if entry.points_each is not None else None

        return ArmyListEntryRead(
            id=entry.id,
            army_list_id=entry.army_list_id,
            display_name=entry.nickname or datasheet_name,
            datasheet_id=entry.datasheet_id,
            datasheet_name=datasheet_name,
            datasheet_role=current_datasheet.role if current_datasheet else None,
            datasheet_link=current_datasheet.link if current_datasheet else None,
            datasheet_available=current_datasheet is not None,
            model_line=entry.model_line,
            model_profile_id=current_model.row_id if current_model else None,
            model_name=model_name,
            model_available=model_available,
            unit_size=entry.unit_size,
            quantity=entry.quantity,
            entry_model_count=entry.unit_size * entry.quantity,
            points_each=entry.points_each,
            total_points=total_points,
            cost_label=entry.cost_label,
            nickname=entry.nickname,
            notes=entry.notes,
            sort_order=entry.sort_order,
            reference_warning=reference_warning,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )

    def _next_sort_order(self, army_list: ArmyList) -> int:
        return (max((entry.sort_order for entry in army_list.entries), default=0) + 10) or 10

    def _touch_list(self, army_list: ArmyList) -> None:
        army_list.updated_at = utcnow()

    def _build_model_name(
        self,
        model: DatasheetModel | None,
        datasheet: Datasheet | None,
        *,
        fallback: str | None = None,
    ) -> str | None:
        if model and model.name:
            return model.name
        if fallback:
            return fallback
        if datasheet:
            return datasheet.name
        return None

    def _clean_required_text(self, value: str, label: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError(f"{label} cannot be empty.")
        return cleaned

    def _clean_optional_text(self, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None
