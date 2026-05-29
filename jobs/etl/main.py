from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from config import get_settings
from ingest.statsbomb import build_manifest, ingest_statsbomb_source, scan_statsbomb_source
from metrics.pipeline import compute_metrics_for_all_matches
from metrics.player_pipeline import compute_player_metrics_for_all_matches
from metrics.player_window_pipeline import compute_player_window_metrics
from metrics.window_pipeline import compute_team_window_metrics


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap CLI for Tactics Lab ETL jobs.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("manifest", help="Print the provider manifest used for local ingestion.")
    subparsers.add_parser("plan", help="Print the first ETL tasks in execution order.")

    scan_statsbomb = subparsers.add_parser("scan-statsbomb", help="Scan local StatsBomb Open Data files.")
    scan_statsbomb.add_argument("--raw-dir", help="Path to a StatsBomb open-data checkout or data folder.")
    scan_statsbomb.add_argument("--limit-matches", type=int, default=None)
    scan_statsbomb.add_argument(
        "--team",
        action="append",
        default=None,
        help="Exact team name filter. Repeat to include multiple teams.",
    )

    ingest_statsbomb = subparsers.add_parser("ingest-statsbomb", help="Ingest local StatsBomb Open Data into Postgres.")
    ingest_statsbomb.add_argument("--raw-dir", help="Path to a StatsBomb open-data checkout or data folder.")
    ingest_statsbomb.add_argument("--database-url", help="Postgres database URL.")
    ingest_statsbomb.add_argument("--limit-matches", type=int, default=None)
    ingest_statsbomb.add_argument(
        "--team",
        action="append",
        default=None,
        help="Exact team name filter. Repeat to include multiple teams.",
    )
    ingest_statsbomb.add_argument("--dry-run", action="store_true", help="Only scan files; do not write to Postgres.")

    compute_metrics = subparsers.add_parser("compute-team-metrics", help="Compute team match metrics from ingested events.")
    compute_metrics.add_argument("--database-url", help="Postgres database URL.")
    compute_metrics.add_argument("--limit-matches", type=int, default=None)

    compute_team_windows = subparsers.add_parser(
        "compute-team-window-metrics",
        help="Aggregate team match metrics into historical team style windows.",
    )
    compute_team_windows.add_argument("--database-url", help="Postgres database URL.")
    compute_team_windows.add_argument("--team-id", type=int, default=None)

    compute_player_metrics = subparsers.add_parser(
        "compute-player-match-metrics",
        help="Compute player match metrics from ingested events and lineups.",
    )
    compute_player_metrics.add_argument("--database-url", help="Postgres database URL.")
    compute_player_metrics.add_argument("--limit-matches", type=int, default=None)

    compute_player_windows = subparsers.add_parser(
        "compute-player-window-metrics",
        help="Aggregate player match metrics into historical player role windows.",
    )
    compute_player_windows.add_argument("--database-url", help="Postgres database URL.")
    compute_player_windows.add_argument("--player-id", type=int, default=None)
    compute_player_windows.add_argument("--team-id", type=int, default=None)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    settings = get_settings()

    if args.command == "manifest":
        print(json.dumps(build_manifest(settings).model_dump(), indent=2))
        return 0

    if args.command == "plan":
        plan = [
            "ingest_competitions",
            "ingest_matches",
            "ingest_lineups",
            "ingest_events",
            "ingest_manual_position_profiles",
            "compute_team_match_metrics",
            "compute_team_window_metrics",
            "compute_player_match_metrics",
            "compute_player_window_metrics",
            "generate_tactical_report",
        ]
        print(json.dumps({"provider": settings.provider_code, "tasks": plan}, indent=2))
        return 0

    if args.command == "scan-statsbomb":
        raw_dir = Path(args.raw_dir) if args.raw_dir else Path(settings.raw_data_root) / "statsbomb"
        summary = scan_statsbomb_source(raw_dir, limit_matches=args.limit_matches, team_names=args.team)
        print(json.dumps(summary.model_dump(), indent=2))
        return 0

    if args.command == "ingest-statsbomb":
        raw_dir = Path(args.raw_dir) if args.raw_dir else Path(settings.raw_data_root) / "statsbomb"
        if args.dry_run:
            summary = scan_statsbomb_source(raw_dir, limit_matches=args.limit_matches, team_names=args.team)
        else:
            summary = ingest_statsbomb_source(
                raw_dir,
                database_url=args.database_url or settings.database_url,
                limit_matches=args.limit_matches,
                team_names=args.team,
            )
        print(json.dumps(summary.model_dump(), indent=2))
        return 0

    if args.command == "compute-team-metrics":
        summary = compute_metrics_for_all_matches(
            database_url=args.database_url or settings.database_url,
            limit_matches=args.limit_matches,
        )
        print(json.dumps(asdict(summary), indent=2))
        return 0

    if args.command == "compute-team-window-metrics":
        summary = compute_team_window_metrics(
            database_url=args.database_url or settings.database_url,
            team_id=args.team_id,
        )
        print(json.dumps(asdict(summary), indent=2))
        return 0

    if args.command == "compute-player-match-metrics":
        summary = compute_player_metrics_for_all_matches(
            database_url=args.database_url or settings.database_url,
            limit_matches=args.limit_matches,
        )
        print(json.dumps(asdict(summary), indent=2))
        return 0

    if args.command == "compute-player-window-metrics":
        summary = compute_player_window_metrics(
            database_url=args.database_url or settings.database_url,
            player_id=args.player_id,
            team_id=args.team_id,
        )
        print(json.dumps(asdict(summary), indent=2))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
