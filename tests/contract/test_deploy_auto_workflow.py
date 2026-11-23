"""The auto-deploy workflow: what triggers it, which server it may reach and which repository that server accepts.

The server is named by the repository's own variables (``DEPLOY_HOST``, ``DEPLOY_KNOWN_HOSTS``, ``DEPLOY_PATH``), never by source, and the server
accepts a deployment only from the repository its checkout was cloned from (owner ruling ``R-158f``). A fork therefore deploys nowhere until its
owner names a server, and a fork holding this server's credentials still cannot roll it back. The two scripts the workflow runs are executed here
against stub ``git`` and ``ssh`` binaries, each rule next to the case that must come out the other way.
"""

import os
import re
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "deploy-auto.yml"

DEPLOY_LOCAL = ROOT / "infra" / "deploy" / "deploy-local.sh"
#: The job's whole condition: only `main`, and an explicit opt-out for a repository whose server deploys itself (`FIRST-INSTALL-03`).
#: With `DEPLOY_MODE` unset the job still runs and refuses on a missing `DEPLOY_*` variable, as before.
JOB_CONDITION = "github.ref == 'refs/heads/main' && vars.DEPLOY_MODE != 'local'"

KEY = "AAAAC3NzaC1lZDI1NTE5AAAAIPZcfVwHVIUEU7W0auTb70VKY/aLppXM/54vzpmy0+XV"
SHA = "a" * 40


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


def _prepare_script(text: str) -> str:
    match = re.search(r"(?ms)^      - name: Prepare SSH\n.*?^        run: \|\n(?P<script>.*?)\n\n      - name: Deploy", text)
    if match is None:
        raise AssertionError("expected the Prepare SSH step before the deploy step")
    return textwrap.dedent(match.group("script"))


def _deploy_step_script(text: str) -> str:
    match = re.search(r"(?ms)^      - name: Deploy and verify exact commit\n.*?^        run: \|\n(?P<script>.*?^          REMOTE)$", text)
    if match is None:
        raise AssertionError("expected the deploy step with its remote heredoc")
    return textwrap.dedent(match.group("script"))


def _remote_script(text: str) -> str:
    """Extract the script sent to the host, including its real command ordering."""
    match = re.search(
        r"(?ms)^            bash -s -- \"\$DEPLOY_SHA\" \"\$DEPLOY_PATH\" \"\$DEPLOY_REPOSITORY\" <<'REMOTE'\n"
        r"(?P<script>.*?)^          REMOTE$",
        text,
    )
    if match is None:
        raise AssertionError("expected exactly one remote Bash heredoc")
    script = match.group("script")
    if not all(line.startswith("          ") for line in script.splitlines() if line):
        raise AssertionError("remote Bash heredoc indentation changed")
    return textwrap.dedent(script)


def _local_remote_script(text: str) -> str:
    """The script `deploy-local.sh` hands to `bash -s`: the heredoc, as it is in that file (no YAML indentation to remove)."""
    match = re.search(r"(?ms)<<'REMOTE'\n(?P<script>.*?)\nREMOTE\n", text)
    if match is None:
        raise AssertionError("expected the remote script heredoc in deploy-local.sh")
    return match.group("script")


