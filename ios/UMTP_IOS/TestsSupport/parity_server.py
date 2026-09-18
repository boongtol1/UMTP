#!/usr/bin/env python3
"""Loopback-only contract fixture for XCTest UI flows; never connects to UMTP.

Run: UMTP_SIMULATOR_ID=<simulator-uuid> python3 ios/UMTP_IOS/TestsSupport/parity_server.py
State is in memory and POST /__reset clears only these fictional fixtures.
The optional /__simulate-push endpoint injects one fixed payload into that Simulator;
it does not contact APNs, Firebase, or the production server.
"""
import copy
import json
import os
import plistlib
import re
import subprocess
import threading
import uuid
from decimal import Decimal, ROUND_HALF_UP
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from xml.parsers.expat import ExpatError

LOCK = threading.RLock()
PUSH_TITLE = "UMTP 검증 알림"
COLD_LAUNCH_BUNDLE_ID = "boongtol.UMTP-IOS"
COLD_LAUNCH_FIXTURE_URL = "http://127.0.0.1:18765"


def simulator_id():
    configured = os.environ.get("UMTP_SIMULATOR_ID", "")
    try:
        return str(uuid.UUID(configured))
    except ValueError:
        return None


def simulate_push():
    target = simulator_id()
    if target is None:
        return 503, {"ok": False, "reason": "simulator_not_configured"}
    payload = {"aps": {"alert": {"title": PUSH_TITLE, "body": "검증용 맥북 에어 M1 · 500,000원"},
                       "sound": "default"}, "alert_id": "101"}
    try:
        result = subprocess.run(
            ["/usr/bin/xcrun", "simctl", "push", target, "boongtol.UMTP-IOS", "-"],
            input=json.dumps(payload, ensure_ascii=False), text=True, capture_output=True,
            timeout=15, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 503, {"ok": False, "reason": "simulator_push_unavailable"}
    if result.returncode != 0:
        return 503, {"ok": False, "reason": "simulator_push_failed"}
    with LOCK:
        STATE["events"].append(dict(method="POST", path="/__simulate-push", body={"alert_id": 101}, transport="simctl"))
    return 200, {"ok": True, "transport": "simctl", "alert_id": 101}


def simulator_clipboard():
    target = simulator_id()
    if target is None:
        return 503, {"ok": False, "reason": "simulator_not_configured"}
    try:
        result = subprocess.run(
            ["/usr/bin/xcrun", "simctl", "pbpaste", target],
            text=True, capture_output=True, timeout=10, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 503, {"ok": False, "reason": "simulator_clipboard_unavailable"}
    if result.returncode != 0:
        return 503, {"ok": False, "reason": "simulator_clipboard_failed"}
    return 200, {"text": result.stdout}


def cold_launch_status():
    target = simulator_id()
    status = dict(ready=False, simulator_configured=target is not None,
                  app_installed=False, bundle_identifier_matches=False,
                  simulator_platform_matches=False, fixture_url_matches=False,
                  debug_build_matches=False,
                  reason="simulator_not_configured")
    if target is None:
        return status
    try:
        result = subprocess.run(
            ["/usr/bin/xcrun", "simctl", "get_app_container", target, COLD_LAUNCH_BUNDLE_ID, "app"],
            text=True, capture_output=True, timeout=10, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        status["reason"] = "simulator_query_unavailable"
        return status
    if result.returncode != 0:
        status["reason"] = "app_not_installed"
        return status
    bundle_path = result.stdout.strip()
    if not os.path.isabs(bundle_path):
        status["reason"] = "installed_app_metadata_unavailable"
        return status
    status["app_installed"] = True
    try:
        # Inspect only the installed bundle's metadata. Do not return paths or plist contents.
        with open(os.path.join(bundle_path, "Info.plist"), "rb") as plist_file:
            info = plistlib.load(plist_file)
    except (OSError, ValueError, plistlib.InvalidFileException, ExpatError):
        status["reason"] = "installed_app_metadata_unavailable"
        return status
    if not isinstance(info, dict):
        status["reason"] = "installed_app_metadata_unavailable"
        return status
    status["bundle_identifier_matches"] = info.get("CFBundleIdentifier") == COLD_LAUNCH_BUNDLE_ID
    status["simulator_platform_matches"] = info.get("DTPlatformName") == "iphonesimulator"
    status["fixture_url_matches"] = info.get("UMTPParityFixtureURL") == COLD_LAUNCH_FIXTURE_URL
    conditions = info.get("UMTPParityCompilationConditions")
    status["debug_build_matches"] = isinstance(conditions, str) and "DEBUG" in conditions.split()
    status["ready"] = all(status[key] for key in (
        "bundle_identifier_matches", "simulator_platform_matches", "fixture_url_matches",
        "debug_build_matches"))
    status["reason"] = "ready" if status["ready"] else "fixture_build_required"
    return status


UNITS = [dict(product_type="MacBook Air", chip="M1", screen_inch=13, ram_gb=8, ssd_gb=256),
         dict(product_type="Mac mini", chip="M4", screen_inch=0, ram_gb=16, ssd_gb=256)]
# Exercise the actual seed catalog, including generation-specific RAM/SSD choices.
MACBOOK_PRO_SEED = Path(__file__).resolve().parents[3] / "umtp/sql/seed_silicon_macbook_pro_fair_prices.sql"
MACBOOK_PRO_PRICES = {}
for chip, screen, ram, ssd, price in re.findall(
        r"\('MacBook Pro', '([^']+)', (\d+), (\d+), (\d+), (\d+)\)",
        MACBOOK_PRO_SEED.read_text(encoding="utf-8")):
    unit = dict(product_type="MacBook Pro", chip=chip, screen_inch=int(screen), ram_gb=int(ram), ssd_gb=int(ssd))
    UNITS.append(unit)
    MACBOOK_PRO_PRICES[(chip, int(screen), int(ram), int(ssd))] = int(price)
if not MACBOOK_PRO_PRICES:
    raise ValueError("MacBook Pro fixture requires the fair-price SQL seed")
ALERT = dict(id=101, alert_event_id=101, user_id="parity-fixture-user", title="검증용 맥북 에어 M1",
             product_type="MacBook Air", chip="M1", screen_inch=13, ram_gb=8, ssd_gb=256,
             listing_price_krw=500000, user_market_price_krw=800000, fair_price_krw=800000,
             alert_target_price_krw=640000, alert_drop_rate_percent=20, alert_price_direction="BELOW_OR_EQUAL",
             alert_type_label="새 매물 알림", risk_level="low", risk_keywords=["직거래"],
             fraud_probability=0.15, fraud_probability_v1=0.1, fraud_probability_v2=0.2, fraud_probability_v3=0.15,
             fraud_probability_comparison_text="v1 10% → v2 20% → v3 15%", source="joongna",
             body_text="실제 서비스와 연결되지 않은 UI 검증 매물입니다. 배터리와 거래 내용을 확인합니다.",
             product_url="https://web.joongna.com/product/123456", created_at="2026-09-15 15:00:00", is_read=False)
TRADE = dict(id=None, source="joongna", product_id="123456", title="검증용 맥북 에어 M1",
             product_url="https://web.joongna.com/product/123456", current_stage="DISCOVERED",
             product_type="MacBook Air", chip="M1", screen_inch=13, ram_gb=8, ssd_gb=256,
             listing_price_krw=500000, seller_nickname="검증 판매자", fair_price_krw=800000,
             body_text="자동채움 검증 본문", image_urls=[], seller_location="서울")


def reset():
    global STATE
    STATE = dict(alerts=[copy.deepcopy(ALERT)], archived=[], settings=[], purchased=[], completed=[], events=[], fail=False)
    for index, unit in enumerate(UNITS):
        price = MACBOOK_PRO_PRICES.get(tuple(unit[key] for key in ("chip", "screen_inch", "ram_gb", "ssd_gb")), 800000) \
            if unit["product_type"] == "MacBook Pro" else 800000
        name = {"MacBook Air": "맥북 에어", "Mac mini": "맥미니", "MacBook Pro": "맥북 프로"}[unit["product_type"]]
        keyword = f"{name} {unit['chip']}"
        STATE["settings"].append(dict(**unit, id=index + 1, system_fair_price_krw=price,
            user_fair_price_krw=price, effective_fair_price_krw=price, user_alert_drop_rate_percent=20,
            effective_alert_drop_rate_percent=20, effective_target_buy_price_krw=price * 4 // 5,
            user_target_buy_price_krw=price * 4 // 5, enabled=True, has_user_override=True,
            priority="NORMAL", recommended_search_keyword=keyword, effective_search_keyword=keyword,
            user_alert_price_direction="BELOW_OR_EQUAL", poll_interval_seconds=60))


def seed_trade_history():
    common = dict(TRADE, user_id="parity-fixture-user", purchased_at="2026-09-10 10:00:00",
                  purchase_price_krw=450000, transport_cost_krw=2000, shipping_cost_krw=3000,
                  total_cost_krw=455000, serial_number="FIXTURE-SERIAL", updated_at="2026-09-14 12:00:00")
    STATE["completed"] = [
        dict(common, id=401, product_id="completed-401", title="완료 거래 맥북 에어 401",
             current_stage="SOLD", sold_at="2026-09-14 12:00:00", sale_price_krw=620000),
        dict(common, id=402, product_id="completed-402", title="완료 거래 맥북 에어 402",
             current_stage="SOLD", sold_at="2026-09-13 12:00:00", sale_price_krw=610000),
        dict(common, id=490, user_id="other-fixture-user", product_id="other-490",
             title="다른 사용자 완료 거래", current_stage="SOLD",
             sold_at="2026-09-14 12:00:00", sale_price_krw=600000),
    ]
    STATE["purchased"] = [
        dict(common, id=403, product_id="keep-403", title="보유 거래 맥북 에어 403", current_stage="KEEP"),
        dict(common, id=404, product_id="purchase-404", title="구매 거래 맥북 에어 404", current_stage="INSPECTED"),
        dict(common, id=491, user_id="other-fixture-user", product_id="other-491",
             title="다른 사용자 보유 거래", current_stage="KEEP"),
    ]


def save_trade(row, updates, mode):
    row = copy.deepcopy(row)
    row.update(updates)
    row["total_cost_krw"] = sum(int(row.get(key, 0) or 0)
                                for key in ("purchase_price_krw", "transport_cost_krw", "shipping_cost_krw"))
    if updates.get("current_stage"):
        row["current_stage"] = updates["current_stage"]
    elif mode == "resale":
        if row.get("sold_at") or row.get("sale_price_krw") is not None:
            row["current_stage"] = "SOLD"
        elif any(row.get(key) for key in ("resale_platform", "resale_url", "resale_listing_price_krw")):
            row["current_stage"] = "RESALE_LISTED"
    elif set(updates).intersection({"purchased_at", "purchase_price_krw", "transport_cost_krw",
            "shipping_cost_krw", "purchase_method", "purchase_location", "payment_method",
            "inspection_notes", "serial_number", "model_number", "battery_cycle_count",
            "battery_health_percent", "activation_lock_off", "mdm_lock_none"}):
        row["current_stage"] = "INSPECTED"
    for collection in ("completed", "purchased"):
        STATE[collection] = [item for item in STATE[collection] if item["id"] != row["id"]]
    STATE["completed" if row.get("current_stage") == "SOLD" else "purchased"].append(row)
    return dict(ok=True, id=row["id"], row=row)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Do not log request payloads, user IDs or server credentials.
        pass

    def do_GET(self):
        self.handle_request()

    def do_POST(self):
        self.handle_request()

    def do_PATCH(self):
        self.handle_request()

    def handle_request(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length)) if length else {}
        except ValueError:
            return self.reply(400, {"ok": False})
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        if path == "/__push-status":
            return self.reply(200, {"configured": simulator_id() is not None})
        if path == "/__simulate-push":
            if self.command != "POST" or self.client_address[0] not in {"127.0.0.1", "::1"}:
                return self.reply(405, {"ok": False})
            status, payload = simulate_push()
            return self.reply(status, payload)
        if path == "/__clipboard":
            if self.command != "GET" or self.client_address[0] not in {"127.0.0.1", "::1"}:
                return self.reply(405, {"ok": False})
            status, payload = simulator_clipboard()
            return self.reply(status, payload)
        if path == "/__cold-launch-status":
            if self.command != "GET" or self.client_address[0] not in {"127.0.0.1", "::1"}:
                return self.reply(405, {"ok": False})
            return self.reply(200, cold_launch_status())
        with LOCK:
            if path == "/__reset":
                reset()
                return self.reply(200, {"ok": True})
            if path == "/__events":
                return self.reply(200, {"events": STATE["events"]})
            if path == "/__fail":
                STATE["fail"] = bool(body.get("enabled"))
                return self.reply(200, {"ok": True})
            if path == "/__scenario/trade-history":
                if self.command != "POST":
                    return self.reply(405, {"ok": False})
                seed_trade_history()
                return self.reply(200, {"ok": True})
            if path == "/__external-link-fixture":
                if self.command != "POST":
                    return self.reply(405, {"ok": False})
                product_url = "http://127.0.0.1:18765/__listing/101"
                for item in STATE["alerts"]:
                    if item["id"] == 101:
                        item["product_url"] = product_url
                return self.reply(200, {"ok": True, "product_url": product_url})
            STATE["events"].append(dict(method=self.command, path=path, body=body, query=query))
            if STATE["fail"]:
                return self.reply(503, {"ok": False, "reason": "fixture outage"})
            if path == "/__listing/101" and self.command == "GET":
                return self.reply_html("<!doctype html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'><title>UMTP Local Listing 101</title></head><body><h1>UMTP Local Listing 101</h1><p>Local UI test listing.</p></body></html>")
            result = self.route(path, body, query)
        self.reply(200 if result is not None else 404, result or {"ok": False})

    def route(self, path, body, query=None):
        if path == "/users/register":
            return dict(ok=True, user_id=body["user_id"])
        if path == "/macbook-air-units":
            return dict(ok=True, units=UNITS)
        if path == "/user-fair-prices":
            return dict(ok=True, items=STATE["settings"])
        if path == "/user-fair-prices/upsert":
            for item in STATE["settings"]:
                if all(item[k] == body[k] for k in ("product_type", "chip", "screen_inch", "ram_gb", "ssd_gb")):
                    item.update({"user_" + key: value for key, value in body.items()
                                 if key in ("fair_price_krw", "alert_drop_rate_percent", "alert_price_direction", "min_price_krw", "max_price_krw")})
                    item.update({key: value for key, value in body.items() if key in ("enabled", "priority", "condition_change_candidate_notice_enabled")})
                    target = int((Decimal(str(body["fair_price_krw"])) * (1 - Decimal(str(body["alert_drop_rate_percent"])) / 100)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
                    item.update(effective_fair_price_krw=body["fair_price_krw"], user_target_buy_price_krw=target,
                                effective_target_buy_price_krw=target, effective_alert_drop_rate_percent=body["alert_drop_rate_percent"],
                                custom_search_keyword=body.get("search_keyword"), effective_search_keyword=body.get("search_keyword") or item["recommended_search_keyword"])
            return dict(ok=True, immediate_poll_requested=True, missed_candidate_count=0)
        if path.endswith("/refresh"):
            return dict(ok=True, refreshed_rule_count=2, rule_id=1)
        if path == "/alerts":
            return dict(ok=True, items=STATE["alerts"])
        if path == "/alert-events/read/grouped":
            groups = {}
            for item in STATE["archived"]:
                groups.setdefault(item["chip"], {}).setdefault(str(item["screen_inch"]), []).append(item)
            return dict(ok=True, groups=groups)
        if path.endswith("/read") or path == "/alert-events/read-all":
            ids = [item["id"] for item in STATE["alerts"]] if path.endswith("read-all") else [int(path.split("/")[2])]
            for item in list(STATE["alerts"]):
                if item["id"] in ids:
                    STATE["alerts"].remove(item)
                    STATE["archived"].append(dict(item, is_read=True, read_archive_event_id=1000 + item["id"], read_at="2026-09-15 16:00:00"))
            return dict(ok=True, is_read=True, updated_count=len(ids))
        if path.startswith("/alert-events/read/archive/clear-"):
            ids = body.get("alert_event_ids", [item["id"] for item in STATE["archived"]])
            STATE["archived"] = [item for item in STATE["archived"] if item["id"] not in ids]
            return dict(ok=True, cleared_count=len(ids), skipped_count=0)
        if path.startswith("/trade-journeys/start-"):
            return dict(ok=True, existing=False, row=TRADE)
        parts = [unquote(part) for part in path.strip("/").split("/")]
        if len(parts) >= 4 and parts[0] == "users" and parts[2] == "resale-trade-journeys":
            user = parts[1]
            if len(parts) == 4 and self.command == "GET" and parts[3] in {"completed", "purchased"}:
                collection = parts[3]
                rows = [row for row in STATE[collection] if row.get("user_id") == user
                        and (collection == "completed" or row.get("purchased_at"))]
                date = "sold_at" if collection == "completed" else "purchased_at"
                rows.sort(key=lambda row: (row.get(date) or row.get("updated_at") or "", row["id"]), reverse=True)
                limit = int((query or {}).get("limit", ["200"])[0])
                return dict(ok=True, items=rows[:200 if limit <= 0 else min(limit, 1000)])
            if len(parts) == 5 and self.command == "PATCH" and parts[3] == "completed" and parts[4] in {"delete-selected", "delete-all"}:
                ids = set(body.get("journey_ids", []))
                deleted = [row for row in STATE["completed"] if row.get("user_id") == user
                           and row.get("current_stage") == "SOLD"
                           and (parts[4] == "delete-all" or row["id"] in ids)]
                deleted_ids = {row["id"] for row in deleted}
                STATE["completed"] = [row for row in STATE["completed"] if row["id"] not in deleted_ids]
                return dict(ok=True, deleted_count=len(deleted))
            if len(parts) == 5 and self.command == "PATCH" and parts[3].isdigit() and parts[4] in {"purchase", "resale", "sold"}:
                row = next((row for row in STATE["purchased"] + STATE["completed"]
                            if row["id"] == int(parts[3]) and row.get("user_id") == user), None)
                if row is None:
                    return dict(ok=False, reason="not_found")
                return save_trade(row, body.get("updates", {}), "purchase" if parts[4] == "purchase" else "resale")
        if self.command == "POST" and path in {"/resale-trades/after-purchase/upsert", "/resale-trades/after-resale/upsert"}:
            rows = STATE["purchased"] + STATE["completed"]
            row = next((row for row in rows if row.get("user_id") == body.get("user_id")
                        and row.get("source") == body.get("source")
                        and row.get("product_id") == body.get("product_id")), None)
            if row is None:
                row = dict(TRADE, id=max([300] + [row["id"] for row in rows]) + 1,
                           user_id=body["user_id"], source=body.get("source", "joongna"),
                           product_id=body.get("product_id", TRADE["product_id"]))
            return save_trade(row, body.get("updates", {}), "resale" if "after-resale" in path else "purchase")
        return None

    def reply_html(self, html):
        encoded = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def reply(self, status, payload):
        encoded = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


if __name__ == "__main__":
    reset()
    print("UMTP fixture listening on http://127.0.0.1:18765", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 18765), Handler).serve_forever()
