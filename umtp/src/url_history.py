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

    return {
        "id": int(row[0]),
        "status": str(row[1]),
    }


def save_duplicate_url_record(cursor, user_id, url, source="joongna", reason="이미 분석된 URL"):
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
