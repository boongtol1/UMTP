import argparse
import os
import sys
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from src.notification_worker import process_pending_alert_events
except ModuleNotFoundError:
    from notification_worker import process_pending_alert_events


DEFAULT_INTERVAL_SECONDS = 3
DEFAULT_LIMIT = 20


def parse_args():
    parser = argparse.ArgumentParser(description="UMTP notification worker")
    parser.add_argument("--once", action="store_true", help="1회 처리 후 종료")
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL_SECONDS,
        help=f"worker 주기(초), 기본값 {DEFAULT_INTERVAL_SECONDS}",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"한 번에 처리할 최대 alert 수, 기본값 {DEFAULT_LIMIT}",
    )
    return parser.parse_args()


def _print_summary(stats):
    print("[notification_worker] 요약")
    print(
        f"fetched={stats.get('fetched', 0)}, "
        f"sent={stats.get('sent', 0)}, "
        f"app_only={stats.get('app_only', 0)}, "
        f"failed={stats.get('failed', 0)}"
    )


def main():
    args = parse_args()

    if args.interval <= 0:
        raise ValueError("--interval은 1 이상의 정수여야 합니다.")
    if args.limit <= 0:
        raise ValueError("--limit은 1 이상의 정수여야 합니다.")

    print("notification worker 시작")
    print(f"interval={args.interval}s, once={args.once}, limit={args.limit}")

    try:
        while True:
            stats = process_pending_alert_events(limit=args.limit)
            _print_summary(stats)

            if args.once:
                break

            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("사용자 요청으로 notification worker를 종료합니다.")


if __name__ == "__main__":
    main()
