import argparse
import os
import sys
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from src.listing_analysis_pipeline import process_pending_analysis_jobs
    from src.worker_heartbeat import write_worker_heartbeat
except ModuleNotFoundError:
    from listing_analysis_pipeline import process_pending_analysis_jobs
    from worker_heartbeat import write_worker_heartbeat


DEFAULT_INTERVAL_SECONDS = 5
DEFAULT_LIMIT = 20
HEARTBEAT_WORKER_NAME = "umtp-analysis-worker"


def parse_args():
    parser = argparse.ArgumentParser(description="UMTP analysis_jobs worker")
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
        help=f"한 번에 처리할 최대 job 수, 기본값 {DEFAULT_LIMIT}",
    )
    return parser.parse_args()


def _print_summary(stats):
    print("[analysis_worker] 요약")
    print(
        f"fetched={stats.get('fetched', 0)}, "
        f"done={stats.get('done', 0)}, "
        f"failed={stats.get('failed', 0)}"
    )
    print(
        f"fetched_list_count={stats.get('fetched_list_count', 0)}, "
        f"detail_fetch_count={stats.get('detail_fetch_count', 0)}, "
        f"detail_skipped_count={stats.get('detail_skipped_count', 0)}, "
        f"unchanged_detail_skipped_count={stats.get('unchanged_detail_skipped_count', 0)}"
    )
    print(f"detail_fetch_reason_counts={stats.get('detail_fetch_reason_counts', {})}")


def _build_heartbeat_stats(stats):
    if not isinstance(stats, dict):
        return {}
    return {
        "fetched": stats.get("fetched", 0),
        "done": stats.get("done", 0),
        "failed": stats.get("failed", 0),
        "detail_fetch_count": stats.get("detail_fetch_count", 0),
        "detail_skipped_count": stats.get("detail_skipped_count", 0),
        "unchanged_detail_skipped_count": stats.get("unchanged_detail_skipped_count", 0),
    }


def _heartbeat_status(stats):
    if not isinstance(stats, dict):
        return "ok"
    if stats.get("failed", 0) > 0:
        return "degraded"
    return "ok"


def main():
    args = parse_args()

    if args.interval <= 0:
        raise ValueError("--interval은 1 이상의 정수여야 합니다.")
    if args.limit <= 0:
        raise ValueError("--limit은 1 이상의 정수여야 합니다.")

    print("analysis worker 시작")
    print(f"interval={args.interval}s, once={args.once}, limit={args.limit}")

    try:
        while True:
            stats = process_pending_analysis_jobs(limit=args.limit)
            _print_summary(stats)
            heartbeat_stats = _build_heartbeat_stats(stats)
            heartbeat_detail = (
                f"fetched={heartbeat_stats.get('fetched', 0)} "
                f"done={heartbeat_stats.get('done', 0)} "
                f"failed={heartbeat_stats.get('failed', 0)}"
            )
            write_worker_heartbeat(
                HEARTBEAT_WORKER_NAME,
                status=_heartbeat_status(stats),
                detail=heartbeat_detail,
                stats=heartbeat_stats,
            )

            if args.once:
                break

            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("사용자 요청으로 analysis worker를 종료합니다.")


if __name__ == "__main__":
    main()
