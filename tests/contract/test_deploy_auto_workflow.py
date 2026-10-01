import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "deploy-auto.yml"


class DeployAutoWorkflowContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_only_main_and_manual_dispatch_trigger_deployment(self) -> None:
        self.assertIn("  push:\n    branches:\n      - main\n", self.text)
        self.assertIn("  workflow_dispatch:\n", self.text)
        self.assertIn("if: github.ref == 'refs/heads/main'", self.text)

    def test_deployments_are_serial_and_never_cancel_each_other(self) -> None:
        self.assertIn("group: auditmanager-alpha-production", self.text)
        self.assertIn("cancel-in-progress: false", self.text)

    def test_ssh_is_fail_closed_and_uses_only_declared_secrets(self) -> None:
        for secret in ("VPS_HOST", "VPS_USER", "VPS_SSH_KEY"):
            self.assertIn(f"secrets.{secret}", self.text)
        self.assertNotIn("secrets.VPS_KNOWN_HOSTS", self.text)
        self.assertIn(
            "SHA256:n4RyFDQqWLPJnXyZ3SvyXUf8dpDNWjzShuPRYDdF2LE", self.text
        )
        self.assertIn("135.106.164.147 ssh-ed25519 AAAAC3", self.text)
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


if __name__ == "__main__":
    unittest.main()
