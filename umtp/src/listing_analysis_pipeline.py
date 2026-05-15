try:
    from src.analysis_log import save_success_log
    from src.analysis_jobs import (
        create_analysis_jobs_for_rules,
        get_pending_analysis_jobs,
        mark_analysis_job_done,
        mark_analysis_job_failed,
        mark_analysis_job_started,
    )
    from src.db import get_connection
    from src.joongna_seen_products import mark_seen_product_analyzed
    from src.listing_page_parser import fetch_html, parse_joongna_listing_page
    from src.risk_analyzer import analyze_risk
    from src.spec_parser import parse_listing_title
    from src.user_fair_price import fetch_user_fair_price
    from src.user_watch_rules import compute_alert_drop_rate_percent
    from src.watch_rule_matcher import matches_watch_rule
except ModuleNotFoundError:
    from analysis_log import save_success_log
    from analysis_jobs import (
        create_analysis_jobs_for_rules,
        get_pending_analysis_jobs,
        mark_analysis_job_done,
        mark_analysis_job_failed,
        mark_analysis_job_started,
    )
    from db import get_connection
    from joongna_seen_products import mark_seen_product_analyzed
    from listing_page_parser import fetch_html, parse_joongna_listing_page
    from risk_analyzer import analyze_risk
    from spec_parser import parse_listing_title
    from user_fair_price import fetch_user_fair_price
    from user_watch_rules import compute_alert_drop_rate_percent
    from watch_rule_matcher import matches_watch_rule


DEFAULT_USER_ID = "test_user"


def _normalize_optional_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    cleaned = str(value).strip()
    return cleaned or None


def _normalize_optional_int(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_optional_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_listing_snapshot_from_job(job):
    return {
        "product_id": _normalize_optional_text(job.get("product_id")),
        "product_url": _normalize_optional_text(job.get("url")),
        "title": _normalize_optional_text(job.get("title")),
        "price": _normalize_optional_int(job.get("price_krw")),
        "search_keyword": _normalize_optional_text(job.get("search_keyword")),
        "user_id": _normalize_optional_text(job.get("user_id")),
    }


def enqueue_analysis_for_product(product, watch_rules, trigger_reason):
    return create_analysis_jobs_for_rules(product, watch_rules, trigger_reason)


def _get_watch_rule_by_id(watch_rule_id):
    normalized_watch_rule_id = _normalize_optional_int(watch_rule_id)
    if normalized_watch_rule_id is None:
        return None

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
                    user_id,
                    product_type,
                    chip,
                    screen_inch,
                    ram_gb,
                    ssd_gb,
                    search_keyword,
                    enabled,
                    target_price_krw,
                    fair_price_krw,
                    alert_drop_rate_percent
                FROM user_watch_rules
                WHERE id = %s
                LIMIT 1
                """,
                (normalized_watch_rule_id,),
            )
            return cursor.fetchone()
        except Exception:
            # watch_rules 제거 이후에도 과거 analysis_job 처리를 위해 안전하게 None 처리
            return None
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def _resolve_price_rules(cursor, user_id, parsed_spec, watch_rule):
    watch_rule = watch_rule or {}

    fair_price_krw = _normalize_optional_int(watch_rule.get("fair_price_krw"))
    target_price_krw = _normalize_optional_int(watch_rule.get("target_price_krw"))
    alert_drop_rate_percent = _normalize_optional_float(watch_rule.get("alert_drop_rate_percent"))

    if alert_drop_rate_percent is None:
        alert_drop_rate_percent = compute_alert_drop_rate_percent(target_price_krw, fair_price_krw)

    if fair_price_krw is None:
        normalized_user_id = _normalize_optional_text(user_id)
        parse_success = bool(parsed_spec.get("parse_success")) if isinstance(parsed_spec, dict) else False
        if normalized_user_id and parse_success:
            user_fair_price = fetch_user_fair_price(cursor, normalized_user_id, parsed_spec)
            if user_fair_price is not None:
                fair_price_krw = _normalize_optional_int(user_fair_price.get("fair_price_krw"))
                if alert_drop_rate_percent is None:
                    alert_drop_rate_percent = _normalize_optional_float(
                        user_fair_price.get("alert_drop_rate_percent")
                    )

    return fair_price_krw, target_price_krw, alert_drop_rate_percent


def _build_alert_message(title, listing_price_krw, fair_price_krw, drop_rate_percent, url):
    drop_text = "-"
    if drop_rate_percent is not None:
        drop_text = f"{round(drop_rate_percent, 2)}%"

    return (
        "[UMTP 알림]\n"
        f"{title or '-'}\n\n"
        f"현재가: {listing_price_krw:,}원\n"
        f"내 공정가: {fair_price_krw:,}원\n"
        f"저평가율: {drop_text}\n\n"
        "URL:\n"
        f"{url}"
    )


def _find_recent_duplicate_alert(
    cursor,
    *,
    user_id,
    product_id,
    watch_rule_id,
    trigger_reason,
    within_seconds=300,
):
    normalized_user_id = _normalize_optional_text(user_id)
    normalized_product_id = _normalize_optional_text(product_id)
    normalized_watch_rule_id = _normalize_optional_int(watch_rule_id)
    normalized_trigger_reason = _normalize_optional_text(trigger_reason)
    normalized_within_seconds = _normalize_optional_int(within_seconds) or 300

    if normalized_user_id is None:
        return None

    cursor.execute(
        """
        SELECT id
        FROM alert_events
        WHERE user_id = %s
          AND (
                (product_id IS NULL AND %s IS NULL)
             OR product_id = %s
          )
          AND (
                (watch_rule_id IS NULL AND %s IS NULL)
             OR watch_rule_id = %s
          )
          AND (
                (trigger_reason IS NULL AND %s IS NULL)
             OR trigger_reason = %s
          )
          AND status IN ('pending', 'sending', 'sent', 'app_only')
          AND TIMESTAMPDIFF(SECOND, created_at, CURRENT_TIMESTAMP) <= %s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (
            normalized_user_id,
            normalized_product_id,
            normalized_product_id,
            normalized_watch_rule_id,
            normalized_watch_rule_id,
            normalized_trigger_reason,
            normalized_trigger_reason,
            normalized_within_seconds,
        ),
    )
    return cursor.fetchone()


