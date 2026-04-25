from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routers.health import healthcheck


class HealthTests(unittest.TestCase):
    def test_healthcheck(self) -> None:
        payload = healthcheck()
        self.assertEqual(payload["status"], "ok")
        self.assertIn("timestamp", payload)


if __name__ == "__main__":
    unittest.main()
