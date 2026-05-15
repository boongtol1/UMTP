try:
    from src.db import get_connection
    from src.joongna_search_client import search_joongna_products
    from src.joongna_seen_products import (
        get_seen_product,
        should_analyze_seen_product,
        upsert_seen_product_observation,
    )
    from src.listing_analysis_pipeline import (
        enqueue_analysis_for_product,
    )
    from src.search_keyword_utils import dedupe_keywords_keep_order, normalize_search_keyword
    from src.user_settings_service import (
        get_due_user_fair_price_polling_targets as get_due_watch_rules,
        mark_user_fair_price_polled as mark_watch_rule_polled,
    )
except ModuleNotFoundError:
    from db import get_connection
    from joongna_search_client import search_joongna_products
    from joongna_seen_products import (
        get_seen_product,
        should_analyze_seen_product,
        upsert_seen_product_observation,
    )
    from listing_analysis_pipeline import (
        enqueue_analysis_for_product,
    )
    from search_keyword_utils import dedupe_keywords_keep_order, normalize_search_keyword
    from user_settings_service import (
        get_due_user_fair_price_polling_targets as get_due_watch_rules,
        mark_user_fair_price_polled as mark_watch_rule_polled,
    )


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

    normalized = dedupe_keywords_keep_order(search_words)
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
        "settings_due": 0,
        "settings_marked": 0,
        "analysis_jobs_created": 0,
        "analysis_jobs_skipped_duplicate": 0,
        "analysis_jobs_processed": 0,
        "analysis_jobs_process_failed": 0,
    }


def _build_observed_product(search_word, item):
    return {
        "product_id": item.get("product_id") or item.get("seq"),
        "seq": item.get("seq"),
        "search_word": search_word,
        "search_keyword": search_word,
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
        normalized_search_word = normalize_search_keyword(search_word)
        if not normalized_search_word:
            continue
        targets[normalized_search_word] = [
            {
                "user_id": resolved_user_id,
                "rule_id": None,
                "watch_rule": None,
            }
        ]
    return targets


def _build_keyword_targets_from_user_fair_prices(watch_rules):
    keyword_targets = {}
    target_by_key = {}

    for rule in watch_rules:
        search_keyword = normalize_search_keyword(rule.get("search_keyword"))
        user_id = _normalize_optional_user_id(rule.get("user_id"))
        if not search_keyword or not user_id:
            continue

        setting_id = rule.get("id")
        target_key = (search_keyword.lower(), user_id)
        existing_target = target_by_key.get(target_key)
        if existing_target is None:
            existing_target = {
                "user_id": user_id,
                "rule_id": None,
                "setting_ids": [],
                "watch_rule": None,
            }
            target_by_key[target_key] = existing_target
            keyword_targets.setdefault(search_keyword, []).append(existing_target)

        if setting_id is not None and setting_id not in existing_target["setting_ids"]:
            existing_target["setting_ids"].append(setting_id)

    return keyword_targets


def _build_keyword_targets_from_watch_rules(watch_rules):
    # Deprecated: watch_rule fanout은 사용하지 않고 user_fair_prices 기반 사용자 타겟만 유지
    return _build_keyword_targets_from_user_fair_prices(watch_rules)


def _resolve_poll_targets(search_words, user_id):
    normalized_user_id = _normalize_optional_user_id(user_id)

    if search_words:
        words = _normalize_search_words(search_words)
        return words, _build_single_user_keyword_targets(words, normalized_user_id), [], "cli"

    try:
        due_rules = get_due_watch_rules(user_id=normalized_user_id)
    except Exception as exc:
        print(f"[polling] user_fair_prices(enabled) 조회 실패, DEFAULT_SEARCH_WORDS로 fallback: {exc}")
        words = DEFAULT_SEARCH_WORDS
        return words, _build_single_user_keyword_targets(words, normalized_user_id), [], "fallback"

    keyword_targets = _build_keyword_targets_from_user_fair_prices(due_rules)
    if keyword_targets:
        words = list(keyword_targets.keys())
        return words, keyword_targets, due_rules, "settings"

    words = DEFAULT_SEARCH_WORDS
    return words, _build_single_user_keyword_targets(words, normalized_user_id), [], "fallback"


def poll_once(user_id=None, search_words=None, *, inline_process=False, inline_process_limit=50):
    words, keyword_targets, due_rules, target_source = _resolve_poll_targets(search_words, user_id)
    stats = _build_poll_stats(words)
    stats["settings_due"] = len(due_rules)

    connection = None
    cursor = None
    seen_db_ready = False
    processed_products = {}

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
        if target_source != "settings":
            return

        marked_rule_ids = set()
        for target in targets:
            setting_ids = target.get("setting_ids")
            if not setting_ids:
                fallback_setting_id = target.get("setting_id") or target.get("rule_id")
                setting_ids = [fallback_setting_id] if fallback_setting_id is not None else []

            for setting_id in setting_ids:
                if setting_id is None or setting_id in marked_rule_ids:
                    continue
                marked_rule_ids.add(setting_id)

                try:
                    mark_watch_rule_polled(setting_id)
                    stats["settings_marked"] += 1
                except Exception as exc:
                    stats["db_errors"] += 1
                    print(f"[polling] setting polled_at 갱신 실패 (setting_id={setting_id}): {exc}")

    try:
        try:
            connection = get_connection()
            cursor = connection.cursor()
            seen_db_ready = True
        except Exception as exc:
            print(f"[polling] seen DB 연결 실패: {exc}")

        for search_word in words:
            targets_for_word = keyword_targets.get(search_word) or []
            search_completed_for_word = False

            try:
                print(f"[{search_word}] Search API 조회 시작")
                try:
                    items = search_joongna_products(search_word)
                    search_completed_for_word = True
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
                                    existing,
                                    observed_product,
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
                                    status="analysis_pending" if should_analyze else "unchanged",
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
                        }
                        processed_products[product_id] = product_state

                        if not should_analyze:
                            stats["skipped_seen"] += 1
                            print(
                                f"[{search_word}] 상태 동일하여 스킵 "
                                f"(seq={product_id}, reason={change_reason})"
                            )
                            continue

                        print(
                            f"[{search_word}] 분석 큐 등록 대상 감지 "
                            f"(seq={product_id}, reason={change_reason})"
                        )
                        stats["new_items"] += 1

                    if not product_state.get("should_analyze"):
                        continue

                    try:
                        enqueue_result = enqueue_analysis_for_product(
                            observed_product,
                            targets_for_word,
                            product_state.get("change_reason"),
                        )
                        created_jobs = enqueue_result.get("created_jobs") or []
                        skipped_jobs = enqueue_result.get("skipped_jobs") or []
                        stats["analysis_jobs_created"] += len(created_jobs)
                        stats["analysis_jobs_skipped_duplicate"] += len(skipped_jobs)
                    except Exception as exc:
                        stats["db_errors"] += 1
                        print(
                            f"[{search_word}] analysis job enqueue 실패 "
                            f"(seq={product_id}): {exc}"
                        )
                        continue
            finally:
                if search_completed_for_word:
                    mark_related_rules_polled(targets_for_word)
                elif target_source == "settings" and targets_for_word:
                    print(
                        f"[{search_word}] Search API 실패로 setting polled_at 갱신 생략 "
                        "(force_poll 유지)"
                    )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    if inline_process:
        print("[polling] inline_process=True 요청이 들어왔지만 enqueue-only 정책으로 무시합니다.")

    return stats
