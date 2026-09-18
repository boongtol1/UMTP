"""Fill missing search-result bodies without creating analysis jobs or alerts."""

import argparse
import json
import os
import time
from collections import deque
from contextlib import suppress
from datetime import datetime, timezone

try:
    from src.db import get_connection
    from src.listing_page_parser import extract_listing_body_text, fetch_html
    from src.search_result_enrichment import fill_missing_search_result_bodies
except ModuleNotFoundError:
    from db import get_connection
    from listing_page_parser import extract_listing_body_text, fetch_html
    from search_result_enrichment import fill_missing_search_result_bodies


MISSING_BODY_SQL = "(sr.body_text IS NULL OR sr.body_text NOT REGEXP '[^[:space:]]')"
DEFAULT_BATCH_SIZE = 100


def _close(connection, cursor):
    if cursor is not None:
        with suppress(Exception):
            cursor.close()
    if connection is not None:
        with suppress(Exception):
            connection.close()


def _row_dict(row, keys):
    return dict(row) if isinstance(row, dict) else dict(zip(keys, row))


def find_missing_body_candidates(cursor, *, limit=None, product_id=None, after=None):
    """One row per product, newest first; keyset pagination survives filled rows."""
    predicates = ["sq.source = 'joongna'", MISSING_BODY_SQL]
    params = []
    if product_id is not None:
        predicates.append("sr.product_id = %s")
        params.append(str(product_id))
    having = ""
    if after is not None:
        having = """
            HAVING MAX(sr.fetched_at) < %s
                OR (MAX(sr.fetched_at) = %s AND MAX(sr.id) < %s)
        """
        params.extend((after[0], after[0], after[1]))
    limit_sql = ""
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be positive")
        limit_sql = "LIMIT %s"
        params.append(int(limit))
    cursor.execute(
        f"""
        SELECT sr.product_id, MAX(sr.fetched_at) AS latest_fetched_at,
               MAX(sr.id) AS latest_id, COUNT(*) AS missing_rows
        FROM search_results sr
        INNER JOIN search_queries sq ON sq.id = sr.search_query_id
        WHERE {' AND '.join(predicates)}
        GROUP BY sr.product_id
        {having}
        ORDER BY MAX(sr.fetched_at) DESC, MAX(sr.id) DESC
        {limit_sql}
        """,
        tuple(params),
    )
    keys = ("product_id", "latest_fetched_at", "latest_id", "missing_rows")
    return [_row_dict(row, keys) for row in cursor.fetchall() or []]


def _load_donor(cursor, product_id):
    cursor.execute(
        """
        SELECT body_text, body_fetched_at
        FROM search_results
        WHERE product_id = %s
          AND body_text REGEXP '[^[:space:]]'
        ORDER BY body_fetched_at DESC, fetched_at DESC, id DESC
        LIMIT 1
        """,
        (str(product_id),),
    )
    row = cursor.fetchone()
    return _row_dict(row, ("body_text", "body_fetched_at")) if row else None


def _http_status(exc):
    visited = set()
    while exc is not None and id(exc) not in visited:
        visited.add(id(exc))
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if isinstance(status, int):
            return status
        exc = exc.__cause__ or exc.__context__
    return None


def backfill_product(product_id):
    """Reuse stored text first, otherwise fetch only the body from its detail page."""
    connection = None
    cursor = None
    result = {"product_id": str(product_id), "processed": 1, "updated_rows": 0}
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            f"SELECT 1 FROM search_results sr WHERE sr.product_id = %s AND {MISSING_BODY_SQL} LIMIT 1",
            (str(product_id),),
        )
        if cursor.fetchone() is None:
            return {**result, "reason": "already_filled", "skipped": 1}
        donor = _load_donor(cursor, product_id)
        if donor:
            body_text = donor["body_text"]
            body_fetched_at = donor["body_fetched_at"]
            source = "stored"
        else:
            cursor.execute(
                """
                SELECT url FROM search_results
                WHERE product_id = %s AND NULLIF(TRIM(url), '') IS NOT NULL
                ORDER BY fetched_at DESC, id DESC LIMIT 1
                """,
                (str(product_id),),
            )
            row = cursor.fetchone()
            url = (row.get("url") if isinstance(row, dict) else row[0]) if row else None
            url = url or f"https://web.joongna.com/product/{product_id}"
            # Release the read transaction before a potentially slow HTTP request.
            connection.rollback()
            body_text = extract_listing_body_text(fetch_html(url))
            if not isinstance(body_text, str) or not body_text.strip():
                return {**result, "failed": 1, "reason": "empty_body"}
            cursor.execute("SELECT CURRENT_TIMESTAMP")
            timestamp_row = cursor.fetchone()
            body_fetched_at = (
                next(iter(timestamp_row.values()))
                if isinstance(timestamp_row, dict)
                else timestamp_row[0]
            )
            source = "detail"
        updated_rows = fill_missing_search_result_bodies(
            cursor, product_id, body_text, body_fetched_at=body_fetched_at
        )
        connection.commit()
        return {**result, "updated_rows": updated_rows, "source": source}
    except Exception as exc:
        if connection is not None:
            with suppress(Exception):
                connection.rollback()
        # Never include fetched page contents, listing bodies, or DB credentials.
        return {
            **result,
            "failed": 1,
            "reason": type(exc).__name__,
            "http_status": _http_status(exc),
        }
    finally:
        _close(connection, cursor)


