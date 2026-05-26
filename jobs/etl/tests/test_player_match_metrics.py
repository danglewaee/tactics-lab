from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from metrics.player_match import compute_player_match_metrics


class PlayerMatchMetricTests(unittest.TestCase):
    def test_compute_player_match_metrics(self) -> None:
        events = [
            {
                "index_in_match": 1,
                "minute": 10,
                "team_id": 1,
                "player_id": 101,
                "pass_recipient_player_id": 102,
                "play_pattern": "Regular Play",
                "event_type": "Pass",
                "outcome": None,
                "x_start": Decimal("10.0"),
                "x_end": Decimal("25.0"),
            },
            {
                "index_in_match": 2,
                "minute": 11,
                "team_id": 1,
                "player_id": 101,
                "play_pattern": "Regular Play",
                "event_type": "Carry",
                "x_start": Decimal("32.0"),
                "x_end": Decimal("44.0"),
            },
            {
                "index_in_match": 3,
                "minute": 12,
                "team_id": 2,
                "player_id": 201,
                "play_pattern": "Regular Play",
                "event_type": "Pass",
                "outcome": None,
                "x_start": Decimal("40.0"),
                "x_end": Decimal("60.0"),
                "pass_recipient_player_id": 202,
            },
            {
                "index_in_match": 4,
                "minute": 13,
                "team_id": 1,
                "player_id": 101,
                "play_pattern": "Regular Play",
                "event_type": "Ball Recovery",
                "x_start": Decimal("84.0"),
            },
            {
                "index_in_match": 5,
                "minute": 14,
                "team_id": 2,
                "player_id": 202,
                "pass_recipient_player_id": 102,
                "play_pattern": "Regular Play",
                "event_type": "Pass",
                "outcome": None,
                "x_start": Decimal("20.0"),
                "x_end": Decimal("35.0"),
            },
            {
                "index_in_match": 6,
                "minute": 15,
                "team_id": 1,
                "player_id": 102,
                "play_pattern": "Regular Play",
                "event_type": "Pressure",
                "x_start": Decimal("50.0"),
            },
        ]

        lineup_row = {
            "player_id": 102,
            "team_id": 1,
            "start_minute": 0,
            "end_minute": 120,
        }

        metrics = compute_player_match_metrics(events, lineup_row, match_end_minute=90)

        self.assertEqual(metrics["minutes_played"], 90.0)
        self.assertEqual(metrics["progressive_passes"], 0.0)
        self.assertEqual(metrics["progressive_carries"], 0.0)
        self.assertEqual(metrics["passes_received"], 2.0)
        self.assertEqual(metrics["pressures"], 1.0)
        self.assertEqual(metrics["high_regains"], 0.0)

    def test_compute_player_match_metrics_for_ball_winner(self) -> None:
        events = [
            {
                "index_in_match": 1,
                "minute": 20,
                "team_id": 2,
                "player_id": 201,
                "play_pattern": "Regular Play",
                "event_type": "Pass",
                "outcome": None,
                "x_start": Decimal("30.0"),
                "x_end": Decimal("50.0"),
            },
            {
                "index_in_match": 2,
                "minute": 21,
                "team_id": 1,
                "player_id": 101,
                "play_pattern": "Regular Play",
                "event_type": "Interception",
                "x_start": Decimal("86.0"),
            },
        ]

        lineup_row = {
            "player_id": 101,
            "team_id": 1,
            "start_minute": 0,
            "end_minute": 90,
        }

        metrics = compute_player_match_metrics(events, lineup_row, match_end_minute=90)
        self.assertEqual(metrics["high_regains"], 1.0)


if __name__ == "__main__":
    unittest.main()
