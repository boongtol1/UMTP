import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import get_connection  # noqa: E402


MIGRATION_SQL_PATH = os.path.join(PROJECT_ROOT, "sql", "create_resale_trade_journeys.sql")


def _execute_sql_script(connection, path):
    with open(path, "r", encoding="utf-8") as file:
        raw_sql = file.read()

    statements = [statement.strip() for statement in raw_sql.split(";") if statement.strip()]
    cursor = connection.cursor()
    try:
        for statement in statements:
            cursor.execute(statement)
            while cursor.nextset():
                pass
        connection.commit()
    finally:
        cursor.close()


class ResaleTradeJourneysMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            connection = get_connection()
        except Exception as exc:  # pragma: no cover
            raise unittest.SkipTest(f"MySQL not available: {exc}") from exc
        else:
            connection.close()

    def test_migration_creates_current_table_idempotently(self):
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            _execute_sql_script(connection, MIGRATION_SQL_PATH)
            _execute_sql_script(connection, MIGRATION_SQL_PATH)

            cursor.execute(
                """
                SELECT COUNT(*) AS table_count
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                  AND table_name = 'resale_trade_journeys'
                """
            )
            table_row = cursor.fetchone() or {}
            self.assertEqual(int(table_row.get("table_count", 0)), 1)

            expected_columns = [
                "source",
                "product_id",
                "url",
                "title",
                "listing_price_krw",
                "seller_nickname",
                "seller_location",
                "image_urls",
                "body_text",
                "product_type",
                "chip",
                "screen_inch",
                "ram_gb",
                "ssd_gb",
                "fair_price_krw",
                "discount_rate_percent",
                "contacted_at",
                "seller_response_at",
                "purchased_at",
                "purchase_price_krw",
                "purchase_method",
                "purchase_location",
                "transport_cost_krw",
                "shipping_cost_krw",
                "total_cost_krw",
                "payment_method",
                "serial_number",
                "model_number",
                "battery_cycle_count",
                "battery_health_percent",
                "activation_lock_off",
                "mdm_lock_none",
                "inspection_notes",
                "resale_listing_price_krw",
                "resale_platform",
                "resale_url",
                "sold_at",
                "sale_price_krw",
                "buyer_nickname",
                "sale_method",
                "sale_location",
                "sale_platform",
                "current_stage",
            ]

            for column_name in expected_columns:
                cursor.execute(
                    """
                    SELECT COUNT(*) AS column_count
                    FROM information_schema.columns
                    WHERE table_schema = DATABASE()
                      AND table_name = 'resale_trade_journeys'
                      AND column_name = %s
                    """,
                    (column_name,),
                )
                row = cursor.fetchone() or {}
                self.assertEqual(int(row.get("column_count", 0)), 1, f"missing column: {column_name}")

            cursor.execute(
                """
                SELECT column_name AS name
                FROM information_schema.columns
                WHERE table_schema = DATABASE()
                  AND table_name = 'resale_trade_journeys'
                  AND column_name IN ('seller_nickname', 'seller_location', 'image_urls')
                ORDER BY ordinal_position
                """
            )
            ordered_location_columns = [row.get("name") for row in cursor.fetchall() or []]
            self.assertEqual(
                ordered_location_columns,
                ["seller_nickname", "seller_location", "image_urls"],
            )

            removed_columns = [
                "gross_profit_krw",
                "net_profit_krw",
                "roi_percent",
                "url_digest",
                "listing_created_at",
                "discovered_at",
                "seller_shop_id",
                "purchase_contact_record",
                "purchase_conversation_text",
                "response_time_minutes",
                "money_sent_at",
                "money_received_at",
                "purchase_account_number",
                "cpu_core_count",
                "gpu_core_count",
                "applecare_status",
                "minimum_accept_price_krw",
                "resale_listing_created_at",
                "resale_product_id",
                "initial_resale_price_krw",
                "resale_contact_record",
                "resale_conversation_text",
                "resale_account_number",
                "final_shipping_cost_krw",
                "platform_fee_krw",
                "refund_or_claim",
                "expected_profit_krw",
                "risk_score",
                "reason_tags",
                "purchase_speed_minutes",
                "sale_duration_hours",
                "total_holding_time_hours",
                "profit_per_day_krw",
                "final_result_notes",
            ]

            cursor.execute(
                f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = DATABASE()
                  AND table_name = 'resale_trade_journeys'
                  AND column_name IN ({", ".join(["%s"] * len(removed_columns))})
                """,
                tuple(removed_columns),
            )
            rows = cursor.fetchall() or []
            self.assertEqual(rows, [])

            expected_indexes = [
                "uniq_resale_journey_user_source_product",
                "idx_resale_journey_source_product",
                "idx_resale_journey_stage",
            ]

            for index_name in expected_indexes:
                cursor.execute(
                    """
                    SELECT COUNT(*) AS index_count
                    FROM information_schema.statistics
                    WHERE table_schema = DATABASE()
                      AND table_name = 'resale_trade_journeys'
                      AND index_name = %s
                    """,
                    (index_name,),
                )
                row = cursor.fetchone() or {}
                self.assertGreaterEqual(int(row.get("index_count", 0)), 1, f"missing index: {index_name}")
        finally:
            cursor.close()
            connection.close()


if __name__ == "__main__":
    unittest.main()
