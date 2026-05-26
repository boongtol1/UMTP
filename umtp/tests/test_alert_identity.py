import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.listing_analysis_pipeline import maybe_create_alert_event  # noqa: E402


class _FakeCursor:
    def __init__(self, *, duplicate_row=None, raise_duplicate_on_insert=False, lastrowid=1):
        self.duplicate_row = duplicate_row
        self.raise_duplicate_on_insert = raise_duplicate_on_insert
        self.lastrowid = lastrowid
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))
        normalized_query = " ".join(query.split()).lower()

        if normalized_query.startswith("insert into alert_events") and self.raise_duplicate_on_insert:
            raise RuntimeError("Duplicate entry 'u1-1-p1' for key 'uq_alert_events_user_rule_product'")

    def fetchone(self):
        return self.duplicate_row


class AlertIdentityTest(unittest.TestCase):
    def test_duplicate_identity_returns_skip(self):
        fake_cursor = _FakeCursor(duplicate_row={"id": 5})

        result = maybe_create_alert_event(
            fake_cursor,
            analysis_job_id=1,
            user_id="u1",
            watch_rule_id=1,
            product_id="p1",
            url="https://web.joongna.com/product/1",
            title="title",
            price_krw=100,
            fair_price_krw=200,
            target_price_krw=150,
            drop_rate_percent=50.0,
            trigger_reason="new_product",
            message="msg",
        )

        self.assertFalse(result.get("created"))
        self.assertEqual(result.get("reason"), "duplicate_identity_alert")
        self.assertEqual(result.get("alert_id"), 5)

    def test_insert_success_creates_alert(self):
        fake_cursor = _FakeCursor(duplicate_row=None, lastrowid=9)

        result = maybe_create_alert_event(
            fake_cursor,
            analysis_job_id=1,
            user_id="u1",
            watch_rule_id=1,
            product_id="p1",
            url="https://web.joongna.com/product/1",
            title="title",
            price_krw=100,
            fair_price_krw=200,
            target_price_krw=150,
            drop_rate_percent=50.0,
            trigger_reason="new_product",
            message="msg",
            sort_date="2026-05-19 10:30:00",
        )

        self.assertTrue(result.get("created"))
        self.assertEqual(result.get("alert_id"), 9)
        self.assertIn("change_fingerprint", fake_cursor.executed[0][0].lower())

    def test_duplicate_insert_error_returns_existing_alert(self):
        class _DynamicCursor(_FakeCursor):
            def __init__(self):
                super().__init__(duplicate_row=None, raise_duplicate_on_insert=True)
                self.lookup_count = 0

            def fetchone(self):
                self.lookup_count += 1
                if self.lookup_count >= 2:
                    return {"id": 17}
                return None

        fake_cursor = _DynamicCursor()

        result = maybe_create_alert_event(
            fake_cursor,
            analysis_job_id=1,
            user_id="u1",
            watch_rule_id=1,
            product_id="p1",
            url="https://web.joongna.com/product/1",
            title="title",
            price_krw=100,
            fair_price_krw=200,
            target_price_krw=150,
            drop_rate_percent=50.0,
            trigger_reason="new_product",
            message="msg",
        )

        self.assertFalse(result.get("created"))
        self.assertEqual(result.get("reason"), "duplicate_identity_alert")
        self.assertEqual(result.get("alert_id"), 17)

    def test_content_change_family_dedupe_lookup_ignores_watch_rule_id(self):
        fake_cursor = _FakeCursor(duplicate_row=None, lastrowid=11)

        maybe_create_alert_event(
            fake_cursor,
            analysis_job_id=1,
            user_id="u1",
            watch_rule_id=99,
            product_id="p1",
            url="https://web.joongna.com/product/1",
            title="title",
            price_krw=100,
            fair_price_krw=200,
            target_price_krw=150,
            drop_rate_percent=50.0,
            trigger_reason="self_check_changed",
            change_fingerprint="cfp-1",
            message="msg",
        )

        first_query = " ".join((fake_cursor.executed[0][0] or "").split()).lower()
        self.assertIn("from alert_events", first_query)
        self.assertNotIn("watch_rule_id", first_query)

    def test_non_content_changed_dedupe_lookup_keeps_watch_rule_id(self):
        fake_cursor = _FakeCursor(duplicate_row=None, lastrowid=12)

        maybe_create_alert_event(
            fake_cursor,
            analysis_job_id=1,
            user_id="u1",
            watch_rule_id=99,
            product_id="p1",
            url="https://web.joongna.com/product/1",
            title="title",
            price_krw=100,
            fair_price_krw=200,
            target_price_krw=150,
            drop_rate_percent=50.0,
            trigger_reason="sort_date_changed",
            change_fingerprint="cfp-2",
            message="msg",
        )

        first_query = " ".join((fake_cursor.executed[0][0] or "").split()).lower()
        self.assertIn("watch_rule_id", first_query)


if __name__ == "__main__":
    unittest.main()
