import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import requests


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.fraud_store_monitor_service import (  # noqa: E402
    _probe_store_status,
    _refresh_training_labels_for_candidates,
    run_fraud_store_monitor_once,
)


class _FakeCursor:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class _FakeConnection:
    def __init__(self):
        self.closed = False
        self.committed = False
        self.rolled_back = False
        self.cursor_obj = _FakeCursor()

    def cursor(self, dictionary=False):
        _ = dictionary
        return self.cursor_obj

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def is_connected(self):
        return not self.closed

    def close(self):
        self.closed = True


class _LabelCalcCursor:
    def __init__(self, snapshots_by_store):
        self.snapshots_by_store = snapshots_by_store
        self._last_rows = []
        self.updated_rows = []

    def execute(self, query, params):
        normalized = " ".join(query.lower().split())
        if "from fraud_store_status_snapshots" in normalized:
            store_id = params[0]
            self._last_rows = self.snapshots_by_store.get(store_id, [])
            return
        raise AssertionError(f"unexpected query: {query}")

    def fetchall(self):
        return self._last_rows

    def executemany(self, query, rows):
        normalized = " ".join(query.lower().split())
        if "update fraud_training_label_candidates" not in normalized:
            raise AssertionError(f"unexpected executemany query: {query}")
        self.updated_rows.extend(rows)


class _FakeHttpResponse:
    def __init__(
        self,
        status_code=200,
        text="",
        content=None,
        encoding=None,
        apparent_encoding=None,
        json_payload=None,
    ):
        self.status_code = status_code
        self.text = text
        self.content = content if content is not None else text.encode("utf-8")
        self.encoding = encoding
        self.apparent_encoding = apparent_encoding
        self._json_payload = json_payload

    def json(self):
        if self._json_payload is None:
            raise ValueError("no json payload")
        return self._json_payload


