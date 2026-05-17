import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import get_connection  # noqa: E402


MIGRATION_SQL_PATH = os.path.join(PROJECT_ROOT, "sql", "migrate_body_text_fields.sql")
INIT_MVP_TABLES_SQL_PATH = os.path.join(PROJECT_ROOT, "sql", "init_mvp_tables.sql")
CREATE_ALERT_EVENTS_SQL_PATH = os.path.join(PROJECT_ROOT, "sql", "create_or_alter_alert_events.sql")
CREATE_URL_LOGS_SQL_PATH = os.path.join(PROJECT_ROOT, "sql", "add_url_analysis_logs.sql")


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


class BodyTextMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            connection = get_connection()
        except Exception as exc:  # pragma: no cover
            raise unittest.SkipTest(f"MySQL not available: {exc}") from exc
        else:
            connection.close()

    def test_migration_adds_body_text_columns(self):
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            _execute_sql_script(connection, INIT_MVP_TABLES_SQL_PATH)
            _execute_sql_script(connection, CREATE_ALERT_EVENTS_SQL_PATH)
            _execute_sql_script(connection, CREATE_URL_LOGS_SQL_PATH)

            _execute_sql_script(connection, MIGRATION_SQL_PATH)
            _execute_sql_script(connection, MIGRATION_SQL_PATH)

            checks = [
                ("alert_events", "body_text"),
                ("listing_analysis_results", "body_text"),
                ("url_analysis_logs", "body_text"),
            ]

            for table_name, column_name in checks:
                cursor.execute(
                    """
                    SELECT COUNT(*) AS column_count
                    FROM information_schema.columns
                    WHERE table_schema = DATABASE()
                      AND table_name = %s
                      AND column_name = %s
                    """,
                    (table_name, column_name),
                )
                row = cursor.fetchone() or {}
                self.assertEqual(int(row.get("column_count", 0)), 1, f"missing {table_name}.{column_name}")
        finally:
            cursor.close()
            connection.close()


if __name__ == "__main__":
    unittest.main()
