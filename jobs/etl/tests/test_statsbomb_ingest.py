from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingest.statsbomb import normalize_event_payload, scan_statsbomb_source, timestamp_to_ms


class StatsBombIngestTests(unittest.TestCase):
    def test_timestamp_to_ms(self) -> None:
        self.assertEqual(timestamp_to_ms("00:01:02.345"), 62345)
        self.assertEqual(timestamp_to_ms("01:00:00.000"), 3600000)
        self.assertIsNone(timestamp_to_ms(None))

    def test_normalize_pass_event(self) -> None:
        raw_event = {
            "id": "event-1",
            "index": 7,
            "period": 1,
            "timestamp": "00:02:03.456",
            "minute": 2,
            "second": 3,
            "type": {"id": 30, "name": "Pass"},
            "location": [42.0, 36.0],
            "under_pressure": True,
            "pass": {
                "recipient": {"id": 10, "name": "Receiver"},
                "length": 18.2,
                "angle": 0.4,
                "height": {"id": 1, "name": "Ground Pass"},
                "end_location": [61.0, 41.0],
                "body_part": {"id": 40, "name": "Right Foot"},
                "outcome": {"id": 1, "name": "Complete"},
            },
        }

        normalized = normalize_event_payload(raw_event)

        self.assertEqual(normalized["event_type"], "Pass")
        self.assertEqual(normalized["timestamp_ms"], 123456)
        self.assertEqual(normalized["x_start"], 42.0)
        self.assertEqual(normalized["x_end"], 61.0)
        self.assertEqual(normalized["pass_height"], "Ground Pass")
        self.assertEqual(normalized["body_part"], "Right Foot")
        self.assertTrue(normalized["under_pressure"])

    def test_scan_statsbomb_source_supports_checkout_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "statsbomb" / "data"
            (root / "matches" / "1").mkdir(parents=True)
            (root / "lineups").mkdir()
            (root / "events").mkdir()

            write_json(
                root / "competitions.json",
                [
                    {
                        "competition_id": 1,
                        "season_id": 99,
                        "competition_name": "Test Cup",
                        "season_name": "2026",
                    }
                ],
            )
            write_json(root / "matches" / "1" / "99.json", [{"match_id": 1234}])
            write_json(
                root / "lineups" / "1234.json",
                [{"team_id": 1, "team_name": "Team A", "lineup": [{"player_id": 9, "player_name": "Nine"}]}],
            )
            write_json(root / "events" / "1234.json", [{"id": "event-1", "type": {"name": "Pass"}}])

            summary = scan_statsbomb_source(Path(tmp) / "statsbomb")

            self.assertEqual(summary.competitions, 1)
            self.assertEqual(summary.seasons, 1)
            self.assertEqual(summary.matches, 1)
            self.assertEqual(summary.lineups, 1)
            self.assertEqual(summary.events, 1)


def write_json(path: Path, payload: object) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle)


if __name__ == "__main__":
    unittest.main()
