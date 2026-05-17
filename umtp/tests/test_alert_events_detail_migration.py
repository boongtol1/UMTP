import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import get_connection  # noqa: E402


MIGRATION_SQL_PATH = os.path.join(PROJECT_ROOT, "sql", "migrate_alert_events_detail_fields.sql")
BODY_TEXT_MIGRATION_SQL_PATH = os.path.join(PROJECT_ROOT, "sql", "migrate_body_text_fields.sql")
CREATE_ALERT_EVENTS_SQL_PATH = os.path.join(PROJECT_ROOT, "sql", "create_or_alter_alert_events.sql")


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


class AlertEventsDetailMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            connection = get_connection()
        except Exception as exc:  # pragma: no cover
            raise unittest.SkipTest(f"MySQL not available: {exc}") from exc
        else:
            connection.close()

    def test_migration_adds_columns_and_is_idempotent(self):
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            _execute_sql_script(connection, CREATE_ALERT_EVENTS_SQL_PATH)
            _execute_sql_script(connection, MIGRATION_SQL_PATH)
            _execute_sql_script(connection, MIGRATION_SQL_PATH)
            _execute_sql_script(connection, BODY_TEXT_MIGRATION_SQL_PATH)
            _execute_sql_script(connection, BODY_TEXT_MIGRATION_SQL_PATH)

            expected_columns = {
                "source",
                "product_type",
                "chip",
                "screen_inch",
                "ram_gb",
                "ssd_gb",
                "alert_drop_rate_percent",
                "alert_price_direction",
                "risk_level",
                "risk_score",
                "risk_keywords",
                "is_exchange_post",
                "trade_type",
                "body_excerpt",
                "body_text",
                "analyzed_at",
            }

            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = DATABASE()
                  AND table_name = 'alert_events'
                """
            )
            existing_columns = set()
            for row in cursor.fetchall() or []:
                if not isinstance(row, dict):
                    continue
                for key, value in row.items():
                    if str(key).lower() == "column_name":
                        existing_columns.add(value)

            missing_columns = expected_columns - existing_columns
            self.assertEqual(missing_columns, set())
        finally:
            cursor.close()
            connection.close()


if __name__ == "__main__":
    unittest.main()
