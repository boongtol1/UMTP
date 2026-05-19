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
    *,
    include_sort_date=True,
):
    normalized_user_id = _normalize_optional_text(user_id)
    normalized_watch_rule_id = _normalize_optional_watch_rule_id(watch_rule_id)
    normalized_product_id = _normalize_product_id(product_id)
    normalized_sort_date = _normalize_sort_date_for_db(sort_date)

    if normalized_user_id is None or normalized_product_id is None:
        return None

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            if include_sort_date:
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

    identity_job = find_analysis_job_by_identity(
        normalized_user_id,
        normalized_watch_rule_id,
        normalized_product_id,
        normalized_sort_date,
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
                    normalized_sort_date,
                    normalized_trigger_reason,
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
                            normalized_watch_rule_id,
                            normalized_trigger_reason,
                        ),
                    )
                except Exception as second_exc:
                    lowered_second_exc = str(second_exc).lower()
                    if "unknown column" not in lowered_second_exc:
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
                )
                if duplicate_job is None:
                    duplicate_job = find_analysis_job_by_identity(
                        normalized_user_id,
                        normalized_watch_rule_id,
                        normalized_product_id,
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

    for target in unique_targets:

        result = create_analysis_job(
            source="joongna",
            product_id=product.get("product_id"),
            url=product.get("product_url"),
            title=product.get("title"),
            price_krw=product.get("price"),
            search_keyword=product.get("search_keyword") or product.get("search_word"),
            user_id=target.get("user_id"),
            watch_rule_id=target.get("watch_rule_id"),
            sort_date=product.get("sort_date"),
            trigger_reason=trigger_reason,
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
