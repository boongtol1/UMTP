import argparse
import time

from src.joongna_polling_service import DEFAULT_USER_ID, poll_once


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
        default=DEFAULT_USER_ID,
        help=f"분석 user_id (기본값: {DEFAULT_USER_ID})",
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
        f"search_errors={stats.get('search_errors', 0)}, "
        f"db_errors={stats.get('db_errors', 0)}"
    )


def main():
    args = parse_args()

    if args.interval <= 0:
        raise ValueError("--interval은 1 이상의 정수여야 합니다.")

    print("중고나라 polling 시작")
    print(f"interval={args.interval}s, once={args.once}, user_id={args.user_id}")

    try:
        while True:
            stats = poll_once(
                user_id=args.user_id,
                search_words=args.search_words,
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
