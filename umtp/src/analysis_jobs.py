import hashlib
import json
from contextlib import contextmanager
from datetime import datetime, timezone

from src.db import get_connection


DUPLICATE_ENTRY_ERROR_CODE = 1062


def _normalize_optional_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    cleaned = str(value).strip()
    return cleaned or None


def _normalize_required_text(value, field_name):
    normalized = _normalize_optional_text(value)
    if normalized is None:
        raise ValueError(f"invalid_{field_name}")
    return normalized


def _normalize_optional_int(value, field_name):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid_{field_name}") from exc


def _normalize_limit(limit):
    normalized = _normalize_optional_int(limit, "limit")
    if normalized is None:
        return 20
    if normalized <= 0:
        raise ValueError("invalid_limit")
    return min(normalized, 200)


def _normalize_job_id(job_id):
    normalized = _normalize_optional_int(job_id, "job_id")
    if normalized is None or normalized <= 0:
        raise ValueError("invalid_job_id")
    return normalized


def _normalize_within_seconds(within_seconds):
    normalized = _normalize_optional_int(within_seconds, "within_seconds")
    if normalized is None or normalized <= 0:
        return 300
    return normalized


def _normalize_product_id(product_id):
    return _normalize_optional_text(product_id)


def _normalize_optional_watch_rule_id(watch_rule_id):
    normalized = _normalize_optional_int(watch_rule_id, "watch_rule_id")
    if normalized is None:
        return None
    if normalized <= 0:
        raise ValueError("invalid_watch_rule_id")
    return normalized


def _normalize_sort_date_for_db(sort_date):
    normalized = _normalize_optional_text(sort_date)
    if normalized is None:
        return None

    candidate = normalized.replace("Z", "+00:00")
    parsed = None
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        pass

    if parsed is None:
        for date_format in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
        ):
            try:
                parsed = datetime.strptime(normalized, date_format)
                break
            except ValueError:
                continue

    if parsed is None:
        return None

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)

    return parsed.replace(microsecond=0)


def _normalize_status(status):
    normalized = _normalize_required_text(status, "status")
    return normalized.lower()


def _normalize_change_fingerprint(value):
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return ""
    return normalized[:64]


