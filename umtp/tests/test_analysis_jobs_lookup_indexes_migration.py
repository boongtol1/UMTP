import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import get_connection  # noqa: E402


CREATE_ANALYSIS_JOBS_SQL_PATH = os.path.join(PROJECT_ROOT, "sql", "create_analysis_jobs.sql")
MIGRATION_SQL_PATH = os.path.join(PROJECT_ROOT, "sql", "migrate_analysis_jobs_lookup_indexes.sql")


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


class AnalysisJobsLookupIndexesMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            connection = get_connection()
        except Exception as exc:  # pragma: no cover
            raise unittest.SkipTest(f"MySQL not available: {exc}") from exc
        else:
            connection.close()

    def test_migration_adds_lookup_indexes(self):
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            _execute_sql_script(connection, CREATE_ANALYSIS_JOBS_SQL_PATH)
            _execute_sql_script(connection, MIGRATION_SQL_PATH)
            _execute_sql_script(connection, MIGRATION_SQL_PATH)

            expected_indexes = [
                ("idx_analysis_jobs_user_source_keyword_created_at", "user_id,source,search_keyword,created_at"),
                (
                    "idx_analysis_jobs_user_source_keyword_product_created_at",
                    "user_id,source,search_keyword,product_id,created_at",
                ),
            ]

            for index_name, expected_columns in expected_indexes:
                cursor.execute(
                    """
                    SELECT GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',') AS column_list
                    FROM information_schema.statistics
                    WHERE table_schema = DATABASE()
                      AND table_name = 'analysis_jobs'
                      AND index_name = %s
                    """,
                    (index_name,),
                )
                row = cursor.fetchone() or {}
                self.assertEqual((row.get("column_list") or ""), expected_columns, f"invalid {index_name}")
        finally:
            cursor.close()
            connection.close()


if __name__ == "__main__":
    unittest.main()
