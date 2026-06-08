from __future__ import annotations

import bleach
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..domain.simulation import build_weapon_profile, parse_required_roll
from ..ingest.wahapedia import WahapediaClient
from ..models import (
    Ability,
    Datasheet,
    DatasheetAbility,
    DatasheetDetachmentAbility,
    DatasheetEnhancement,
    DatasheetKeyword,
    DatasheetLeader,
    DatasheetModel,
    DatasheetModelCost,
    DatasheetOption,
    DatasheetStratagem,
    DatasheetUnitComposition,
    DatasheetWargear,
    DetachmentAbility,
    Enhancement,
    Faction,
    LastUpdate,
    Source,
    Stratagem,
)
from ..schemas.api import (
    DashboardStatsRead,
    DatasheetAbilityRead,
    DatasheetCostRead,
    DatasheetDetailRead,
    DatasheetOptionRead,
    DatasheetReferenceRead,
    DatasheetSummaryRead,
    FactionRead,
    ModelProfileRead,
    RuleReferenceRead,
    WeaponProfileRead,
)

ALLOWED_TAGS = [
    "b",
    "br",
    "em",
    "i",
    "li",
    "ol",
    "p",
    "span",
    "strong",
    "u",
    "ul",
]
ALLOWED_ATTRIBUTES = {"span": ["class"]}


def sanitize_html_fragment(value: str | None) -> str | None:
    if not value:
        return None
    return bleach.clean(value, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)