def _build_change_fingerprint(
    *,
    trigger_reason,
    sort_date,
    title,
    price_krw,
    url,
    refresh_key=None,
):
    payload = {
        "trigger_reason": _normalize_optional_text(trigger_reason) or "",
        "sort_date": str(sort_date) if sort_date is not None else "",
        "title": _normalize_optional_text(title) or "",
        "price_krw": _normalize_optional_int(price_krw, "price_krw"),
        "url": _normalize_optional_text(url) or "",
        "refresh_key": _normalize_optional_text(refresh_key) or "",
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _is_duplicate_entry_error(exc):
    error_code = getattr(exc, "errno", None)
    if error_code == DUPLICATE_ENTRY_ERROR_CODE:
        return True

    message = str(exc).lower()
    return "duplicate" in message and "entry" in message


def find_analysis_job_by_identity(
    user_id,
    watch_rule_id,
    product_id,
    sort_date=None,
    change_fingerprint=None,
    *,
    include_sort_date=True,
):
    normalized_user_id = _normalize_optional_text(user_id)
    normalized_watch_rule_id = _normalize_optional_watch_rule_id(watch_rule_id)
    normalized_product_id = _normalize_product_id(product_id)
    normalized_sort_date = _normalize_sort_date_for_db(sort_date)
    normalized_change_fingerprint = _normalize_change_fingerprint(change_fingerprint)

    if normalized_user_id is None or normalized_product_id is None:
        return None

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            if normalized_change_fingerprint:
                cursor.execute(
                    """
                    SELECT
                        id,
                        status,
                        created_at
                    FROM analysis_jobs
                    WHERE user_id = %s
                      AND (
                            (watch_rule_id IS NULL AND %s IS NULL)
                         OR watch_rule_id = %s
                      )
                      AND product_id = %s
                      AND change_fingerprint = %s
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (
                        normalized_user_id,
                        normalized_watch_rule_id,
                        normalized_watch_rule_id,
                        normalized_product_id,
                        normalized_change_fingerprint,
                    ),
                )
            elif include_sort_date:
                cursor.execute(
                    """
                    SELECT
                        id,
                        status,
                        created_at
                    FROM analysis_jobs
                    WHERE user_id = %s
                      AND (
                            (watch_rule_id IS NULL AND %s IS NULL)
                         OR watch_rule_id = %s
                      )
                      AND product_id = %s
                      AND (
                            (sort_date IS NULL AND %s IS NULL)
                         OR sort_date = %s
                      )
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (
                        normalized_user_id,
                        normalized_watch_rule_id,
                        normalized_watch_rule_id,
                        normalized_product_id,
                        normalized_sort_date,
                        normalized_sort_date,
                    ),
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        id,
                        status,
                        created_at
                    FROM analysis_jobs
                    WHERE user_id = %s
                      AND (
                            (watch_rule_id IS NULL AND %s IS NULL)
                         OR watch_rule_id = %s
                      )
                      AND product_id = %s
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (
                        normalized_user_id,
                        normalized_watch_rule_id,
                        normalized_watch_rule_id,
                        normalized_product_id,
                    ),
                )
        except Exception as exc:
            if "unknown column" not in str(exc).lower():
                raise
            cursor.execute(
                """
                SELECT
                    id,
                    status,
                    created_at
                FROM analysis_jobs
                WHERE user_id = %s
                  AND product_id = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (
                    normalized_user_id,
                    normalized_product_id,
                ),
            )
        return cursor.fetchone()
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def find_recent_duplicate_job(product_id, watch_rule_id, trigger_reason, within_seconds=300):
    normalized_product_id = _normalize_product_id(product_id)
    normalized_trigger_reason = _normalize_optional_text(trigger_reason)
    normalized_within_seconds = _normalize_within_seconds(within_seconds)

    if normalized_product_id is None:
        return None

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                id,
                status,
                created_at
            FROM analysis_jobs
            WHERE product_id = %s
              AND (
                    (trigger_reason IS NULL AND %s IS NULL)
                 OR trigger_reason = %s
              )
              AND status IN ('pending', 'processing', 'running', 'done')
              AND TIMESTAMPDIFF(SECOND, created_at, CURRENT_TIMESTAMP) <= %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (
                normalized_product_id,
                normalized_trigger_reason,
                normalized_trigger_reason,
                normalized_within_seconds,
            ),
        )
        return cursor.fetchone()
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def create_analysis_job(
    *,
    source="joongna",
    product_id=None,
    url,
    title=None,
    price_krw=None,
    search_keyword=None,
    user_id=None,
    watch_rule_id=None,
    sort_date=None,
    trigger_reason=None,
    change_fingerprint=None,
    refresh_key=None,
    dedupe_within_seconds=300,
):
    normalized_source = _normalize_required_text(source, "source")
    normalized_url = _normalize_required_text(url, "url")
    normalized_product_id = _normalize_product_id(product_id)
    normalized_title = _normalize_optional_text(title)
    normalized_price_krw = _normalize_optional_int(price_krw, "price_krw")
    normalized_search_keyword = _normalize_optional_text(search_keyword)
    normalized_user_id = _normalize_optional_text(user_id)
    normalized_watch_rule_id = _normalize_optional_watch_rule_id(watch_rule_id)
    normalized_sort_date = _normalize_sort_date_for_db(sort_date)
    normalized_trigger_reason = _normalize_optional_text(trigger_reason)
    normalized_change_fingerprint = _normalize_change_fingerprint(change_fingerprint)
    normalized_refresh_key = _normalize_optional_text(refresh_key)

    if not normalized_change_fingerprint:
        normalized_change_fingerprint = _build_change_fingerprint(
            trigger_reason=normalized_trigger_reason,
            sort_date=normalized_sort_date,
            title=normalized_title,
            price_krw=normalized_price_krw,
            url=normalized_url,
            refresh_key=normalized_refresh_key,
        )

    identity_job = find_analysis_job_by_identity(
        normalized_user_id,
        normalized_watch_rule_id,
        normalized_product_id,
        normalized_sort_date,
        normalized_change_fingerprint,
    )
    if identity_job is not None:
        return {
            "ok": True,
            "created": False,
            "reason": "duplicate_identity_job",
            "job_id": int(identity_job.get("id")),
            "status": identity_job.get("status"),
        }

    # user_id/product_id가 없는 구버전 입력도 안전 처리
    if normalized_user_id is None or normalized_product_id is None:
        existing = find_recent_duplicate_job(
            normalized_product_id,
            normalized_watch_rule_id,
            normalized_trigger_reason,
            within_seconds=dedupe_within_seconds,
        )
        if existing is not None:
            return {
                "ok": True,
                "created": False,
                "reason": "duplicate_recent_job",
                "job_id": int(existing.get("id")),
                "status": existing.get("status"),
            }

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO analysis_jobs (
                    source,
                    product_id,
                    url,
                    title,
                    price_krw,
                    search_keyword,
                    user_id,
                    watch_rule_id,
                    sort_date,
                    trigger_reason,
                    change_fingerprint,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
                """,
                (
                    normalized_source,
                    normalized_product_id,
                    normalized_url,
                    normalized_title,
                    normalized_price_krw,
                    normalized_search_keyword,
                    normalized_user_id,
                    normalized_watch_rule_id,
                    normalized_sort_date,
                    normalized_trigger_reason,
                    normalized_change_fingerprint,
                ),
            )
        except Exception as exc:
            lowered_exc = str(exc).lower()
            if "unknown column" in lowered_exc:
                try:
                    cursor.execute(
                        """
                        INSERT INTO analysis_jobs (
                            source,
                            product_id,
                            url,
                            title,
                            price_krw,
                            search_keyword,
                            user_id,
                            watch_rule_id,
                            change_fingerprint,
                            trigger_reason,
                            status
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
                        """,
                        (
                            normalized_source,
                            normalized_product_id,
                            normalized_url,
                            normalized_title,
                            normalized_price_krw,
                            normalized_search_keyword,
                            normalized_user_id,
                            normalized_watch_rule_id,
                            normalized_change_fingerprint,
                            normalized_trigger_reason,
                        ),
                    )
                except Exception as second_exc:
                    lowered_second_exc = str(second_exc).lower()
                    if "unknown column" not in lowered_second_exc:
                        raise
                    try:
                        cursor.execute(
                            """
                            INSERT INTO analysis_jobs (
                                source,
                                product_id,
                                url,
                                title,
                                price_krw,
                                search_keyword,
                                user_id,
                                change_fingerprint,
                                trigger_reason,
                                status
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
                            """,
                            (
                                normalized_source,
                                normalized_product_id,
                                normalized_url,
                                normalized_title,
                                normalized_price_krw,
                                normalized_search_keyword,
                                normalized_user_id,
                                normalized_change_fingerprint,
                                normalized_trigger_reason,
                            ),
                        )
                    except Exception as third_exc:
                        lowered_third_exc = str(third_exc).lower()
                        if "unknown column" not in lowered_third_exc:
                            raise
                        cursor.execute(
                            """
                            INSERT INTO analysis_jobs (
                                source,
                                product_id,
                                url,
                                title,
                                price_krw,
                                search_keyword,
                                user_id,
                                trigger_reason,
                                status
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending')
                            """,
                            (
                                normalized_source,
                                normalized_product_id,
                                normalized_url,
                                normalized_title,
                                normalized_price_krw,
                                normalized_search_keyword,
                                normalized_user_id,
                                normalized_trigger_reason,
                            ),
                        )
                # Unknown-column fallback succeeded; continue normal flow.
                pass
            elif _is_duplicate_entry_error(exc):
                duplicate_job = find_analysis_job_by_identity(
                    normalized_user_id,
                    normalized_watch_rule_id,
                    normalized_product_id,
                    normalized_sort_date,
                    normalized_change_fingerprint,
                )
                if duplicate_job is None:
                    duplicate_job = find_analysis_job_by_identity(
                        normalized_user_id,
                        normalized_watch_rule_id,
                        normalized_product_id,
                        change_fingerprint=normalized_change_fingerprint,
                        include_sort_date=False,
                    )
                if duplicate_job is not None:
                    return {
                        "ok": True,
                        "created": False,
                        "reason": "duplicate_identity_job",
                        "job_id": int(duplicate_job.get("id")),
                        "status": duplicate_job.get("status"),
                    }
                raise
            else:
                raise

        job_id = int(cursor.lastrowid)
        connection.commit()
        return {
            "ok": True,
            "created": True,
            "job_id": job_id,
            "status": "pending",
        }
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def create_analysis_jobs_for_rules(product, watch_rules, trigger_reason):
    if not isinstance(product, dict):
        raise ValueError("invalid_product")

    normalized_watch_rules = watch_rules if isinstance(watch_rules, list) else []
    created_jobs = []
    skipped_jobs = []

    if not normalized_watch_rules:
        result = create_analysis_job(
            source="joongna",
            product_id=product.get("product_id"),
            url=product.get("product_url"),
            title=product.get("title"),
            price_krw=product.get("price"),
            search_keyword=product.get("search_keyword") or product.get("search_word"),
            user_id=product.get("user_id"),
            sort_date=product.get("sort_date"),
            trigger_reason=trigger_reason,
            change_fingerprint=product.get("change_fingerprint"),
            refresh_key=product.get("refresh_key"),
        )
        if result.get("created"):
            created_jobs.append(result)
        else:
            skipped_jobs.append(result)

        return {
            "ok": True,
            "created_jobs": created_jobs,
            "skipped_jobs": skipped_jobs,
        }

    unique_targets = []
    seen_target_keys = set()
    for watch_rule in normalized_watch_rules:
        user_id = None
        watch_rule_id = None
        if isinstance(watch_rule, dict):
            user_id = watch_rule.get("user_id")
            watch_rule_id = watch_rule.get("setting_id")
            if watch_rule_id is None:
                watch_rule_id = watch_rule.get("rule_id")
            nested_rule = watch_rule.get("watch_rule")
            if isinstance(nested_rule, dict):
                user_id = nested_rule.get("user_id") or user_id
                if watch_rule_id is None:
                    watch_rule_id = nested_rule.get("id")

        normalized_user_id = _normalize_optional_text(user_id)
        if normalized_user_id is None:
            continue
        try:
            normalized_watch_rule_id = _normalize_optional_watch_rule_id(watch_rule_id)
        except ValueError:
            continue

        target_key = (normalized_user_id, normalized_watch_rule_id)
        if target_key in seen_target_keys:
            continue
        seen_target_keys.add(target_key)
        unique_targets.append(
            {
                "user_id": normalized_user_id,
                "watch_rule_id": normalized_watch_rule_id,
            }
        )

    return _create_analysis_job_group(product, unique_targets, trigger_reason)


def _create_analysis_job_group(product, targets, trigger_reason):
    """Publish every recipient of one observation in a single transaction.

    A worker must never see just the first user's jobs while the poller is still
    inserting the others. Preserve the existing per-rule identities and rows.
    """
    result = {"ok": True, "created_jobs": [], "skipped_jobs": []}
    if not targets:
        return result
    source = _normalize_optional_text(product.get("source")) or "joongna"
    product_id = _normalize_required_text(product.get("product_id"), "product_id")
    url = _normalize_required_text(product.get("product_url"), "url")
    title = _normalize_optional_text(product.get("title"))
    price = _normalize_optional_int(product.get("price"), "price_krw")
    keyword = _normalize_optional_text(product.get("search_keyword") or product.get("search_word"))
    sort_date = _normalize_sort_date_for_db(product.get("sort_date"))
    reason = _normalize_optional_text(trigger_reason)
    fingerprint = _normalize_change_fingerprint(product.get("change_fingerprint"))
    if not fingerprint:
        fingerprint = _build_change_fingerprint(
            trigger_reason=reason, sort_date=sort_date, title=title,
            price_krw=price, url=url, refresh_key=product.get("refresh_key"),
        )
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        lookup = """
            SELECT id, user_id, watch_rule_id, status FROM analysis_jobs
            WHERE source = %s AND product_id = %s AND change_fingerprint = %s
        """
        scope = (source, product_id, fingerprint)
        cursor.execute(lookup, scope)
        existing = {(row["user_id"], row["watch_rule_id"]): row for row in cursor.fetchall()}
        values = [
            (source, product_id, url, title, price, keyword, target["user_id"],
             target["watch_rule_id"], sort_date, reason, fingerprint)
            for target in targets
            if (target["user_id"], target["watch_rule_id"]) not in existing
        ]
        for offset in range(0, len(values), 500):
            cursor.executemany(
                """
                INSERT INTO analysis_jobs (
                    source, product_id, url, title, price_krw, search_keyword,
                    user_id, watch_rule_id, sort_date, trigger_reason,
                    change_fingerprint, status
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending')
                ON DUPLICATE KEY UPDATE id = id
                """, values[offset:offset + 500],
            )
        # Locking read also sees a concurrently committed duplicate under RR.
        cursor.execute(lookup + " FOR UPDATE", scope)
        rows = {(row["user_id"], row["watch_rule_id"]): row for row in cursor.fetchall()}
        for target in targets:
            key = (target["user_id"], target["watch_rule_id"])
            row = rows[key]
            created = key not in existing
            item = {"ok": True, "created": created, "job_id": int(row["id"]), "status": row["status"]}
            if not created:
                item["reason"] = "duplicate_identity_job"
            result["created_jobs" if created else "skipped_jobs"].append(item)
        connection.commit()
        return result
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def _analysis_product_lock_name(job):
    identity = [
        _normalize_optional_text(job.get("source")) or "joongna",
        _normalize_optional_text(job.get("product_id")) or _normalize_optional_text(job.get("url")),
    ]
    digest = hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode("utf-8")).hexdigest()
    return "umtp:analysis:" + digest[:48]


