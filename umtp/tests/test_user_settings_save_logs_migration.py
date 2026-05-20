import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import get_connection  # noqa: E402


MIGRATION_SQL_PATH = os.path.join(PROJECT_ROOT, "sql", "add_user_settings_save_logs.sql")


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


class UserSettingsSaveLogsMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            connection = get_connection()
        except Exception as exc:  # pragma: no cover
            raise unittest.SkipTest(f"MySQL not available: {exc}") from exc
        else:
            connection.close()

    def test_migration_creates_save_logs_table_columns_and_indexes(self):
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            _execute_sql_script(connection, MIGRATION_SQL_PATH)
            _execute_sql_script(connection, MIGRATION_SQL_PATH)

            expected_columns = [
                "user_id",
                "watch_rule_id",
                "action_type",
                "request_json",
                "response_json",
                "success",
                "error_code",
                "error_message",
                "metadata_json",
                "created_at",
            ]
            for column_name in expected_columns:
                cursor.execute(
                    """
                    SELECT COUNT(*) AS column_count
                    FROM information_schema.columns
                    WHERE table_schema = DATABASE()
                      AND table_name = 'user_settings_save_logs'
                      AND column_name = %s
                    """,
                    (column_name,),
                )
                row = cursor.fetchone() or {}
                self.assertEqual(int(row.get("column_count", 0)), 1, f"missing column {column_name}")

            expected_indexes = [
                "idx_user_settings_save_logs_user_created_at",
                "idx_user_settings_save_logs_watch_rule_created_at",
                "idx_user_settings_save_logs_action_created_at",
                "idx_user_settings_save_logs_success_created_at",
            ]
            for index_name in expected_indexes:
                cursor.execute(
                    """
                    SELECT COUNT(*) AS index_count
                    FROM information_schema.statistics
                    WHERE table_schema = DATABASE()
                      AND table_name = 'user_settings_save_logs'
                      AND index_name = %s
                    """,
                    (index_name,),
                )
                row = cursor.fetchone() or {}
                self.assertGreaterEqual(int(row.get("index_count", 0)), 1, f"missing index {index_name}")
        finally:
            cursor.close()
            connection.close()


if __name__ == "__main__":
    unittest.main()
