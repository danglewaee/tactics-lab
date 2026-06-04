from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from schemas.match import MetricValue
from services.editorial import (
    _match_card_from_row,
    _qualification_minutes_for_window,
    _resolve_team_type,
    _select_team_row_for_slug,
    get_match_detail,
    get_team,
    get_team_players,
    get_team_style,
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

    def test_list_teams_deduplicates_editorial_slug_variants(self) -> None:
        rows = [
            {
                "team_id": 77,
                "external_id": "1475",
                "name": "Manchester United",
                "short_name": "MUW",
                "country_name": "England",
                "team_type": None,
                "match_count": 36,
            },
            {
                "team_id": 55,
                "external_id": "39",
                "name": "Manchester United",
                "short_name": "MU",
                "country_name": "England",
                "team_type": None,
                "match_count": 43,
            },
            {
                "team_id": 90,
                "external_id": "780",
                "name": "Portugal",
                "short_name": "POR",
                "country_name": "Portugal",
                "team_type": None,
                "match_count": 18,
            },
        ]

        with patch("services.editorial._query_rows_safe", return_value=rows):
            teams = list_teams()

        self.assertEqual([team.team_slug for team in teams], ["manchester-united", "portugal"])
        self.assertEqual(teams[0].short_name, "MU")
        self.assertEqual(teams[1].team_type, "national_team")

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

    def test_select_team_row_for_slug_prefers_editorial_external_id(self) -> None:
        rows = [
            {
                "team_id": 77,
                "external_id": "1475",
                "name": "Manchester United",
                "short_name": "MUW",
                "country_name": "England",
                "team_type": None,
                "match_count": 36,
            },
            {
                "team_id": 55,
                "external_id": "39",
                "name": "Manchester United",
                "short_name": "MU",
                "country_name": "England",
                "team_type": None,
                "match_count": 43,
            },
        ]

        selected = _select_team_row_for_slug(rows, "manchester-united")

        self.assertEqual(selected["team_id"], 55)
        self.assertEqual(selected["external_id"], "39")

    def test_select_team_row_for_slug_falls_back_to_highest_match_count(self) -> None:
        rows = [
            {
                "team_id": 11,
                "external_id": "501",
                "name": "Valencia",
                "short_name": "VAL B",
                "country_name": "Spain",
                "team_type": None,
                "match_count": 7,
            },
            {
                "team_id": 10,
                "external_id": "500",
                "name": "Valencia",
                "short_name": "VAL",
                "country_name": "Spain",
                "team_type": None,
                "match_count": 12,
            },
        ]

        selected = _select_team_row_for_slug(rows, "valencia")

        self.assertEqual(selected["team_id"], 10)
        self.assertEqual(selected["external_id"], "500")

    def test_select_team_row_for_slug_breaks_ties_by_lower_team_id(self) -> None:
        rows = [
            {
                "team_id": 21,
                "external_id": "601",
                "name": "Sevilla",
                "short_name": "SEV B",
                "country_name": "Spain",
                "team_type": None,
                "match_count": 9,
            },
            {
                "team_id": 20,
                "external_id": "600",
                "name": "Sevilla",
                "short_name": "SEV",
                "country_name": "Spain",
                "team_type": None,
                "match_count": 9,
            },
        ]

        selected = _select_team_row_for_slug(rows, "sevilla")

        self.assertEqual(selected["team_id"], 20)
        self.assertEqual(selected["external_id"], "600")

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
            "home_team_id": 1,
            "away_team_id": 2,
            "home_team_name": "Manchester United",
            "away_team_name": "Portugal",
            "home_score": 3,
            "away_score": 2,
            "has_events": True,
        }

        with patch("services.editorial._load_match_row", return_value=match_row), patch(
            "services.editorial._load_match_takeaways", return_value=[]
        ), patch(
            "services.editorial._load_match_metrics",
            return_value=[MetricValue(key="progressive_passes", label="Progressive passes", value=9.0, display_value="9")],
        ) as metrics_mock:
            match = get_match_detail("77")

        self.assertIsNotNone(match)
        self.assertEqual(match.match_id, "77")
        self.assertEqual(match.subject_team_slug, "manchester-united")
        self.assertEqual(match.data_status, "ready")
        self.assertIn("pass_network", match.chart_blocks)
        self.assertEqual(match.metrics[0].label, "Progressive passes")
        self.assertEqual(match.takeaways[0].title, "Metrics pending")
        metrics_mock.assert_called_once_with(77, 1)

    def test_get_match_detail_filters_takeaways_to_subject_team(self) -> None:
        match_row = {
            "match_id": 77,
            "external_id": "9001",
            "home_team_id": 1,
            "away_team_id": 2,
            "home_team_name": "Manchester United",
            "away_team_name": "Portugal",
            "home_score": 3,
            "away_score": 2,
            "has_events": True,
        }

        with patch("services.editorial._load_match_row", return_value=match_row), patch(
            "services.editorial._load_match_metrics", return_value=[]
        ), patch(
            "services.editorial._load_match_takeaways", return_value=[]
        ) as reports_mock:
            get_match_detail("77")

        reports_mock.assert_called_once_with(77, subject_team_id=1)

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

    def test_qualification_minutes_switches_at_three_matches(self) -> None:
        self.assertEqual(_qualification_minutes_for_window(0), 60)
        self.assertEqual(_qualification_minutes_for_window(2), 60)
        self.assertEqual(_qualification_minutes_for_window(3), 270)

    def test_get_team_style_uses_window_metrics(self) -> None:
        team_row = {
            "team_id": 1,
            "external_id": "1",
            "name": "Manchester United",
            "short_name": "MU",
            "country_name": "England",
            "team_type": None,
            "match_count": 3,
        }
        window_rows = [
            {
                "window_type": "all_matches",
                "window_key": "team:1:all_matches",
                "match_count": 3,
                "window_start_date": "2024-01-01",
                "window_end_date": "2024-01-30",
                "metric_key": "field_tilt",
                "metric_value": 0.62,
                "competition_name": None,
                "season_name": None,
            },
            {
                "window_type": "all_matches",
                "window_key": "team:1:all_matches",
                "match_count": 3,
                "window_start_date": "2024-01-01",
                "window_end_date": "2024-01-30",
                "metric_key": "progressive_passes",
                "metric_value": 15,
                "competition_name": None,
                "season_name": None,
            },
        ]

        with patch("services.editorial._load_team_row_by_slug", return_value=team_row), patch(
            "services.editorial._query_rows_safe", return_value=window_rows
        ):
            response = get_team_style("manchester-united")

        self.assertIsNotNone(response)
        self.assertEqual(response.data_status, "ready")
        self.assertEqual(len(response.windows), 1)
        self.assertEqual(response.windows[0].label, "All ingested matches")
        self.assertEqual(response.windows[0].metrics[0].label, "Field tilt")

    def test_get_team_players_uses_player_window_metrics(self) -> None:
        team_row = {
            "team_id": 1,
            "external_id": "1",
            "name": "Manchester United",
            "short_name": "MU",
            "country_name": "England",
            "team_type": None,
            "match_count": 3,
        }
        window_row = {
            "window_type": "all_matches",
            "match_count": 3,
            "window_start_date": "2024-01-01",
            "window_end_date": "2024-01-30",
            "competition_id": None,
            "season_id": None,
            "competition_name": None,
            "season_name": None,
        }
        player_rows = [
            {
                "player_id": 10,
                "team_id": 1,
                "name": "Bruno Fernandes",
                "display_name": "Bruno",
                "primary_position": "Attacking Midfield",
                "position_group": "midfielder",
                "match_count": 3,
                "minutes_played_total": 280,
                "metric_key": "progressive_passes_per90",
                "metric_value": 6.5,
            },
            {
                "player_id": 10,
                "team_id": 1,
                "name": "Bruno Fernandes",
                "display_name": "Bruno",
                "primary_position": "Attacking Midfield",
                "position_group": "midfielder",
                "match_count": 3,
                "minutes_played_total": 280,
                "metric_key": "pressures_per90",
                "metric_value": 18.0,
            },
            {
                "player_id": 11,
                "team_id": 1,
                "name": "Short Sample",
                "display_name": None,
                "primary_position": "Forward",
                "position_group": "forward",
                "match_count": 1,
                "minutes_played_total": 40,
                "metric_key": "progressive_passes_per90",
                "metric_value": 2.0,
            },
        ]

        with patch("services.editorial._load_team_row_by_slug", return_value=team_row), patch(
            "services.editorial._load_team_players_window_meta", return_value=window_row
        ), patch(
            "services.editorial._load_team_players_for_window"
        ) as players_mock:
            players_mock.return_value = []
            response = get_team_players("manchester-united")

        self.assertIsNotNone(response)
        self.assertEqual(response.window.qualification_minutes, 270)
        players_mock.assert_called_once_with(
            1,
            window_type="all_matches",
            competition_id=None,
            season_id=None,
            qualification_minutes=270,
            qualified_only=True,
        )

        with patch("services.editorial._load_team_row_by_slug", return_value=team_row), patch(
            "services.editorial._load_team_players_window_meta", return_value=window_row
        ), patch(
            "services.editorial._query_rows_safe", return_value=player_rows
        ):
            response = get_team_players("manchester-united")

        self.assertEqual(len(response.players), 1)
        self.assertEqual(response.players[0].name, "Bruno Fernandes")
        self.assertTrue(response.players[0].qualified)
        self.assertEqual(response.players[0].metrics[0].label, "Progressive passes / 90")

    def test_get_team_players_relaxes_threshold_for_small_windows(self) -> None:
        team_row = {
            "team_id": 1,
            "external_id": "1",
            "name": "Manchester United",
            "short_name": "MU",
            "country_name": "England",
            "team_type": None,
            "match_count": 2,
        }
        window_row = {
            "window_type": "competition",
            "match_count": 2,
            "window_start_date": "2024-01-01",
            "window_end_date": "2024-01-10",
            "competition_id": 39,
            "season_id": None,
            "competition_name": "Premier League",
            "season_name": None,
        }
        player_rows = [
            {
                "player_id": 10,
                "team_id": 1,
                "name": "Bruno Fernandes",
                "display_name": "Bruno",
                "primary_position": "Attacking Midfield",
                "position_group": "midfielder",
                "match_count": 2,
                "minutes_played_total": 75,
                "metric_key": "progressive_passes_per90",
                "metric_value": 6.5,
            }
        ]

        with patch("services.editorial._load_team_row_by_slug", return_value=team_row), patch(
            "services.editorial._load_team_players_window_meta", return_value=window_row
        ), patch(
            "services.editorial._query_rows_safe", return_value=player_rows
        ):
            response = get_team_players("manchester-united", competition_id=39)

        self.assertEqual(response.window.qualification_minutes, 60)
        self.assertEqual(len(response.players), 1)
        self.assertTrue(response.players[0].qualified)


if __name__ == "__main__":
    unittest.main()
