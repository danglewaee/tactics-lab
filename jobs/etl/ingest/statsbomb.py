from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from db import Database
from pydantic import BaseModel, Field

from config import ETLSettings


class ProviderManifest(BaseModel):
    provider: str
    raw_root: str
    processed_root: str
    expected_entities: list[str] = Field(default_factory=list)


def build_manifest(settings: ETLSettings) -> ProviderManifest:
    return ProviderManifest(
        provider=settings.provider_code,
        raw_root=settings.raw_data_root,
        processed_root=settings.processed_data_root,
        expected_entities=["competitions", "matches", "lineups", "events"],
    )


class IngestionSummary(BaseModel):
    provider: str = "statsbomb"
    source_root: str
    competitions: int = 0
    seasons: int = 0
    teams: int = 0
    players: int = 0
    matches: int = 0
    lineups: int = 0
    events: int = 0
    related_events: int = 0
    files: dict[str, int] = Field(default_factory=dict)


@dataclass(slots=True)
class StatsBombDataSource:
    raw_dir: Path

    @property
    def data_root(self) -> Path:
        candidates = [self.raw_dir, self.raw_dir / "data"]
        for candidate in candidates:
            if (candidate / "competitions.json").exists():
                return candidate
        for candidate in candidates:
            if any((candidate / folder).exists() for folder in ("matches", "lineups", "events")):
                return candidate
        raise FileNotFoundError(
            "StatsBomb data root not found. Expected competitions.json or data/competitions.json "
            f"under {self.raw_dir}."
        )

    @property
    def competitions_path(self) -> Path:
        return self.data_root / "competitions.json"

    @property
    def matches_root(self) -> Path:
        return self.data_root / "matches"

    @property
    def lineups_root(self) -> Path:
        return self.data_root / "lineups"

    @property
    def events_root(self) -> Path:
        return self.data_root / "events"

    def read_competitions(self) -> list[dict[str, Any]]:
        if not self.competitions_path.exists():
            return []
        return read_json_list(self.competitions_path)

    def iter_match_files(self) -> Iterable[Path]:
        if not self.matches_root.exists():
            return []
        return sorted(self.matches_root.glob("*/*.json"))

    def event_file_for_match(self, match_external_id: str) -> Path:
        return self.events_root / f"{match_external_id}.json"

    def lineup_file_for_match(self, match_external_id: str) -> Path:
        return self.lineups_root / f"{match_external_id}.json"


def read_json_list(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"Expected a JSON array in {path}.")
    return payload


def scan_statsbomb_source(raw_dir: str | Path, limit_matches: int | None = None) -> IngestionSummary:
    source = StatsBombDataSource(Path(raw_dir))
    data_root = source.data_root
    summary = IngestionSummary(source_root=str(data_root))

    competitions = source.read_competitions()
    summary.competitions = len({item.get("competition_id") for item in competitions})
    summary.seasons = len({item.get("season_id") for item in competitions})
    summary.files["competitions"] = int(source.competitions_path.exists())

    match_records = 0
    match_ids: list[str] = []
    match_files = 0
    for match_file in source.iter_match_files():
        match_files += 1
        for match in read_json_list(match_file):
            if limit_matches is not None and match_records >= limit_matches:
                break
            match_records += 1
            match_ids.append(str(match.get("match_id")))
        if limit_matches is not None and match_records >= limit_matches:
            break

    summary.matches = match_records
    summary.files["matches"] = match_files

    lineup_records = 0
    lineup_files = 0
    event_records = 0
    event_files = 0
    for match_id in match_ids:
        lineup_file = source.lineup_file_for_match(match_id)
        if lineup_file.exists():
            lineup_files += 1
            lineup_records += sum(len(team.get("lineup", [])) for team in read_json_list(lineup_file))

        event_file = source.event_file_for_match(match_id)
        if event_file.exists():
            event_files += 1
            event_records += len(read_json_list(event_file))

    summary.lineups = lineup_records
    summary.events = event_records
    summary.files["lineups"] = lineup_files
    summary.files["events"] = event_files

    return summary


