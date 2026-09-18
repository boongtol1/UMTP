"""Opt-in MySQL migration test; all writes target session-local temporary tables."""

import json
import os
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.db import get_connection  # noqa: E402


@unittest.skipUnless(
    os.getenv("UMTP_RUN_MYSQL_BACKFILL_TESTS") == "1",
    "Set UMTP_RUN_MYSQL_BACKFILL_TESTS=1 to test with isolated MySQL temporary tables",
)
class UserSettingsSaveLogsBackfillTest(unittest.TestCase):
    def test_backfill_repairs_only_confirmed_successes_and_is_idempotent(self):
        sql = (PROJECT_ROOT / "sql/migrate_user_settings_save_logs_watch_rule_id.sql").read_text()
        statements = [part.strip() for part in sql.split(";") if part.strip()]
        self.assertEqual(len(statements), 3)
        # Never execute USE: stay in the connection's database and shadow both
        # production table names with temporary tables before any data writes.
        self.assertEqual(statements[0], "USE UMTP_RB")
        update_sql = statements[1]
        uncommented_update = "\n".join(
            line for line in update_sql.splitlines() if not line.lstrip().startswith("--")
        ).strip()
        self.assertTrue(uncommented_update.startswith("UPDATE user_settings_save_logs AS save_log\n"))
        self.assertEqual(statements[2], "SELECT ROW_COUNT() AS repaired_save_log_count")

        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT DATABASE()")
            initial_database = cursor.fetchone()[0]
            self.assertIsNotNone(initial_database)
            cursor.execute("""
                CREATE TEMPORARY TABLE user_fair_prices (
                    id BIGINT NOT NULL PRIMARY KEY,
                    user_id VARCHAR(64) NOT NULL,
                    product_type VARCHAR(64) NOT NULL,
                    chip VARCHAR(32) NOT NULL,
                    screen_inch INT NOT NULL,
                    ram_gb INT NOT NULL,
                    ssd_gb INT NOT NULL,
                    created_at DATETIME NOT NULL,
                    UNIQUE KEY spec_key (user_id, product_type, chip, screen_inch, ram_gb, ssd_gb)
                ) ENGINE=InnoDB
            """)
            cursor.execute("""
                CREATE TEMPORARY TABLE user_settings_save_logs (
                    id BIGINT NOT NULL PRIMARY KEY,
                    user_id VARCHAR(64) NOT NULL,
                    watch_rule_id BIGINT NULL,
                    action_type VARCHAR(64) NOT NULL,
                    request_json JSON NULL,
                    response_json JSON NULL,
                    success BOOLEAN NOT NULL,
                    created_at DATETIME NOT NULL
                ) ENGINE=InnoDB
            """)
            specs = (
                ("MacBook Pro", "M1 Pro", 14, 16, 512),
                ("MacBook Neo", "A18 Pro", 13, 8, 256),
                ("iMac", "M1", 24, 8, 256),
                ("Mac Studio", "M1 Max", 0, 32, 512),
                ("MacBook Air", "M1", 13, 8, 256),
            )
            fields = ("product_type", "chip", "screen_inch", "ram_gb", "ssd_gb")
            for rule_id, spec in enumerate(specs, 101):
                cursor.execute("""
                    INSERT INTO user_fair_prices
                        (id, user_id, product_type, chip, screen_inch, ram_gb, ssd_gb, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (rule_id, "owner", *spec, "2026-09-18 10:00:00"))

            cases = []

            def add_case(label, *, spec=specs[1], request_override=None,
                         omitted_fields=(), response_json='{"item":{"id":null},"original":true}',
                         user_id="owner", action="create_watch_rule", success=1,
                         watch_rule_id=None, created_at="2026-09-18 11:00:00", expected_id=None):
                request = dict(zip(fields, spec))
                request.update(request_override or {})
                for field in omitted_fields:
                    request.pop(field)
                log_id = len(cases) + 1
                cursor.execute("""
                    INSERT INTO user_settings_save_logs
                        (id, user_id, watch_rule_id, action_type, request_json,
                         response_json, success, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (log_id, user_id, watch_rule_id, action, json.dumps(request),
                      response_json, success, created_at))
                cases.append((log_id, label, expected_id))

            for rule_id, spec in enumerate(specs[:4], 101):
                add_case(f"first save {spec[0]}", spec=spec, expected_id=rule_id)
            add_case("update action with matching response ID", action="update_watch_rule",
                     response_json='{"item":{"id":102},"original":true}', expected_id=102)
            add_case("absent response ID", response_json='{"item":{"chip":"A18 Pro"}}', expected_id=102)
            add_case("SQL NULL response", response_json=None, expected_id=102)
            add_case("failed save", success=0)
            add_case("existing nonnull ID", watch_rule_id=999, expected_id=999)
            add_case("different user", user_id="other-owner")
            add_case("different specification", request_override={"ssd_gb": 512})
            add_case("unsupported Air", spec=specs[4])
            add_case("unrelated action", action="bulk_update")
            add_case("rule created after log", created_at="2026-09-18 09:00:00")
            add_case("conflicting response ID", response_json='{"item":{"id":999}}')
            for field in fields:
                add_case(f"missing {field}", omitted_fields=(field,))
            for field, malformed in (
                ("screen_inch", "13"), ("screen_inch", 13.0), ("screen_inch", True),
                ("screen_inch", "13garbage"), ("screen_inch", None),
                ("ram_gb", "8"), ("ram_gb", [8]), ("ssd_gb", "256"),
                ("ssd_gb", {"capacity": 256}),
            ):
                add_case(f"malformed {field}: {malformed!r}", request_override={field: malformed})

            read_rows_sql = """
                SELECT id, user_id, watch_rule_id, action_type, request_json,
                       response_json, success, created_at
                FROM user_settings_save_logs ORDER BY id
            """
            cursor.execute(read_rows_sql)
            before = {row[0]: row for row in cursor.fetchall()}
            cursor.execute(update_sql)
            cursor.execute(statements[2])
            self.assertEqual(cursor.fetchone()[0], 7)
            cursor.execute(read_rows_sql)
            after = {row[0]: row for row in cursor.fetchall()}
            self.assertEqual(set(before), set(after))
            for log_id, label, expected_id in cases:
                with self.subTest(case=label):
                    expected = list(before[log_id])
                    expected[2] = expected_id
                    # Includes both original JSON payloads, timestamps, and flags.
                    self.assertEqual(after[log_id], tuple(expected))

            cursor.execute(update_sql)
            cursor.execute(statements[2])
            self.assertEqual(cursor.fetchone()[0], 0)
            cursor.execute(read_rows_sql)
            self.assertEqual({row[0]: row for row in cursor.fetchall()}, after)
            cursor.execute("SELECT DATABASE()")
            self.assertEqual(cursor.fetchone()[0], initial_database)
        finally:
            cursor.close()
            # Closing the session discards temporary tables. Never DROP/DELETE
            # by a production table name, even when setup or assertions fail.
            connection.close()


if __name__ == "__main__":
    unittest.main()
