from datetime import datetime, timezone

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

def _normalize_search_words(search_words):
    if not search_words:
        return []

    return dedupe_keywords_keep_order(search_words)


def _normalize_optional_user_id(user_id):
    if not isinstance(user_id, str):
        return None
    cleaned = user_id.strip()
    return cleaned or None


def parse_sort_date(item):
    if not isinstance(item, dict):
        return None

    raw_value = item.get("sort_date")
    if raw_value is None:
        raw_value = item.get("sortDate")
    if raw_value is None:
        return None

    if isinstance(raw_value, str):
        cleaned = raw_value.strip()
    else:
        cleaned = str(raw_value).strip()

    return cleaned or None


def _coerce_datetime(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        parsed = value
    else:
        if isinstance(value, str):
            text = value.strip()
        else:
            text = str(value).strip()

        if not text:
            return None

        parsed = None
        candidate = text.replace("Z", "+00:00")
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
                    parsed = datetime.strptime(text, date_format)
                    break
                except ValueError:
                    continue

        if parsed is None:
            return None

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)

    return parsed.replace(microsecond=0)


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
        "skipped_before_saved_at": 0,
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
        "sort_date": parse_sort_date(item),
        "refresh_key": item.get("refresh_key"),
    }


def _build_keyword_targets_from_user_fair_prices(watch_rules):
    keyword_targets = {}
    target_keys = set()

    for rule in watch_rules:
        if rule.get("enabled") is not None and not bool(rule.get("enabled")):
            continue
        if "last_poll_requested_at" in rule and rule.get("last_poll_requested_at") is None:
            continue

        search_keyword = normalize_search_keyword(rule.get("search_keyword"))
        user_id = _normalize_optional_user_id(rule.get("user_id"))
        if not search_keyword or not user_id:
            continue

        setting_id = rule.get("id")
        target_key = (search_keyword.lower(), user_id, setting_id)
        if target_key in target_keys:
            continue
        target_keys.add(target_key)

        target = {
            "user_id": user_id,
            "rule_id": setting_id,
            "setting_id": setting_id,
            "setting_ids": [setting_id] if setting_id is not None else [],
            "saved_at": rule.get("saved_at"),
            "search_keyword": search_keyword,
            "watch_rule": None,
        }
        keyword_targets.setdefault(search_keyword, []).append(target)

    return keyword_targets


def _build_keyword_targets_from_watch_rules(watch_rules):
    # Deprecated: watch_rule fanout은 사용하지 않고 user_fair_prices 기반 사용자 타겟만 유지
    return _build_keyword_targets_from_user_fair_prices(watch_rules)


def _resolve_poll_targets(search_words, user_id):
    normalized_user_id = _normalize_optional_user_id(user_id)

    try:
        due_rules = get_due_watch_rules(user_id=normalized_user_id)
    except Exception as exc:
        print(f"[polling] user_fair_prices(enabled) 조회 실패, polling 스킵: {exc}")
        return [], {}, [], "settings_error"

    keyword_targets = _build_keyword_targets_from_user_fair_prices(due_rules)

    if search_words:
        requested_words = _normalize_search_words(search_words)
        requested_word_set = set()
        for word in requested_words:
            normalized = normalize_search_keyword(word)
            if normalized:
                requested_word_set.add(normalized.lower())

        filtered_targets = {}
        for keyword, targets in keyword_targets.items():
            if keyword.lower() in requested_word_set:
                filtered_targets[keyword] = targets

        words = list(filtered_targets.keys())
        return words, filtered_targets, due_rules, "cli"

    if keyword_targets:
        words = list(keyword_targets.keys())
        return words, keyword_targets, due_rules, "settings"

    return [], {}, due_rules, "settings_empty"


def poll_once(user_id=None, search_words=None, *, inline_process=False, inline_process_limit=50):
    words, keyword_targets, due_rules, target_source = _resolve_poll_targets(search_words, user_id)
    stats = _build_poll_stats(words)
    stats["settings_due"] = len(due_rules)

    if not words:
        print("[polling] enabled 토글 대상 검색어가 없어 이번 주기는 스킵합니다.")
        return stats

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

    def filter_targets_by_saved_window(observed_product, targets):
        listing_sort_date = _coerce_datetime(observed_product.get("sort_date"))
        if listing_sort_date is None:
            return []

        eligible_targets = []
        for target in targets:
            saved_at = _coerce_datetime(target.get("saved_at"))
            if saved_at is None:
                continue
            if listing_sort_date >= saved_at:
                eligible_targets.append(target)
        return eligible_targets

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
                            print(f"[{search_word}] 상태 동일(글로벌) (seq={product_id}, reason={change_reason})")

                        if should_analyze:
                            print(
                                f"[{search_word}] 분석 큐 등록 대상 감지 "
                                f"(seq={product_id}, reason={change_reason})"
                            )
                            stats["new_items"] += 1

                    eligible_targets = filter_targets_by_saved_window(observed_product, targets_for_word)
                    if not eligible_targets:
                        stats["skipped_before_saved_at"] += len(targets_for_word)
                        continue

                    try:
                        enqueue_result = enqueue_analysis_for_product(
                            observed_product,
                            eligible_targets,
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
