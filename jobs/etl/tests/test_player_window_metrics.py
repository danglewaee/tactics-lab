from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from metrics.player_window import aggregate_player_window_metrics


class PlayerWindowMetricTests(unittest.TestCase):
    def test_aggregate_player_window_metrics(self) -> None:
        rows = [
            {
                "player_id": 10,
                "team_id": 1,
                "match_id": 1001,
                "competition_id": 11,
                "season_id": 101,
                "match_date": "2024-06-01",
                "metric_key": "minutes_played",
                "metric_value": Decimal("90.0000"),
            },
            {
                "player_id": 10,
                "team_id": 1,
                "match_id": 1001,
                "competition_id": 11,
                "season_id": 101,
                "match_date": "2024-06-01",
                "metric_key": "progressive_passes",
                "metric_value": Decimal("5.0000"),
            },
            {
                "player_id": 10,
                "team_id": 1,
                "match_id": 1002,
                "competition_id": 11,
                "season_id": 101,
                "match_date": "2024-06-10",
                "metric_key": "minutes_played",
                "metric_value": Decimal("45.0000"),
            },
            {
                "player_id": 10,
                "team_id": 1,
                "match_id": 1002,
                "competition_id": 11,
                "season_id": 101,
                "match_date": "2024-06-10",
                "metric_key": "progressive_passes",
                "metric_value": Decimal("1.0000"),
            },
            {
                "player_id": 10,
                "team_id": 1,
                "match_id": 1002,
                "competition_id": 11,
                "season_id": 101,
                "match_date": "2024-06-10",
                "metric_key": "pressures",
                "metric_value": Decimal("4.0000"),
            },
        ]

        metrics = aggregate_player_window_metrics(rows)
        by_key = {(metric.window_type, metric.window_key, metric.metric_key): metric for metric in metrics}

        all_minutes = by_key[("all_matches", "player:10:team:1:all_matches", "minutes_played")]
        self.assertEqual(all_minutes.metric_value, 135.0)
        self.assertEqual(all_minutes.minutes_played_total, 135)
        self.assertEqual(all_minutes.match_count, 2)

        all_progressive = by_key[("all_matches", "player:10:team:1:all_matches", "progressive_passes_per90")]
        self.assertAlmostEqual(all_progressive.metric_value, 4.0)

        competition_pressures = by_key[
            ("competition", "player:10:team:1:competition:11", "pressures_per90")
        ]
        self.assertAlmostEqual(competition_pressures.metric_value, round((4 / 135) * 90, 4))


if __name__ == "__main__":
    unittest.main()
