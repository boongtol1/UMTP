import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import get_connection  # noqa: E402


MIGRATION_SQL_PATH = os.path.join(PROJECT_ROOT, "sql", "migrate_saved_at_alert_window.sql")
USER_FAIR_PRICES_SQL_PATH = os.path.join(PROJECT_ROOT, "sql", "add_user_fair_prices.sql")
ANALYSIS_JOBS_SQL_PATH = os.path.join(PROJECT_ROOT, "sql", "create_analysis_jobs.sql")
ALERT_EVENTS_SQL_PATH = os.path.join(PROJECT_ROOT, "sql", "create_or_alter_alert_events.sql")


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


class SavedAtAlertWindowMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            connection = get_connection()
        except Exception as exc:  # pragma: no cover
            raise unittest.SkipTest(f"MySQL not available: {exc}") from exc
        else:
            connection.close()

    def test_migration_adds_required_columns_and_indexes(self):
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            _execute_sql_script(connection, USER_FAIR_PRICES_SQL_PATH)
            _execute_sql_script(connection, ANALYSIS_JOBS_SQL_PATH)
            _execute_sql_script(connection, ALERT_EVENTS_SQL_PATH)

            _execute_sql_script(connection, MIGRATION_SQL_PATH)
            _execute_sql_script(connection, MIGRATION_SQL_PATH)

            expected_columns = [
                ("user_fair_prices", "saved_at"),
                ("analysis_jobs", "sort_date"),
                ("alert_events", "sort_date"),
            ]

            for table_name, column_name in expected_columns:
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

            expected_indexes = [
                ("analysis_jobs", "uq_analysis_jobs_user_rule_product"),
                ("alert_events", "uq_alert_events_user_rule_product"),
            ]

            for table_name, index_name in expected_indexes:
                cursor.execute(
                    """
                    SELECT COUNT(*) AS index_count
                    FROM information_schema.statistics
                    WHERE table_schema = DATABASE()
                      AND table_name = %s
                      AND index_name = %s
                    """,
                    (table_name, index_name),
                )
                row = cursor.fetchone() or {}
                self.assertGreaterEqual(int(row.get("index_count", 0)), 1, f"missing {table_name}.{index_name}")
        finally:
            cursor.close()
            connection.close()


if __name__ == "__main__":
    unittest.main()
