from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.editorial import (
    _match_card_from_row,
    _resolve_team_type,
    get_match_detail,
    get_team,
    list_teams,
)


class DatabaseReadTests(unittest.TestCase):
    def test_list_teams_uses_database_rows_when_available(self) -> None:
        rows = [
            {
                "team_id": 1,
                "external_id": "1",
                "name": "Manchester United",
                "short_name": "MU",
                "country_name": "England",
                "team_type": None,
                "match_count": 5,
            }
        ]

        with patch("services.editorial._query_rows_safe", return_value=rows):
            teams = list_teams()

        self.assertEqual(len(teams), 1)
        self.assertEqual(teams[0].team_slug, "manchester-united")
        self.assertTrue(teams[0].editorial_focus)
        self.assertEqual(teams[0].team_type, "club")

    def test_get_team_uses_database_row_and_editorial_metadata(self) -> None:
        row = {
            "team_id": 1,
            "external_id": "1",
            "name": "Portugal",
            "short_name": "POR",
            "country_name": "Portugal",
            "team_type": None,
            "match_count": 3,
        }

        with patch("services.editorial._load_team_row_by_slug", return_value=row), patch(
            "services.editorial._team_has_events", return_value=True
        ):
            team = get_team("portugal")

        self.assertIsNotNone(team)
        self.assertEqual(team.team_slug, "portugal")
        self.assertEqual(team.team_type, "national_team")
        self.assertEqual(team.data_status, "ready")
        self.assertIn("counterpress_regains", team.target_metrics)

    def test_match_card_marks_event_backed_matches_ready(self) -> None:
        card = _match_card_from_row(
            {
                "match_id": 12,
                "home_team_name": "Manchester United",
                "away_team_name": "Portugal",
                "home_score": 2,
                "away_score": 1,
                "has_events": True,
            },
            subject_team_slug="manchester-united",
            subject_team_name="Manchester United",
        )

        self.assertEqual(card.match_id, "12")
        self.assertEqual(card.title, "Manchester United 2-1 Portugal")
        self.assertEqual(card.data_status, "ready")

    def test_get_match_detail_uses_database_match(self) -> None:
        match_row = {
            "match_id": 77,
            "external_id": "9001",
            "home_team_name": "Manchester United",
            "away_team_name": "Portugal",
            "home_score": 3,
            "away_score": 2,
            "has_events": True,
        }

        with patch("services.editorial._load_match_row", return_value=match_row), patch(
            "services.editorial._load_match_takeaways", return_value=[]
        ):
            match = get_match_detail("77")

        self.assertIsNotNone(match)
        self.assertEqual(match.match_id, "77")
        self.assertEqual(match.subject_team_slug, "manchester-united")
        self.assertEqual(match.data_status, "ready")
        self.assertIn("pass_network", match.chart_blocks)
        self.assertEqual(match.takeaways[0].title, "Metrics pending")

    def test_resolve_team_type_infers_national_team_from_country_name(self) -> None:
        team_type = _resolve_team_type(
            {
                "name": "Portugal",
                "country_name": "Portugal",
                "team_type": None,
            },
            editorial=None,
        )

        self.assertEqual(team_type, "national_team")


if __name__ == "__main__":
    unittest.main()
