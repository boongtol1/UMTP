import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import get_connection  # noqa: E402


MIGRATION_DIRECTION_SQL_PATH = os.path.join(PROJECT_ROOT, "sql", "migrate_alert_price_direction.sql")
MIGRATION_TARGET_SQL_PATH = os.path.join(PROJECT_ROOT, "sql", "migrate_target_buy_price_generated_column.sql")

TEST_USER_ID = "alert_direction_migration_it"
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


class AlertPriceDirectionMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            connection = get_connection()
        except Exception as exc:  # pragma: no cover
            raise unittest.SkipTest(f"MySQL not available: {exc}") from exc
        else:
            connection.close()

    def test_direction_migration_is_idempotent_and_defaults_existing_behavior(self):
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            _execute_sql_script(connection, MIGRATION_TARGET_SQL_PATH)
            _execute_sql_script(connection, MIGRATION_DIRECTION_SQL_PATH)
            _execute_sql_script(connection, MIGRATION_DIRECTION_SQL_PATH)

            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = DATABASE()
                  AND table_name = 'user_fair_prices'
                  AND column_name = 'alert_price_direction'
                """
            )
            self.assertIsNotNone(cursor.fetchone())

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
                    enabled,
                    search_keyword,
                    poll_interval_seconds,
                    force_poll,
                    last_poll_requested_at,
                    last_polled_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE, %s, %s, FALSE, NULL, NULL)
                """,
                (
                    TEST_USER_ID,
                    TEST_PRODUCT_TYPE,
                    TEST_CHIP,
                    TEST_SCREEN_INCH,
                    TEST_RAM_GB,
                    TEST_SSD_GB,
                    1000000,
                    20.50,
                    "direction-migration-test",
                    60,
                ),
            )
            connection.commit()

            cursor.execute(
                """
                SELECT alert_price_direction
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
            inserted = cursor.fetchone()
            self.assertEqual(inserted.get("alert_price_direction"), "BELOW_OR_EQUAL")

            cursor.execute(
                """
                UPDATE user_fair_prices
                SET alert_price_direction = 'ABOVE_OR_EQUAL'
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

            cursor.execute(
                """
                SELECT alert_price_direction
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
            updated = cursor.fetchone()
            self.assertEqual(updated.get("alert_price_direction"), "ABOVE_OR_EQUAL")
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