def maybe_create_alert_event(
    cursor,
    *,
    analysis_job_id,
    user_id,
    watch_rule_id,
    product_id,
    url,
    title,
    price_krw,
    fair_price_krw,
    target_price_krw,
    drop_rate_percent,
    trigger_reason,
    message,
):
    duplicate = _find_recent_duplicate_alert(
        cursor,
        user_id=user_id,
        product_id=product_id,
        watch_rule_id=watch_rule_id,
        trigger_reason=trigger_reason,
    )
    if duplicate is not None:
        return {
            "created": False,
            "reason": "duplicate_recent_alert",
            "alert_id": int(duplicate[0]) if isinstance(duplicate, (tuple, list)) else int(duplicate.get("id")),
        }

    cursor.execute(
        """
        INSERT INTO alert_events (
            user_id,
            watch_rule_id,
            analysis_job_id,
            product_id,
            url,
            title,
            price_krw,
            fair_price_krw,
            target_price_krw,
            drop_rate_percent,
            trigger_reason,
            message,
            status,
            send_attempts
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', 0)
        """,
        (
            _normalize_optional_text(user_id),
            _normalize_optional_int(watch_rule_id),
            _normalize_optional_int(analysis_job_id),
            _normalize_optional_text(product_id),
            _normalize_optional_text(url),
            _normalize_optional_text(title),
            _normalize_optional_int(price_krw),
            _normalize_optional_int(fair_price_krw),
            _normalize_optional_int(target_price_krw),
            _normalize_optional_float(drop_rate_percent),
            _normalize_optional_text(trigger_reason),
            _normalize_optional_text(message),
        ),
    )
    return {
        "created": True,
        "alert_id": int(cursor.lastrowid),
    }


