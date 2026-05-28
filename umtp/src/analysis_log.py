import json
import hashlib


def _insert_url_analysis_log_v1(
    cursor,
    *,
    user_id,
    url,
    source=None,
    title=None,
    listing_price_krw=None,
    product_type=None,
    chip=None,
    screen_inch=None,
    ram_gb=None,
    ssd_gb=None,
    fair_price_krw=None,
    diff_ratio=None,
    is_alert_target=None,
    status,
    reason=None,
    body_text=None,
):
    cursor.execute(
        """
        INSERT INTO url_analysis_logs (
            user_id,
            url,
            source,
            title,
            listing_price_krw,
            product_type,
            chip,
            screen_inch,
            ram_gb,
            ssd_gb,
            fair_price_krw,
            diff_ratio,
            is_alert_target,
            status,
            reason
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            user_id,
            url,
            source,
            title,
            listing_price_krw,
            product_type,
            chip,
            screen_inch,
            ram_gb,
            ssd_gb,
            fair_price_krw,
            diff_ratio,
            is_alert_target,
            status,
            reason,
        ),
    )


def _insert_url_analysis_log_with_parser_fields(
    cursor,
    *,
    user_id,
    url,
    source=None,
    title=None,
    listing_price_krw=None,
    product_type=None,
    chip=None,
    screen_inch=None,
    ram_gb=None,
    ssd_gb=None,
    fair_price_krw=None,
    diff_ratio=None,
    is_alert_target=None,
    status,
    reason=None,
    confidence_score=None,
    screen_inch_defaulted=None,
    unit_valid=None,
    unit_validation_reason=None,
    body_text=None,
):
    cursor.execute(
        """
        INSERT INTO url_analysis_logs (
            user_id,
            url,
            source,
            title,
            listing_price_krw,
            product_type,
            chip,
            screen_inch,
            ram_gb,
            ssd_gb,
            fair_price_krw,
            diff_ratio,
            is_alert_target,
            status,
            reason,
            confidence_score,
            screen_inch_defaulted,
            unit_valid,
            unit_validation_reason
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            user_id,
            url,
            source,
            title,
            listing_price_krw,
            product_type,
            chip,
            screen_inch,
            ram_gb,
            ssd_gb,
            fair_price_krw,
            diff_ratio,
            is_alert_target,
            status,
            reason,
            confidence_score,
            screen_inch_defaulted,
            unit_valid,
            unit_validation_reason,
        ),
    )


def _safe_json_text(value):
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _is_unknown_column_error(exc):
    lowered = str(exc).lower()
    return "unknown column" in lowered or "doesn't exist" in lowered


def _normalize_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    cleaned = str(value).strip()
    return cleaned or None