def ingest_statsbomb_source(
    raw_dir: str | Path,
    database_url: str,
    limit_matches: int | None = None,
) -> IngestionSummary:
    source = StatsBombDataSource(Path(raw_dir))
    summary = IngestionSummary(source_root=str(source.data_root))

    with Database(database_url) as database:
        writer = StatsBombWriter(database)
        writer.ensure_provider()

        competitions = source.read_competitions()
        summary.files["competitions"] = int(source.competitions_path.exists())
        for item in competitions:
            writer.upsert_competition_and_season(item)
        summary.competitions = len(writer.competition_cache)
        summary.seasons = len(writer.season_cache)

        match_records = 0
        match_files = 0
        match_external_ids: list[str] = []
        for match_file in source.iter_match_files():
            match_files += 1
            for match in read_json_list(match_file):
                if limit_matches is not None and match_records >= limit_matches:
                    break
                match_id = writer.upsert_match(match)
                if match_id is not None:
                    match_records += 1
                    match_external_ids.append(str(match.get("match_id")))
            if limit_matches is not None and match_records >= limit_matches:
                break

        summary.matches = match_records
        summary.files["matches"] = match_files

        lineup_files = 0
        event_files = 0
        for match_external_id in match_external_ids:
            lineup_file = source.lineup_file_for_match(match_external_id)
            if lineup_file.exists():
                lineup_files += 1
                summary.lineups += writer.ingest_lineups(match_external_id, read_json_list(lineup_file))

            event_file = source.event_file_for_match(match_external_id)
            if event_file.exists():
                event_files += 1
                event_counts = writer.ingest_events(match_external_id, read_json_list(event_file))
                summary.events += event_counts["events"]
                summary.related_events += event_counts["related_events"]

        summary.files["lineups"] = lineup_files
        summary.files["events"] = event_files
        summary.teams = len(writer.team_cache)
        summary.players = len(writer.player_cache)

    return summary