def save_listing_analysis_result(
    cursor,
    *,
    analysis_job_id,
    watch_rule_id,
    trigger_reason,
    search_keyword,
    title,
    parsed_spec,
    listing_price_krw,
    fair_price_krw,
    is_alert_target,
    matched_watch_rule,
    alert_created,
):
    parsed_spec = parsed_spec or {}

    normalized_title = _normalize_optional_text(title) or "UNKNOWN"
    normalized_product_type = _normalize_optional_text(parsed_spec.get("product_type")) or "UNKNOWN"
    normalized_chip = _normalize_optional_text(parsed_spec.get("chip")) or "UNKNOWN"
    normalized_screen_inch = _normalize_optional_int(parsed_spec.get("screen_inch")) or 0
    normalized_ram_gb = _normalize_optional_int(parsed_spec.get("ram_gb")) or 0
    normalized_ssd_gb = _normalize_optional_int(parsed_spec.get("ssd_gb")) or 0
    normalized_listing_price_krw = _normalize_optional_int(listing_price_krw) or 0
    normalized_fair_price_krw = _normalize_optional_int(fair_price_krw) or 0

    diff_amount_krw = normalized_fair_price_krw - normalized_listing_price_krw
    diff_ratio = 0.0
    if normalized_fair_price_krw > 0:
        diff_ratio = (diff_amount_krw / normalized_fair_price_krw) * 100

    try:
        cursor.execute(
            """
            INSERT INTO listing_analysis_results (
                analysis_job_id,
                watch_rule_id,
                trigger_reason,
                search_keyword,
                title,
                product_type,
                chip,
                screen_inch,
                ram_gb,
                ssd_gb,
                listing_price_krw,
                fair_price_krw,
                diff_amount_krw,
                diff_ratio,
                is_alert_target,
                matched_watch_rule,
                alert_created
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                _normalize_optional_int(analysis_job_id),
                _normalize_optional_int(watch_rule_id),
                _normalize_optional_text(trigger_reason),
                _normalize_optional_text(search_keyword),
                normalized_title,
                normalized_product_type,
                normalized_chip,
                normalized_screen_inch,
                normalized_ram_gb,
                normalized_ssd_gb,
                normalized_listing_price_krw,
                normalized_fair_price_krw,
                diff_amount_krw,
                round(diff_ratio, 2),
                bool(is_alert_target),
                bool(matched_watch_rule),
                bool(alert_created),
            ),
        )
        return {
            "inserted": True,
            "analysis_result_id": int(cursor.lastrowid),
            "diff_ratio": round(diff_ratio, 2),
        }
    except Exception as exc:
        if "Unknown column" not in str(exc):
            raise

    cursor.execute(
        """
        INSERT INTO listing_analysis_results (
            title,
            product_type,
            chip,
            screen_inch,
            ram_gb,
            ssd_gb,
            listing_price_krw,
            fair_price_krw,
            diff_amount_krw,
            diff_ratio,
            is_alert_target
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            normalized_title,
            normalized_product_type,
            normalized_chip,
            normalized_screen_inch,
            normalized_ram_gb,
            normalized_ssd_gb,
            normalized_listing_price_krw,
            normalized_fair_price_krw,
            diff_amount_krw,
            round(diff_ratio, 2),
            bool(is_alert_target),
        ),
    )
    return {
        "inserted": True,
        "analysis_result_id": int(cursor.lastrowid),
        "diff_ratio": round(diff_ratio, 2),
    }


