import os
import re
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "deploy-auto.yml"
HOST_KEY_BLOB = "AAAAC3NzaC1lZDI1NTE5AAAAIPZcfVwHVIUEU7W0auTb70VKY/aLppXM/54vzpmy0+XV"
HOST_KEY_FINGERPRINT = "SHA256:n4RyFDQqWLPJnXyZ3SvyXUf8dpDNWjzShuPRYDdF2LE"


def _top_level_block(text: str, name: str) -> list[str] | None:
    lines = text.splitlines()
    starts = [index for index, line in enumerate(lines) if line == f"{name}:"]
    if len(starts) != 1:
        return None
    block: list[str] = []
    for line in lines[starts[0] + 1 :]:
        if line and not line.startswith((" ", "\t")):
            break
        block.append(line)
    return block


def _mapping_keys(lines: list[str], indent: int) -> set[str]:
    prefix = " " * indent
    keys: set[str] = set()
    for line in lines:
        match = re.fullmatch(rf"{re.escape(prefix)}([A-Za-z_][A-Za-z0-9_-]*):(?:\s.*)?", line)
        if match is not None:
            keys.add(match.group(1))
    return keys


def workflow_shape_findings(text: str) -> set[str]:
    findings: set[str] = set()
    triggers = _top_level_block(text, "on")
    if triggers is None or _mapping_keys(triggers, 2) != {"push", "workflow_dispatch"}:
        findings.add("DEPLOY_TRIGGER_SET")
    elif not re.search(r"(?m)^  push:\s*$\n    branches:\s*$\n      - main\s*$", "\n".join(triggers)):
        findings.add("DEPLOY_PUSH_BRANCH")

    permissions = _top_level_block(text, "permissions")
    permission_lines = [line for line in permissions or [] if line.strip() and not line.lstrip().startswith("#")]
    if permission_lines != ["  contents: read"]:
        findings.add("TOP_LEVEL_PERMISSIONS")
    jobs = _top_level_block(text, "jobs")
    if jobs is None or re.search(r"(?m)^    permissions\s*:", "\n".join(jobs)):
        findings.add("JOB_PERMISSIONS")

    for host in ("135.106.164.147", "audit.135.106.164.147.sslip.io"):
        exact = f"'{host} ssh-ed25519 {HOST_KEY_BLOB}'"
        if text.count(exact) != 1:
            findings.add("PINNED_HOST_KEY_BLOB")
    if text.count(f"Fingerprint: {HOST_KEY_FINGERPRINT}") != 1:
        findings.add("PINNED_HOST_KEY_FINGERPRINT")
    lines = text.splitlines()
    redirects = [
        index for index, line in enumerate(lines)
        if line.strip() == '> "$HOME/.ssh/known_hosts"'
    ]
    if len(redirects) != 1:
        findings.add("PINNED_HOST_KEY_SET")
    else:
        redirect = redirects[0]
        starts = [
            index for index, line in enumerate(lines[:redirect])
            if line.strip() == "printf '%s\\n' \\"
        ]
        expected = [
            f"'{host} ssh-ed25519 {HOST_KEY_BLOB}'" for host in
            ("135.106.164.147", "audit.135.106.164.147.sslip.io")
        ]
        actual = [line.strip().rstrip(" \\") for line in lines[starts[-1] + 1:redirect]] if starts else []
        if actual != expected:
            findings.add("PINNED_HOST_KEY_SET")
    return findings


def _remote_script(text: str) -> str:
    """Extract the script sent to the host, including its real command ordering."""
    match = re.search(
        r"(?ms)^            bash -s -- \"\$DEPLOY_SHA\" <<'REMOTE'\n"
        r"(?P<script>.*?)^          REMOTE$",
        text,
    )
    if match is None:
        raise AssertionError("expected exactly one remote Bash heredoc")
    script = match.group("script")
    if not all(line.startswith("          ") for line in script.splitlines() if line):
        raise AssertionError("remote Bash heredoc indentation changed")
    return textwrap.dedent(script)


class DeployAutoWorkflowContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_only_main_and_manual_dispatch_trigger_deployment(self) -> None:
        self.assertNotIn("DEPLOY_TRIGGER_SET", workflow_shape_findings(self.text))
        self.assertNotIn("DEPLOY_PUSH_BRANCH", workflow_shape_findings(self.text))
        self.assertIn("if: github.ref == 'refs/heads/main'", self.text)

    def test_workflow_permissions_are_exactly_read_only(self) -> None:
        self.assertNotIn("TOP_LEVEL_PERMISSIONS", workflow_shape_findings(self.text))
        self.assertNotIn("JOB_PERMISSIONS", workflow_shape_findings(self.text))

    def test_deployments_are_serial_and_never_cancel_each_other(self) -> None:
        self.assertIn("group: auditmanager-alpha-production", self.text)
        self.assertIn("cancel-in-progress: false", self.text)

    def test_ssh_is_fail_closed_and_uses_only_declared_secrets(self) -> None:
        for secret in ("VPS_HOST", "VPS_USER", "VPS_SSH_KEY"):
            self.assertIn(f"secrets.{secret}", self.text)
        self.assertNotIn("secrets.VPS_KNOWN_HOSTS", self.text)
        self.assertNotIn("PINNED_HOST_KEY_BLOB", workflow_shape_findings(self.text))
        self.assertNotIn("PINNED_HOST_KEY_FINGERPRINT", workflow_shape_findings(self.text))
        self.assertNotIn("PINNED_HOST_KEY_SET", workflow_shape_findings(self.text))
        self.assertIn(
            "135.106.164.147|audit.135.106.164.147.sslip.io", self.text
        )
        self.assertIn("VPS_HOST is not the pinned alpha SSH endpoint.", self.text)
        self.assertIn("StrictHostKeyChecking=yes", self.text)
        self.assertIn("BatchMode=yes", self.text)
        self.assertIn("IdentitiesOnly=yes", self.text)
        self.assertNotIn("StrictHostKeyChecking=no", self.text)

    def test_remote_tree_must_be_clean_before_and_after_deploy(self) -> None:
        cleanliness_probe = "git status --porcelain --untracked-files=all"
        self.assertGreaterEqual(self.text.count(cleanliness_probe), 3)
        self.assertLess(
            self.text.index("REFUSED: $REPOSITORY has tracked or untracked changes."),
            self.text.index("git fetch --prune origin"),
        )
        self.assertNotIn("git clean", self.text)
        self.assertNotIn("git reset", self.text)

    def test_trigger_sha_is_selected_before_deploy_and_verified_afterwards(self) -> None:
        ordered = (
            "git fetch --prune origin",
            'git cat-file -e "${DEPLOY_SHA}^{commit}"',
            'git merge-base --is-ancestor "$DEPLOY_SHA" origin/main',
            'git checkout --detach "$DEPLOY_SHA"',
            "infra/deploy/deploy.sh",
            "infra/deploy/verify-deployed.sh",
            'echo "DEPLOY OK: $DEPLOY_SHA"',
        )
        positions = [self.text.index(fragment) for fragment in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertGreaterEqual(
            self.text.count('test "$(git rev-parse HEAD)" = "$DEPLOY_SHA"'), 2
        )
        self.assertNotIn("git pull", self.text)

    def test_stdin_draining_deploy_cannot_skip_host_verification(self) -> None:
        """A child reading stdin must not swallow later remote shell commands."""
        sha = "a" * 40
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = root / "repo"
            deployment = repository / "infra" / "deploy"
            deployment.mkdir(parents=True)
            binaries = root / "bin"
            binaries.mkdir()

            git_stub = binaries / "git"
            git_stub.write_text(
                '#!/bin/sh\n'
                'if [ "$1" = rev-parse ]; then printf "%s\\n" "$TEST_SHA"; fi\n',
                encoding="utf-8",
            )
            git_stub.chmod(0o755)
            deploy_stub = deployment / "deploy.sh"
            deploy_stub.write_text(
                '#!/bin/sh\nprintf "DEPLOY STUB CALLED\\n"\ncat >/dev/null\n',
                encoding="utf-8",
            )
            deploy_stub.chmod(0o755)
            verify_stub = deployment / "verify-deployed.sh"
            verify_stub.write_text(
                '#!/bin/sh\nprintf "VERIFY STUB CALLED\\n"\ncat >/dev/null\n'
                'exit "${VERIFY_EXIT:-0}"\n',
                encoding="utf-8",
            )
            verify_stub.chmod(0o755)

            remote = _remote_script(self.text).replace(
                "readonly REPOSITORY=/srv/auditmanager",
                f"readonly REPOSITORY={repository}",
                1,
            )
            environment = os.environ | {
                "PATH": f"{binaries}:{os.environ['PATH']}",
                "TEST_SHA": sha,
            }
            for verify_exit in ("0", "7"):
                with self.subTest(verify_exit=verify_exit):
                    completed = subprocess.run(
                        ["bash", "-s", "--", sha],
                        input=remote,
                        text=True,
                        capture_output=True,
                        env=environment | {"VERIFY_EXIT": verify_exit},
                        timeout=10,
                        check=False,
                    )
                    self.assertIn("DEPLOY STUB CALLED", completed.stdout)
                    self.assertIn("=== verify deployed tree ===", completed.stdout)
                    self.assertIn("VERIFY STUB CALLED", completed.stdout)
                    if verify_exit == "0":
                        self.assertEqual(completed.returncode, 0, completed.stderr)
                        self.assertIn(f"DEPLOY OK: {sha}", completed.stdout)
                    else:
                        self.assertEqual(completed.returncode, 7)
                        self.assertNotIn("DEPLOY OK:", completed.stdout)

    def test_semantic_mutations_are_rejected(self) -> None:
        extra_trigger = self.text.replace(
            "  workflow_dispatch:\n", "  workflow_dispatch:\n  pull_request_target:\n", 1
        )
        self.assertIn("DEPLOY_TRIGGER_SET", workflow_shape_findings(extra_trigger))

        write_permission = self.text.replace("  contents: read\n", "  contents: write\n", 1)
        self.assertIn("TOP_LEVEL_PERMISSIONS", workflow_shape_findings(write_permission))

        changed_key = self.text.replace(HOST_KEY_BLOB, f"{HOST_KEY_BLOB[:-1]}A", 1)
        self.assertIn("PINNED_HOST_KEY_BLOB", workflow_shape_findings(changed_key))

        job_write = self.text.replace(
            "    timeout-minutes: 90\n",
            "    timeout-minutes: 90\n    permissions:\n      contents: write\n",
            1,
        )
        self.assertIn("JOB_PERMISSIONS", workflow_shape_findings(job_write))

        extra_host = self.text.replace(
            '            > "$HOME/.ssh/known_hosts"',
            "            'foreign.example ssh-ed25519 AAAA' \\\n"
            '            > "$HOME/.ssh/known_hosts"',
            1,
        )
        self.assertIn("PINNED_HOST_KEY_SET", workflow_shape_findings(extra_host))


if __name__ == "__main__":
    unittest.main()
