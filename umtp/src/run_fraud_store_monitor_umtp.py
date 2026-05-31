import argparse
import os
import sys
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from src.fraud_store_monitor_service import (
        DEFAULT_MONITOR_INTERVAL_SECONDS,
        get_fraud_store_monitor_config,
        run_fraud_store_monitor_once,
    )
except ModuleNotFoundError:
    from fraud_store_monitor_service import (
        DEFAULT_MONITOR_INTERVAL_SECONDS,
        get_fraud_store_monitor_config,
        run_fraud_store_monitor_once,
    )


def parse_args():
    parser = argparse.ArgumentParser(description="UMTP fraud store monitor worker")
    parser.add_argument("--once", action="store_true", help="1회 처리 후 종료")
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help=(
            "worker 주기(초), 미지정 시 "
            f"{DEFAULT_MONITOR_INTERVAL_SECONDS} 또는 env(FRAUD_STORE_MONITOR_INTERVAL_SECONDS)"
        ),
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=None,
        help="최근 매물 조회 범위(일), 미지정 시 env/default 사용",
    )
    parser.add_argument(
        "--min-check-interval-minutes",
        type=int,
        default=None,
        help="동일 상점 최소 체크 간격(분), 미지정 시 env/default 사용",
    )
    return parser.parse_args()


def _print_summary(stats):
    print("[fraud_store_monitor] 요약")
    print(
        f"candidate_listing_count={stats.get('candidate_listing_count', 0)}, "
        f"target_store_count={stats.get('target_store_count', 0)}, "
        f"checked_count={stats.get('checked_count', 0)}, "
        f"skipped_count={stats.get('skipped_count', 0)}"
    )
    print(
        f"active_count={stats.get('active_count', 0)}, "
        f"inactive_count={stats.get('inactive_count', 0)}, "
        f"unknown_count={stats.get('unknown_count', 0)}, "
        f"error_count={stats.get('error_count', 0)}"
    )
    print(
        f"label_candidates_upserted={stats.get('label_candidates_upserted', 0)}, "
        f"label_rows_updated={stats.get('label_rows_updated', 0)}, "
        f"store_errors={stats.get('store_errors', 0)}, "
        f"fatal_error={stats.get('fatal_error')}"
    )


def main():
    args = parse_args()
    config = get_fraud_store_monitor_config()
    interval_seconds = args.interval
    if interval_seconds is None:
        interval_seconds = int(config.get("interval_seconds") or DEFAULT_MONITOR_INTERVAL_SECONDS)

    if interval_seconds <= 0:
        raise ValueError("--interval은 1 이상의 정수여야 합니다.")
    if args.lookback_days is not None and args.lookback_days <= 0:
        raise ValueError("--lookback-days는 1 이상의 정수여야 합니다.")
    if args.min_check_interval_minutes is not None and args.min_check_interval_minutes <= 0:
        raise ValueError("--min-check-interval-minutes는 1 이상의 정수여야 합니다.")

    print("fraud store monitor worker 시작")
    print(
        f"interval={interval_seconds}s, once={args.once}, "
        f"lookback_days={args.lookback_days}, min_check_interval_minutes={args.min_check_interval_minutes}"
    )

    try:
        while True:
            stats = run_fraud_store_monitor_once(
                lookback_days=args.lookback_days,
                min_check_interval_minutes=args.min_check_interval_minutes,
            )
            _print_summary(stats)

            if args.once:
                break

            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("사용자 요청으로 fraud store monitor worker를 종료합니다.")


if __name__ == "__main__":
    main()
