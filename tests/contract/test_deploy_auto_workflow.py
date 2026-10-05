import re
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

    for host in ("135.106.164.147", "audit.135.106.164.147.sslip.io"):
        exact = f"'{host} ssh-ed25519 {HOST_KEY_BLOB}'"
        if text.count(exact) != 1:
            findings.add("PINNED_HOST_KEY_BLOB")
    if text.count(f"Fingerprint: {HOST_KEY_FINGERPRINT}") != 1:
        findings.add("PINNED_HOST_KEY_FINGERPRINT")
    return findings


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

    def test_deployments_are_serial_and_never_cancel_each_other(self) -> None:
        self.assertIn("group: auditmanager-alpha-production", self.text)
        self.assertIn("cancel-in-progress: false", self.text)

    def test_ssh_is_fail_closed_and_uses_only_declared_secrets(self) -> None:
        for secret in ("VPS_HOST", "VPS_USER", "VPS_SSH_KEY"):
            self.assertIn(f"secrets.{secret}", self.text)
        self.assertNotIn("secrets.VPS_KNOWN_HOSTS", self.text)
        self.assertNotIn("PINNED_HOST_KEY_BLOB", workflow_shape_findings(self.text))
        self.assertNotIn("PINNED_HOST_KEY_FINGERPRINT", workflow_shape_findings(self.text))
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

    def test_semantic_mutations_are_rejected(self) -> None:
        extra_trigger = self.text.replace(
            "  workflow_dispatch:\n", "  workflow_dispatch:\n  pull_request_target:\n", 1
        )
        self.assertIn("DEPLOY_TRIGGER_SET", workflow_shape_findings(extra_trigger))

        write_permission = self.text.replace("  contents: read\n", "  contents: write\n", 1)
        self.assertIn("TOP_LEVEL_PERMISSIONS", workflow_shape_findings(write_permission))

        changed_key = self.text.replace(HOST_KEY_BLOB, f"{HOST_KEY_BLOB[:-1]}A", 1)
        self.assertIn("PINNED_HOST_KEY_BLOB", workflow_shape_findings(changed_key))


if __name__ == "__main__":
    unittest.main()
