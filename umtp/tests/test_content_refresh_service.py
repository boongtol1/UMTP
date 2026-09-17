import os
import sys
import unittest
from unittest.mock import MagicMock, call, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import content_refresh_service as service  # noqa: E402


class Cursor:
    def close(self):
        return None


class Connection:
    def __init__(self):
        self.cursor_value = Cursor()
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self, dictionary=False):
        return self.cursor_value

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def is_connected(self):
        return not self.closed

    def close(self):
        self.closed = True


class ContentRefreshServiceTest(unittest.TestCase):
    def _candidate(self):
        return {
            "product_id": 1001,
            "search_word": "m2 맥북에어",
            "title": "맥북에어 M2 8GB 256GB",
            "price": 700000,
            "product_url": "https://web.joongna.com/product/1001",
            "sort_date": "2026-09-17 10:00:00",
        }

    def test_defers_while_analysis_queue_has_work(self):
        connection = Connection()
        with patch.object(service, "get_connection", return_value=connection):
            with patch.object(service, "has_pending_analysis_jobs", return_value=True):
                with patch.object(service, "find_due_content_candidate") as find_candidate:
                    result = service.process_next_content_refresh()

        self.assertEqual(result["reason"], "analysis_backlog")
        find_candidate.assert_not_called()

    def test_body_change_is_persisted_and_enqueued_once(self):
        first_connection = Connection()
        second_connection = Connection()
        previous = {
            "last_body_hash": service.build_listing_content_snapshot(
                body_text="이전 본문"
            )["body_hash"],
            "last_self_check_hash": None,
        }
        targets = [{"setting_id": 1, "rule_id": 1, "user_id": "u1"}]
        page = {
            "title": "맥북에어 M2 8GB 256GB",
            "description": "변경된 본문",
            "listing_price_krw": 700000,
            "self_check_fields": {},
        }

        with patch.object(
            service,
            "get_connection",
            side_effect=[first_connection, second_connection],
        ):
            with patch.object(service, "has_pending_analysis_jobs", return_value=False):
                with patch.object(service, "find_due_content_candidate", return_value=self._candidate()):
                    with patch.object(service, "fetch_html", return_value="<html>"):
                        with patch.object(service, "parse_joongna_listing_page", return_value=page):
                            with patch.object(service, "get_seen_product", return_value=previous):
                                with patch.object(service, "load_latest_search_result", return_value={}):
                                    with patch.object(service, "persist_latest_search_result_enrichment") as persist:
                                        with patch.object(service, "update_seen_product_content_snapshot") as update:
                                            with patch.object(
                                                service,
                                                "load_active_targets_for_product",
                                                return_value=targets,
                                            ):
                                                with patch.object(
                                                    service,
                                                    "create_analysis_jobs_for_rules",
                                                    return_value={"created_jobs": [{"job_id": 9}]},
                                                ) as enqueue:
                                                    result = service.process_next_content_refresh()

        self.assertEqual(result["change_reason"], "body_changed")
        self.assertEqual(result["analysis_jobs_created"], 1)
        persist.assert_called_once()
        update.assert_called_once()
        enqueue.assert_called_once()
        product = enqueue.call_args.args[0]
        self.assertEqual(product["body_text"], "변경된 본문")
        self.assertEqual(enqueue.call_args.args[2], "body_changed")
        self.assertEqual(second_connection.commits, 1)

    def test_first_body_snapshot_does_not_send_change_alert(self):
        first_connection = Connection()
        second_connection = Connection()
        with patch.object(
            service,
            "get_connection",
            side_effect=[first_connection, second_connection],
        ):
            with patch.object(service, "has_pending_analysis_jobs", return_value=False):
                with patch.object(service, "find_due_content_candidate", return_value=self._candidate()):
                    with patch.object(service, "fetch_html", return_value="<html>"):
                        with patch.object(
                            service,
                            "parse_joongna_listing_page",
                            return_value={
                                "title": "맥북에어",
                                "description": "최초 본문",
                                "listing_price_krw": 700000,
                                "self_check_fields": {},
                            },
                        ):
                            with patch.object(service, "get_seen_product", return_value={}):
                                with patch.object(service, "load_latest_search_result", return_value={}):
                                    with patch.object(service, "persist_latest_search_result_enrichment"):
                                        with patch.object(service, "update_seen_product_content_snapshot"):
                                            with patch.object(service, "create_analysis_jobs_for_rules") as enqueue:
                                                result = service.process_next_content_refresh()

        self.assertIsNone(result["change_reason"])
        enqueue.assert_not_called()


if __name__ == "__main__":
    unittest.main()