@contextmanager
def claim_pending_analysis_group():
    """Own one complete listing event until the caller finishes processing it.

    The MySQL named lock is held on this connection across the caller's work.
    It serializes revisions of a product, but allows other workers to process
    other products. A crashed owner's connection releases the lock; the next
    owner can safely reclaim its running rows without a time-based lease race.
    All analysis workers must use this protocol (stop old workers at rollout).
    """
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    lock_name = None
    claimed_ids = []
    try:
        cursor.execute(
            """
            SELECT aj.* FROM analysis_jobs aj
            JOIN (
                SELECT MIN(id) AS id FROM analysis_jobs
                WHERE status IN ('pending', 'running')
                GROUP BY source, product_id
                ORDER BY MIN(id) LIMIT 200
            ) candidates ON candidates.id = aj.id
            ORDER BY aj.id
            """
        )
        candidates = cursor.fetchall() or []
        connection.commit()
        jobs = []
        for candidate in candidates:
            name = _analysis_product_lock_name(candidate)
            cursor.execute("SELECT GET_LOCK(%s, 0) AS acquired", (name,))
            acquired = cursor.fetchone() or {}
            if acquired.get("acquired") != 1:
                continue
            lock_name = name
            # FOR UPDATE is a current read, including recovery after a crash.
            cursor.execute(
                """
                SELECT * FROM analysis_jobs
                WHERE source = %s AND product_id <=> %s
                  AND change_fingerprint = %s
                  AND status IN ('pending', 'running')
                ORDER BY id FOR UPDATE
                """,
                (candidate["source"], candidate.get("product_id"), candidate["change_fingerprint"]),
            )
            jobs = cursor.fetchall() or []
            if jobs:
                claimed_ids = [int(job["id"]) for job in jobs]
                for offset in range(0, len(claimed_ids), 500):
                    ids = claimed_ids[offset:offset + 500]
                    placeholders = ",".join(["%s"] * len(ids))
                    cursor.execute(
                        f"""UPDATE analysis_jobs SET status = 'running',
                            attempts = COALESCE(attempts, 0) + 1,
                            started_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                            WHERE id IN ({placeholders})""", tuple(ids),
                    )
                connection.commit()
                break
            connection.commit()
            cursor.execute("SELECT RELEASE_LOCK(%s)", (name,))
            cursor.fetchone()
            lock_name = None
        yield jobs
    finally:
        try:
            connection.rollback()
            if claimed_ids:
                # Aborted/uncaught processing becomes retryable. Committed done
                # or failed jobs are never reset and therefore never replayed.
                for offset in range(0, len(claimed_ids), 500):
                    ids = claimed_ids[offset:offset + 500]
                    placeholders = ",".join(["%s"] * len(ids))
                    cursor.execute(
                        f"""UPDATE analysis_jobs SET status = 'pending',
                            updated_at = CURRENT_TIMESTAMP
                            WHERE id IN ({placeholders}) AND status = 'running'""", tuple(ids),
                    )
                connection.commit()
        finally:
            try:
                if lock_name is not None:
                    cursor.execute("SELECT RELEASE_LOCK(%s)", (lock_name,))
                    cursor.fetchone()
            finally:
                cursor.close()
                connection.close()


