import argparse
import os
import sys
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from src.joongna_polling_service import poll_once
except ModuleNotFoundError:
    from joongna_polling_service import poll_once


DEFAULT_INTERVAL_SECONDS = 60


def parse_args():
    parser = argparse.ArgumentParser(
        description="중고나라 Search API polling 기반 UMTP 분석 실행기",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="1회만 polling 후 종료",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL_SECONDS,
        help=f"polling 주기(초), 기본값 {DEFAULT_INTERVAL_SECONDS}",
    )
    parser.add_argument(
        "--search-word",
        dest="search_words",
        action="append",
        help="검색어(여러 번 지정 가능)",
    )
    parser.add_argument(
        "--user-id",
        default=None,
        help="설정 user_id 필터(미지정 시 전체 due enabled 설정 대상)",
    )
    return parser.parse_args()


def _print_summary(stats):
    print("[polling] 요약")
    print(
        f"fetched={stats.get('fetched_items', 0)}, "
        f"new={stats.get('new_items', 0)}, "
        f"seen_skip={stats.get('skipped_seen', 0)}, "
        f"no_seq_skip={stats.get('skipped_no_seq', 0)}"
    )
    print(
        f"analysis_success={stats.get('analysis_success', 0)}, "
        f"analysis_duplicate={stats.get('analysis_duplicate', 0)}, "
        f"analysis_failed={stats.get('analysis_failed', 0)}, "
        f"rule_mismatch_skip={stats.get('skipped_rule_mismatch', 0)}, "
        f"price_condition_skip={stats.get('skipped_price_condition', 0)}, "
        f"search_errors={stats.get('search_errors', 0)}, "
        f"db_errors={stats.get('db_errors', 0)}, "
        f"settings_due={stats.get('settings_due', stats.get('watch_rules_due', 0))}"
    )
    print(
        f"group_count={stats.get('polling_group_count', 0)}, "
        f"external_calls={stats.get('external_api_calls', 0)}, "
        f"matched_watch_rules={stats.get('matched_watch_rules', 0)}, "
        f"created_alerts={stats.get('created_alert_count', 0)}"
    )
    print(
        f"fetched_count={stats.get('fetched_count', 0)}, "
        f"new_count={stats.get('new_count', 0)}, "
        f"changed_count={stats.get('changed_count', 0)}, "
        f"unchanged_skipped_count={stats.get('unchanged_skipped_count', 0)}, "
        f"analyzed_count={stats.get('analyzed_count', 0)}, "
        f"alert_created_count={stats.get('alert_created_count', 0)}"
    )
    print(
        f"search_results_saved={stats.get('search_results_saved', 0)}, "
        f"search_results_save_errors={stats.get('search_results_save_errors', 0)}"
    )


def main():
    args = parse_args()

    if args.interval <= 0:
        raise ValueError("--interval은 1 이상의 정수여야 합니다.")

    print("중고나라 polling 시작")
    user_scope = args.user_id if isinstance(args.user_id, str) and args.user_id.strip() else "ALL"
    print(f"interval={args.interval}s, once={args.once}, user_scope={user_scope}")

    try:
        while True:
            stats = poll_once(
                user_id=args.user_id,
                search_words=args.search_words,
                inline_process=False,
            )
            _print_summary(stats)

            if args.once:
                break

            print(f"다음 polling까지 {args.interval}초 대기")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("사용자 요청으로 polling을 종료합니다.")


if __name__ == "__main__":
    main()
