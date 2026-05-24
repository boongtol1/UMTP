import os
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import api_server  # noqa: E402


class ApiServerResaleTradeEndpointsTest(unittest.TestCase):
    @patch(
        "src.api_server.upsert_resale_trade_after_purchase",
        return_value={"ok": True, "id": 11, "current_stage": "PURCHASED"},
    )
    @patch("src.api_server.register_user", return_value={"ok": True, "user_id": "boongtol"})
    def test_after_purchase_upsert_registers_user_and_forwards_payload(
        self,
        mock_register_user,
        mock_upsert,
    ):
        request = api_server.ResaleTradeAfterPurchaseUpsertRequest(
            user_id="boongtol",
            source="joongna",
            product_id="123",
            updates={
                "purchase_price_krw": 650000,
                "purchase_method": "직거래",
            },
        )

        response = api_server.resale_trades_after_purchase_upsert(request)

        self.assertTrue(response.get("ok"))
        mock_register_user.assert_called_once_with(user_id="boongtol")
        mock_upsert.assert_called_once()
        kwargs = mock_upsert.call_args.kwargs
        self.assertEqual(kwargs.get("user_id"), "boongtol")
        self.assertEqual(kwargs.get("source"), "joongna")
        self.assertEqual(kwargs.get("product_id"), "123")
        self.assertEqual(kwargs.get("purchase_price_krw"), 650000)

    @patch(
        "src.api_server.upsert_resale_trade_after_purchase",
        side_effect=ValueError("invalid_identity"),
    )
    def test_after_purchase_upsert_requires_product_or_url(self, _mock_upsert):
        request = api_server.ResaleTradeAfterPurchaseUpsertRequest(
            source="joongna",
            updates={"purchase_price_krw": 650000},
        )

        response = api_server.resale_trades_after_purchase_upsert(request)

        self.assertFalse(response.get("ok"))
        self.assertIn("product_id 또는 url", response.get("reason", ""))

    @patch(
        "src.api_server.upsert_resale_trade_after_resale",
        return_value={"ok": True, "id": 11, "current_stage": "FINALIZED"},
    )
    def test_after_resale_upsert_without_user_id(self, mock_upsert):
        request = api_server.ResaleTradeAfterResaleUpsertRequest(
            source="joongna",
            product_id="123",
            updates={
                "sold_at": "2026-05-24 18:30:00",
                "sale_price_krw": 820000,
            },
        )

        response = api_server.resale_trades_after_resale_upsert(request)

        self.assertTrue(response.get("ok"))
        mock_upsert.assert_called_once()
        kwargs = mock_upsert.call_args.kwargs
        self.assertEqual(kwargs.get("product_id"), "123")
        self.assertEqual(kwargs.get("sale_price_krw"), 820000)


if __name__ == "__main__":
    unittest.main()
