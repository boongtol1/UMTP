import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import get_connection  # noqa: E402


CREATE_ALERT_EVENTS_SQL_PATH = os.path.join(PROJECT_ROOT, "sql", "create_or_alter_alert_events.sql")
READ_STATUS_MIGRATION_SQL_PATH = os.path.join(PROJECT_ROOT, "sql", "add_alert_event_read_status.sql")


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


class AlertEventsReadStatusMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            connection = get_connection()
        except Exception as exc:  # pragma: no cover
            raise unittest.SkipTest(f"MySQL not available: {exc}") from exc
        else:
            connection.close()

    def test_migration_adds_read_columns_and_index_idempotently(self):
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            _execute_sql_script(connection, CREATE_ALERT_EVENTS_SQL_PATH)
            _execute_sql_script(connection, READ_STATUS_MIGRATION_SQL_PATH)
            _execute_sql_script(connection, READ_STATUS_MIGRATION_SQL_PATH)

            expected_columns = {"is_read", "read_at"}
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
            self.assertTrue(expected_columns.issubset(existing_columns))

            cursor.execute(
                """
                SELECT COUNT(*) AS index_count
                FROM information_schema.statistics
                WHERE table_schema = DATABASE()
                  AND table_name = 'alert_events'
                  AND index_name = 'idx_alert_events_user_is_read'
                """
            )
            row = cursor.fetchone() or {}
            self.assertGreaterEqual(int(row.get("index_count", 0)), 1)
        finally:
            cursor.close()
            connection.close()


if __name__ == "__main__":
    unittest.main()
