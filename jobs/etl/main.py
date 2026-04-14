from __future__ import annotations

import argparse
import json
from pathlib import Path

from config import get_settings
from ingest.statsbomb import build_manifest, ingest_statsbomb_source, scan_statsbomb_source


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap CLI for Tactics Lab ETL jobs.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("manifest", help="Print the provider manifest used for local ingestion.")
    subparsers.add_parser("plan", help="Print the first ETL tasks in execution order.")

    scan_statsbomb = subparsers.add_parser("scan-statsbomb", help="Scan local StatsBomb Open Data files.")
    scan_statsbomb.add_argument("--raw-dir", help="Path to a StatsBomb open-data checkout or data folder.")
    scan_statsbomb.add_argument("--limit-matches", type=int, default=None)

    ingest_statsbomb = subparsers.add_parser("ingest-statsbomb", help="Ingest local StatsBomb Open Data into Postgres.")
    ingest_statsbomb.add_argument("--raw-dir", help="Path to a StatsBomb open-data checkout or data folder.")
    ingest_statsbomb.add_argument("--database-url", help="Postgres database URL.")
    ingest_statsbomb.add_argument("--limit-matches", type=int, default=None)
    ingest_statsbomb.add_argument("--dry-run", action="store_true", help="Only scan files; do not write to Postgres.")

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
            "compute_player_match_metrics",
            "generate_tactical_report",
        ]
        print(json.dumps({"provider": settings.provider_code, "tasks": plan}, indent=2))
        return 0

    if args.command == "scan-statsbomb":
        raw_dir = Path(args.raw_dir) if args.raw_dir else Path(settings.raw_data_root) / "statsbomb"
        summary = scan_statsbomb_source(raw_dir, limit_matches=args.limit_matches)
        print(json.dumps(summary.model_dump(), indent=2))
        return 0

    if args.command == "ingest-statsbomb":
        raw_dir = Path(args.raw_dir) if args.raw_dir else Path(settings.raw_data_root) / "statsbomb"
        if args.dry_run:
            summary = scan_statsbomb_source(raw_dir, limit_matches=args.limit_matches)
        else:
            summary = ingest_statsbomb_source(
                raw_dir,
                database_url=args.database_url or settings.database_url,
                limit_matches=args.limit_matches,
            )
        print(json.dumps(summary.model_dump(), indent=2))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