class StatsBombWriter:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.provider_id: int | None = None
        self.competition_cache: dict[str, int] = {}
        self.season_cache: dict[str, int] = {}
        self.team_cache: dict[str, int] = {}
        self.player_cache: dict[str, int] = {}
        self.match_cache: dict[str, int] = {}

    def ensure_provider(self) -> int:
        if self.provider_id is not None:
            return self.provider_id

        provider_id = self.database.fetch_value(
            """
            insert into providers (code, name, base_reference)
            values ('statsbomb', 'StatsBomb / event-data style provider', 'https://github.com/statsbomb/open-data')
            on conflict (code) do update set
                name = excluded.name,
                base_reference = excluded.base_reference
            returning provider_id
            """,
            (),
        )
        self.provider_id = int(provider_id)
        return self.provider_id

    def upsert_competition_and_season(self, item: dict[str, Any]) -> tuple[int, int]:
        provider_id = self.ensure_provider()
        competition_external_id = str(item["competition_id"])
        season_external_id = str(item["season_id"])

        competition_id = self.database.fetch_value(
            """
            insert into competitions (
                provider_id, external_id, name, country_name, competition_gender, metadata
            )
            values (%s, %s, %s, %s, %s, %s)
            on conflict (provider_id, external_id) do update set
                name = excluded.name,
                country_name = excluded.country_name,
                competition_gender = excluded.competition_gender,
                metadata = excluded.metadata
            returning competition_id
            """,
            (
                provider_id,
                competition_external_id,
                item.get("competition_name") or f"Competition {competition_external_id}",
                item.get("country_name"),
                item.get("competition_gender"),
                self.database.jsonb(item),
            ),
        )
        self.competition_cache[competition_external_id] = int(competition_id)

        season_id = self.database.fetch_value(
            """
            insert into seasons (
                provider_id, competition_id, external_id, name, start_date, end_date, metadata
            )
            values (%s, %s, %s, %s, %s, %s, %s)
            on conflict (provider_id, external_id) do update set
                competition_id = excluded.competition_id,
                name = excluded.name,
                metadata = excluded.metadata
            returning season_id
            """,
            (
                provider_id,
                int(competition_id),
                season_external_id,
                item.get("season_name") or f"Season {season_external_id}",
                None,
                None,
                self.database.jsonb(item),
            ),
        )
        self.season_cache[season_external_id] = int(season_id)
        return int(competition_id), int(season_id)

    def upsert_match(self, match: dict[str, Any]) -> int | None:
        provider_id = self.ensure_provider()
        match_external_id = str(match.get("match_id"))
        if not match_external_id or match_external_id == "None":
            return None

        competition_id, season_id = self._ensure_match_competition_and_season(match)
        home_team_id = self.upsert_team(match.get("home_team", {}), "home_team")
        away_team_id = self.upsert_team(match.get("away_team", {}), "away_team")

        match_id = self.database.fetch_value(
            """
            insert into matches (
                provider_id, external_id, competition_id, season_id, match_date, kickoff_at,
                home_team_id, away_team_id, home_score, away_score, stadium_name,
                referee_name, match_week, metadata
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (provider_id, external_id) do update set
                competition_id = excluded.competition_id,
                season_id = excluded.season_id,
                match_date = excluded.match_date,
                kickoff_at = excluded.kickoff_at,
                home_team_id = excluded.home_team_id,
                away_team_id = excluded.away_team_id,
                home_score = excluded.home_score,
                away_score = excluded.away_score,
                stadium_name = excluded.stadium_name,
                referee_name = excluded.referee_name,
                match_week = excluded.match_week,
                metadata = excluded.metadata
            returning match_id
            """,
            (
                provider_id,
                match_external_id,
                competition_id,
                season_id,
                match.get("match_date") or date.today().isoformat(),
                build_kickoff_at(match),
                home_team_id,
                away_team_id,
                match.get("home_score"),
                match.get("away_score"),
                entity_name(match.get("stadium"), "stadium"),
                entity_name(match.get("referee"), "referee"),
                match.get("match_week"),
                self.database.jsonb(match),
            ),
        )
        self.match_cache[match_external_id] = int(match_id)
        return int(match_id)

    def ingest_lineups(self, match_external_id: str, payload: list[dict[str, Any]]) -> int:
        match_id = self.match_cache.get(match_external_id)
        if match_id is None:
            return 0

        written = 0
        for team_payload in payload:
            team_id = self.upsert_team(team_payload, "team")
            for player_payload in team_payload.get("lineup", []):
                player_id = self.upsert_player(player_payload, fallback_position=first_position_name(player_payload))
                position = first_position(player_payload)
                start_minute, end_minute = position_window(player_payload)

                self.database.fetch_value(
                    """
                    insert into lineups (
                        match_id, team_id, player_id, jersey_number, position_name, position_group,
                        is_starter, start_minute, end_minute, metadata
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (match_id, team_id, player_id) do update set
                        jersey_number = excluded.jersey_number,
                        position_name = excluded.position_name,
                        position_group = excluded.position_group,
                        is_starter = excluded.is_starter,
                        start_minute = excluded.start_minute,
                        end_minute = excluded.end_minute,
                        metadata = excluded.metadata
                    returning lineup_id
                    """,
                    (
                        match_id,
                        team_id,
                        player_id,
                        player_payload.get("jersey_number"),
                        entity_name(position, "position"),
                        position_group(entity_name(position, "position")),
                        start_minute == 0,
                        start_minute,
                        end_minute,
                        self.database.jsonb(player_payload),
                    ),
                )
                written += 1
        return written

    def ingest_events(self, match_external_id: str, payload: list[dict[str, Any]]) -> dict[str, int]:
        match_id = self.match_cache.get(match_external_id)
        if match_id is None:
            return {"events": 0, "related_events": 0}

        external_to_internal: dict[str, int] = {}
        for raw_event in payload:
            event_id = self.upsert_event(match_id, raw_event)
            if event_id is not None:
                external_to_internal[str(raw_event.get("id"))] = event_id

        related_written = 0
        for raw_event in payload:
            event_id = external_to_internal.get(str(raw_event.get("id")))
            if event_id is None:
                continue

            for related_external_id in raw_event.get("related_events", []):
                related_event_id = external_to_internal.get(str(related_external_id))
                if related_event_id is None:
                    continue
                self.database.execute(
                    """
                    insert into event_related_events (event_id, related_event_id, relation_type)
                    values (%s, %s, 'statsbomb_related')
                    on conflict do nothing
                    """,
                    (event_id, related_event_id),
                )
                related_written += 1

        return {"events": len(external_to_internal), "related_events": related_written}

    def upsert_event(self, match_id: int, raw_event: dict[str, Any]) -> int | None:
        provider_id = self.ensure_provider()
        external_id = str(raw_event.get("id"))
        if not external_id or external_id == "None":
            return None

        team_id = self.upsert_team(raw_event.get("team"), "team") if raw_event.get("team") else None
        player_id = self.upsert_player(raw_event.get("player")) if raw_event.get("player") else None
        possession_team_id = (
            self.upsert_team(raw_event.get("possession_team"), "team")
            if raw_event.get("possession_team")
            else None
        )
        pass_payload = raw_event.get("pass") if isinstance(raw_event.get("pass"), dict) else {}
        pass_recipient_player_id = (
            self.upsert_player(pass_payload.get("recipient"))
            if isinstance(pass_payload, dict) and pass_payload.get("recipient")
            else None
        )
        normalized = normalize_event_payload(raw_event)

        event_id = self.database.fetch_value(
            """
            insert into events (
                match_id, provider_id, external_id, index_in_match, period, minute, second,
                timestamp_ms, team_id, player_id, possession_id, play_pattern, event_type,
                event_subtype, outcome, body_part, technique, under_pressure, counterpress,
                x_start, y_start, x_end, y_end, duration_seconds, pass_recipient_player_id,
                pass_height, pass_length, pass_angle, shot_xg, related_team_id, metadata, raw_event
            )
            values (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            on conflict (match_id, external_id) do update set
                index_in_match = excluded.index_in_match,
                period = excluded.period,
                minute = excluded.minute,
                second = excluded.second,
                timestamp_ms = excluded.timestamp_ms,
                team_id = excluded.team_id,
                player_id = excluded.player_id,
                possession_id = excluded.possession_id,
                play_pattern = excluded.play_pattern,
                event_type = excluded.event_type,
                event_subtype = excluded.event_subtype,
                outcome = excluded.outcome,
                body_part = excluded.body_part,
                technique = excluded.technique,
                under_pressure = excluded.under_pressure,
                counterpress = excluded.counterpress,
                x_start = excluded.x_start,
                y_start = excluded.y_start,
                x_end = excluded.x_end,
                y_end = excluded.y_end,
                duration_seconds = excluded.duration_seconds,
                pass_recipient_player_id = excluded.pass_recipient_player_id,
                pass_height = excluded.pass_height,
                pass_length = excluded.pass_length,
                pass_angle = excluded.pass_angle,
                shot_xg = excluded.shot_xg,
                related_team_id = excluded.related_team_id,
                metadata = excluded.metadata,
                raw_event = excluded.raw_event
            returning event_id
            """,
            (
                match_id,
                provider_id,
                external_id,
                normalized["index_in_match"],
                normalized["period"],
                normalized["minute"],
                normalized["second"],
                normalized["timestamp_ms"],
                team_id,
                player_id,
                raw_event.get("possession"),
                entity_name(raw_event.get("play_pattern"), "play_pattern"),
                normalized["event_type"],
                normalized["event_subtype"],
                normalized["outcome"],
                normalized["body_part"],
                normalized["technique"],
                normalized["under_pressure"],
                normalized["counterpress"],
                normalized["x_start"],
                normalized["y_start"],
                normalized["x_end"],
                normalized["y_end"],
                raw_event.get("duration"),
                pass_recipient_player_id,
                normalized["pass_height"],
                normalized["pass_length"],
                normalized["pass_angle"],
                normalized["shot_xg"],
                possession_team_id,
                self.database.jsonb({"provider": "statsbomb"}),
                self.database.jsonb(raw_event),
            ),
        )
        return int(event_id)

    def upsert_team(self, entity: Any, prefix: str) -> int:
        provider_id = self.ensure_provider()
        external_id = entity_external_id(entity, prefix)
        if external_id is None:
            raise ValueError(f"Missing team id for {entity!r}.")

        external_id = str(external_id)
        if external_id in self.team_cache:
            return self.team_cache[external_id]

        team_id = self.database.fetch_value(
            """
            insert into teams (provider_id, external_id, name, short_name, country_name, team_type, metadata)
            values (%s, %s, %s, %s, %s, %s, %s)
            on conflict (provider_id, external_id) do update set
                name = excluded.name,
                short_name = excluded.short_name,
                country_name = excluded.country_name,
                metadata = teams.metadata || excluded.metadata
            returning team_id
            """,
            (
                provider_id,
                external_id,
                entity_name(entity, prefix) or f"Team {external_id}",
                entity_short_name(entity, prefix),
                entity_country(entity),
                None,
                self.database.jsonb(entity if isinstance(entity, dict) else {}),
            ),
        )
        self.team_cache[external_id] = int(team_id)
        return int(team_id)

    def upsert_player(self, entity: Any, fallback_position: str | None = None) -> int:
        provider_id = self.ensure_provider()
        external_id = entity_external_id(entity, "player")
        if external_id is None:
            raise ValueError(f"Missing player id for {entity!r}.")

        external_id = str(external_id)
        if external_id in self.player_cache:
            return self.player_cache[external_id]

        player_name = entity_name(entity, "player") or f"Player {external_id}"
        position = entity_name(entity.get("position"), "position") if isinstance(entity, dict) else None
        player_id = self.database.fetch_value(
            """
            insert into players (
                provider_id, external_id, name, display_name, country_name, birth_date,
                dominant_foot, primary_position, position_group, metadata
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (provider_id, external_id) do update set
                name = excluded.name,
                display_name = coalesce(excluded.display_name, players.display_name),
                country_name = coalesce(excluded.country_name, players.country_name),
                primary_position = coalesce(excluded.primary_position, players.primary_position),
                position_group = coalesce(excluded.position_group, players.position_group),
                metadata = players.metadata || excluded.metadata
            returning player_id
            """,
            (
                provider_id,
                external_id,
                player_name,
                entity.get("player_nickname") if isinstance(entity, dict) else None,
                entity_country(entity),
                None,
                None,
                position or fallback_position,
                position_group(position or fallback_position),
                self.database.jsonb(entity if isinstance(entity, dict) else {}),
            ),
        )
        self.player_cache[external_id] = int(player_id)
        return int(player_id)

    def _ensure_match_competition_and_season(self, match: dict[str, Any]) -> tuple[int, int]:
        provider_id = self.ensure_provider()
        competition = match.get("competition", {})
        season = match.get("season", {})
        competition_external_id = str(entity_external_id(competition, "competition"))
        season_external_id = str(entity_external_id(season, "season"))

        if competition_external_id in self.competition_cache and season_external_id in self.season_cache:
            return self.competition_cache[competition_external_id], self.season_cache[season_external_id]

        competition_id = self.database.fetch_value(
            """
            insert into competitions (provider_id, external_id, name, country_name, competition_gender, metadata)
            values (%s, %s, %s, %s, %s, %s)
            on conflict (provider_id, external_id) do update set
                name = excluded.name,
                metadata = competitions.metadata || excluded.metadata
            returning competition_id
            """,
            (
                provider_id,
                competition_external_id,
                entity_name(competition, "competition") or f"Competition {competition_external_id}",
                None,
                None,
                self.database.jsonb(competition),
            ),
        )
        self.competition_cache[competition_external_id] = int(competition_id)

        season_id = self.database.fetch_value(
            """
            insert into seasons (provider_id, competition_id, external_id, name, start_date, end_date, metadata)
            values (%s, %s, %s, %s, %s, %s, %s)
            on conflict (provider_id, external_id) do update set
                competition_id = excluded.competition_id,
                name = excluded.name,
                metadata = seasons.metadata || excluded.metadata
            returning season_id
            """,
            (
                provider_id,
                int(competition_id),
                season_external_id,
                entity_name(season, "season") or f"Season {season_external_id}",
                None,
                None,
                self.database.jsonb(season),
            ),
        )
        self.season_cache[season_external_id] = int(season_id)
        return int(competition_id), int(season_id)


