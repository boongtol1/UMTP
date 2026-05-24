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

    def test_migration_creates_table_and_core_columns_idempotently(self):
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
                "listing_created_at",
                "discovered_at",
                "listing_price_krw",
                "fair_price_krw",
                "purchased_at",
                "sale_price_krw",
                "net_profit_krw",
                "current_stage",
                "response_time_minutes",
                "total_cost_krw",
                "roi_percent",
                "cpu_core_count",
                "gpu_core_count",
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