class CatalogService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.settings = get_settings()

    def get_dashboard_stats(self) -> DashboardStatsRead:
        manifest = WahapediaClient.load_manifest(self.settings.fixtures_dir)
        last_update = self.session.scalar(select(LastUpdate.last_update))
        faction_count = self.session.scalar(select(func.count()).select_from(Faction)) or 0
        datasheet_count = self.session.scalar(select(func.count()).select_from(Datasheet)) or 0
        weapon_count = self.session.scalar(select(func.count()).select_from(DatasheetWargear)) or 0
        return DashboardStatsRead(
            fixtures_dir=str(self.settings.fixtures_dir),
            faction_count=faction_count,
            datasheet_count=datasheet_count,
            weapon_count=weapon_count,
            last_update=last_update,
            last_downloaded_at=manifest.downloaded_at if manifest else None,
            fixture_file_count=len(manifest.files) if manifest else 0,
        )

    def list_factions(self) -> list[FactionRead]:
        factions = self.session.scalars(select(Faction).order_by(Faction.name.asc())).all()
        return [
            FactionRead(id=faction.id, name=faction.name, link=faction.link) for faction in factions
        ]

    def list_datasheets(
        self,
        *,
        search: str | None = None,
        faction_id: str | None = None,
        limit: int = 2500,
    ) -> list[DatasheetSummaryRead]:
        statement = (
            select(Datasheet, Faction.name, Source.name)
            .join(Faction, Datasheet.faction_id == Faction.id)
            .outerjoin(Source, Datasheet.source_id == Source.id)
            .order_by(Faction.name.asc(), Datasheet.name.asc())
            .limit(limit)
        )

        if search:
            statement = statement.where(Datasheet.name.ilike(f"%{search.strip()}%"))
        if faction_id:
            statement = statement.where(Datasheet.faction_id == faction_id)

        rows = self.session.execute(statement).all()
        return [
            DatasheetSummaryRead(
                id=datasheet.id,
                name=datasheet.name,
                faction_id=datasheet.faction_id,
                faction_name=faction_name,
                source_name=source_name or "Unknown source",
                role=datasheet.role,
                virtual=datasheet.virtual,
                link=datasheet.link,
            )
            for datasheet, faction_name, source_name in rows
        ]

    def get_datasheet_detail(self, datasheet_id: str) -> DatasheetDetailRead | None:
        row = self.session.execute(
            select(Datasheet, Faction.name, Source.name)
            .join(Faction, Datasheet.faction_id == Faction.id)
            .outerjoin(Source, Datasheet.source_id == Source.id)
            .where(Datasheet.id == datasheet_id)
        ).one_or_none()
        if row is None:
            return None

        datasheet, faction_name, source_name = row
        keywords = self.session.scalars(
            select(DatasheetKeyword.keyword)
            .where(DatasheetKeyword.datasheet_id == datasheet_id)
            .order_by(DatasheetKeyword.is_faction_keyword.desc(), DatasheetKeyword.keyword.asc())
        ).all()

        abilities = self.session.execute(
            select(DatasheetAbility, Ability.name, Ability.description)
            .outerjoin(Ability, DatasheetAbility.ability_id == Ability.id)
            .where(DatasheetAbility.datasheet_id == datasheet_id)
            .order_by(DatasheetAbility.line.asc())
        ).all()
        models = self.session.scalars(
            select(DatasheetModel)
            .where(DatasheetModel.datasheet_id == datasheet_id)
            .order_by(DatasheetModel.line.asc())
        ).all()
        options = self.session.scalars(
            select(DatasheetOption)
            .where(DatasheetOption.datasheet_id == datasheet_id)
            .order_by(DatasheetOption.line.asc())
        ).all()
        unit_composition = self.session.scalars(
            select(DatasheetUnitComposition.description)
            .where(DatasheetUnitComposition.datasheet_id == datasheet_id)
            .order_by(DatasheetUnitComposition.line.asc())
        ).all()
        costs = self.session.scalars(
            select(DatasheetModelCost)
            .where(DatasheetModelCost.datasheet_id == datasheet_id)
            .order_by(DatasheetModelCost.line.asc())
        ).all()
        weapons = self.session.scalars(
            select(DatasheetWargear)
            .where(DatasheetWargear.datasheet_id == datasheet_id)
            .order_by(DatasheetWargear.line.asc(), DatasheetWargear.line_in_wargear.asc())
        ).all()
        attachable_leaders = self.session.execute(
            select(Datasheet.id, Datasheet.name, Faction.name, Datasheet.role)
            .join(DatasheetLeader, Datasheet.id == DatasheetLeader.leader_id)
            .join(Faction, Datasheet.faction_id == Faction.id)
            .where(DatasheetLeader.attached_id == datasheet_id)
            .order_by(Datasheet.name.asc())
        ).all()

        stratagems = (
            self.session.execute(
                select(Stratagem)
                .join(DatasheetStratagem, Stratagem.id == DatasheetStratagem.stratagem_id)
                .where(DatasheetStratagem.datasheet_id == datasheet_id)
                .order_by(Stratagem.name.asc())
            )
            .scalars()
            .all()
        )
        enhancements = (
            self.session.execute(
                select(Enhancement)
                .join(DatasheetEnhancement, Enhancement.id == DatasheetEnhancement.enhancement_id)
                .where(DatasheetEnhancement.datasheet_id == datasheet_id)
                .order_by(Enhancement.name.asc())
            )
            .scalars()
            .all()
        )
        detachment_abilities = (
            self.session.execute(
                select(DetachmentAbility)
                .join(
                    DatasheetDetachmentAbility,
                    DetachmentAbility.id == DatasheetDetachmentAbility.detachment_ability_id,
                )
                .where(DatasheetDetachmentAbility.datasheet_id == datasheet_id)
                .order_by(DetachmentAbility.name.asc())
            )
            .scalars()
            .all()
        )

        return DatasheetDetailRead(
            id=datasheet.id,
            name=datasheet.name,
            faction_id=datasheet.faction_id,
            faction_name=faction_name,
            source_name=source_name or "Unknown source",
            role=datasheet.role,
            legend_html=sanitize_html_fragment(datasheet.legend),
            loadout_html=sanitize_html_fragment(datasheet.loadout),
            transport_html=sanitize_html_fragment(datasheet.transport),
            leader_head_html=sanitize_html_fragment(datasheet.leader_head),
            leader_footer_html=sanitize_html_fragment(datasheet.leader_footer),
            damaged_profile_label=datasheet.damaged_w,
            damaged_profile_html=sanitize_html_fragment(datasheet.damaged_description),
            link=datasheet.link,
            keywords=keywords,
            abilities=[
                DatasheetAbilityRead(
                    name=ability_row.name or inherited_name or "Unnamed ability",
                    ability_type=ability_row.type,
                    parameter=ability_row.parameter,
                    model=ability_row.model,
                    description_html=sanitize_html_fragment(
                        ability_row.description or inherited_description
                    ),
                )
                for ability_row, inherited_name, inherited_description in abilities
            ],
            attachable_leaders=[
                DatasheetReferenceRead(
                    id=leader_id,
                    name=leader_name,
                    faction_name=leader_faction_name,
                    role=leader_role,
                )
                for leader_id, leader_name, leader_faction_name, leader_role in attachable_leaders
            ],
            options=[
                DatasheetOptionRead(
                    button=option.button,
                    description_html=sanitize_html_fragment(option.description),
                )
                for option in options
            ],
            unit_composition=[entry for entry in unit_composition if entry],
            costs=[
                DatasheetCostRead(description=cost.description, cost=cost.cost) for cost in costs
            ],
            models=[
                ModelProfileRead(
                    model_id=model.row_id,
                    line=model.line,
                    name=model.name or datasheet.name,
                    movement=model.m,
                    toughness=parse_required_roll(model.t),
                    save=parse_required_roll(model.sv),
                    invulnerable_save=parse_required_roll(model.inv_sv),
                    wounds=parse_required_roll(model.w),
                    leadership=model.ld,
                    objective_control=model.oc,
                    base_size=model.base_size,
                    base_size_description=model.base_size_descr,
                )
                for model in models
            ],
            weapons=[self._build_weapon_payload(weapon) for weapon in weapons],
            stratagems=[
                RuleReferenceRead(
                    id=stratagem.id,
                    name=stratagem.name,
                    subtitle=stratagem.phase or stratagem.detachment or stratagem.type,
                    cost=stratagem.cp_cost,
                    description_html=sanitize_html_fragment(stratagem.description),
                )
                for stratagem in stratagems
            ],
            enhancements=[
                RuleReferenceRead(
                    id=enhancement.id,
                    name=enhancement.name,
                    subtitle=enhancement.detachment,
                    cost=enhancement.cost,
                    description_html=sanitize_html_fragment(enhancement.description),
                )
                for enhancement in enhancements
            ],
            detachment_abilities=[
                RuleReferenceRead(
                    id=ability.id,
                    name=ability.name,
                    subtitle=ability.detachment,
                    cost=None,
                    description_html=sanitize_html_fragment(ability.description),
                )
                for ability in detachment_abilities
            ],
        )

    def _build_weapon_payload(self, weapon: DatasheetWargear) -> WeaponProfileRead:
        analyzed_weapon = build_weapon_profile(
            weapon_id=weapon.row_id,
            name=weapon.name,
            kind=weapon.type,
            range_value=weapon.range,
            attacks_value=weapon.a,
            skill_value=weapon.bs_ws,
            strength_value=weapon.s,
            ap_value=weapon.ap,
            damage_value=weapon.d,
            description=weapon.description,
        )
        return WeaponProfileRead(
            weapon_id=weapon.row_id,
            line=weapon.line,
            line_in_wargear=weapon.line_in_wargear,
            name=weapon.name,
            weapon_type=weapon.type,
            range=weapon.range,
            attacks=weapon.a,
            skill=weapon.bs_ws,
            strength=weapon.s,
            armour_penetration=weapon.ap,
            damage=weapon.d,
            description_html=sanitize_html_fragment(weapon.description),
            rules=list(analyzed_weapon.rules.supported_rules),
            ignored_rules=list(analyzed_weapon.rules.ignored_rules),
            is_simulatable=analyzed_weapon.weapon is not None,
            simulation_issue=analyzed_weapon.error,
        )