def get_pending_analysis_jobs(limit=20):
    normalized_limit = _normalize_limit(limit)

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT
                    id,
                    source,
                    product_id,
                    url,
                    title,
                    price_krw,
                    search_keyword,
                    user_id,
                    watch_rule_id,
                    sort_date,
                    trigger_reason,
                    status,
                    error_message,
                    attempts,
                    created_at,
                    started_at,
                    processed_at,
                    updated_at
                FROM analysis_jobs
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT %s
                """,
                (normalized_limit,),
            )
        except Exception as exc:
            if "unknown column" not in str(exc).lower():
                raise
            cursor.execute(
                """
                SELECT
                    id,
                    source,
                    product_id,
                    url,
                    title,
                    price_krw,
                    search_keyword,
                    user_id,
                    NULL AS watch_rule_id,
                    NULL AS sort_date,
                    trigger_reason,
                    status,
                    error_message,
                    attempts,
                    created_at,
                    started_at,
                    processed_at,
                    updated_at
                FROM analysis_jobs
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT %s
                """,
                (normalized_limit,),
            )
        return cursor.fetchall() or []
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def mark_analysis_job_started(job_id):
    normalized_job_id = _normalize_job_id(job_id)

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE analysis_jobs
            SET
                status = 'running',
                attempts = COALESCE(attempts, 0) + 1,
                started_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
              AND status = 'pending'
            """,
            (normalized_job_id,),
        )
        connection.commit()

        return cursor.rowcount == 1
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def mark_analysis_job_done(job_id):
    normalized_job_id = _normalize_job_id(job_id)

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE analysis_jobs
            SET
                status = 'done',
                processed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (normalized_job_id,),
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def mark_analysis_job_failed(job_id, error_message):
    normalized_job_id = _normalize_job_id(job_id)
    normalized_error_message = _normalize_required_text(error_message, "error_message")

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE analysis_jobs
            SET
                status = 'failed',
                error_message = %s,
                processed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (normalized_error_message, normalized_job_id),
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def get_analysis_job(job_id):
    normalized_job_id = _normalize_job_id(job_id)

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT
                    id,
                    source,
                    product_id,
                    url,
                    title,
                    price_krw,
                    search_keyword,
                    user_id,
                    watch_rule_id,
                    sort_date,
                    trigger_reason,
                    status,
                    error_message,
                    attempts,
                    created_at,
                    started_at,
                    processed_at,
                    updated_at
                FROM analysis_jobs
                WHERE id = %s
                LIMIT 1
                """,
                (normalized_job_id,),
            )
        except Exception as exc:
            if "unknown column" not in str(exc).lower():
                raise
            cursor.execute(
                """
                SELECT
                    id,
                    source,
                    product_id,
                    url,
                    title,
                    price_krw,
                    search_keyword,
                    user_id,
                    NULL AS watch_rule_id,
                    NULL AS sort_date,
                    trigger_reason,
                    status,
                    error_message,
                    attempts,
                    created_at,
                    started_at,
                    processed_at,
                    updated_at
                FROM analysis_jobs
                WHERE id = %s
                LIMIT 1
                """,
                (normalized_job_id,),
            )
        return cursor.fetchone()
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
