from __future__ import annotations

import argparse
import json

from config import get_settings
from ingest.statsbomb import build_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap CLI for Tactics Lab ETL jobs.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("manifest", help="Print the provider manifest used for local ingestion.")
    subparsers.add_parser("plan", help="Print the first ETL tasks in execution order.")

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

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
