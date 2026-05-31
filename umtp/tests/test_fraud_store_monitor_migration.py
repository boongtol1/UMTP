import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import get_connection  # noqa: E402


MIGRATION_SQL_PATH = os.path.join(PROJECT_ROOT, "sql", "migrate_fraud_store_monitor.sql")


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


class FraudStoreMonitorMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            connection = get_connection()
        except Exception as exc:  # pragma: no cover
            raise unittest.SkipTest(f"MySQL not available: {exc}") from exc
        else:
            connection.close()

    def test_migration_creates_fraud_store_monitor_tables(self):
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            _execute_sql_script(connection, MIGRATION_SQL_PATH)
            _execute_sql_script(connection, MIGRATION_SQL_PATH)

            expected_columns = [
                ("fraud_store_status_snapshots", "store_id"),
                ("fraud_store_status_snapshots", "store_seq"),
                ("fraud_store_status_snapshots", "status"),
                ("fraud_store_status_snapshots", "status_reason"),
                ("fraud_store_status_snapshots", "source"),
                ("fraud_store_status_snapshots", "http_status"),
                ("fraud_store_status_snapshots", "meta_code"),
                ("fraud_store_status_snapshots", "raw_response_json"),
                ("fraud_store_activity_snapshots", "posts_last_1h"),
                ("fraud_store_activity_snapshots", "store_seq"),
                ("fraud_store_activity_snapshots", "observed_at"),
                ("fraud_store_activity_snapshots", "store_name"),
                ("fraud_store_activity_snapshots", "store_name_fingerprint"),
                ("fraud_store_activity_snapshots", "profile_fingerprint"),
                ("fraud_store_activity_snapshots", "posts_last_24h"),
                ("fraud_store_activity_snapshots", "visible_product_count"),
                ("fraud_training_label_candidates", "product_id"),
                ("fraud_training_label_candidates", "store_id"),
                ("fraud_training_label_candidates", "first_inactive_at"),
                ("fraud_training_label_candidates", "inactive_after_minutes"),
                ("fraud_training_label_candidates", "label"),
                ("fraud_training_label_candidates", "label_reason"),
                ("joongna_store_profiles", "store_name_fingerprint"),
                ("joongna_store_profiles", "profile_fingerprint"),
                ("joongna_store_profiles", "last_status"),
                ("joongna_store_profiles", "last_seen_at"),
                ("joongna_store_name_changes", "store_seq"),
                ("joongna_store_name_changes", "new_name"),
                ("joongna_store_name_changes", "new_fingerprint"),
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
                ("fraud_store_status_snapshots", "idx_store_checked"),
                ("fraud_store_status_snapshots", "idx_status_checked"),
                ("fraud_store_status_snapshots", "idx_store_seq_checked"),
                ("fraud_store_activity_snapshots", "idx_store_checked"),
                ("fraud_store_activity_snapshots", "idx_checked_at"),
                ("fraud_store_activity_snapshots", "idx_store_seq_observed"),
                ("fraud_training_label_candidates", "uq_product_id"),
                ("fraud_training_label_candidates", "idx_store_id"),
                ("fraud_training_label_candidates", "idx_label"),
                ("fraud_training_label_candidates", "idx_listing_sort_date"),
                ("joongna_store_name_changes", "idx_store_name_changes_store_seq"),
                ("joongna_store_name_changes", "idx_store_name_changes_changed_at"),
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