def normalize_event_payload(raw_event: dict[str, Any]) -> dict[str, Any]:
    event_type = entity_name(raw_event.get("type"), "type") or "Unknown"
    event_detail = event_detail_payload(raw_event, event_type)
    pass_payload = raw_event.get("pass") if isinstance(raw_event.get("pass"), dict) else {}
    shot_payload = raw_event.get("shot") if isinstance(raw_event.get("shot"), dict) else {}

    x_start, y_start = normalize_coordinates(raw_event.get("location"))
    x_end, y_end = normalize_coordinates(end_location(raw_event, event_type))

    return {
        "index_in_match": int(raw_event.get("index") or 0),
        "period": int(raw_event.get("period") or 0),
        "minute": int(raw_event.get("minute") or 0),
        "second": int(raw_event.get("second") or 0),
        "timestamp_ms": timestamp_to_ms(raw_event.get("timestamp")),
        "event_type": event_type,
        "event_subtype": entity_name(event_detail.get("type"), "type") if event_detail else None,
        "outcome": first_entity_name("outcome", event_detail, shot_payload, pass_payload),
        "body_part": first_entity_name("body_part", event_detail, shot_payload, pass_payload),
        "technique": first_entity_name("technique", event_detail, shot_payload, pass_payload),
        "under_pressure": bool(raw_event.get("under_pressure", False)),
        "counterpress": bool(raw_event.get("counterpress", False)),
        "x_start": x_start,
        "y_start": y_start,
        "x_end": x_end,
        "y_end": y_end,
        "pass_height": entity_name(pass_payload.get("height"), "height") if pass_payload else None,
        "pass_length": pass_payload.get("length") if pass_payload else None,
        "pass_angle": pass_payload.get("angle") if pass_payload else None,
        "shot_xg": shot_payload.get("statsbomb_xg") if shot_payload else None,
    }


