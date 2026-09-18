import argparse
import os
import sys
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from src.content_refresh_service import process_next_content_refresh
    from src.search_body_backfill import process_next_search_body_backfill
except ModuleNotFoundError:
    from content_refresh_service import process_next_content_refresh
    from search_body_backfill import process_next_search_body_backfill


DEFAULT_INTERVAL_SECONDS = 5


def parse_args():
    parser = argparse.ArgumentParser(description="UMTP low-priority listing content refresh worker")
    parser.add_argument("--once", action="store_true", help="내용 갱신과 누락 본문 보강을 각각 최대 한 건 처리한 후 종료")
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL_SECONDS,
        help=f"처리할 작업이 없을 때 대기(초), 기본값 {DEFAULT_INTERVAL_SECONDS}",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.interval <= 0:
        raise ValueError("--interval은 1 이상의 정수여야 합니다.")
    print(f"content refresh worker 시작 interval={args.interval}s, once={args.once}")
    try:
        while True:
            result = process_next_content_refresh()
            print(f"[content_refresh_worker] {result}")
            body_result = process_next_search_body_backfill()
            print(f"[search_body_backfill_worker] {body_result}")
            if args.once:
                return
            if not result.get("processed") and not body_result.get("processed"):
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print("사용자 요청으로 content refresh worker를 종료합니다.")


if __name__ == "__main__":
    main()