class FraudStoreMonitorServiceTest(unittest.TestCase):
    def test_run_once_skips_recently_checked_store_and_checks_due_store(self):
        now = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
        listing_candidates = [
            {
                "store_id": "100",
                "product_id": "P-100",
                "listing_sort_date": now - timedelta(hours=2),
                "discovered_at": now - timedelta(hours=2),
            },
            {
                "store_id": "200",
                "product_id": "P-200",
                "listing_sort_date": now - timedelta(hours=1),
                "discovered_at": now - timedelta(hours=1),
            },
        ]
        probe_result = {
            "checked_at": now,
            "status": "active",
            "is_active": 1,
            "raw_status_text": "ok",
            "raw_response_json": {"meta": {"code": 200}},
            "error_message": None,
            "source": "my_store_api",
            "http_status": 200,
            "meta_code": 0,
            "meta_message": "SUCCESS",
            "raw_snippet": "ok",
            "profile": {
                "store_id": "200",
                "store_name": "테스트상점",
                "profile_image_url": "https://img2.joongna.com/common/Profile/Default/profile_m.png",
                "store_level_number": 1,
                "review_count": 0,
                "reliability_score": 0,
                "activity_score": 0,
                "trust_score": 0,
                "safe_trade_count": 0,
                "raw_json": {"storeName": "테스트상점"},
            },
        }

        with patch("src.fraud_store_monitor_service.get_connection", return_value=_FakeConnection()):
            with patch(
                "src.fraud_store_monitor_service._fetch_recent_listing_candidates",
                return_value=listing_candidates,
            ):
                with patch(
                    "src.fraud_store_monitor_service._fetch_last_checked_map",
                    return_value={"100": now - timedelta(minutes=5)},
                ):
                    with patch("src.fraud_store_monitor_service._probe_store_status", return_value=probe_result):
                        with patch("src.fraud_store_monitor_service._insert_status_snapshot") as mock_insert_status:
                            with patch(
                                "src.fraud_store_monitor_service._upsert_joongna_store_profile_snapshot"
                            ) as mock_upsert_profile:
                                with patch(
                                    "src.fraud_store_monitor_service._compute_activity_snapshot_from_db",
                                    return_value={
                                        "posts_last_1h": 1,
                                        "posts_last_6h": 2,
                                        "posts_last_24h": 3,
                                        "posts_last_7d": 4,
                                        "visible_product_count": 5,
                                    },
                                ):
                                    with patch(
                                        "src.fraud_store_monitor_service._insert_activity_snapshot"
                                    ) as mock_insert_activity:
                                        with patch(
                                            "src.fraud_store_monitor_service._upsert_training_label_candidates",
                                            return_value=2,
                                        ):
                                            with patch(
                                                "src.fraud_store_monitor_service._refresh_training_labels_for_candidates",
                                                return_value=2,
                                            ):
                                                stats = run_fraud_store_monitor_once(
                                                    force_enabled=True,
                                                    min_check_interval_minutes=30,
                                                    lookback_days=14,
                                                )

        self.assertEqual(stats.get("candidate_listing_count"), 2)
        self.assertEqual(stats.get("target_store_count"), 2)
        self.assertEqual(stats.get("checked_count"), 1)
        self.assertEqual(stats.get("skipped_count"), 1)
        self.assertEqual(stats.get("active_count"), 1)
        self.assertEqual(stats.get("inactive_count"), 0)
        self.assertEqual(stats.get("error_count"), 0)
        self.assertEqual(stats.get("label_candidates_upserted"), 2)
        self.assertEqual(stats.get("label_rows_updated"), 2)
        self.assertEqual(mock_insert_status.call_count, 1)
        self.assertEqual(mock_upsert_profile.call_count, 1)
        self.assertEqual(mock_insert_activity.call_count, 1)

    def test_refresh_training_labels_assigns_positive_negative_and_pending(self):
        now = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
        listing_a = now - timedelta(days=2)
        listing_b = now - timedelta(days=20)
        listing_c = now - timedelta(days=3)

        cursor = _LabelCalcCursor(
            snapshots_by_store={
                "A": [
                    {"checked_at": listing_a + timedelta(hours=12), "status": "active"},
                    {"checked_at": listing_a + timedelta(days=1), "status": "inactive"},
                ],
                "B": [
                    {"checked_at": listing_b + timedelta(days=15), "status": "active"},
                ],
                "C": [
                    {"checked_at": listing_c + timedelta(days=5), "status": "active"},
                ],
            }
        )
        listing_candidates = [
            {
                "store_id": "A",
                "product_id": "PA",
                "listing_sort_date": listing_a,
                "discovered_at": listing_a,
            },
            {
                "store_id": "B",
                "product_id": "PB",
                "listing_sort_date": listing_b,
                "discovered_at": listing_b,
            },
            {
                "store_id": "C",
                "product_id": "PC",
                "listing_sort_date": listing_c,
                "discovered_at": listing_c,
            },
        ]

        updated_count = _refresh_training_labels_for_candidates(
            cursor,
            listing_candidates=listing_candidates,
        )
        self.assertEqual(updated_count, 3)

        updates = {row[4]: row for row in cursor.updated_rows}
        pa = updates["PA"]
        pb = updates["PB"]
        pc = updates["PC"]

        self.assertIsNotNone(pa[0])
        self.assertEqual(pa[2], 1)
        self.assertEqual(pa[3], "store_inactive_within_7d")

        self.assertIsNone(pb[0])
        self.assertEqual(pb[2], 0)
        self.assertEqual(pb[3], "store_active_after_14d")

        self.assertIsNone(pc[0])
        self.assertIsNone(pc[2])
        self.assertEqual(pc[3], "pending_observation")

    def test_probe_store_status_suspended_by_full_phrase(self):
        my_store = _FakeHttpResponse(
            status_code=200,
            json_payload={"meta": {"code": 400999, "message": "이용제한된 회원의 가게입니다"}, "data": ""},
        )
        with patch("src.fraud_store_monitor_service.requests.get", return_value=my_store):
            result = _probe_store_status("2920235")

        self.assertEqual(result.get("status"), "suspended")
        self.assertEqual(result.get("is_active"), 0)
        self.assertEqual(result.get("source"), "my_store_api")

    def test_probe_store_status_suspended_from_utf8_bytes_when_text_is_garbled(self):
        phrase = "이용제한된 회원의 가게입니다"
        utf8_bytes = phrase.encode("utf-8")
        garbled_text = utf8_bytes.decode("iso-8859-1", errors="ignore")
        my_store = _FakeHttpResponse(
            status_code=200,
            json_payload={"meta": {"code": 123, "message": "UNKNOWN"}, "data": ""},
        )
        rsc = _FakeHttpResponse(
            status_code=200,
            text=garbled_text,
            content=utf8_bytes,
            encoding="ISO-8859-1",
            apparent_encoding="utf-8",
        )
        with patch("src.fraud_store_monitor_service.requests.get", side_effect=[my_store, rsc]):
            result = _probe_store_status("2920235")

        self.assertEqual(result.get("status"), "suspended")
        self.assertEqual(result.get("is_active"), 0)
        self.assertEqual(result.get("source"), "store_rsc")

    def test_probe_store_status_suspended_by_short_phrase(self):
        my_store = _FakeHttpResponse(
            status_code=200,
            json_payload={"meta": {"code": 111, "message": "UNKNOWN"}, "data": ""},
        )
        rsc = _FakeHttpResponse(
            status_code=200,
            text="이 상점은 이용제한 상태입니다",
        )
        with patch("src.fraud_store_monitor_service.requests.get", side_effect=[my_store, rsc]):
            result = _probe_store_status("2920235")

        self.assertEqual(result.get("status"), "suspended")
        self.assertEqual(result.get("is_active"), 0)

    def test_probe_store_status_deleted_by_phrase(self):
        my_store = _FakeHttpResponse(
            status_code=200,
            json_payload={"meta": {"code": 111, "message": "UNKNOWN"}, "data": ""},
        )
        rsc = _FakeHttpResponse(
            status_code=200,
            text="탈퇴한 회원 입니다",
        )
        with patch("src.fraud_store_monitor_service.requests.get", side_effect=[my_store, rsc]):
            result = _probe_store_status("2920235")

        self.assertEqual(result.get("status"), "deleted")
        self.assertEqual(result.get("is_active"), 0)

    def test_probe_store_status_deleted_by_http_404(self):
        my_store = _FakeHttpResponse(
            status_code=200,
            json_payload={"meta": {"code": 111, "message": "UNKNOWN"}, "data": ""},
        )
        rsc = _FakeHttpResponse(status_code=404, text="")
        with patch("src.fraud_store_monitor_service.requests.get", side_effect=[my_store, rsc]):
            result = _probe_store_status("2920235")

        self.assertEqual(result.get("status"), "deleted")
        self.assertEqual(result.get("is_active"), 0)

    def test_probe_store_status_active_when_store_info_exists(self):
        response = _FakeHttpResponse(
            status_code=200,
            json_payload={
                "meta": {"code": 0, "message": "SUCCESS"},
                "data": {"storeSeq": 2920235, "storeName": "테스트상점", "nickName": "테스트상점"},
            },
        )
        with patch("src.fraud_store_monitor_service.requests.get", return_value=response):
            result = _probe_store_status("2920235")

        self.assertEqual(result.get("status"), "active")
        self.assertEqual(result.get("is_active"), 1)
        self.assertEqual(result.get("source"), "my_store_api")
        self.assertEqual((result.get("profile") or {}).get("store_name"), "테스트상점")

    def test_probe_store_status_error_on_request_exception(self):
        with patch("src.fraud_store_monitor_service.requests.get", side_effect=requests.RequestException("timeout")):
            result = _probe_store_status("2920235")

        self.assertEqual(result.get("status"), "error")
        self.assertEqual(result.get("is_active"), 0)
        self.assertIsNotNone(result.get("error_message"))


if __name__ == "__main__":
    unittest.main()
