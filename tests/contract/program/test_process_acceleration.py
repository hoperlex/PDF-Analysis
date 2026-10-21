"""Focused process checks; no application service or network is needed."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

import lane_prepare  # noqa: E402
import task_handoff  # noqa: E402


def command(root: Path, *argv: str) -> str:
    result = subprocess.run(argv, cwd=root, text=True, capture_output=True, check=True)
    return result.stdout.strip()


def free_ports() -> tuple[int, int, int]:
    return 62000, 62001, 62002


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="process-accel-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        command(self.root, "git", "init", "-q")
        command(self.root, "git", "config", "user.name", "Process Test")
        command(self.root, "git", "config", "user.email", "process-test@example.invalid")
        (self.root / ".gitignore").write_text(".local/\n.env\n", encoding="utf-8")
        (self.root / ".env.example").write_bytes((ROOT / ".env.example").read_bytes())
        (self.root / "owned.txt").write_text("base\n", encoding="utf-8")
        command(self.root, "git", "add", ".gitignore", ".env.example", "owned.txt")
        command(self.root, "git", "commit", "-qm", "base")
        self.base = command(self.root, "git", "rev-parse", "HEAD")
        self.task_path = self.root / "docs/program/tasks/T-01.md"
        self.task_path.parent.mkdir(parents=True)
        self.ports = free_ports()
        self.proc_net = self.root / "procnet"
        self.proc_net.mkdir()
        (self.proc_net / "tcp").write_text("sl local_address rem_address st\n", encoding="ascii")
        (self.proc_net / "tcp6").write_text("sl local_address rem_address st\n", encoding="ascii")
        self.write_task()
        command(self.root, "git", "add", "docs/program/tasks/T-01.md")
        command(self.root, "git", "commit", "-qm", "dispatch")

    def write_task(self, allowed: str = "- `owned.txt`", instance: str = "auditmanager-t-01") -> None:
        pg, s3, console = self.ports
        self.task_path.write_text(
            f"# Task T-01 — fixture\n\n## Frozen inputs\n\n- base commit: `{self.base}`\n\n"
            f"## Allowed paths\n\n{allowed}\n\n## Lane resources\n\n"
            f"- foundation_instance: `{instance}`\n- postgres_port: `{pg}`\n"
            f"- s3_api_port: `{s3}`\n- s3_console_port: `{console}`\n"
            "- postgres_db: `auditmanager_t_01`\n- s3_bucket: `auditmanager-t-01`\n",
            encoding="utf-8",
        )


class CurrentStateTest(unittest.TestCase):
    def test_archive_is_the_exact_base_document_and_live_entry_is_short(self) -> None:
        live = (ROOT / "docs/program/CURRENT_STATE.md").read_text(encoding="utf-8")
        archive = re.search(r"\(history/(CURRENT_STATE_2026-10-15_([0-9a-f]{7,40})\.md)\)", live)
        self.assertIsNotNone(archive)
        assert archive is not None
        archived = ROOT / "docs/program/history" / archive.group(1)
        original = subprocess.run(
            ["git", "show", f"{archive.group(2)}:docs/program/CURRENT_STATE.md"],
            cwd=ROOT, capture_output=True, check=True,
        ).stdout
        self.assertEqual(archived.read_bytes(), original)
        self.assertLessEqual(len(live.splitlines()), 120)
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertIn(f"`VERSION` is `{version}`", live)
        self.assertIn("infra/deploy/verify-deployed.sh", live)
        self.assertIn("## Previous release state — wave 48 (historical record)", live)


class TaskHandoffTest(Fixture):
    def test_read_task_rejects_ambiguous_or_escaping_allowlists(self) -> None:
        self.assertEqual(task_handoff.read_task(self.task_path).base, self.base)
        self.write_task(allowed="- `web/app/[user_uid]/page.tsx`")
        self.assertEqual(task_handoff.read_task(self.task_path).allowed, ("web/app/[user_uid]/page.tsx",))
        self.write_task(allowed="- `owned.txt` — with prose")
        with self.assertRaisesRegex(task_handoff.HandoffError, "unparseable"):
            task_handoff.read_task(self.task_path)
        self.write_task(allowed="- `../other.txt`")
        with self.assertRaisesRegex(task_handoff.HandoffError, "unsafe"):
            task_handoff.read_task(self.task_path)

    def test_handoff_binds_dispatch_task_lane_head_paths_and_real_check_log(self) -> None:
        lane = lane_prepare.prepare(self.root, self.task_path, install=False, proc_net=self.proc_net)
        (lane / "owned.txt").write_text("changed\n", encoding="utf-8")
        command(lane, "git", "add", "owned.txt")
        command(lane, "git", "commit", "-qm", "work")
        output, green = task_handoff.produce(
            lane, self.task_path, [[sys.executable, "-c", "print('focused check passed')"]],
            lane / ".local/handoff/T-01-evidence.md",
        )
        report = output.read_text(encoding="utf-8")
        self.assertTrue(green)
        self.assertIn(self.base, report)
        self.assertIn(command(lane, "git", "rev-parse", "HEAD"), report)
        self.assertIn("`M` `owned.txt`", report)
        self.assertIn("Check status: PASS", report)
        self.assertIn("unverified", report)
        self.assertIn("focused check passed", next(output.parent.glob("T-01-*-logs/check-01.log")).read_text())
        self.assertEqual(os.stat(output).st_mode & 0o777, 0o600)
        self.assertEqual(os.stat(next(output.parent.glob("T-01-*-logs/check-01.log"))).st_mode & 0o777, 0o600)

    def test_handoff_refuses_unowned_path_and_dirty_lane(self) -> None:
        lane = lane_prepare.prepare(self.root, self.task_path, install=False, proc_net=self.proc_net)
        (lane / "outside.txt").write_text("unexpected\n", encoding="utf-8")
        command(lane, "git", "add", "outside.txt")
        command(lane, "git", "commit", "-qm", "outside")
        with self.assertRaisesRegex(task_handoff.HandoffError, "outside Allowed paths"):
            task_handoff.produce(lane, self.task_path, [], lane / ".local/handoff/evidence.md")
        (lane / "owned.txt").write_text("dirty\n", encoding="utf-8")
        with self.assertRaisesRegex(task_handoff.HandoffError, "dirty"):
            task_handoff.produce(lane, self.task_path, [], lane / ".local/handoff/evidence.md")

    def test_task_source_must_be_committed_and_from_same_repository(self) -> None:
        lane = lane_prepare.prepare(self.root, self.task_path, install=False, proc_net=self.proc_net)
        self.write_task(allowed="- `owned.txt`\n- `outside.txt`")
        with self.assertRaisesRegex(task_handoff.HandoffError, "differs from its committed source"):
            task_handoff.produce(lane, self.task_path, [], lane / ".local/handoff/evidence.md")

    def test_handoff_refuses_task_changed_by_a_check_in_dispatch_checkout(self) -> None:
        lane = lane_prepare.prepare(self.root, self.task_path, install=False, proc_net=self.proc_net)
        (lane / "owned.txt").write_text("changed\n", encoding="utf-8")
        command(lane, "git", "add", "owned.txt")
        command(lane, "git", "commit", "-qm", "work")
        with self.assertRaisesRegex(task_handoff.HandoffError, "differs from its committed source"):
            task_handoff.produce(
                lane, self.task_path,
                [[sys.executable, "-c", "from pathlib import Path; Path(%r).write_text('changed')" % str(self.task_path)]],
                lane / ".local/handoff/evidence.md",
            )

    def test_handoff_replaces_a_symlink_without_writing_its_target(self) -> None:
        lane = lane_prepare.prepare(self.root, self.task_path, install=False, proc_net=self.proc_net)
        (lane / "owned.txt").write_text("changed\n", encoding="utf-8")
        command(lane, "git", "add", "owned.txt")
        command(lane, "git", "commit", "-qm", "work")
        output = lane / ".local/handoff/evidence.md"
        output.parent.mkdir(parents=True)
        victim = self.root / "victim.txt"
        victim.write_text("keep\n", encoding="utf-8")
        output.symlink_to(victim)
        task_handoff.produce(lane, self.task_path, [[sys.executable, "-c", "print('ok')"]], output)
        self.assertEqual(victim.read_text(encoding="utf-8"), "keep\n")
        self.assertFalse(output.is_symlink())


class LanePrepareTest(Fixture):
    def test_refuses_uncommitted_task_and_root_environment_collision(self) -> None:
        self.write_task(allowed="- `owned.txt`\n- `other.txt`")
        with self.assertRaisesRegex(task_handoff.HandoffError, "differs from its committed source"):
            lane_prepare.prepare(self.root, self.task_path, install=False, proc_net=self.proc_net)
        command(self.root, "git", "checkout", "--", "docs/program/tasks/T-01.md")
        (self.root / ".env").write_text(f"S3_API_PORT={self.ports[0]}\n", encoding="utf-8")
        with self.assertRaisesRegex(task_handoff.HandoffError, "already assigned"):
            lane_prepare.prepare(self.root, self.task_path, install=False, proc_net=self.proc_net)

    def test_dry_run_and_preparation_use_exact_base_and_disposable_env(self) -> None:
        target = lane_prepare.prepare(self.root, self.task_path, dry_run=True, install=False, proc_net=self.proc_net)
        self.assertFalse(target.exists())
        target = lane_prepare.prepare(self.root, self.task_path, install=False, proc_net=self.proc_net)
        self.assertEqual(command(target, "git", "rev-parse", "HEAD"), self.base)
        self.assertEqual(command(target, "git", "branch", "--show-current"), "agent/T-01")
        env = (target / ".env").read_text(encoding="utf-8")
        self.assertIn(f"FOUNDATION_INSTANCE=auditmanager-t-01\n", env)
        self.assertIn(f"POSTGRES_PORT={self.ports[0]}\n", env)
        self.assertIn(f"S3_API_PORT={self.ports[1]}\n", env)
        self.assertIn(f"S3_CONSOLE_PORT={self.ports[2]}\n", env)
        self.assertIn(f"@127.0.0.1:{self.ports[0]}/auditmanager_t_01", env)
        self.assertEqual(os.stat(target / ".env").st_mode & 0o777, 0o600)
        self.assertEqual(lane_prepare.prepare(self.root, self.task_path, install=False, proc_net=self.proc_net), target)

    def test_rejects_cross_role_port_collision_and_conflicting_env(self) -> None:
        other = self.root / ".local/worktrees/other"
        other.mkdir(parents=True)
        (other / ".env").write_text(f"S3_CONSOLE_PORT={self.ports[0]}\n", encoding="utf-8")
        with self.assertRaisesRegex(task_handoff.HandoffError, "already assigned"):
            lane_prepare.prepare(self.root, self.task_path, install=False, proc_net=self.proc_net)
        (other / ".env").unlink()
        target = lane_prepare.prepare(self.root, self.task_path, install=False, proc_net=self.proc_net)
        (target / ".env").write_text("FOUNDATION_INSTANCE=wrong\n", encoding="utf-8")
        with self.assertRaisesRegex(task_handoff.HandoffError, "existing .env differs"):
            lane_prepare.prepare(self.root, self.task_path, install=False, proc_net=self.proc_net)

    def test_registered_worktree_outside_lane_directory_reserves_database_and_bucket(self) -> None:
        other = self.root / "external-worktree"
        command(self.root, "git", "worktree", "add", "-qb", "other-lane", str(other), self.base)
        (other / ".env").write_text("POSTGRES_DB=auditmanager_t_01\n", encoding="utf-8")
        with self.assertRaisesRegex(task_handoff.HandoffError, "database already assigned"):
            lane_prepare.prepare(self.root, self.task_path, install=False, proc_net=self.proc_net)
        (other / ".env").write_text("S3_BUCKET=auditmanager-t-01\n", encoding="utf-8")
        with self.assertRaisesRegex(task_handoff.HandoffError, "bucket already assigned"):
            lane_prepare.prepare(self.root, self.task_path, install=False, proc_net=self.proc_net)

    def test_rejects_unsafe_resource_and_bound_port(self) -> None:
        self.write_task(instance="bad;touch /tmp/unsafe")
        with self.assertRaisesRegex(task_handoff.HandoffError, "safe lane name"):
            lane_prepare.read_resources(self.task_path)
        self.write_task()
        port_hex = f"{self.ports[0]:04X}"
        (self.proc_net / "tcp").write_text(
            f"sl local_address rem_address st\n 0: 0100007F:{port_hex} 00000000:0000 0A\n",
            encoding="ascii",
        )
        with self.assertRaisesRegex(task_handoff.HandoffError, "already listening"):
            lane_prepare.prepare(self.root, self.task_path, install=False, proc_net=self.proc_net)


if __name__ == "__main__":
    unittest.main()
