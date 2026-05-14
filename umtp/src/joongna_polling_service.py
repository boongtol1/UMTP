try:
    from src.analysis_service import analyze_url_for_user
    from src.db import get_connection
    from src.joongna_search_client import search_joongna_products
    from src.joongna_seen_products import (
        get_seen_product,
        mark_seen_product_analyzed,
        should_analyze_seen_product,
        upsert_seen_product_observation,
    )
    from src.user_watch_rules import get_due_watch_rules, mark_watch_rule_polled
except ModuleNotFoundError:
    from analysis_service import analyze_url_for_user
    from db import get_connection
    from joongna_search_client import search_joongna_products
    from joongna_seen_products import (
        get_seen_product,
        mark_seen_product_analyzed,
        should_analyze_seen_product,
        upsert_seen_product_observation,
    )
    from user_watch_rules import get_due_watch_rules, mark_watch_rule_polled


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


def _normalize_optional_user_id(user_id):
    if not isinstance(user_id, str):
        return None
    cleaned = user_id.strip()
    return cleaned or None


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
        "watch_rules_due": 0,
        "watch_rules_marked": 0,
    }


def _build_observed_product(search_word, item):
    return {
        "product_id": item.get("product_id") or item.get("seq"),
        "seq": item.get("seq"),
        "search_word": search_word,
        "title": item.get("title"),
        "price": item.get("price"),
        "product_url": item.get("product_url"),
        "image_url": item.get("image_url"),
        "sort_date": item.get("sort_date"),
        "refresh_key": item.get("refresh_key"),
    }


def _build_single_user_keyword_targets(search_words, user_id):
    resolved_user_id = _normalize_optional_user_id(user_id) or DEFAULT_USER_ID
    targets = {}
    for search_word in search_words:
        targets[search_word] = [{"user_id": resolved_user_id, "rule_id": None}]
    return targets


def _build_keyword_targets_from_watch_rules(watch_rules):
    keyword_targets = {}
    for rule in watch_rules:
        search_keyword = rule.get("search_keyword")
        user_id = _normalize_optional_user_id(rule.get("user_id"))
        if not isinstance(search_keyword, str) or not search_keyword.strip() or not user_id:
            continue

        keyword = search_keyword.strip()
        keyword_targets.setdefault(keyword, []).append(
            {
                "user_id": user_id,
                "rule_id": rule.get("id"),
            }
        )
    return keyword_targets


def _resolve_poll_targets(search_words, user_id):
    normalized_user_id = _normalize_optional_user_id(user_id)

    if search_words:
        words = _normalize_search_words(search_words)
        return words, _build_single_user_keyword_targets(words, normalized_user_id), [], "cli"

    try:
        due_rules = get_due_watch_rules(user_id=normalized_user_id)
    except Exception as exc:
        print(f"[polling] user_watch_rules 조회 실패, DEFAULT_SEARCH_WORDS로 fallback: {exc}")
        words = DEFAULT_SEARCH_WORDS
        return words, _build_single_user_keyword_targets(words, normalized_user_id), [], "fallback"

    keyword_targets = _build_keyword_targets_from_watch_rules(due_rules)
    if keyword_targets:
        words = list(keyword_targets.keys())
        return words, keyword_targets, due_rules, "watch_rules"

    words = DEFAULT_SEARCH_WORDS
    return words, _build_single_user_keyword_targets(words, normalized_user_id), [], "fallback"