def workflow_shape_findings(text: str) -> set[str]:
    findings: set[str] = set()
    conditions = re.findall(r"(?m)^    if: (.*)$", text)
    if conditions != [JOB_CONDITION]:
        findings.add("DEPLOY_JOB_CONDITION")
    if not any(re.search(r"github\.ref == 'refs/heads/main'", condition) and " && " in condition for condition in conditions):
        findings.add("DEPLOY_NOT_MAIN_ONLY")
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

    # The target lives in the repository's variables: no address, host key or checkout path in source.
    if (re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", text) or re.search(r"ssh-(?:ed25519|rsa|dss) AAAA", text)
            or re.search(r"/srv/", text) or "sslip.io" in text):
        findings.add("TARGET_IN_SOURCE")
    if (text.count("${{ vars.DEPLOY_HOST }}") != 2 or text.count("${{ vars.DEPLOY_KNOWN_HOSTS }}") != 1
            or text.count("${{ vars.DEPLOY_PATH }}") != 1 or "secrets.VPS_HOST" in text or "secrets.VPS_KNOWN_HOSTS" in text):
        findings.add("TARGET_NOT_FROM_VARIABLES")

    # The server checks where the deployment comes from before it writes or fetches anything.
    try:
        remote = _remote_script(text)
    except AssertionError:
        findings.add("SOURCE_NOT_BOUND")
    else:
        binding = remote.find("git remote get-url origin")
        refusal = remote.find("this deployment comes from")
        first_write = min(position for position in (remote.find(".git/info"), remote.find("git fetch")) if position >= 0)
        if ("DEPLOY_REPOSITORY: ${{ github.repository }}" not in text or binding < 0 or refusal < 0
                or not binding < refusal < first_write or "exit 4" not in remote[refusal:first_write]):
            findings.add("SOURCE_NOT_BOUND")
    return findings


def _run(script: str, args: list[str], env: dict[str, str], stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", "-c", script, "workflow-step", *args], input=stdin, text=True, capture_output=True,
                          env=env, timeout=20, check=False)


class DeployAutoWorkflowContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_only_main_and_manual_dispatch_trigger_deployment(self) -> None:
        self.assertNotIn("DEPLOY_TRIGGER_SET", workflow_shape_findings(self.text))
        self.assertNotIn("DEPLOY_PUSH_BRANCH", workflow_shape_findings(self.text))
        self.assertNotIn("DEPLOY_JOB_CONDITION", workflow_shape_findings(self.text))
        self.assertNotIn("DEPLOY_NOT_MAIN_ONLY", workflow_shape_findings(self.text))
        self.assertIn(f"    if: {JOB_CONDITION}\n", self.text)

    def test_workflow_permissions_are_exactly_read_only(self) -> None:
        self.assertNotIn("TOP_LEVEL_PERMISSIONS", workflow_shape_findings(self.text))
        self.assertNotIn("JOB_PERMISSIONS", workflow_shape_findings(self.text))

    def test_deployments_are_serial_and_never_cancel_each_other(self) -> None:
        self.assertIn("group: auditmanager-alpha-production", self.text)
        self.assertIn("cancel-in-progress: false", self.text)

    def test_the_server_is_this_repositorys_configuration_and_never_source(self) -> None:
        findings = workflow_shape_findings(self.text)
        self.assertNotIn("TARGET_IN_SOURCE", findings)
        self.assertNotIn("TARGET_NOT_FROM_VARIABLES", findings)
        for secret in ("VPS_USER", "VPS_SSH_KEY"):
            self.assertIn(f"secrets.{secret}", self.text)
        for option in ("StrictHostKeyChecking=yes", "BatchMode=yes", "IdentitiesOnly=yes", 'UserKnownHostsFile="$HOME/.ssh/known_hosts"'):
            self.assertIn(option, self.text)
        self.assertNotIn("StrictHostKeyChecking=no", self.text)
        self.assertNotIn("ssh-keyscan", self.text)

    def test_the_server_accepts_only_its_own_repository_before_it_writes_anything(self) -> None:
        self.assertNotIn("SOURCE_NOT_BOUND", workflow_shape_findings(self.text))

    def test_prepare_refuses_until_this_repository_names_its_server(self) -> None:
        script = _prepare_script(self.text)
        good = f"203.0.113.7 ssh-ed25519 {KEY}\nprod.example.org ssh-ed25519 {KEY}\n"
        refused = {
            "no variables at all (a fresh fork)": ({"DEPLOY_HOST": "", "DEPLOY_KNOWN_HOSTS": ""}, "are not configured for this repository"),
            "no host key": ({"DEPLOY_KNOWN_HOSTS": ""}, "are not configured for this repository"),
            "no ssh key": ({"SSH_KEY": ""}, "VPS_SSH_KEY is not configured"),
            "a host with a space": ({"DEPLOY_HOST": "203.0.113.7 -oProxyCommand=x"}, "DEPLOY_HOST is not a host name"),
            "a hashed host line": ({"DEPLOY_KNOWN_HOSTS": f"|1|abc=|def= ssh-ed25519 {KEY}"}, "not a plain host key"),
            "a marker line": ({"DEPLOY_KNOWN_HOSTS": f"@cert-authority * ssh-ed25519 {KEY}"}, "not a plain host key"),
            "a comment line": ({"DEPLOY_KNOWN_HOSTS": f"# 203.0.113.7 ssh-ed25519 {KEY}"}, "not a plain host key"),
            "keys for another server only": ({"DEPLOY_KNOWN_HOSTS": f"198.51.100.1 ssh-ed25519 {KEY}"}, "has no key for DEPLOY_HOST"),
        }
        with tempfile.TemporaryDirectory() as home:
            base = {"PATH": os.environ["PATH"], "HOME": home, "SSH_KEY": "-----BEGIN KEY-----", "DEPLOY_HOST": "203.0.113.7",
                    "DEPLOY_KNOWN_HOSTS": good}
            for case, (override, message) in refused.items():
                with self.subTest(case=case):
                    completed = _run(script, [], base | override)
                    self.assertEqual(completed.returncode, 1, completed.stderr)
                    self.assertIn(message, completed.stdout)
                    self.assertFalse((Path(home) / ".ssh" / "known_hosts").exists())
            for host, keys in (("203.0.113.7", good), ("prod.example.org", good.replace("\n", "\r\n")),
                               ("10.0.0.5", f"ops.example.org,10.0.0.5 ssh-ed25519 {KEY}")):
                with self.subTest(accepted=host):
                    completed = _run(script, [], base | {"DEPLOY_HOST": host, "DEPLOY_KNOWN_HOSTS": keys})
                    self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                    written = (Path(home) / ".ssh" / "known_hosts").read_text(encoding="utf-8")
                    self.assertNotIn("\r", written)
                    self.assertIn(host, written)
                    self.assertEqual(oct((Path(home) / ".ssh" / "known_hosts").stat().st_mode & 0o777), "0o600")

    def test_the_deploy_step_validates_its_path_and_passes_the_repository(self) -> None:
        script = _deploy_step_script(self.text)
        with tempfile.TemporaryDirectory() as temporary:
            binaries = Path(temporary) / "bin"
            binaries.mkdir()
            ssh_stub = binaries / "ssh"
            ssh_stub.write_text('#!/bin/sh\nprintf "SSH %s\\n" "$*"\ncat >/dev/null\n', encoding="utf-8")
            ssh_stub.chmod(0o755)
            base = {"PATH": f"{binaries}:{os.environ['PATH']}", "HOME": temporary, "VPS_HOST": "203.0.113.7", "VPS_USER": "deploy",
                    "DEPLOY_PATH": "/srv/fork-app", "DEPLOY_SHA": SHA, "DEPLOY_REPOSITORY": "owner/fork-app"}
            for path in ("", "relative/app", "/srv/../etc", "/srv/./app", "/srv/app name", "/srv/app;rm"):
                with self.subTest(refused=path):
                    completed = _run(script, [], base | {"DEPLOY_PATH": path})
                    self.assertEqual(completed.returncode, 1, completed.stderr)
                    self.assertIn("DEPLOY_PATH is not configured", completed.stdout)
                    self.assertNotIn("SSH ", completed.stdout)
            completed = _run(script, [], base)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn(f"deploy@203.0.113.7 bash -s -- {SHA} /srv/fork-app owner/fork-app", completed.stdout)
            self.assertNotEqual(_run(script, [], base | {"DEPLOY_REPOSITORY": "owner/app;x"}).returncode, 0)

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
            "git remote get-url origin",
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

    def _host(self, root: Path) -> tuple[Path, dict[str, str]]:
        """A checkout with stub git and deploy scripts; ``TEST_ORIGIN`` is what ``git remote get-url origin`` answers."""
        repository = root / "repo"
        deployment = repository / "infra" / "deploy"
        deployment.mkdir(parents=True)
        (repository / ".git").mkdir()
        binaries = root / "bin"
        binaries.mkdir()
        git_stub = binaries / "git"
        git_stub.write_text(
            '#!/bin/sh\n'
            'if [ "$1" = rev-parse ]; then printf "%s\\n" "$TEST_SHA"; fi\n'
            'if [ "$1" = remote ] && [ "$2" = get-url ]; then printf "%s\\n" "$TEST_ORIGIN"; fi\n'
            'if [ "$1" = fetch ]; then printf "FETCHED\\n"; fi\n',
            encoding="utf-8",
        )
        git_stub.chmod(0o755)
        deploy_stub = deployment / "deploy.sh"
        deploy_stub.write_text('#!/bin/sh\nprintf "DEPLOY STUB CALLED\\n"\ncat >/dev/null\n', encoding="utf-8")
        deploy_stub.chmod(0o755)
        verify_stub = deployment / "verify-deployed.sh"
        verify_stub.write_text(
            '#!/bin/sh\nprintf "VERIFY STUB CALLED\\n"\ncat >/dev/null\nexit "${VERIFY_EXIT:-0}"\n', encoding="utf-8"
        )
        verify_stub.chmod(0o755)
        environment = os.environ | {"PATH": f"{binaries}:{os.environ['PATH']}", "TEST_SHA": SHA,
                                    "TEST_ORIGIN": "https://github.com/Owner/Product.git"}
        return repository, environment

    def _remote(self, repository: Path, environment: dict[str, str], source: str, **extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["bash", "-s", "--", SHA, str(repository), source], input=_remote_script(self.text), text=True,
                              capture_output=True, env=environment | extra, timeout=10, check=False)

    def test_a_server_deploys_only_the_repository_it_was_cloned_from(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository, environment = self._host(Path(temporary))
            for origin in ("https://github.com/Owner/Product.git", "https://github.com/owner/product", "git@github.com:owner/product.git",
                           "ssh://git@github.com/Owner/Product.git", "github-deploy:Owner/Product.git",
                           "https://x-access-token:secret@github.com/Owner/Product.git/"):
                with self.subTest(accepted=origin):
                    completed = self._remote(repository, environment, "Owner/Product", TEST_ORIGIN=origin)
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertIn(f"DEPLOY OK: {SHA}", completed.stdout)
            for origin, source in (("https://github.com/Owner/Product.git", "fork-owner/Product"),
                                   ("https://github.com/Owner/Product.git", "Owner/Product-fork"),
                                   ("git@github.com:fork-owner/product.git", "Owner/Product"),
                                   ("/srv/mirror.git", "Owner/Product")):
                with self.subTest(refused=(origin, source)):
                    exclude = repository / ".git" / "info" / "exclude"
                    if exclude.exists():
                        exclude.unlink()
                    completed = self._remote(repository, environment, source, TEST_ORIGIN=origin)
                    self.assertEqual(completed.returncode, 4, completed.stdout + completed.stderr)
                    self.assertIn("this deployment comes from", completed.stderr)
                    for never in ("FETCHED", "DEPLOY STUB CALLED", "DEPLOY OK:"):
                        self.assertNotIn(never, completed.stdout)
                    self.assertFalse(exclude.exists(), "a refused deployment wrote to the checkout")

    def test_stdin_draining_deploy_cannot_skip_host_verification(self) -> None:
        """A child reading stdin must not swallow later remote shell commands."""
        with tempfile.TemporaryDirectory() as temporary:
            repository, environment = self._host(Path(temporary))
            for verify_exit in ("0", "7"):
                with self.subTest(verify_exit=verify_exit):
                    completed = self._remote(repository, environment, "Owner/Product", VERIFY_EXIT=verify_exit)
                    self.assertIn("DEPLOY STUB CALLED", completed.stdout)
                    self.assertIn("=== verify deployed tree ===", completed.stdout)
                    self.assertIn("VERIFY STUB CALLED", completed.stdout)
                    if verify_exit == "0":
                        self.assertEqual(completed.returncode, 0, completed.stderr)
                        self.assertIn(f"DEPLOY OK: {SHA}", completed.stdout)
                    else:
                        self.assertEqual(completed.returncode, 7)
                        self.assertNotIn("DEPLOY OK:", completed.stdout)

    def test_deploy_local_runs_the_workflows_own_remote_script_byte_for_byte(self) -> None:
        """`FIRST-INSTALL-03`: the pull-based deploy and the ssh-based one are one script. If either changes alone, this fails."""
        local = _local_remote_script(DEPLOY_LOCAL.read_text(encoding="utf-8"))
        self.assertEqual(local, _remote_script(self.text).rstrip("\n"))
        self.assertGreater(len(local.splitlines()), 40)
        changed = self.text.replace('echo "DEPLOY OK: $DEPLOY_SHA"', 'echo "DEPLOY OK: $DEPLOY_SHA" # changed here only', 1)
        self.assertNotEqual(local, _remote_script(changed).rstrip("\n"))

    def test_deploy_local_orders_the_commands_the_way_the_workflow_does(self) -> None:
        ordered = (
            "git remote get-url origin",
            "git fetch --prune origin",
            'git cat-file -e "${DEPLOY_SHA}^{commit}"',
            'git merge-base --is-ancestor "$DEPLOY_SHA" origin/main',
            'git checkout --detach "$DEPLOY_SHA"',
            "infra/deploy/deploy.sh </dev/null",
            "infra/deploy/verify-deployed.sh </dev/null",
            'echo "DEPLOY OK: $DEPLOY_SHA"',
        )
        local = DEPLOY_LOCAL.read_text(encoding="utf-8")
        inside = _local_remote_script(local)
        positions = [inside.index(fragment) for fragment in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertGreaterEqual(inside.count('test "$(git rev-parse HEAD)" = "$DEPLOY_SHA"'), 2)
        self.assertGreaterEqual(inside.count("git status --porcelain --untracked-files=all"), 3)
        # Nothing of the deploy is done outside that script: the wrapper only chooses the commit, locks, logs and records.
        outside = "\n".join(line for line in local.replace(inside, "").splitlines() if not line.lstrip().startswith("#"))
        for command in ("git checkout", "git fetch", "git merge-base", "infra/deploy/deploy.sh", "infra/deploy/verify-deployed.sh", "git pull",
                        "git clean", "git reset"):
            self.assertNotIn(command, outside, command)

    def test_the_job_condition_is_exactly_main_and_the_explicit_local_opt_out(self) -> None:
        self.assertEqual(workflow_shape_findings(self.text) & {"DEPLOY_JOB_CONDITION", "DEPLOY_NOT_MAIN_ONLY"}, set())
        self.assertEqual(re.findall(r"(?m)^    if: (.*)$", self.text), [JOB_CONDITION])
        # Unset means "not local": the job runs and the missing DEPLOY_* variables stop it, as they always did.
        self.assertIn("DEPLOY_HOST and DEPLOY_KNOWN_HOSTS are not configured for this repository", self.text)

    def test_semantic_mutations_are_rejected(self) -> None:
        no_main_guard = self.text.replace(f"    if: {JOB_CONDITION}\n", "    if: vars.DEPLOY_MODE != 'local'\n", 1)
        self.assertIn("DEPLOY_NOT_MAIN_ONLY", workflow_shape_findings(no_main_guard))
        self.assertIn("DEPLOY_JOB_CONDITION", workflow_shape_findings(no_main_guard))
        no_job_condition = self.text.replace(f"    if: {JOB_CONDITION}\n", "", 1)
        self.assertIn("DEPLOY_NOT_MAIN_ONLY", workflow_shape_findings(no_job_condition))
        no_opt_out = self.text.replace(f"    if: {JOB_CONDITION}\n", "    if: github.ref == 'refs/heads/main'\n", 1)
        self.assertIn("DEPLOY_JOB_CONDITION", workflow_shape_findings(no_opt_out))
        silent_skip = self.text.replace("vars.DEPLOY_MODE != 'local'", "vars.DEPLOY_HOST != ''", 1)
        self.assertIn("DEPLOY_JOB_CONDITION", workflow_shape_findings(silent_skip))
        wrong_mode = self.text.replace("vars.DEPLOY_MODE != 'local'", "vars.DEPLOY_MODE == 'github'", 1)
        self.assertIn("DEPLOY_JOB_CONDITION", workflow_shape_findings(wrong_mode))
        or_condition = self.text.replace("&& vars.DEPLOY_MODE", "|| vars.DEPLOY_MODE", 1)
        self.assertIn("DEPLOY_JOB_CONDITION", workflow_shape_findings(or_condition))


        extra_trigger = self.text.replace(
            "  workflow_dispatch:\n", "  workflow_dispatch:\n  pull_request_target:\n", 1
        )
        self.assertIn("DEPLOY_TRIGGER_SET", workflow_shape_findings(extra_trigger))

        write_permission = self.text.replace("  contents: read\n", "  contents: write\n", 1)
        self.assertIn("TOP_LEVEL_PERMISSIONS", workflow_shape_findings(write_permission))

        job_write = self.text.replace(
            "    timeout-minutes: 90\n",
            "    timeout-minutes: 90\n    permissions:\n      contents: write\n",
            1,
        )
        self.assertIn("JOB_PERMISSIONS", workflow_shape_findings(job_write))

        pinned_host = self.text.replace("${{ vars.DEPLOY_HOST }}", "203.0.113.7", 1)
        self.assertIn("TARGET_IN_SOURCE", workflow_shape_findings(pinned_host))
        self.assertIn("TARGET_NOT_FROM_VARIABLES", workflow_shape_findings(pinned_host))

        pinned_key = self.text.replace(
            '"$DEPLOY_KNOWN_HOSTS" | tr', f"'prod.example.org ssh-ed25519 {KEY}' | tr", 1
        )
        self.assertIn("TARGET_IN_SOURCE", workflow_shape_findings(pinned_key))

        pinned_path = self.text.replace('"$DEPLOY_PATH" "$DEPLOY_REPOSITORY" <<', '/srv/app "$DEPLOY_REPOSITORY" <<', 1)
        self.assertIn("SOURCE_NOT_BOUND", workflow_shape_findings(pinned_path))
        self.assertIn("TARGET_IN_SOURCE", workflow_shape_findings(pinned_path))

        secret_host = self.text.replace("VPS_HOST: ${{ vars.DEPLOY_HOST }}", "VPS_HOST: ${{ secrets.VPS_HOST }}", 1)
        self.assertIn("TARGET_NOT_FROM_VARIABLES", workflow_shape_findings(secret_host))

        unbound = self.text.replace("            exit 4\n", "            true\n", 1)
        self.assertIn("SOURCE_NOT_BOUND", workflow_shape_findings(unbound))

        late_binding = self.text.replace('origin_url="$(git remote get-url origin)"', 'origin_url="$(git fetch && git remote get-url origin)"', 1)
        self.assertIn("SOURCE_NOT_BOUND", workflow_shape_findings(late_binding))


if __name__ == "__main__":
    unittest.main()
