from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from metrics.team_window import aggregate_team_window_metrics


class TeamWindowMetricTests(unittest.TestCase):
    def test_aggregate_team_window_metrics(self) -> None:
        rows = [
            {
                "team_id": 1,
                "match_id": 1001,
                "competition_id": 11,
                "season_id": 101,
                "match_date": "2024-06-01",
                "metric_key": "field_tilt",
                "metric_value": Decimal("0.6000"),
            },
            {
                "team_id": 1,
                "match_id": 1002,
                "competition_id": 11,
                "season_id": 101,
                "match_date": "2024-06-10",
                "metric_key": "field_tilt",
                "metric_value": Decimal("0.4000"),
            },
            {
                "team_id": 1,
                "match_id": 1003,
                "competition_id": 12,
                "season_id": 102,
                "match_date": "2024-07-01",
                "metric_key": "field_tilt",
                "metric_value": Decimal("0.8000"),
            },
            {
                "team_id": 1,
                "match_id": 1001,
                "competition_id": 11,
                "season_id": 101,
                "match_date": "2024-06-01",
                "metric_key": "progressive_passes",
                "metric_value": Decimal("20.0000"),
            },
            {
                "team_id": 1,
                "match_id": 1002,
                "competition_id": 11,
                "season_id": 101,
                "match_date": "2024-06-10",
                "metric_key": "progressive_passes",
                "metric_value": Decimal("10.0000"),
            },
            {
                "team_id": 1,
                "match_id": 1003,
                "competition_id": 12,
                "season_id": 102,
                "match_date": "2024-07-01",
                "metric_key": "progressive_passes",
                "metric_value": Decimal("30.0000"),
            },
        ]

        metrics = aggregate_team_window_metrics(rows)
        by_key = {(metric.window_type, metric.window_key, metric.metric_key): metric for metric in metrics}

        all_field_tilt = by_key[("all_matches", "team:1:all_matches", "field_tilt")]
        self.assertAlmostEqual(all_field_tilt.metric_value, 0.6)
        self.assertEqual(all_field_tilt.match_count, 3)

        competition_field_tilt = by_key[("competition", "team:1:competition:11", "field_tilt")]
        self.assertAlmostEqual(competition_field_tilt.metric_value, 0.5)
        self.assertEqual(competition_field_tilt.match_count, 2)

        season_progressive = by_key[("season", "team:1:season:101", "progressive_passes")]
        self.assertAlmostEqual(season_progressive.metric_value, 15.0)
        self.assertEqual(season_progressive.match_count, 2)

        competition_season_progressive = by_key[
            ("competition_season", "team:1:competition:12:season:102", "progressive_passes")
        ]
        self.assertAlmostEqual(competition_season_progressive.metric_value, 30.0)
        self.assertEqual(competition_season_progressive.match_count, 1)


if __name__ == "__main__":
    unittest.main()
