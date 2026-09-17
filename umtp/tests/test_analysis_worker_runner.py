import os
import sys
import unittest
from argparse import Namespace
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import run_analysis_worker_umtp as runner


def arguments(**kwargs):
    values = dict(workers=2, once=True, limit=20, interval=1)
    values.update(kwargs)
    return Namespace(**values)


class AnalysisWorkerRunnerTest(unittest.TestCase):
    def test_defaults_use_two_independent_workers(self):
        with patch.object(sys, "argv", ["worker"]):
            self.assertEqual(runner.parse_args().workers, 2)

    def test_single_worker_preserves_direct_once_loop(self):
        with patch.object(runner, "parse_args", return_value=arguments(workers=1)):
            with patch.object(runner, "process_pending_analysis_jobs", return_value={"fetched": 3}) as process:
                with patch.object(runner, "_supervise_workers") as supervise:
                    with patch.object(runner.signal, "signal"):
                        runner.main()
        process.assert_called_once_with(limit=20)
        supervise.assert_not_called()

    def test_invalid_worker_count_is_rejected_before_starting(self):
        for value in (0, 9):
            with patch.object(runner, "parse_args", return_value=arguments(workers=value)):
                with patch.object(runner, "_supervise_workers") as supervise:
                    with self.assertRaisesRegex(ValueError, "workers"):
                        runner.main()
                    supervise.assert_not_called()

    def test_busy_queue_drains_without_sleeping_between_batches(self):
        with patch.object(runner, "process_pending_analysis_jobs", side_effect=[{"fetched": 2}, {"fetched": 0}, KeyboardInterrupt]):
            with patch.object(runner.time, "sleep") as sleep:
                with self.assertRaises(KeyboardInterrupt):
                    runner._run_worker_loop(arguments(once=False))
        sleep.assert_called_once_with(1)

    def test_once_starts_spawned_processes_each_with_own_limit(self):
        children = [Mock(pid=index + 100, exitcode=0, name=f"worker-{index}") for index in range(2)]
        for child in children:
            child.is_alive.return_value = False
        context = Mock()
        context.Process.side_effect = children
        args = arguments(limit=7)
        with patch.object(runner.multiprocessing, "get_context", return_value=context) as get_context:
            runner._supervise_workers(args)
        get_context.assert_called_once_with("spawn")
        self.assertEqual(context.Process.call_count, 2)
        for call, child in zip(context.Process.call_args_list, children):
            self.assertEqual(call.kwargs["args"], (args,))
            self.assertIs(call.kwargs["target"], runner._worker_entry)
            child.start.assert_called_once()
            child.terminate.assert_not_called()

    def test_child_failure_stops_sibling_and_propagates_for_supervisor_restart(self):
        failed = Mock(pid=101, exitcode=1, name="failed")
        failed.is_alive.return_value = False
        sibling = Mock(pid=102, exitcode=None, name="sibling")
        sibling.is_alive.side_effect = [True, False]
        context = Mock()
        context.Process.side_effect = [failed, sibling]
        with patch.object(runner.multiprocessing, "get_context", return_value=context):
            with self.assertRaisesRegex(RuntimeError, "exited unexpectedly: 1"):
                runner._supervise_workers(arguments())
        sibling.terminate.assert_called_once()
        sibling.kill.assert_not_called()

    def test_unexpected_clean_exit_is_failure_in_continuous_mode(self):
        child = Mock(pid=101, exitcode=0, name="early-exit")
        child.is_alive.return_value = False
        context = Mock()
        context.Process.return_value = child
        with patch.object(runner.multiprocessing, "get_context", return_value=context):
            with self.assertRaisesRegex(RuntimeError, "exited unexpectedly: 0"):
                runner._supervise_workers(arguments(workers=1, once=False))

    def test_interrupt_terminates_children_and_escalates_hung_child(self):
        child = Mock(pid=101, exitcode=None)
        child.join.side_effect = [KeyboardInterrupt, None, None]
        child.is_alive.return_value = True
        context = Mock()
        context.Process.return_value = child
        with patch.object(runner.multiprocessing, "get_context", return_value=context):
            with self.assertRaises(KeyboardInterrupt):
                runner._supervise_workers(arguments(workers=1))
        child.terminate.assert_called_once()
        child.kill.assert_called_once()

    def test_partial_start_failure_does_not_orphan_started_children(self):
        started = Mock(pid=101)
        started.is_alive.side_effect = [True, False]
        failed = Mock(pid=None)
        failed.start.side_effect = RuntimeError("spawn failed")
        context = Mock()
        context.Process.side_effect = [started, failed]
        with patch.object(runner.multiprocessing, "get_context", return_value=context):
            with self.assertRaisesRegex(RuntimeError, "spawn failed"):
                runner._supervise_workers(arguments())
        started.terminate.assert_called_once()
        failed.terminate.assert_not_called()

    def test_sigterm_unwinds_and_previous_handler_is_restored(self):
        with patch.object(runner, "parse_args", return_value=arguments(workers=1)):
            with patch.object(runner, "_run_worker_loop", side_effect=KeyboardInterrupt):
                with patch.object(runner.signal, "signal", return_value="previous") as handler:
                    runner.main()
        self.assertEqual(handler.call_args_list[0].args, (runner.signal.SIGTERM, runner._request_shutdown))
        self.assertEqual(handler.call_args_list[-1].args, (runner.signal.SIGTERM, "previous"))
        with self.assertRaises(KeyboardInterrupt):
            runner._request_shutdown(runner.signal.SIGTERM, None)


if __name__ == "__main__":
    unittest.main()
