from src.analysis_service import analyze_url_for_user
from src.db import get_connection
from src.joongna_search_client import search_joongna_products


DEFAULT_SEARCH_WORDS = [
    "m1맥북에어",
    "m2맥북에어",
    "m3맥북에어",
    "m4맥북에어",
    "m5맥북에어",
]
DEFAULT_USER_ID = "test_user"


def _normalize_search_words(search_words):
    if not search_words:
        return DEFAULT_SEARCH_WORDS

    normalized = []
    for word in search_words:
        if not isinstance(word, str):
            continue
        cleaned = word.strip()
        if cleaned:
            normalized.append(cleaned)

    return normalized or DEFAULT_SEARCH_WORDS


def _is_seen_seq(cursor, seq):
    cursor.execute(
        """
        SELECT 1
        FROM joongna_seen_products
        WHERE seq = %s
        LIMIT 1
        """,
        (seq,),
    )
    return cursor.fetchone() is not None


def _save_seen_seq(cursor, search_word, item):
    cursor.execute(
        """
        INSERT INTO joongna_seen_products (
            seq,
            search_word,
            title,
            price,
            product_url,
            image_url,
            sort_date
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            item.get("seq"),
            search_word,
            item.get("title"),
            item.get("price"),
            item.get("product_url"),
            item.get("image_url"),
            item.get("sort_date"),
        ),
    )


def _build_poll_stats(search_words):
    return {
        "search_words": search_words,
        "fetched_items": 0,
        "new_items": 0,
        "skipped_no_seq": 0,
        "skipped_seen": 0,
        "search_errors": 0,
        "db_errors": 0,
        "analysis_success": 0,
        "analysis_duplicate": 0,
        "analysis_failed": 0,
    }


def poll_once(user_id=DEFAULT_USER_ID, search_words=None):
    words = _normalize_search_words(search_words)
    stats = _build_poll_stats(words)
    seen_in_this_run = set()

    connection = None
    cursor = None
    seen_db_ready = False

    try:
        try:
            connection = get_connection()
            cursor = connection.cursor()
            seen_db_ready = True
        except Exception as exc:
            print(f"[polling] seen DB 연결 실패: {exc}")

        for search_word in words:
            print(f"[{search_word}] Search API 조회 시작")
            try:
                items = search_joongna_products(search_word)
                stats["fetched_items"] += len(items)
                print(f"[{search_word}] 검색 결과 {len(items)}건")
            except Exception as exc:
                stats["search_errors"] += 1
                print(f"[{search_word}] Search API 조회 실패: {exc}")
                continue

            for item in items:
                seq = item.get("seq")
                if seq is None:
                    stats["skipped_no_seq"] += 1
                    continue

                if seq in seen_in_this_run:
                    stats["skipped_seen"] += 1
                    continue

                already_seen = False
                if seen_db_ready and cursor is not None:
                    try:
                        already_seen = _is_seen_seq(cursor, seq)
                    except Exception as exc:
                        stats["db_errors"] += 1
                        print(f"[{search_word}] seen 조회 실패 (seq={seq}): {exc}")
                        already_seen = False

                if already_seen:
                    stats["skipped_seen"] += 1
                    seen_in_this_run.add(seq)
                    continue

                seen_in_this_run.add(seq)

                if seen_db_ready and cursor is not None:
                    try:
                        _save_seen_seq(cursor, search_word, item)
                        connection.commit()
                    except Exception as exc:
                        stats["db_errors"] += 1
                        try:
                            connection.rollback()
                        except Exception:
                            pass
                        print(f"[{search_word}] seen 저장 실패 (seq={seq}): {exc}")

                print(f"[{search_word}] 새 매물 발견")
                print(f"seq={seq}")
                print(f"title={item.get('title') or '-'}")
                print(f"price={item.get('price')}")
                print(f"product_url={item.get('product_url') or '-'}")
                stats["new_items"] += 1

                product_url = item.get("product_url")
                if not isinstance(product_url, str) or not product_url.strip():
                    print(f"[{search_word}] 분석 스킵: product_url이 비어 있습니다.")
                    stats["analysis_failed"] += 1
                    continue

                try:
                    print("-> UMTP 분석 시작")
                    analysis_result = analyze_url_for_user(
                        user_id=user_id,
                        url=product_url.strip(),
                    )
                except Exception as exc:
                    print(f"-> UMTP 분석 예외: {exc}")
                    stats["analysis_failed"] += 1
                    continue

                if analysis_result.get("ok"):
                    status = analysis_result.get("status")
                    if status == "success":
                        stats["analysis_success"] += 1
                    elif status == "duplicate":
                        stats["analysis_duplicate"] += 1
                    else:
                        stats["analysis_failed"] += 1

                    print(
                        "-> UMTP 분석 완료 "
                        f"(status={status}, "
                        f"alert={analysis_result.get('is_alert_target')}, "
                        f"telegram_sent={analysis_result.get('telegram_sent')})"
                    )
                    continue

                stats["analysis_failed"] += 1
                print(f"-> UMTP 분석 실패: {analysis_result.get('reason')}")

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    return stats