def poll_once(user_id=None, search_words=None):
    words, keyword_targets, due_rules, target_source = _resolve_poll_targets(search_words, user_id)
    stats = _build_poll_stats(words)
    stats["watch_rules_due"] = len(due_rules)

    connection = None
    cursor = None
    seen_db_ready = False
    processed_products = {}
    analyzed_users_by_product = {}

    def disable_seen_db(reason):
        nonlocal connection, cursor, seen_db_ready
        seen_db_ready = False
        print(f"[polling] seen DB 비활성화: {reason}")
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
            cursor = None
        if connection is not None and connection.is_connected():
            try:
                connection.close()
            except Exception:
                pass
            connection = None

    def mark_related_rules_polled(targets):
        if target_source != "watch_rules":
            return

        for target in targets:
            rule_id = target.get("rule_id")
            if rule_id is None:
                continue
            try:
                mark_watch_rule_polled(rule_id)
                stats["watch_rules_marked"] += 1
            except Exception as exc:
                stats["db_errors"] += 1
                print(f"[polling] watch rule polled_at 갱신 실패 (rule_id={rule_id}): {exc}")

    try:
        try:
            connection = get_connection()
            cursor = connection.cursor()
            seen_db_ready = True
        except Exception as exc:
            print(f"[polling] seen DB 연결 실패: {exc}")

        for search_word in words:
            targets_for_word = keyword_targets.get(search_word) or []

            try:
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
                    observed_product = _build_observed_product(search_word, item)
                    product_id = observed_product.get("product_id")
                    if product_id is None:
                        stats["skipped_no_seq"] += 1
                        continue

                    product_state = processed_products.get(product_id)
                    if product_state is None:
                        should_analyze = True
                        change_reason = "new_product"

                        if seen_db_ready and cursor is not None:
                            try:
                                existing = get_seen_product(cursor, product_id)
                                should_analyze, change_reason = should_analyze_seen_product(
                                    existing, observed_product
                                )
                            except Exception as exc:
                                stats["db_errors"] += 1
                                print(f"[{search_word}] seen 조회 실패 (seq={product_id}): {exc}")
                                disable_seen_db(str(exc))
                                should_analyze = True
                                change_reason = "new_product"

                        if seen_db_ready and cursor is not None:
                            try:
                                upsert_seen_product_observation(
                                    cursor,
                                    observed_product,
                                    change_reason=change_reason,
                                    status="analyze_pending" if should_analyze else "unchanged",
                                )
                                connection.commit()
                            except Exception as exc:
                                stats["db_errors"] += 1
                                try:
                                    connection.rollback()
                                except Exception:
                                    pass
                                print(f"[{search_word}] seen 관측 저장 실패 (seq={product_id}): {exc}")
                                disable_seen_db(str(exc))

                        product_state = {
                            "should_analyze": should_analyze,
                            "change_reason": change_reason,
                            "product_url": item.get("product_url"),
                            "title": item.get("title"),
                            "price": item.get("price"),
                            "refresh_key": item.get("refresh_key"),
                        }
                        processed_products[product_id] = product_state
                        analyzed_users_by_product[product_id] = set()

                        if not should_analyze:
                            stats["skipped_seen"] += 1
                            print(
                                f"[{search_word}] 상태 동일하여 스킵 "
                                f"(seq={product_id}, reason={change_reason})"
                            )
                            continue

                        print(
                            f"[{search_word}] 분석 대상 감지 "
                            f"(seq={product_id}, reason={change_reason})"
                        )
                        print(f"title={item.get('title') or '-'}")
                        print(f"price={item.get('price')}")
                        print(f"refresh_key={item.get('refresh_key') or '-'}")
                        print(f"product_url={item.get('product_url') or '-'}")
                        stats["new_items"] += 1

                    if not product_state.get("should_analyze"):
                        continue

                    product_url = product_state.get("product_url")
                    if not isinstance(product_url, str) or not product_url.strip():
                        print(f"[{search_word}] 분석 스킵: product_url이 비어 있습니다.")
                        stats["analysis_failed"] += 1
                        continue

                    analyzed_users = analyzed_users_by_product.setdefault(product_id, set())
                    for target in targets_for_word:
                        target_user_id = _normalize_optional_user_id(target.get("user_id")) or DEFAULT_USER_ID
                        if target_user_id in analyzed_users:
                            continue

                        analysis_result = None
                        try:
                            print(f"-> UMTP 분석 시작 (user_id={target_user_id})")
                            analysis_result = analyze_url_for_user(
                                user_id=target_user_id,
                                url=product_url.strip(),
                                force_reanalyze=True,
                            )
                            analyzed_users.add(target_user_id)
                        except Exception as exc:
                            print(f"-> UMTP 분석 예외 (user_id={target_user_id}): {exc}")
                            stats["analysis_failed"] += 1
                            if seen_db_ready and cursor is not None:
                                try:
                                    mark_seen_product_analyzed(
                                        cursor, product_id, status="analysis_exception"
                                    )
                                    connection.commit()
                                except Exception as mark_exc:
                                    stats["db_errors"] += 1
                                    try:
                                        connection.rollback()
                                    except Exception:
                                        pass
                                    print(
                                        f"[{search_word}] analyzed_at 갱신 실패 "
                                        f"(seq={product_id}): {mark_exc}"
                                    )
                                    disable_seen_db(str(mark_exc))
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
                                f"(user_id={target_user_id}, "
                                f"status={status}, "
                                f"alert={analysis_result.get('is_alert_target')}, "
                                f"telegram_sent={analysis_result.get('telegram_sent')})"
                            )
                        else:
                            stats["analysis_failed"] += 1
                            print(
                                f"-> UMTP 분석 실패 (user_id={target_user_id}): "
                                f"{analysis_result.get('reason')}"
                            )

                        if seen_db_ready and cursor is not None:
                            try:
                                analyzed_status = (
                                    analysis_result.get("status") if analysis_result else "failed"
                                )
                                mark_seen_product_analyzed(cursor, product_id, status=analyzed_status)
                                connection.commit()
                            except Exception as exc:
                                stats["db_errors"] += 1
                                try:
                                    connection.rollback()
                                except Exception:
                                    pass
                                print(
                                    f"[{search_word}] analyzed_at 갱신 실패 "
                                    f"(seq={product_id}): {exc}"
                                )
                                disable_seen_db(str(exc))
            finally:
                mark_related_rules_polled(targets_for_word)

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    return stats