def normalize_coordinates(location: Any) -> tuple[float | None, float | None]:
    if not isinstance(location, list) or len(location) < 2:
        return None, None
    return float(location[0]), float(location[1])


def end_location(raw_event: dict[str, Any], event_type: str) -> Any:
    if event_type == "Pass" and isinstance(raw_event.get("pass"), dict):
        return raw_event["pass"].get("end_location")
    if event_type == "Carry" and isinstance(raw_event.get("carry"), dict):
        return raw_event["carry"].get("end_location")
    if isinstance(raw_event.get("shot"), dict):
        return raw_event["shot"].get("end_location")
    return None


def event_detail_payload(raw_event: dict[str, Any], event_type: str) -> dict[str, Any]:
    candidates = [
        slugify_event_key(event_type),
        slugify_event_key(event_type).replace("_", ""),
        "goalkeeper" if event_type == "Goal Keeper" else "",
        "ball_receipt" if event_type.startswith("Ball Receipt") else "",
    ]
    for key in candidates:
        value = raw_event.get(key)
        if isinstance(value, dict):
            return value
    return {}


def timestamp_to_ms(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    match = re.match(r"^(?P<h>\d+):(?P<m>\d+):(?P<s>\d+)(?:\.(?P<ms>\d+))?$", value)
    if match is None:
        return None
    hours = int(match.group("h"))
    minutes = int(match.group("m"))
    seconds = int(match.group("s"))
    milliseconds = int((match.group("ms") or "0").ljust(3, "0")[:3])
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + milliseconds


def slugify_event_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def first_entity_name(key: str, *payloads: Any) -> str | None:
    for payload in payloads:
        if isinstance(payload, dict):
            name = entity_name(payload.get(key), key)
            if name:
                return name
    return None


def entity_external_id(entity: Any, prefix: str) -> Any:
    if not isinstance(entity, dict):
        return None
    return entity.get(f"{prefix}_id") or entity.get("id")


def entity_name(entity: Any, prefix: str) -> str | None:
    if not isinstance(entity, dict):
        return None
    value = entity.get(f"{prefix}_name") or entity.get("name")
    return str(value) if value is not None else None


def entity_short_name(entity: Any, prefix: str) -> str | None:
    if not isinstance(entity, dict):
        return None
    value = entity.get(f"{prefix}_short_name") or entity.get("short_name")
    return str(value) if value is not None else None


def entity_country(entity: Any) -> str | None:
    if not isinstance(entity, dict):
        return None
    if entity.get("country_name"):
        return str(entity["country_name"])
    country = entity.get("country")
    if isinstance(country, dict):
        return entity_name(country, "country")
    return None


def build_kickoff_at(match: dict[str, Any]) -> str | None:
    match_date = match.get("match_date")
    kickoff = match.get("kick_off")
    if not match_date or not kickoff:
        return None
    return f"{match_date} {kickoff}+00"


def first_position(player_payload: dict[str, Any]) -> dict[str, Any]:
    positions = player_payload.get("positions")
    if isinstance(positions, list) and positions:
        first = positions[0]
        if isinstance(first, dict):
            return first
    return {}


def first_position_name(player_payload: dict[str, Any]) -> str | None:
    return entity_name(first_position(player_payload), "position")


def position_window(player_payload: dict[str, Any]) -> tuple[int, int]:
    positions = player_payload.get("positions")
    if not isinstance(positions, list) or not positions:
        return 0, 120

    starts = [minute_from_position_time(item.get("from")) for item in positions if isinstance(item, dict)]
    ends = [minute_from_position_time(item.get("to")) for item in positions if isinstance(item, dict)]
    starts = [item for item in starts if item is not None]
    ends = [item for item in ends if item is not None]
    return min(starts or [0]), max(ends or [120])


def minute_from_position_time(value: Any) -> int | None:
    if not isinstance(value, str) or ":" not in value:
        return None
    return int(value.split(":", 1)[0])


def position_group(position_name: str | None) -> str | None:
    if not position_name:
        return None
    name = position_name.lower()
    if "goalkeeper" in name:
        return "goalkeeper"
    if "back" in name:
        return "defender"
    if "midfield" in name:
        return "midfielder"
    if "wing" in name or "forward" in name or "striker" in name:
        return "forward"
    return None
