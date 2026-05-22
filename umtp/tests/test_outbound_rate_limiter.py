import os
import sys
import threading
import time
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.outbound_rate_limiter import (  # noqa: E402
    SimpleRateLimiter,
    joongna_detail_limiter,
    joongna_search_limiter,
)


class OutboundRateLimiterTest(unittest.TestCase):
    def test_wait_sleeps_when_called_too_fast(self):
        limiter = SimpleRateLimiter(min_interval_seconds=1.0)

        with patch("src.outbound_rate_limiter.time.monotonic", side_effect=[100.0, 100.2]):
            with patch("src.outbound_rate_limiter.time.sleep") as mock_sleep:
                first_sleep = limiter.wait()
                second_sleep = limiter.wait()

        self.assertEqual(first_sleep, 0.0)
        self.assertAlmostEqual(second_sleep, 0.8, places=2)
        mock_sleep.assert_called_once()
        self.assertAlmostEqual(mock_sleep.call_args[0][0], 0.8, places=2)

    def test_global_limiters_use_required_intervals(self):
        self.assertAlmostEqual(joongna_search_limiter._min_interval_seconds, 1.0, places=3)
        self.assertAlmostEqual(joongna_detail_limiter._min_interval_seconds, 0.5, places=3)

    def test_multithread_global_spacing_is_preserved(self):
        limiter = SimpleRateLimiter(min_interval_seconds=0.1)
        start_gate = threading.Event()
        append_lock = threading.Lock()
        finished_times = []

        def worker():
            start_gate.wait()
            limiter.wait()
            done_at = time.monotonic()
            with append_lock:
                finished_times.append(done_at)

        threads = [threading.Thread(target=worker, daemon=True) for _ in range(4)]
        for thread in threads:
            thread.start()

        started_at = time.monotonic()
        start_gate.set()

        for thread in threads:
            thread.join(timeout=2.0)

        self.assertEqual(len(finished_times), 4)
        ordered = sorted(finished_times)
        for index in range(1, len(ordered)):
            self.assertGreaterEqual(ordered[index] - ordered[index - 1], 0.08)
        self.assertGreaterEqual(ordered[-1] - started_at, 0.28)


if __name__ == "__main__":
    unittest.main()

