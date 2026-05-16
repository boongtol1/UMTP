import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import get_connection  # noqa: E402


MIGRATION_DIRECTION_SQL_PATH = os.path.join(PROJECT_ROOT, "sql", "migrate_alert_price_direction.sql")
MIGRATION_TARGET_SQL_PATH = os.path.join(PROJECT_ROOT, "sql", "migrate_target_buy_price_generated_column.sql")
MIGRATION_BOUNDS_SQL_PATH = os.path.join(PROJECT_ROOT, "sql", "migrate_min_max_price_bounds.sql")

TEST_USER_ID = "min_max_bounds_it"
TEST_PRODUCT_TYPE = "MacBook Air"
TEST_CHIP = "M2"
TEST_SCREEN_INCH = 13
TEST_RAM_GB = 8
TEST_SSD_GB = 256


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


class MinMaxPriceBoundsMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            connection = get_connection()
        except Exception as exc:  # pragma: no cover - local DB unavailable case
            raise unittest.SkipTest(f"MySQL not available: {exc}") from exc
        else:
            connection.close()

    def test_migration_adds_columns_and_is_idempotent(self):
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            _execute_sql_script(connection, MIGRATION_DIRECTION_SQL_PATH)
            _execute_sql_script(connection, MIGRATION_TARGET_SQL_PATH)
            _execute_sql_script(connection, MIGRATION_BOUNDS_SQL_PATH)
            _execute_sql_script(connection, MIGRATION_BOUNDS_SQL_PATH)

            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = DATABASE()
                  AND table_name = 'user_fair_prices'
                  AND column_name IN ('min_price_krw', 'max_price_krw')
                ORDER BY column_name ASC
                """
            )
            rows = cursor.fetchall() or []
            column_names = [
                (row.get("column_name") or row.get("COLUMN_NAME"))
                for row in rows
            ]
            self.assertEqual(column_names, ["max_price_krw", "min_price_krw"])
        finally:
            cursor.close()
            connection.close()

    def test_direction_specific_bounds_are_saved(self):
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            _execute_sql_script(connection, MIGRATION_DIRECTION_SQL_PATH)
            _execute_sql_script(connection, MIGRATION_TARGET_SQL_PATH)
            _execute_sql_script(connection, MIGRATION_BOUNDS_SQL_PATH)

            cursor.execute(
                """
                DELETE FROM user_fair_prices
                WHERE user_id = %s
                  AND product_type = %s
                  AND chip = %s
                  AND screen_inch = %s
                  AND ram_gb = %s
                  AND ssd_gb = %s
                """,
                (
                    TEST_USER_ID,
                    TEST_PRODUCT_TYPE,
                    TEST_CHIP,
                    TEST_SCREEN_INCH,
                    TEST_RAM_GB,
                    TEST_SSD_GB,
                ),
            )

            cursor.execute(
                """
                INSERT INTO user_fair_prices (
                    user_id,
                    product_type,
                    chip,
                    screen_inch,
                    ram_gb,
                    ssd_gb,
                    fair_price_krw,
                    alert_drop_rate_percent,
                    alert_price_direction,
                    min_price_krw,
                    max_price_krw,
                    enabled,
                    search_keyword,
                    poll_interval_seconds,
                    force_poll,
                    last_poll_requested_at,
                    last_polled_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, %s, %s, FALSE, NULL, NULL)
                """,
                (
                    TEST_USER_ID,
                    TEST_PRODUCT_TYPE,
                    TEST_CHIP,
                    TEST_SCREEN_INCH,
                    TEST_RAM_GB,
                    TEST_SSD_GB,
                    1000000,
                    20.0,
                    "BELOW_OR_EQUAL",
                    300000,
                    None,
                    "m2맥북에어",
                    60,
                ),
            )
            connection.commit()

            cursor.execute(
                """
                SELECT alert_price_direction, min_price_krw, max_price_krw
                FROM user_fair_prices
                WHERE user_id = %s
                  AND product_type = %s
                  AND chip = %s
                  AND screen_inch = %s
                  AND ram_gb = %s
                  AND ssd_gb = %s
                """,
                (
                    TEST_USER_ID,
                    TEST_PRODUCT_TYPE,
                    TEST_CHIP,
                    TEST_SCREEN_INCH,
                    TEST_RAM_GB,
                    TEST_SSD_GB,
                ),
            )
            inserted = cursor.fetchone() or {}
            self.assertEqual(inserted.get("alert_price_direction"), "BELOW_OR_EQUAL")
            self.assertEqual(inserted.get("min_price_krw"), 300000)
            self.assertIsNone(inserted.get("max_price_krw"))

            cursor.execute(
                """
                UPDATE user_fair_prices
                SET alert_price_direction = %s,
                    min_price_krw = %s,
                    max_price_krw = %s
                WHERE user_id = %s
                  AND product_type = %s
                  AND chip = %s
                  AND screen_inch = %s
                  AND ram_gb = %s
                  AND ssd_gb = %s
                """,
                (
                    "ABOVE_OR_EQUAL",
                    None,
                    900000,
                    TEST_USER_ID,
                    TEST_PRODUCT_TYPE,
                    TEST_CHIP,
                    TEST_SCREEN_INCH,
                    TEST_RAM_GB,
                    TEST_SSD_GB,
                ),
            )
            connection.commit()

            cursor.execute(
                """
                SELECT alert_price_direction, min_price_krw, max_price_krw
                FROM user_fair_prices
                WHERE user_id = %s
                  AND product_type = %s
                  AND chip = %s
                  AND screen_inch = %s
                  AND ram_gb = %s
                  AND ssd_gb = %s
                """,
                (
                    TEST_USER_ID,
                    TEST_PRODUCT_TYPE,
                    TEST_CHIP,
                    TEST_SCREEN_INCH,
                    TEST_RAM_GB,
                    TEST_SSD_GB,
                ),
            )
            updated = cursor.fetchone() or {}
            self.assertEqual(updated.get("alert_price_direction"), "ABOVE_OR_EQUAL")
            self.assertIsNone(updated.get("min_price_krw"))
            self.assertEqual(updated.get("max_price_krw"), 900000)
        finally:
            cursor.execute(
                """
                DELETE FROM user_fair_prices
                WHERE user_id = %s
                  AND product_type = %s
                  AND chip = %s
                  AND screen_inch = %s
                  AND ram_gb = %s
                  AND ssd_gb = %s
                """,
                (
                    TEST_USER_ID,
                    TEST_PRODUCT_TYPE,
                    TEST_CHIP,
                    TEST_SCREEN_INCH,
                    TEST_RAM_GB,
                    TEST_SSD_GB,
                ),
            )
            connection.commit()
            cursor.close()
            connection.close()


if __name__ == "__main__":
    unittest.main()