def _mark_seen_product_status(product_id, status):
    normalized_product_id = _normalize_optional_int(product_id)
    if normalized_product_id is None:
        return

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        mark_seen_product_analyzed(cursor, normalized_product_id, status=status)
        connection.commit()
    except Exception as exc:
        print(f"[analysis_pipeline] seen analyzed 상태 갱신 실패: {exc}")
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def analyze_product_for_watch_rule(job):
    if not isinstance(job, dict):
        raise ValueError("invalid_job")

    job_id = _normalize_optional_int(job.get("id"))
    user_id = _normalize_optional_text(job.get("user_id")) or DEFAULT_USER_ID
    watch_rule_id = _normalize_optional_int(job.get("watch_rule_id"))
    trigger_reason = _normalize_optional_text(job.get("trigger_reason"))
    product_id = _normalize_optional_text(job.get("product_id"))
    url = _normalize_optional_text(job.get("url"))
    search_keyword = _normalize_optional_text(job.get("search_keyword"))

    if not url:
        raise ValueError("analysis_job_url_missing")

    html = fetch_html(url)
    parsed_page = parse_joongna_listing_page(html)

    title = parsed_page.get("title")
    description = parsed_page.get("description")
    listing_price_krw = _normalize_optional_int(parsed_page.get("listing_price_krw"))
    self_check_fields = parsed_page.get("self_check_fields") or {}

    parsing_source_text = f"{title or ''} {description or ''}".strip()
    parsed_spec = parse_listing_title(parsing_source_text, self_check_fields=self_check_fields)
    risk_result = analyze_risk(parsing_source_text, self_check_fields=self_check_fields)

    watch_rule = _get_watch_rule_by_id(watch_rule_id) if watch_rule_id is not None else None

    matched_watch_rule = True
    if watch_rule is not None:
        matched_watch_rule = bool(parsed_spec.get("parse_success")) and matches_watch_rule(parsed_spec, watch_rule)

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        fair_price_krw, target_price_krw, alert_drop_rate_percent = _resolve_price_rules(
            cursor,
            user_id,
            parsed_spec,
            watch_rule,
        )

        drop_rate_percent = None
        if fair_price_krw is not None and fair_price_krw > 0 and listing_price_krw is not None:
            drop_rate_percent = ((fair_price_krw - listing_price_krw) / fair_price_krw) * 100

        price_condition_met = True
        if target_price_krw is not None and listing_price_krw is not None:
            price_condition_met = listing_price_krw <= target_price_krw

        drop_condition_met = True
        if alert_drop_rate_percent is not None and drop_rate_percent is not None:
            drop_condition_met = drop_rate_percent >= alert_drop_rate_percent
        elif alert_drop_rate_percent is not None and drop_rate_percent is None:
            drop_condition_met = False

        is_alert_target = False
        if matched_watch_rule:
            has_price_reference = fair_price_krw is not None and fair_price_krw > 0
            if has_price_reference and listing_price_krw is not None and price_condition_met and drop_condition_met:
                if target_price_krw is not None or alert_drop_rate_percent is not None:
                    is_alert_target = True

        alert_create_result = {
            "created": False,
            "alert_id": None,
        }
        if is_alert_target:
            alert_create_result = maybe_create_alert_event(
                cursor,
                analysis_job_id=job_id,
                user_id=user_id,
                watch_rule_id=watch_rule_id,
                product_id=product_id,
                url=url,
                title=title,
                price_krw=listing_price_krw,
                fair_price_krw=fair_price_krw,
                target_price_krw=target_price_krw,
                drop_rate_percent=drop_rate_percent,
                trigger_reason=trigger_reason,
                message=_build_alert_message(
                    title=title,
                    listing_price_krw=listing_price_krw or 0,
                    fair_price_krw=fair_price_krw or 0,
                    drop_rate_percent=drop_rate_percent,
                    url=url,
                ),
            )

        result_save = save_listing_analysis_result(
            cursor,
            analysis_job_id=job_id,
            watch_rule_id=watch_rule_id,
            trigger_reason=trigger_reason,
            search_keyword=search_keyword,
            title=title,
            parsed_spec=parsed_spec,
            listing_price_krw=listing_price_krw,
            fair_price_krw=fair_price_krw,
            is_alert_target=is_alert_target,
            matched_watch_rule=matched_watch_rule,
            alert_created=bool(alert_create_result.get("created")),
        )

        save_success_log(
            cursor,
            user_id=user_id,
            url=url,
            source="joongna",
            title=_normalize_optional_text(title) or "UNKNOWN",
            listing_price_krw=listing_price_krw or 0,
            parsed_spec=parsed_spec,
            fair_price_krw=fair_price_krw or 0,
            diff_ratio=_normalize_optional_float(result_save.get("diff_ratio")) or 0.0,
            is_alert_target=bool(is_alert_target),
            risk_result=risk_result,
        )

        connection.commit()

        return {
            "ok": True,
            "analysis_job_id": job_id,
            "watch_rule_id": watch_rule_id,
            "product_id": product_id,
            "url": url,
            "title": title,
            "listing_price_krw": listing_price_krw,
            "fair_price_krw": fair_price_krw,
            "target_price_krw": target_price_krw,
            "drop_rate_percent": drop_rate_percent,
            "alert_drop_rate_percent": alert_drop_rate_percent,
            "matched_watch_rule": matched_watch_rule,
            "is_alert_target": is_alert_target,
            "alert_created": bool(alert_create_result.get("created")),
            "alert_event_id": alert_create_result.get("alert_id"),
        }
    except Exception:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def process_analysis_job(job):
    job_id = _normalize_optional_int(job.get("id")) if isinstance(job, dict) else None
    if job_id is None:
        raise ValueError("invalid_job")

    mark_analysis_job_started(job_id)

    try:
        result = analyze_product_for_watch_rule(job)
        mark_analysis_job_done(job_id)
        _mark_seen_product_status(job.get("product_id"), "analyzed")
        return {
            "ok": True,
            "job_id": job_id,
            "result": result,
        }
    except Exception as exc:
        mark_analysis_job_failed(job_id, str(exc))
        _mark_seen_product_status(job.get("product_id"), "analysis_failed")
        return {
            "ok": False,
            "job_id": job_id,
            "reason": str(exc),
        }


def process_pending_analysis_jobs(limit=20):
    jobs = get_pending_analysis_jobs(limit=limit)
    stats = {
        "fetched": len(jobs),
        "done": 0,
        "failed": 0,
        "results": [],
    }

    for job in jobs:
        try:
            result = process_analysis_job(job)
            stats["results"].append(result)
            if result.get("ok"):
                stats["done"] += 1
            else:
                stats["failed"] += 1
        except Exception as exc:
            job_id = _normalize_optional_int(job.get("id")) if isinstance(job, dict) else None
            if job_id is not None:
                try:
                    mark_analysis_job_failed(job_id, str(exc))
                except Exception:
                    pass
            stats["failed"] += 1
            stats["results"].append(
                {
                    "ok": False,
                    "job_id": job_id,
                    "reason": str(exc),
                }
            )

    return stats
