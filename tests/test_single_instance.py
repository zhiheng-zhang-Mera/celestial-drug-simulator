"""Tests for the host-wide single-instance guard (contract v1, section 5)."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from celestial_single_instance import (
    ALREADY_RUNNING,
    EXIT_ALREADY_RUNNING,
    SingleInstance,
    parse_instance_scope,
)

PRODUCT_ID = "celestial-drug-simulator"
APP = "simulator"
TITLE = "Celestial Drug Simulator · 人体作用与证据"
REPO_ROOT = Path(__file__).resolve().parents[1]


class SingleInstanceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.state_root = Path(temporary.name) / "state"

    def guard(self, **kwargs):
        return SingleInstance(PRODUCT_ID, APP, TITLE, scope="state",
                              state_root=self.state_root, **kwargs)

    def test_second_instance_is_rejected_while_first_holds_lock(self):
        first = self.guard()
        self.assertTrue(first.acquire())
        second = self.guard()
        self.assertFalse(second.acquire())
        self.assertEqual(second.mode, "mutex")
        first.release()

    def test_release_allows_the_next_instance(self):
        first = self.guard()
        self.assertTrue(first.acquire())
        first.release()
        second = self.guard()
        self.assertTrue(second.acquire())
        second.release()

    def test_file_lock_fallback_is_exclusive(self):
        first = self.guard(_force_file_lock=True)
        self.assertTrue(first.acquire())
        self.assertEqual(first.mode, "file")
        self.assertTrue(first.lock_path.is_file())
        second = self.guard(_force_file_lock=True)
        self.assertFalse(second.acquire())
        first.release()
        third = self.guard(_force_file_lock=True)
        self.assertTrue(third.acquire())
        third.release()

    def test_distinct_state_roots_are_isolated(self):
        other_root = self.state_root.parent / "other"
        first = self.guard()
        self.assertTrue(first.acquire())
        other = SingleInstance(PRODUCT_ID, APP, TITLE, scope="state", state_root=other_root)
        self.assertTrue(other.acquire())
        first.release()
        other.release()

    def test_scope_argument_is_stripped_from_argv(self):
        scope, cleaned = parse_instance_scope([sys.executable, "--instance-scope=state", "extra"])
        self.assertEqual(scope, "state")
        self.assertEqual(cleaned, [sys.executable, "extra"])
        scope, cleaned = parse_instance_scope([sys.executable])
        self.assertEqual(scope, "global")
        self.assertEqual(cleaned, [sys.executable])

    def test_second_process_exits_three_with_clear_message(self):
        holder = self.guard()
        self.assertTrue(holder.acquire())
        env = dict(os.environ)
        env["CELESTIAL_INSTANCE_STATE_ROOT"] = str(self.state_root)
        env.pop("CELESTIAL_INSTANCE_FORCE_FILE_LOCK", None)
        script = (f"from celestial_single_instance import enforce_single_instance; "
                  f"enforce_single_instance({PRODUCT_ID!r}, {APP!r}, {TITLE!r}, argv=[\"child\", \"--instance-scope=state\"])")
        result = subprocess.run(
            [sys.executable, "-B", "-c", script],
            cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=60,
        )
        holder.release()
        self.assertEqual(result.returncode, EXIT_ALREADY_RUNNING, result.stderr)
        self.assertIn(ALREADY_RUNNING, result.stderr)


if __name__ == "__main__":
    unittest.main()
