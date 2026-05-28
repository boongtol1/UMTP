import hashlib
import json


DUPLICATE_STATUSES = ("success", "duplicate", "failed")


def find_existing_url_record(cursor, user_id, url):
    cursor.execute(
        """
        SELECT id, status
        FROM url_analysis_logs
        WHERE user_id = %s
          AND url = %s
          AND status IN (%s, %s, %s)
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            user_id,
            url,
            DUPLICATE_STATUSES[0],
            DUPLICATE_STATUSES[1],
            DUPLICATE_STATUSES[2],
        ),
    )
    row = cursor.fetchone()
    if not row:
        return None

    if isinstance(row, dict):
        row_id = row.get("id")
        row_status = row.get("status")
    else:
        row_id = row[0]
        row_status = row[1]

    return {
        "id": int(row_id),
        "status": str(row_status),
    }


def save_duplicate_url_record(cursor, user_id, url, source="joongna", reason="이미 분석된 URL"):
    payload = {
        "user_id": user_id,
        "url": url,
        "source": source,
        "status": "duplicate",
        "reason": reason,
    }
    payload_text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    content_signature = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()

    try:
        cursor.execute(
            """
            INSERT INTO url_analysis_logs (
                user_id,
                url,
                source,
                status,
                reason,
                content_signature
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                id = id
            """,
            (
                user_id,
                url,
                source,
                "duplicate",
                reason,
                content_signature,
            ),
        )
        return
    except Exception as exc:
        lowered = str(exc).lower()
        if "unknown column" not in lowered and "doesn't exist" not in lowered:
            raise

    # legacy schema fallback: 최신 duplicate 로그가 동일하면 insert를 생략한다.
    cursor.execute(
        """
        SELECT source, status, reason
        FROM url_analysis_logs
        WHERE user_id = %s
          AND url = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id, url),
    )
    row = cursor.fetchone()
    if row is not None:
        if isinstance(row, dict):
            existing_source = row.get("source")
            existing_status = row.get("status")
            existing_reason = row.get("reason")
        else:
            existing_source = row[0]
            existing_status = row[1]
            existing_reason = row[2]
        if (
            str(existing_status or "").strip().lower() == "duplicate"
            and str(existing_source or "").strip() == str(source or "").strip()
            and str(existing_reason or "").strip() == str(reason or "").strip()
        ):
            return

    cursor.execute(
        """
        INSERT INTO url_analysis_logs (
            user_id,
            url,
            source,
            status,
            reason
        )
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            user_id,
            url,
            source,
            "duplicate",
            reason,
        ),
    )
