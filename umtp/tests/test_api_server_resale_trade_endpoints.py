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
        "src.api_server.create_or_hydrate_resale_trade_journey_from_product",
        return_value={"ok": True, "id": 11, "current_stage": "DISCOVERED"},
    )
    @patch("src.api_server.register_user", return_value={"ok": True, "user_id": "boongtol"})
    def test_from_product_registers_user_and_forwards_payload(
        self,
        mock_register_user,
        mock_create,
    ):
        request = api_server.ResaleTradeJourneyFromProductRequest(
            source="joongna",
            product_id="123",
        )

        response = api_server.create_resale_trade_journey_from_product("boongtol", request)

        self.assertTrue(response.get("ok"))
        mock_register_user.assert_called_once_with(user_id="boongtol")
        mock_create.assert_called_once_with(user_id="boongtol", source="joongna", product_id="123")

    @patch(
        "src.api_server.patch_resale_trade_journey_purchase",
        return_value={"ok": True, "id": 3, "current_stage": "INSPECTED"},
    )
    @patch("src.api_server.register_user", return_value={"ok": True, "user_id": "boongtol"})
    def test_patch_purchase_supports_flat_and_nested_updates(self, _mock_register, mock_patch):
        response = api_server.patch_resale_trade_purchase(
            "boongtol",
            3,
            {
                "purchase_price_krw": 650000,
                "purchase_contact_record": "010-1111-2222",
                "updates": {
                    "battery_health_percent": 92,
                    "money_sent_at": "2026-05-25 12:30:00",
                },
            },
        )

        self.assertTrue(response.get("ok"))
        mock_patch.assert_called_once()
        kwargs = mock_patch.call_args.kwargs
        self.assertEqual(kwargs.get("journey_id"), 3)
        self.assertEqual(kwargs.get("user_id"), "boongtol")
        self.assertEqual(kwargs.get("updates", {}).get("purchase_price_krw"), 650000)
        self.assertEqual(kwargs.get("updates", {}).get("purchase_contact_record"), "010-1111-2222")
        self.assertEqual(kwargs.get("updates", {}).get("battery_health_percent"), 92)
        self.assertEqual(kwargs.get("updates", {}).get("money_sent_at"), "2026-05-25 12:30:00")

    @patch(
        "src.api_server.list_purchased_resale_trade_journeys",
        return_value={"ok": True, "items": [{"id": 9}]},
    )
    @patch("src.api_server.register_user", return_value={"ok": True, "user_id": "boongtol"})
    def test_get_purchased_resale_trade_journeys(self, _mock_register, mock_list):
        response = api_server.get_purchased_resale_trade_journeys("boongtol", limit=55)

        self.assertTrue(response.get("ok"))
        self.assertEqual(response.get("items"), [{"id": 9}])
        mock_list.assert_called_once_with(user_id="boongtol", limit=55)

    @patch(
        "src.api_server.start_resale_trade_journey_from_url",
        return_value={"ok": True, "trade_journey_id": 101, "existing": False},
    )
    @patch("src.api_server.register_user", return_value={"ok": True, "user_id": "boongtol"})
    def test_start_trade_journey_from_url_endpoint(self, _mock_register, mock_start):
        request = api_server.TradeJourneyStartFromUrlRequest(
            user_id="boongtol",
            url="https://web.joongna.com/product/123",
        )

        response = api_server.start_trade_journey_from_url(request)

        self.assertTrue(response.get("ok"))
        self.assertEqual(response.get("trade_journey_id"), 101)
        mock_start.assert_called_once_with(
            user_id="boongtol",
            url="https://web.joongna.com/product/123",
        )

    @patch(
        "src.api_server.build_trade_prefill_from_input",
        return_value={"ok": True, "product_id": "123", "row": {"product_id": "123"}},
    )
    @patch("src.api_server.register_user", return_value={"ok": True, "user_id": "boongtol"})
    def test_get_resale_prefill_endpoint(self, _mock_register, mock_prefill):
        response = api_server.get_resale_trade_prefill(
            user_id="boongtol",
            input="https://web.joongna.com/product/123",
        )

        self.assertTrue(response.get("ok"))
        mock_prefill.assert_called_once_with(
            user_id="boongtol",
            input_value="https://web.joongna.com/product/123",
        )

    @patch(
        "src.api_server.start_resale_trade_journey_from_alert",
        return_value={"ok": True, "trade_journey_id": 102, "existing": True},
    )
    @patch("src.api_server.register_user", return_value={"ok": True, "user_id": "boongtol"})
    def test_start_trade_journey_from_alert_endpoint(self, _mock_register, mock_start):
        request = api_server.TradeJourneyStartFromAlertRequest(
            user_id="boongtol",
            alert_event_id=77,
        )

        response = api_server.start_trade_journey_from_alert(request)

        self.assertTrue(response.get("ok"))
        self.assertEqual(response.get("trade_journey_id"), 102)
        mock_start.assert_called_once_with(user_id="boongtol", alert_event_id=77)

    @patch(
        "src.api_server.start_resale_trade_journey_from_read_archive",
        return_value={"ok": True, "trade_journey_id": 103, "existing": False},
    )
    @patch("src.api_server.register_user", return_value={"ok": True, "user_id": "boongtol"})
    def test_start_trade_journey_from_read_archive_endpoint(self, _mock_register, mock_start):
        request = api_server.TradeJourneyStartFromReadArchiveRequest(
            user_id="boongtol",
            read_archive_event_id=88,
        )

        response = api_server.start_trade_journey_from_read_archive(request)

        self.assertTrue(response.get("ok"))
        self.assertEqual(response.get("trade_journey_id"), 103)
        mock_start.assert_called_once_with(user_id="boongtol", read_archive_event_id=88)

    @patch(
        "src.api_server.upsert_resale_trade_after_purchase",
        return_value={"ok": True, "id": 11, "current_stage": "INSPECTED"},
    )
    @patch("src.api_server.register_user", return_value={"ok": True, "user_id": "boongtol"})
    def test_legacy_after_purchase_upsert_still_works(
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


if __name__ == "__main__":
    unittest.main()