def _normalize_int(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_bool(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "y", "yes", "true"}:
            return True
        if normalized in {"0", "n", "no", "false"}:
            return False
    return bool(value)


def _normalize_scalar(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    return _normalize_text(value)


def _normalize_json_like(value):
    if value is None:
        return None

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = json.loads(text)
            return json.dumps(parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        except Exception:
            return text

    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except Exception:
        return _normalize_text(value)


def _row_value(row, key, index):
    if isinstance(row, dict):
        return row.get(key)
    if isinstance(row, (tuple, list)):
        if index < len(row):
            return row[index]
    return None


def _build_url_analysis_content_signature(
    *,
    user_id,
    url,
    source=None,
    title=None,
    body_text=None,
    listing_price_krw=None,
    product_type=None,
    chip=None,
    screen_inch=None,
    ram_gb=None,
    ssd_gb=None,
    fair_price_krw=None,
    diff_ratio=None,
    is_alert_target=None,
    status=None,
    reason=None,
    confidence_score=None,
    screen_inch_defaulted=None,
    unit_valid=None,
    unit_validation_reason=None,
    risk_detected=None,
    risk_level=None,
    risk_score=None,
    risk_keywords=None,
    risk_categories=None,
    is_exchange_post=None,
    exchange_strength=None,
    exchange_keywords=None,
    trade_type=None,
):
    payload = {
        "user_id": _normalize_text(user_id),
        "url": _normalize_text(url),
        "source": _normalize_text(source),
        "title": _normalize_text(title),
        "body_text": _normalize_text(body_text),
        "listing_price_krw": _normalize_int(listing_price_krw),
        "product_type": _normalize_text(product_type),
        "chip": _normalize_text(chip),
        "screen_inch": _normalize_int(screen_inch),
        "ram_gb": _normalize_int(ram_gb),
        "ssd_gb": _normalize_int(ssd_gb),
        "fair_price_krw": _normalize_int(fair_price_krw),
        "diff_ratio": _normalize_scalar(diff_ratio),
        "is_alert_target": _normalize_bool(is_alert_target),
        "status": _normalize_text(status),
        "reason": _normalize_text(reason),
        "confidence_score": _normalize_int(confidence_score),
        "screen_inch_defaulted": _normalize_bool(screen_inch_defaulted),
        "unit_valid": _normalize_bool(unit_valid),
        "unit_validation_reason": _normalize_text(unit_validation_reason),
        "risk_detected": _normalize_bool(risk_detected),
        "risk_level": _normalize_text(risk_level),
        "risk_score": _normalize_int(risk_score),
        "risk_keywords": _normalize_json_like(risk_keywords),
        "risk_categories": _normalize_json_like(risk_categories),
        "is_exchange_post": _normalize_bool(is_exchange_post),
        "exchange_strength": _normalize_text(exchange_strength),
        "exchange_keywords": _normalize_json_like(exchange_keywords),
        "trade_type": _normalize_text(trade_type),
    }
    signature_source = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(signature_source.encode("utf-8")).hexdigest()


def _fetch_latest_url_analysis_signature(cursor, *, user_id, url):
    queries = [
        (
            """
            SELECT
                content_signature,
                source,
                title,
                body_text,
                listing_price_krw,
                product_type,
                chip,
                screen_inch,
                ram_gb,
                ssd_gb,
                fair_price_krw,
                diff_ratio,
                is_alert_target,
                status,
                reason,
                confidence_score,
                screen_inch_defaulted,
                unit_valid,
                unit_validation_reason,
                risk_detected,
                risk_level,
                risk_score,
                risk_keywords,
                risk_categories,
                is_exchange_post,
                exchange_strength,
                exchange_keywords,
                trade_type
            FROM url_analysis_logs
            WHERE user_id = %s
              AND url = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            True,
        ),
        (
            """
            SELECT
                source,
                title,
                body_text,
                listing_price_krw,
                product_type,
                chip,
                screen_inch,
                ram_gb,
                ssd_gb,
                fair_price_krw,
                diff_ratio,
                is_alert_target,
                status,
                reason,
                confidence_score,
                screen_inch_defaulted,
                unit_valid,
                unit_validation_reason,
                risk_detected,
                risk_level,
                risk_score,
                risk_keywords,
                risk_categories,
                is_exchange_post,
                exchange_strength,
                exchange_keywords,
                trade_type
            FROM url_analysis_logs
            WHERE user_id = %s
              AND url = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            False,
        ),
        (
            """
            SELECT
                source,
                title,
                listing_price_krw,
                product_type,
                chip,
                screen_inch,
                ram_gb,
                ssd_gb,
                fair_price_krw,
                diff_ratio,
                is_alert_target,
                status,
                reason
            FROM url_analysis_logs
            WHERE user_id = %s
              AND url = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            False,
        ),
    ]

    for query, has_content_signature in queries:
        try:
            cursor.execute(query, (user_id, url))
            row = cursor.fetchone()
        except Exception as exc:
            if _is_unknown_column_error(exc):
                continue
            raise

        if row is None:
            return None

        offset = 0
        if has_content_signature:
            existing_signature = _normalize_text(_row_value(row, "content_signature", 0))
            if existing_signature:
                return existing_signature
            offset = 1

        return _build_url_analysis_content_signature(
            user_id=user_id,
            url=url,
            source=_row_value(row, "source", offset + 0),
            title=_row_value(row, "title", offset + 1),
            body_text=_row_value(row, "body_text", offset + 2),
            listing_price_krw=_row_value(row, "listing_price_krw", offset + 3),
            product_type=_row_value(row, "product_type", offset + 4),
            chip=_row_value(row, "chip", offset + 5),
            screen_inch=_row_value(row, "screen_inch", offset + 6),
            ram_gb=_row_value(row, "ram_gb", offset + 7),
            ssd_gb=_row_value(row, "ssd_gb", offset + 8),
            fair_price_krw=_row_value(row, "fair_price_krw", offset + 9),
            diff_ratio=_row_value(row, "diff_ratio", offset + 10),
            is_alert_target=_row_value(row, "is_alert_target", offset + 11),
            status=_row_value(row, "status", offset + 12),
            reason=_row_value(row, "reason", offset + 13),
            confidence_score=_row_value(row, "confidence_score", offset + 14),
            screen_inch_defaulted=_row_value(row, "screen_inch_defaulted", offset + 15),
            unit_valid=_row_value(row, "unit_valid", offset + 16),
            unit_validation_reason=_row_value(row, "unit_validation_reason", offset + 17),
            risk_detected=_row_value(row, "risk_detected", offset + 18),
            risk_level=_row_value(row, "risk_level", offset + 19),
            risk_score=_row_value(row, "risk_score", offset + 20),
            risk_keywords=_row_value(row, "risk_keywords", offset + 21),
            risk_categories=_row_value(row, "risk_categories", offset + 22),
            is_exchange_post=_row_value(row, "is_exchange_post", offset + 23),
            exchange_strength=_row_value(row, "exchange_strength", offset + 24),
            exchange_keywords=_row_value(row, "exchange_keywords", offset + 25),
            trade_type=_row_value(row, "trade_type", offset + 26),
        )

    return None


def _insert_url_analysis_log(
    cursor,
    *,
    user_id,
    url,
    source=None,
    title=None,
    listing_price_krw=None,
    product_type=None,
    chip=None,
    screen_inch=None,
    ram_gb=None,
    ssd_gb=None,
    fair_price_krw=None,
    diff_ratio=None,
    is_alert_target=None,
    status,
    reason=None,
    body_text=None,
    confidence_score=None,
    screen_inch_defaulted=None,
    unit_valid=None,
    unit_validation_reason=None,
    risk_detected=None,
    risk_level=None,
    risk_score=None,
    risk_keywords=None,
    risk_categories=None,
    is_exchange_post=None,
    exchange_strength=None,
    exchange_keywords=None,
    trade_type=None,
):
    content_signature = _build_url_analysis_content_signature(
        user_id=user_id,
        url=url,
        source=source,
        title=title,
        body_text=body_text,
        listing_price_krw=listing_price_krw,
        product_type=product_type,
        chip=chip,
        screen_inch=screen_inch,
        ram_gb=ram_gb,
        ssd_gb=ssd_gb,
        fair_price_krw=fair_price_krw,
        diff_ratio=diff_ratio,
        is_alert_target=is_alert_target,
        status=status,
        reason=reason,
        confidence_score=confidence_score,
        screen_inch_defaulted=screen_inch_defaulted,
        unit_valid=unit_valid,
        unit_validation_reason=unit_validation_reason,
        risk_detected=risk_detected,
        risk_level=risk_level,
        risk_score=risk_score,
        risk_keywords=risk_keywords,
        risk_categories=risk_categories,
        is_exchange_post=is_exchange_post,
        exchange_strength=exchange_strength,
        exchange_keywords=exchange_keywords,
        trade_type=trade_type,
    )

    previous_signature = _fetch_latest_url_analysis_signature(cursor, user_id=user_id, url=url)
    if previous_signature is not None and previous_signature == content_signature:
        return

    try:
        cursor.execute(
            """
            INSERT INTO url_analysis_logs (
                user_id,
                url,
                source,
                title,
                body_text,
                listing_price_krw,
                product_type,
                chip,
                screen_inch,
                ram_gb,
                ssd_gb,
                fair_price_krw,
                diff_ratio,
                is_alert_target,
                status,
                reason,
                content_signature,
                confidence_score,
                screen_inch_defaulted,
                unit_valid,
                unit_validation_reason,
                risk_detected,
                risk_level,
                risk_score,
                risk_keywords,
                risk_categories,
                is_exchange_post,
                exchange_strength,
                exchange_keywords,
                trade_type
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                id = id
            """,
            (
                user_id,
                url,
                source,
                title,
                body_text,
                listing_price_krw,
                product_type,
                chip,
                screen_inch,
                ram_gb,
                ssd_gb,
                fair_price_krw,
                diff_ratio,
                is_alert_target,
                status,
                reason,
                content_signature,
                confidence_score,
                screen_inch_defaulted,
                unit_valid,
                unit_validation_reason,
                risk_detected,
                risk_level,
                risk_score,
                _safe_json_text(risk_keywords),
                _safe_json_text(risk_categories),
                is_exchange_post,
                exchange_strength,
                _safe_json_text(exchange_keywords),
                trade_type,
            ),
        )
        return
    except Exception as exc:
        if not _is_unknown_column_error(exc):
            raise

        try:
            cursor.execute(
                """
                INSERT INTO url_analysis_logs (
                    user_id,
                    url,
                    source,
                    title,
                    listing_price_krw,
                    product_type,
                    chip,
                    screen_inch,
                    ram_gb,
                    ssd_gb,
                    fair_price_krw,
                    diff_ratio,
                    is_alert_target,
                    status,
                    reason,
                    content_signature,
                    confidence_score,
                    screen_inch_defaulted,
                    unit_valid,
                    unit_validation_reason,
                    risk_detected,
                    risk_level,
                    risk_score,
                    risk_keywords,
                    risk_categories,
                    is_exchange_post,
                    exchange_strength,
                    exchange_keywords,
                    trade_type
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    id = id
                """,
                (
                    user_id,
                    url,
                    source,
                    title,
                    listing_price_krw,
                    product_type,
                    chip,
                    screen_inch,
                    ram_gb,
                    ssd_gb,
                    fair_price_krw,
                    diff_ratio,
                    is_alert_target,
                    status,
                    reason,
                    content_signature,
                    confidence_score,
                    screen_inch_defaulted,
                    unit_valid,
                    unit_validation_reason,
                    risk_detected,
                    risk_level,
                    risk_score,
                    _safe_json_text(risk_keywords),
                    _safe_json_text(risk_categories),
                    is_exchange_post,
                    exchange_strength,
                    _safe_json_text(exchange_keywords),
                    trade_type,
                ),
            )
            return
        except Exception as body_text_exc:
            if not _is_unknown_column_error(body_text_exc):
                raise

        try:
            _insert_url_analysis_log_with_parser_fields(
                cursor,
                user_id=user_id,
                url=url,
                source=source,
                title=title,
                listing_price_krw=listing_price_krw,
                product_type=product_type,
                chip=chip,
                screen_inch=screen_inch,
                ram_gb=ram_gb,
                ssd_gb=ssd_gb,
                fair_price_krw=fair_price_krw,
                diff_ratio=diff_ratio,
                is_alert_target=is_alert_target,
                status=status,
                reason=reason,
                body_text=body_text,
                confidence_score=confidence_score,
                screen_inch_defaulted=screen_inch_defaulted,
                unit_valid=unit_valid,
                unit_validation_reason=unit_validation_reason,
            )
            return
        except Exception as exc2:
            if not _is_unknown_column_error(exc2):
                raise

        _insert_url_analysis_log_v1(
            cursor,
            user_id=user_id,
            url=url,
            source=source,
            title=title,
            body_text=body_text,
            listing_price_krw=listing_price_krw,
            product_type=product_type,
            chip=chip,
            screen_inch=screen_inch,
            ram_gb=ram_gb,
            ssd_gb=ssd_gb,
            fair_price_krw=fair_price_krw,
            diff_ratio=diff_ratio,
            is_alert_target=is_alert_target,
            status=status,
            reason=reason,
        )


def save_success_log(
    cursor,
    *,
    user_id,
    url,
    source,
    title,
    listing_price_krw,
    parsed_spec,
    fair_price_krw,
    diff_ratio,
    is_alert_target,
    risk_result=None,
    body_text=None,
):
    risk_result = risk_result or {}
    _insert_url_analysis_log(
        cursor,
        user_id=user_id,
        url=url,
        source=source,
        title=title,
        body_text=body_text,
        listing_price_krw=listing_price_krw,
        product_type=parsed_spec.get("product_type"),
        chip=parsed_spec.get("chip"),
        screen_inch=parsed_spec.get("screen_inch"),
        ram_gb=parsed_spec.get("ram_gb"),
        ssd_gb=parsed_spec.get("ssd_gb"),
        fair_price_krw=fair_price_krw,
        diff_ratio=round(diff_ratio, 2),
        is_alert_target=is_alert_target,
        status="success",
        reason=None,
        confidence_score=parsed_spec.get("confidence_score"),
        screen_inch_defaulted=parsed_spec.get("screen_inch_defaulted"),
        unit_valid=parsed_spec.get("unit_valid"),
        unit_validation_reason=parsed_spec.get("unit_validation_reason"),
        risk_detected=risk_result.get("risk_detected"),
        risk_level=risk_result.get("risk_level"),
        risk_score=risk_result.get("risk_score"),
        risk_keywords=risk_result.get("risk_keywords"),
        risk_categories=risk_result.get("risk_categories"),
        is_exchange_post=risk_result.get("is_exchange_post"),
        exchange_strength=risk_result.get("exchange_strength"),
        exchange_keywords=risk_result.get("exchange_keywords"),
        trade_type=risk_result.get("trade_type"),
    )


def save_failed_log(
    cursor,
    *,
    user_id,
    url,
    reason,
    source=None,
    title=None,
    body_text=None,
    listing_price_krw=None,
    parsed_spec=None,
    risk_result=None,
):
    parsed_spec = parsed_spec or {}
    risk_result = risk_result or {}
    _insert_url_analysis_log(
        cursor,
        user_id=user_id,
        url=url,
        source=source,
        title=title,
        body_text=body_text,
        listing_price_krw=listing_price_krw,
        product_type=parsed_spec.get("product_type"),
        chip=parsed_spec.get("chip"),
        screen_inch=parsed_spec.get("screen_inch"),
        ram_gb=parsed_spec.get("ram_gb"),
        ssd_gb=parsed_spec.get("ssd_gb"),
        fair_price_krw=None,
        diff_ratio=None,
        is_alert_target=None,
        status="failed",
        reason=reason,
        confidence_score=parsed_spec.get("confidence_score"),
        screen_inch_defaulted=parsed_spec.get("screen_inch_defaulted"),
        unit_valid=parsed_spec.get("unit_valid"),
        unit_validation_reason=parsed_spec.get("unit_validation_reason"),
        risk_detected=risk_result.get("risk_detected"),
        risk_level=risk_result.get("risk_level"),
        risk_score=risk_result.get("risk_score"),
        risk_keywords=risk_result.get("risk_keywords"),
        risk_categories=risk_result.get("risk_categories"),
        is_exchange_post=risk_result.get("is_exchange_post"),
        exchange_strength=risk_result.get("exchange_strength"),
        exchange_keywords=risk_result.get("exchange_keywords"),
        trade_type=risk_result.get("trade_type"),
    )


def save_duplicate_log(cursor, *, user_id, url, source="joongna", reason="이미 분석된 URL"):
    _insert_url_analysis_log(
        cursor,
        user_id=user_id,
        url=url,
        source=source,
        status="duplicate",
        reason=reason,
        trade_type="sale",
    )
