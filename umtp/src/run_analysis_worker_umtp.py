import argparse
import multiprocessing
import os
import signal
import sys
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from src.listing_analysis_pipeline import process_pending_analysis_jobs
except ModuleNotFoundError:
    from listing_analysis_pipeline import process_pending_analysis_jobs


DEFAULT_INTERVAL_SECONDS = 1
DEFAULT_LIMIT = 20
DEFAULT_WORKERS = 2


def parse_args():
    parser = argparse.ArgumentParser(description="UMTP analysis_jobs worker")
    parser.add_argument("--once", action="store_true", help="각 worker가 최대 --limit개 이벤트를 처리한 후 종료")
    parser.add_argument(
        "--workers", type=int, default=DEFAULT_WORKERS,
        help=f"독립 분석 프로세스 수(1~8), 기본값 {DEFAULT_WORKERS}",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL_SECONDS,
        help=f"큐가 비어 있을 때 대기(초), 기본값 {DEFAULT_INTERVAL_SECONDS}",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"worker별 한 번에 처리할 최대 판매글 이벤트 묶음 수, 기본값 {DEFAULT_LIMIT}",
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


def _run_worker_loop(args):
    while True:
        stats = process_pending_analysis_jobs(limit=args.limit)
        _print_summary(stats)
        if args.once:
            return
        # Drain backlog immediately; only an empty queue requires waiting.
        if not stats.get("fetched"):
            time.sleep(args.interval)


def _request_shutdown(_signum, _frame):
    raise KeyboardInterrupt


def _worker_entry(args):
    # The parent handles Ctrl-C and terminates every child together. SIGTERM
    # unwinds active DB/advisory-lock contexts before this process exits.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, _request_shutdown)
    try:
        _run_worker_loop(args)
    except KeyboardInterrupt:
        pass


def _stop_children(children):
    started = [child for child in children if child.pid is not None]
    for child in started:
        if child.is_alive():
            child.terminate()
    # Use one shared grace period, rather than N grace periods during shutdown.
    deadline = time.monotonic() + 5
    for child in started:
        child.join(timeout=max(0, deadline - time.monotonic()))
    for child in started:
        if child.is_alive():
            child.kill()
            child.join(timeout=1)


def _supervise_workers(args):
    # Spawn gives each process its own Firebase/model globals and DB connections.
    context = multiprocessing.get_context("spawn")
    children = []
    try:
        for index in range(args.workers):
            child = context.Process(target=_worker_entry, args=(args,), name=f"analysis-{index + 1}")
            children.append(child)
            child.start()
        while True:
            for child in children:
                child.join(timeout=0.2)
                if child.exitcode is not None and (child.exitcode != 0 or not args.once):
                    raise RuntimeError(f"analysis worker {child.name} exited unexpectedly: {child.exitcode}")
            if all(child.exitcode is not None for child in children):
                return
    finally:
        _stop_children(children)


def main():
    args = parse_args()

    if args.interval <= 0:
        raise ValueError("--interval은 1 이상의 정수여야 합니다.")
    if args.limit <= 0:
        raise ValueError("--limit은 1 이상의 정수여야 합니다.")
    if not 1 <= args.workers <= 8:
        raise ValueError("--workers는 1~8의 정수여야 합니다.")

    print("analysis worker 시작")
    print(f"interval={args.interval}s, once={args.once}, limit_per_worker={args.limit}, workers={args.workers}")

    previous_sigterm = signal.signal(signal.SIGTERM, _request_shutdown)
    try:
        if args.workers == 1:
            _run_worker_loop(args)
        else:
            _supervise_workers(args)
    except KeyboardInterrupt:
        print("사용자 요청으로 analysis worker를 종료합니다.")
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)


if __name__ == "__main__":
    main()
