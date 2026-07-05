import argparse
from typing import Any, Dict, List, Optional

try:
    from src.db import get_connection
    from src.fraud_probability_service import score_alert_fraud_probability_comparison
except ModuleNotFoundError:
    from db import get_connection
    from fraud_probability_service import score_alert_fraud_probability_comparison


DEFAULT_LIMIT = 100


def _normalize_optional_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    cleaned = str(value).strip()
    return cleaned or None


def _format_probability_for_log(value: Any) -> str:
    if value is None:
        return "None"
    try:
        return f"{float(value):.5f}"
    except (TypeError, ValueError):
        return str(value)


def _fetch_alert_rows(
    cursor,
    *,
    limit: int,
    user_id: Optional[str],
    only_unread: bool,
    since_hours: Optional[int],
    force: bool,
) -> List[Dict[str, Any]]:
    where_tokens = []
    if not force:
        where_tokens.append(
            "(fraud_probability IS NULL OR fraud_probability_v1 IS NULL OR fraud_probability_v2 IS NULL)"
        )
    where_tokens.extend(
        [
            "product_id IS NOT NULL",
            "CHAR_LENGTH(TRIM(CAST(product_id AS CHAR))) > 0",
        ]
    )
    params: List[Any] = []

    normalized_user_id = _normalize_optional_text(user_id)
    if normalized_user_id is not None:
        where_tokens.append("user_id = %s")
        params.append(normalized_user_id)

    if only_unread:
        where_tokens.append("COALESCE(is_read, 0) = 0")

    if since_hours is not None:
        normalized_since_hours = max(int(since_hours), 1)
        where_tokens.append("created_at >= DATE_SUB(CURRENT_TIMESTAMP, INTERVAL %s HOUR)")
        params.append(normalized_since_hours)

    params.append(max(int(limit), 1))
    cursor.execute(
        f"""
        SELECT
            id,
            product_id,
            seller_store_seq,
            title,
            price_krw,
            drop_rate_percent,
            risk_score,
            risk_level,
            risk_keywords,
            is_exchange_post,
            trade_type,
            body_excerpt,
            body_text
        FROM alert_events
        WHERE {" AND ".join(where_tokens)}
        ORDER BY id DESC
        LIMIT %s
        """,
        tuple(params),
    )
    return cursor.fetchall() or []


def backfill_fraud_probability(
    *,
    limit: int = DEFAULT_LIMIT,
    user_id: Optional[str] = None,
    only_unread: bool = False,
    since_hours: Optional[int] = None,
    force: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    connection = get_connection()
    updated_count = 0
    scored_count = 0
    skipped_count = 0
    rows: List[Dict[str, Any]] = []
    try:
        cursor = connection.cursor(dictionary=True)
        rows = _fetch_alert_rows(
            cursor,
            limit=limit,
            user_id=user_id,
            only_unread=only_unread,
            since_hours=since_hours,
            force=force,
        )

        for row in rows:
            score = score_alert_fraud_probability_comparison(
                cursor,
                product_id=row.get("product_id"),
                store_id=row.get("seller_store_seq"),
                alert_context={
                    "title": row.get("title"),
                    "body_excerpt": row.get("body_excerpt"),
                    "body_text": row.get("body_text"),
                    "price_krw": row.get("price_krw"),
                    "drop_rate_percent": row.get("drop_rate_percent"),
                    "risk_score": row.get("risk_score"),
                    "risk_level": row.get("risk_level"),
                    "trade_type": row.get("trade_type"),
                    "is_exchange_post": row.get("is_exchange_post"),
                    "risk_keywords_json": row.get("risk_keywords"),
                },
            )
            if not score:
                skipped_count += 1
                continue

            scored_count += 1
            if dry_run:
                print(
                    f"dry_run alert_id={row.get('id')} product_id={row.get('product_id')} "
                    f"probability={_format_probability_for_log(score.get('fraud_probability'))} "
                    f"label={score.get('fraud_probability_label')} "
                    f"v1={_format_probability_for_log(score.get('fraud_probability_v1'))} "
                    f"v2={_format_probability_for_log(score.get('fraud_probability_v2'))}"
                )
                continue

            cursor.execute(
                """
                UPDATE alert_events
                SET
                    fraud_probability = %s,
                    fraud_probability_label = %s,
                    fraud_model_version = %s,
                    fraud_scored_at = %s,
                    fraud_probability_v1 = %s,
                    fraud_probability_label_v1 = %s,
                    fraud_model_version_v1 = %s,
                    fraud_scored_at_v1 = %s,
                    fraud_probability_v2 = %s,
                    fraud_probability_label_v2 = %s,
                    fraud_model_version_v2 = %s,
                    fraud_scored_at_v2 = %s
                WHERE id = %s
                """,
                (
                    score.get("fraud_probability"),
                    score.get("fraud_probability_label"),
                    score.get("fraud_model_version"),
                    score.get("fraud_scored_at"),
                    score.get("fraud_probability_v1"),
                    score.get("fraud_probability_label_v1"),
                    score.get("fraud_model_version_v1"),
                    score.get("fraud_scored_at_v1"),
                    score.get("fraud_probability_v2"),
                    score.get("fraud_probability_label_v2"),
                    score.get("fraud_model_version_v2"),
                    score.get("fraud_scored_at_v2"),
                    row.get("id"),
                ),
            )
            updated_count += cursor.rowcount

        if dry_run:
            connection.rollback()
        else:
            connection.commit()

        return {
            "candidate_count": len(rows),
            "scored_count": scored_count,
            "updated_count": updated_count,
            "skipped_count": skipped_count,
            "since_hours": since_hours,
            "force": force,
            "dry_run": dry_run,
        }
    except Exception:
        if connection.is_connected():
            connection.rollback()
        raise
    finally:
        if "cursor" in locals():
            cursor.close()
        if connection.is_connected():
            connection.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Backfill fraud probability fields for alert_events")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--user-id", default=None)
    parser.add_argument("--only-unread", action="store_true")
    parser.add_argument("--since-hours", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    result = backfill_fraud_probability(
        limit=args.limit,
        user_id=args.user_id,
        only_unread=args.only_unread,
        since_hours=args.since_hours,
        force=args.force,
        dry_run=args.dry_run,
    )
    print(result)


if __name__ == "__main__":
    main()
