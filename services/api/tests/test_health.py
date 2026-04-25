from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app
from routers.health import healthcheck


class HealthTests(unittest.TestCase):
    def test_healthcheck(self) -> None:
        payload = healthcheck()
        self.assertEqual(payload["status"], "ok")
        self.assertIn("timestamp", payload)

    def test_preview_route_is_registered(self) -> None:
        paths = {route.path for route in app.routes}
        self.assertIn("/preview", paths)
        self.assertIn("/static", paths)


if __name__ == "__main__":
    unittest.main()
