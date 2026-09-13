import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import get_connection  # noqa: E402


MIGRATION_SQL_PATH = os.path.join(PROJECT_ROOT, "sql", "add_fraud_probability_v3_columns.sql")


def _execute_sql_script(connection, path):
    with open(path, "r", encoding="utf-8") as file:
        statements = [statement.strip() for statement in file.read().split(";") if statement.strip()]
    cursor = connection.cursor()
    try:
        for statement in statements:
            cursor.execute(statement)
            while cursor.nextset():
                pass
        connection.commit()
    finally:
        cursor.close()


class FraudProbabilityV3MigrationTest(unittest.TestCase):
    def test_migration_adds_v3_columns_and_index_idempotently(self):
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            _execute_sql_script(connection, MIGRATION_SQL_PATH)
            _execute_sql_script(connection, MIGRATION_SQL_PATH)

            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = DATABASE()
                  AND table_name = 'alert_events'
                  AND column_name IN (
                    'fraud_probability_v3',
                    'fraud_probability_label_v3',
                    'fraud_model_version_v3',
                    'fraud_scored_at_v3'
                  )
                """
            )
            columns = {
                next(value for key, value in row.items() if str(key).lower() == "column_name")
                for row in cursor.fetchall()
            }
            self.assertEqual(
                columns,
                {
                    "fraud_probability_v3",
                    "fraud_probability_label_v3",
                    "fraud_model_version_v3",
                    "fraud_scored_at_v3",
                },
            )

            cursor.execute(
                """
                SELECT COUNT(*) AS index_count
                FROM information_schema.statistics
                WHERE table_schema = DATABASE()
                  AND table_name = 'alert_events'
                  AND index_name = 'idx_alert_events_fraud_probability_v3'
                """
            )
            index_row = cursor.fetchone()
            index_count = next(
                value for key, value in index_row.items() if str(key).lower() == "index_count"
            )
            self.assertGreaterEqual(int(index_count), 1)
        finally:
            cursor.close()
            connection.close()


if __name__ == "__main__":
    unittest.main()
