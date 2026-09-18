import argparse
import contextlib
import io
import os
import sys
import unittest
from unittest.mock import patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import run_content_refresh_worker_umtp as runner


class ContentRefreshRunnerTest(unittest.TestCase):
    def test_missing_body_is_processed_even_when_analysis_backlog_defers_refresh(self):
        with patch.object(runner, "parse_args", return_value=argparse.Namespace(once=True, interval=5)):
            with patch.object(runner, "process_next_content_refresh", return_value={
                "processed": 0, "deferred": 1, "reason": "analysis_backlog",
            }):
                with patch.object(runner, "process_next_search_body_backfill", return_value={"processed": 1}) as fill:
                    with patch.object(runner.time, "sleep") as sleep:
                        with contextlib.redirect_stdout(io.StringIO()):
                            runner.main()
        fill.assert_called_once_with()
        sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
