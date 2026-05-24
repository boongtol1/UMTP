import os
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import resale_trade_journeys as journeys  # noqa: E402


class _FakeCursor:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class _FakeConnection:
    def __init__(self):
        self._cursor = _FakeCursor()
        self.committed = False

    def cursor(self, dictionary=False):
        return self._cursor

    def commit(self):
        self.committed = True

    def is_connected(self):
        return True

    def close(self):
        return None


class ResaleTradeJourneysTest(unittest.TestCase):
    def test_extract_product_id_from_url(self):
        product_id = journeys._extract_product_id_from_url("https://web.joongna.com/product/12345")
        self.assertEqual(product_id, "12345")

    def test_resolve_stage_does_not_downgrade(self):
        stage = journeys._resolve_stage("FINALIZED", "PURCHASED")
        self.assertEqual(stage, "FINALIZED")

    @patch("src.resale_trade_journeys._load_row_summary", return_value={"id": 5, "current_stage": "INSPECTED"})
    @patch("src.resale_trade_journeys._update_row_by_id")
    @patch("src.resale_trade_journeys._upsert_seed_row", return_value={"id": 5, "current_stage": "AUTO_ANALYZED"})
    @patch("src.resale_trade_journeys._build_seed_snapshot", return_value={"source": "joongna", "product_id": "123"})
    @patch("src.resale_trade_journeys.get_connection", return_value=_FakeConnection())
    def test_upsert_after_purchase_promotes_stage(
        self,
        _mock_conn,
        _mock_seed,
        _mock_upsert_seed,
        mock_update,
        _mock_summary,
    ):
        result = journeys.upsert_resale_trade_after_purchase(
            source="joongna",
            product_id="123",
            purchased_at="2026-05-24 10:00:00",
            purchase_price_krw=640000,
            cpu_core_count=8,
            gpu_core_count=8,
        )

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("current_stage"), "INSPECTED")

        update_kwargs = mock_update.call_args.kwargs
        updates = update_kwargs.get("updates", {})
        self.assertEqual(updates.get("current_stage"), "INSPECTED")
        self.assertEqual(updates.get("purchase_price_krw"), 640000)
        self.assertEqual(updates.get("cpu_core_count"), 8)
        self.assertEqual(updates.get("gpu_core_count"), 8)

    @patch("src.resale_trade_journeys._load_row_summary", return_value={"id": 7, "current_stage": "FINALIZED"})
    @patch("src.resale_trade_journeys._update_row_by_id")
    @patch("src.resale_trade_journeys._upsert_seed_row", return_value={"id": 7, "current_stage": "LISTED"})
    @patch("src.resale_trade_journeys._build_seed_snapshot", return_value={"source": "joongna", "product_id": "777"})
    @patch("src.resale_trade_journeys.get_connection", return_value=_FakeConnection())
    def test_upsert_after_resale_promotes_stage_to_finalized(
        self,
        _mock_conn,
        _mock_seed,
        _mock_upsert_seed,
        mock_update,
        _mock_summary,
    ):
        result = journeys.upsert_resale_trade_after_resale(
            source="joongna",
            product_id="777",
            sold_at="2026-05-24 20:30:00",
            sale_price_krw=850000,
        )

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("current_stage"), "FINALIZED")

        update_kwargs = mock_update.call_args.kwargs
        updates = update_kwargs.get("updates", {})
        self.assertEqual(updates.get("current_stage"), "FINALIZED")
        self.assertEqual(updates.get("sale_price_krw"), 850000)


if __name__ == "__main__":
    unittest.main()
