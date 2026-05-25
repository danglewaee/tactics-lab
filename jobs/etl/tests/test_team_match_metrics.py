from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from metrics.team_match import compute_team_match_metrics


class TeamMatchMetricTests(unittest.TestCase):
    def test_compute_team_match_metrics(self) -> None:
        events = [
            {
                "index_in_match": 1,
                "team_id": 1,
                "possession_id": 1,
                "play_pattern": "Regular Play",
                "event_type": "Pass",
                "x_start": Decimal("10.0"),
                "x_end": Decimal("25.0"),
                "y_start": Decimal("20.0"),
                "outcome": None,
            },
            {
                "index_in_match": 2,
                "team_id": 1,
                "possession_id": 1,
                "play_pattern": "Regular Play",
                "event_type": "Pass",
                "x_start": Decimal("30.0"),
                "x_end": Decimal("38.0"),
                "y_start": Decimal("40.0"),
                "outcome": None,
            },
            {
                "index_in_match": 3,
                "team_id": 1,
                "possession_id": 2,
                "play_pattern": "Regular Play",
                "event_type": "Carry",
                "x_start": Decimal("85.0"),
                "x_end": Decimal("92.0"),
                "y_start": Decimal("32.0"),
            },
            {
                "index_in_match": 4,
                "team_id": 2,
                "possession_id": 3,
                "play_pattern": "Regular Play",
                "event_type": "Pass",
                "x_start": Decimal("50.0"),
                "x_end": Decimal("70.0"),
                "y_start": Decimal("55.0"),
                "outcome": None,
            },
            {
                "index_in_match": 5,
                "team_id": 1,
                "possession_id": 4,
                "play_pattern": "Regular Play",
                "event_type": "Ball Recovery",
                "x_start": Decimal("83.0"),
                "y_start": Decimal("25.0"),
            },
        ]

        metrics = compute_team_match_metrics(events, 1)

        self.assertEqual(metrics["progressive_passes"], 1.0)
        self.assertEqual(metrics["high_regains"], 1.0)
        self.assertAlmostEqual(metrics["left_lane_build_up_share"], 0.5)
        self.assertAlmostEqual(metrics["center_lane_build_up_share"], 0.5)
        self.assertAlmostEqual(metrics["right_lane_build_up_share"], 0.0)
        self.assertAlmostEqual(metrics["field_tilt"], 1.0, places=4)


if __name__ == "__main__":
    unittest.main()