class BodyBackfillState:
    """Process-local cooldowns and bounded batches for the long-running worker."""

    def __init__(self, *, batch_size=DEFAULT_BATCH_SIZE):
        self.batch_size = batch_size
        self.pending = deque()
        self.after = None
        self.retry = {}
        self.next_scan_at = 0.0
        self.next_head_scan_at = 0.0

    def record_result(self, result, *, now):
        product_id = str(result["product_id"])
        if not result.get("failed"):
            self.retry.pop(product_id, None)
            return
        previous = self.retry.get(product_id, (0, 0))
        attempts = previous[1] + 1
        if result.get("http_status") in (404, 410):
            delay = 7 * 24 * 60 * 60
        elif result.get("reason") == "empty_body":
            delay = 6 * 60 * 60
        else:
            delay = min(6 * 60 * 60, 5 * 60 * (2 ** min(attempts - 1, 7)))
        self.retry[product_id] = (now + delay, attempts)

    def _enqueue(self, candidates, *, now, head=False):
        queued = {str(row["product_id"]) for row in self.pending}
        accepted = [
            row for row in candidates
            if str(row["product_id"]) not in queued
            and self.retry.get(str(row["product_id"]), (0, 0))[0] <= now
        ]
        if head:
            self.pending.extendleft(reversed(accepted))
        else:
            self.pending.extend(accepted)

    def next_candidate(self, cursor, *, now):
        if now < self.next_scan_at and not self.pending:
            return None
        # Keep newly collected listings responsive while also progressing through
        # older results. Failed head rows cannot hide candidates in later batches.
        if self.after is not None and now >= self.next_head_scan_at:
            self._enqueue(
                find_missing_body_candidates(cursor, limit=min(20, self.batch_size)),
                now=now, head=True,
            )
            self.next_head_scan_at = now + 60
        for _ in range(2):
            while self.pending:
                candidate = self.pending.popleft()
                if self.retry.get(str(candidate["product_id"]), (0, 0))[0] <= now:
                    return candidate
            rows = find_missing_body_candidates(cursor, limit=self.batch_size, after=self.after)
            if not rows:
                self.after = None
                self.next_scan_at = now + 30
                return None
            self.after = (rows[-1]["latest_fetched_at"], rows[-1]["latest_id"])
            self.next_head_scan_at = max(self.next_head_scan_at, now + 60)
            self._enqueue(rows, now=now)
        return self.pending.popleft() if self.pending else None


_WORKER_STATE = BodyBackfillState()


def process_next_search_body_backfill(*, state=None):
    state = state if state is not None else _WORKER_STATE
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        candidate = state.next_candidate(cursor, now=time.monotonic())
    except Exception as exc:
        return {"processed": 0, "failed": 1, "reason": type(exc).__name__}
    finally:
        _close(connection, cursor)
    if candidate is None:
        return {"processed": 0, "reason": "no_due_missing_body"}
    result = backfill_product(candidate["product_id"])
    state.record_result(result, now=time.monotonic())
    return result


def _write_report(report_path, report):
    if not report_path:
        return
    path = os.path.abspath(report_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary_path = path + ".tmp"
    with open(temporary_path, "w", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
        output.write("\n")
    os.replace(temporary_path, path)


def run_backfill(*, limit=None, dry_run=False, product_id=None, report_path=None):
    """Take one snapshot and attempt every product once, continuing after failures."""
    if limit is not None and limit < 1:
        raise ValueError("limit must be positive")
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        candidates = find_missing_body_candidates(cursor, limit=limit, product_id=product_id)
    finally:
        _close(connection, cursor)
    report = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "candidate_products": len(candidates),
        "candidate_missing_rows": sum(int(row["missing_rows"]) for row in candidates),
        "processed_products": 0,
        "stored_products": 0,
        "detail_products": 0,
        "skipped_products": 0,
        "updated_rows": 0,
        "failures": [],
        "completed": False,
    }
    print(
        f"[search_body_backfill] candidates={report['candidate_products']} "
        f"missing_rows={report['candidate_missing_rows']} dry_run={dry_run}",
        flush=True,
    )
    _write_report(report_path, report)
    try:
        if not dry_run:
            for candidate in candidates:
                result = backfill_product(candidate["product_id"])
                report["processed_products"] += 1
                report["updated_rows"] += result.get("updated_rows", 0)
                source = result.get("source")
                if source in ("stored", "detail"):
                    report[f"{source}_products"] += 1
                if result.get("skipped"):
                    report["skipped_products"] += 1
                if result.get("failed"):
                    report["failures"].append({
                        key: result[key] for key in ("product_id", "reason", "http_status")
                        if key in result
                    })
                print(
                    f"[search_body_backfill] {report['processed_products']}/{len(candidates)} "
                    + json.dumps(result, ensure_ascii=False), flush=True,
                )
                if report["processed_products"] % 25 == 0:
                    _write_report(report_path, report)
        report["completed"] = True
    finally:
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        _write_report(report_path, report)
    return report


def main():
    parser = argparse.ArgumentParser(description="Fill empty search_results bodies only; no analysis jobs or alerts")
    parser.add_argument("--limit", type=int, help="Maximum distinct products to attempt")
    parser.add_argument("--product-id", help="Only fill missing rows for this product")
    parser.add_argument("--dry-run", action="store_true", help="Count candidates without fetching or writing")
    parser.add_argument("--report", help="Write a JSON progress/failure report (no listing bodies)")
    args = parser.parse_args()
    report = run_backfill(
        limit=args.limit, product_id=args.product_id, dry_run=args.dry_run,
        report_path=args.report,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
