import os
import sys
import unittest

import mysql.connector


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import get_connection  # noqa: E402


MIGRATION_SQL_PATH = os.path.join(PROJECT_ROOT, "sql", "migrate_target_buy_price_generated_column.sql")
MIGRATION_ALERT_DIRECTION_SQL_PATH = os.path.join(
    PROJECT_ROOT,
    "sql",
    "migrate_alert_price_direction.sql",
)
TEST_USER_ID = "generated_target_buy_price_it"
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


class TargetBuyPriceGeneratedColumnTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            connection = get_connection()
        except Exception as exc:  # pragma: no cover - local DB unavailable case
            raise unittest.SkipTest(f"MySQL not available: {exc}") from exc
        else:
            connection.close()

    def test_migration_adds_column_and_is_idempotent(self):
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            _execute_sql_script(connection, MIGRATION_SQL_PATH)
            _execute_sql_script(connection, MIGRATION_SQL_PATH)
            _execute_sql_script(connection, MIGRATION_ALERT_DIRECTION_SQL_PATH)
            _execute_sql_script(connection, MIGRATION_ALERT_DIRECTION_SQL_PATH)

            cursor.execute(
                """
                SELECT
                    extra
                FROM information_schema.columns
                WHERE table_schema = DATABASE()
                  AND table_name = 'user_fair_prices'
                  AND column_name = 'target_buy_price_krw'
                """
            )
            row = cursor.fetchone()
            self.assertIsNotNone(row)

            cursor.execute("SHOW CREATE TABLE user_fair_prices")
            create_row = cursor.fetchone() or {}
            create_sql = create_row.get("Create Table", "")
            lowered_create_sql = create_sql.lower()
            self.assertIn("target_buy_price_krw", create_sql)
            self.assertIn("GENERATED ALWAYS AS", create_sql)
            self.assertIn("round((`fair_price_krw` * (1 - (`alert_drop_rate_percent` / 100)))", lowered_create_sql)
            self.assertIn("alert_price_direction", create_sql)
            self.assertIn("below_or_equal", lowered_create_sql)
        finally:
            cursor.close()
            connection.close()

    def test_generated_column_auto_recalculates_and_blocks_manual_write(self):
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("DROP TEMPORARY TABLE IF EXISTS tmp_target_buy_price_generated")
            cursor.execute(
                """
                CREATE TEMPORARY TABLE tmp_target_buy_price_generated (
                    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    fair_price_krw INT NOT NULL,
                    alert_drop_rate_percent DECIMAL(5,2) NOT NULL,
                    target_buy_price_krw INT
                        GENERATED ALWAYS AS (
                            ROUND(
                                fair_price_krw * (
                                    1 - (alert_drop_rate_percent / 100)
                                )
                            )
                        ) STORED
                )
                """
            )
            cursor.execute(
                """
                INSERT INTO tmp_target_buy_price_generated (
                    fair_price_krw,
                    alert_drop_rate_percent
                )
                VALUES (%s, %s)
                """,
                (1000000, 20.50),
            )
            row_id = cursor.lastrowid

            cursor.execute(
                """
                SELECT fair_price_krw, alert_drop_rate_percent, target_buy_price_krw
                FROM tmp_target_buy_price_generated
                WHERE id = %s
                """,
                (row_id,),
            )
            inserted = cursor.fetchone()
            self.assertEqual(inserted.get("target_buy_price_krw"), 795000)

            cursor.execute(
                """
                UPDATE tmp_target_buy_price_generated
                SET fair_price_krw = %s
                WHERE id = %s
                """,
                (900000, row_id),
            )
            cursor.execute(
                """
                SELECT target_buy_price_krw
                FROM tmp_target_buy_price_generated
                WHERE id = %s
                """,
                (row_id,),
            )
            updated_fair = cursor.fetchone()
            self.assertEqual(updated_fair.get("target_buy_price_krw"), 715500)

            cursor.execute(
                """
                UPDATE tmp_target_buy_price_generated
                SET alert_drop_rate_percent = %s
                WHERE id = %s
                """,
                (10.00, row_id),
            )
            cursor.execute(
                """
                SELECT target_buy_price_krw
                FROM tmp_target_buy_price_generated
                WHERE id = %s
                """,
                (row_id,),
            )
            updated_drop = cursor.fetchone()
            self.assertEqual(updated_drop.get("target_buy_price_krw"), 810000)

            cursor.execute(
                """
                UPDATE tmp_target_buy_price_generated
                SET alert_drop_rate_percent = %s
                WHERE id = %s
                """,
                (-10.00, row_id),
            )
            cursor.execute(
                """
                SELECT target_buy_price_krw
                FROM tmp_target_buy_price_generated
                WHERE id = %s
                """,
                (row_id,),
            )
            updated_drop_negative = cursor.fetchone()
            self.assertEqual(updated_drop_negative.get("target_buy_price_krw"), 990000)

            with self.assertRaises(mysql.connector.Error):
                cursor.execute(
                    """
                    UPDATE tmp_target_buy_price_generated
                    SET target_buy_price_krw = %s
                    WHERE id = %s
                    """,
                    (1, row_id),
                )
        finally:
            cursor.close()
            connection.close()

    def test_user_fair_prices_generated_value_updates_on_insert_and_update(self):
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            _execute_sql_script(connection, MIGRATION_SQL_PATH)

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
                    "generated-target-test",
                    60,
                ),
            )

            cursor.execute(
                """
                SELECT target_buy_price_krw
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
            self.assertEqual(inserted.get("target_buy_price_krw"), 795000)

            cursor.execute(
                """
                UPDATE user_fair_prices
                SET fair_price_krw = %s,
                    alert_drop_rate_percent = %s
                WHERE user_id = %s
                  AND product_type = %s
                  AND chip = %s
                  AND screen_inch = %s
                  AND ram_gb = %s
                  AND ssd_gb = %s
                """,
                (
                    900000,
                    10.00,
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
                SELECT target_buy_price_krw
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
            self.assertEqual(updated.get("target_buy_price_krw"), 810000)

            cursor.execute(
                """
                UPDATE user_fair_prices
                SET alert_drop_rate_percent = %s
                WHERE user_id = %s
                  AND product_type = %s
                  AND chip = %s
                  AND screen_inch = %s
                  AND ram_gb = %s
                  AND ssd_gb = %s
                """,
                (
                    -10.00,
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
                SELECT target_buy_price_krw
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
            updated_negative = cursor.fetchone()
            self.assertEqual(updated_negative.get("target_buy_price_krw"), 990000)
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
