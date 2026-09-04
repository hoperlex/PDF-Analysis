# CP-00 automated acceptance — primary report, round 6

This is the first primary automated report written in this program. Rounds one through
five recorded an automated verdict in `manifest.json` with `report_path: null`; the
round-three record notes in its own words that "no primary report file was written".
It is therefore written to be re-derived from, not read: every command below is
copyable, carries its real output, and carries the exit code of the process that was
actually measured.

## Start record

```text
candidate_commit:      5b70ee4e6c29931924f0ff56da499c5cfa0ef9a7 (integration/W0.3)
tested_candidate_digest (recomputed):
                       2b3929be6de447bd1c3a92ff1a9a4fe72bc12d4ee919f3d21af2a979e861582c
                       recipe: manifest.json candidate_digest_recipe; 214 paths;
                       matches the frozen value in manifest.json and in the round-6
                       acceptance_rounds entry
tree:                  5356a3cbb99ffef2eb88c72aedb3bbf43de7ef58
contract_manifest:     domain/analysis/events 1.0.0-draft.1; golden_selection_schema 1;
                       artifact_manifest_sha256 39721aac…, 100 files — recomputed, matches
manifest_blob:         fbcec186877a481dd8d50b39e1962b7c554f9652
                       sha256(file) b9edd536ac11a682a6f4d1dc6747606d60e4dc10efc812438bc82cf0883476ba
migration_head:        none (db/migrations holds only README.md)
backend_runtime:       not applicable - architecture-only checkpoint
frontend_runtime:      not applicable - architecture-only checkpoint
local_infra_versions:  not applicable - architecture-only checkpoint
auditor:               cp00_auto_auditor, independent agent; authored none of the
                       reviewed artifacts, the QA test module or the QA report, and
                       holds no write in this repository other than this file
environment:           Python 3.12.3 (.venv/bootstrap), git 2.43.0, GNU bash 5.2.21,
                       Linux 6.8.0-138-generic x86_64
started_at:            2026-09-04T15:47+05:00 — first measurement; the freeze commit
                       5b70ee4 is itself timestamped 2026-09-04T15:46:37+05:00, so the
                       whole audit runs after the freeze
finished_at:           2026-09-04T16:03+05:00
gate_measurement_window:
                       every command in this report ran between 15:47 and 15:57:42, the
                       latter being the moment the manual stream's report appeared in
                       the working tree (see section 4)
```

Every digest and count in this report was computed against the tree as it stood before
this file existed. Writing this file changes the tree; that is what
`evidence_bundle_digest` is for, and computing it is the integrator's step, not this
stream's.

## 0. Method: which number is the exit code

The task record for this program notes that `$?` after a pipeline reports the last
stage, not the failure, and that this has produced a false finding here before. Every
exit code in this report is measured by running the command with its output redirected
to a file and reading `$?` on the next line — no pipe stands between the process and
the measurement. The trap, shown rather than asserted:

```bash
false | true; echo "exit=$?"
```

```text
exit=0        <- the failing stage is invisible
```

```bash
set -o pipefail; false | true; echo "exit=$?"; set +o pipefail
```

```text
exit=1
```

The same discipline applies to `git status`, which exits `0` whether or not the tree is
dirty. Section 4 asserts a path set for that reason, and demonstrates the trap.

## 1. Confirming the input before judging it

Round six was frozen at `5b70ee4` with
`tested_candidate_digest = 2b3929be6de447bd1c3a92ff1a9a4fe72bc12d4ee919f3d21af2a979e861582c`.
The recipe was implemented from the manifest prose alone. The module helper
`_acceptance_digest` was **not** called: a stream that asks the artifact under test
whether it agrees with itself has measured nothing.

```bash
cat > /tmp/recompute_digest.py <<'PY'
import hashlib, json, subprocess, sys
from pathlib import Path

ROOT = Path("/root/projects/PDF-Analysis")
MANIFEST_REL = "artifacts/checkpoints/CP-00/manifest.json"

def git(*args):
    out = subprocess.run(["git", "-C", str(ROOT), *args],
                         capture_output=True, text=True, check=True)
    return [line for line in out.stdout.split("\n") if line]

def digest(field):
    cached = git("ls-files", "--cached")
    others = git("ls-files", "--others", "--exclude-standard")
    paths = sorted(set(cached) | set(others))
    manifest = json.loads((ROOT / MANIFEST_REL).read_text(encoding="utf-8"))
    outer = hashlib.sha256()
    for rel in paths:
        if rel == MANIFEST_REL:
            blanked = json.loads(json.dumps(manifest))
            blanked[field] = ""
            for entry in blanked.get("acceptance_rounds", []):
                if field in entry:
                    entry[field] = ""
            payload = json.dumps(blanked, sort_keys=True,
                                 separators=(",", ":")).encode("utf-8")
        else:
            payload = (ROOT / rel).read_bytes()
        outer.update(rel.encode("utf-8"))
        outer.update(hashlib.sha256(payload).digest())
    return outer.hexdigest(), len(paths)

field = sys.argv[1] if len(sys.argv) > 1 else "tested_candidate_digest"
value, count = digest(field)
print(f"field={field}")
print(f"paths_enumerated={count}")
print(f"recomputed={value}")
PY
cd /root/projects/PDF-Analysis
.venv/bootstrap/bin/python /tmp/recompute_digest.py tested_candidate_digest
```

```text
field=tested_candidate_digest
paths_enumerated=214
recomputed=2b3929be6de447bd1c3a92ff1a9a4fe72bc12d4ee919f3d21af2a979e861582c
```

measured exit `0`.

**The recomputed value equals the frozen value.** The tree in front of this stream is
the tree round six froze, and the verdict below is a statement about that tree.

Two further facts pin it. First, `5b70ee4` is the only commit in this repository whose
manifest carries that value, so the freeze commit and the audited commit are the same
commit and the post-freeze delta is empty:

```bash
cd /root/projects/PDF-Analysis
for c in $(git log --format=%H -- artifacts/checkpoints/CP-00/manifest.json); do
  v=$(git show $c:artifacts/checkpoints/CP-00/manifest.json \
      | .venv/bootstrap/bin/python -c "import json,sys; print(json.load(sys.stdin).get('tested_candidate_digest'))")
  echo "$(git log -1 --format='%h %ad' --date=short $c)  tested=$v"
done
```

```text
5b70ee4 2026-09-04  tested=2b3929be6de447bd1c3a92ff1a9a4fe72bc12d4ee919f3d21af2a979e861582c
5207fb5 2026-09-03  tested=22e3027b2721d60810ed088911c4cf3ebcfe86a50f6a1fa9e606c2da91177c3a
cdd0c64 2026-09-03  tested=None
e7f3989 2026-09-03  tested=None
ae59d8b 2026-09-03  tested=None
a667a4b 2026-09-02  tested=None
016670a 2026-09-02  tested=None
877fabc 2026-09-02  tested=None
718f90a 2026-09-02  tested=None
00ec644 2026-09-02  tested=None
f4b8882 2026-09-02  tested=None
```

`22e3027b…` is round five's digest, recorded `void` in the manifest; it is present as
history and is not the input here.

Second, index, working tree and `HEAD` are one tree, so "the tree the digest walked"
and "the tree of the commit" are not two different things:

```bash
cd /root/projects/PDF-Analysis
git diff --cached --quiet HEAD; echo "index_vs_HEAD_exit=$?"
git diff --quiet;               echo "worktree_vs_index_exit=$?"
```

```text
index_vs_HEAD_exit=0
worktree_vs_index_exit=0
```

## 2. The contract test suite

```bash
cd /root/projects/PDF-Analysis
.venv/bootstrap/bin/python -m unittest discover -s tests/contract > /tmp/g1.out 2>&1
echo "exit=$?"; cat /tmp/g1.out
```

```text
exit=0
...............................................................................
----------------------------------------------------------------------
Ran 281 tests in 30.640s

OK
```

(The progress line is 281 dots; it is elided here only for width.)

No test is skipped. `OK` carries no `(skipped=N)`, and the verbose run counts 281 `ok`
results and zero `FAIL`/`ERROR`:

```bash
cd /root/projects/PDF-Analysis
.venv/bootstrap/bin/python -m unittest discover -s tests/contract -v > /tmp/verbose_all.out 2>&1
echo "exit=$?"
echo "ok:        $(grep -c ' \.\.\. ok$' /tmp/verbose_all.out)"
echo "fail/error: $(grep -cE '\.\.\. (FAIL|ERROR)' /tmp/verbose_all.out)"
tail -4 /tmp/verbose_all.out
```

```text
exit=0
ok:        281
fail/error: 0
----------------------------------------------------------------------
Ran 281 tests in 34.793s

OK
```

Two lines in the verbose output contain the word "skipped"; both are test docstrings
("nothing declared was skipped", "one reconciliation skipped"), not skip results.

### 2.1 Per module

```bash
cd /root/projects/PDF-Analysis
.venv/bootstrap/bin/python -m unittest discover -s tests/contract \
    -p 'test_cp00_candidate.py' -v > /tmp/g2a.out 2>&1
echo "exit=$?"; tail -4 /tmp/g2a.out
```

```text
exit=0
----------------------------------------------------------------------
Ran 255 tests in 29.000s

OK
```

```bash
cd /root/projects/PDF-Analysis
.venv/bootstrap/bin/python -m unittest discover -s tests/contract \
    -p 'test_validate_bootstrap.py' -v > /tmp/g2b.out 2>&1
echo "exit=$?"; tail -4 /tmp/g2b.out
```

```text
exit=0
----------------------------------------------------------------------
Ran 26 tests in 2.699s

OK
```

255 + 26 = 281, so the discovery run in §2 covers both modules and nothing else.

## 3. The bootstrap validator, standalone

```bash
cd /root/projects/PDF-Analysis
.venv/bootstrap/bin/python scripts/validate_bootstrap.py > /tmp/g3.out 2>&1
echo "exit=$?"; cat /tmp/g3.out
```

```text
exit=0
Bootstrap validation
  json_files=56
  markdown_files=148
  stages=11
  manual_runbooks=11
  adrs=18
PASS
```

`stages=11` here counts `docs/stages/S\d\d_*.md` files. It is a different quantity from
the nine `stage-registry.json` stages recomputed in §8, and the two are not in conflict.
Recorded because the two numbers appear under the same word.

## 4. Working tree cleanliness — asserted as a path set

`git status --porcelain` exits `0` on a dirty tree. The assertion is therefore the set
of reported paths, and the empty set is accepted as the passing result.

```bash
cd /root/projects/PDF-Analysis
git status --porcelain -uall > /tmp/g4a.out 2>&1
echo "exit=$?"; echo "path_count=$(wc -l < /tmp/g4a.out)"; cat /tmp/g4a.out
```

```text
exit=0
path_count=0
```

```bash
cd /root/projects/PDF-Analysis
git status --porcelain -uall -- contracts fixtures docs/architecture scripts > /tmp/g4b.out 2>&1
echo "exit=$?"; echo "path_count=$(wc -l < /tmp/g4b.out)"; cat /tmp/g4b.out
```

```text
exit=0
path_count=0
```

Both path sets are empty at the moment of measurement, which was before 15:57:42. At
15:57:42 the round-6 **manual** stream wrote
`artifacts/checkpoints/CP-00/manual-report-round-6.md`, and this file was written at
15:59:58, so a `git status` run now reports those two untracked paths. Neither existed
when any measurement in this report was taken, neither is inside the four reviewed
families, and re-running the scoped assertion after both appeared still returns the empty
set:

```bash
cd /root/projects/PDF-Analysis
git status --porcelain -uall -- contracts fixtures docs/architecture scripts
echo "reviewed_family_path_count=$(git status --porcelain -uall -- contracts fixtures docs/architecture scripts | wc -l)"
```

```text
reviewed_family_path_count=0
```

That the exit code proves nothing on its own is shown against a throwaway repository
deliberately made dirty:

```bash
T=$(mktemp -d); git -C "$T" init -q; echo x > "$T/f"; git -C "$T" add f
git -C "$T" -c user.email=a@b -c user.name=a commit -qm i
echo CHANGED > "$T/f"
git -C "$T" status --porcelain -uall; echo "exit=$?"; rm -rf "$T"
```

```text
 M f
exit=0
```

A stream that had asserted the exit code would have called that tree clean.

## 5. The four reviewed families against `reviewed_candidate_commit`

`reviewed_candidate_commit` is `92e13fa496a723ed6e4c3adbf138c4f4e1d7c368`.

```bash
cd /root/projects/PDF-Analysis
git rev-parse --verify 92e13fa496a723ed6e4c3adbf138c4f4e1d7c368^{commit}; echo "exit=$?"
git diff --name-status 92e13fa496a723ed6e4c3adbf138c4f4e1d7c368 HEAD \
    -- contracts fixtures docs/architecture scripts > /tmp/g5.out 2>&1
echo "exit=$?"; echo "changed_paths=$(wc -l < /tmp/g5.out)"; cat /tmp/g5.out
```

```text
92e13fa496a723ed6e4c3adbf138c4f4e1d7c368
exit=0
exit=0
changed_paths=0
```

The empty diff is corroborated by content rather than by Git's own comparison: the
`artifact_manifest_recipe` digest over the four families is computed independently at
both commits in §8 and is the same value. A digest over 100 files, computed from blob
contents at two commits, agreeing bit for bit is a byte-identity statement that does not
depend on `git diff` being asked the right question.

## 6. Analysis gates A–D, extracted from the contract and run verbatim

The gate text is not restated in this report. It is read out of
`contracts/analysis/v1/README.md` at run time by heading, so a gate that is edited,
renamed or removed changes what runs and this report stops reproducing.

```bash
cat > /tmp/extract_gates.py <<'PY'
import sys
from pathlib import Path
README = Path("/root/projects/PDF-Analysis/contracts/analysis/v1/README.md")

def fenced_blocks(text):
    blocks, heading = [], None
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#"):
            heading = line.strip()
        if line.startswith("```"):
            body = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                body.append(lines[i]); i += 1
            blocks.append((heading, "\n".join(body) + "\n"))
        i += 1
    return blocks

letter = sys.argv[1]
wanted = f"### Gate {letter} "
matches = [b for h, b in fenced_blocks(README.read_text(encoding="utf-8"))
           if h and h.startswith(wanted)]
if len(matches) != 1:
    raise SystemExit(f"Gate {letter}: found {len(matches)} blocks, expected 1")
sys.stdout.write(matches[0])
PY
cd /root/projects/PDF-Analysis
for L in A B C D; do
  .venv/bootstrap/bin/python /tmp/extract_gates.py $L > /tmp/gate$L.sh
  echo "extract_$L=$? bytes=$(wc -c < /tmp/gate$L.sh)"
  bash /tmp/gate$L.sh > /tmp/gate$L.out 2>&1
  echo "GATE_${L}_EXIT=$?"
  cat /tmp/gate$L.out
done
```

Each gate was located exactly once (`extract_A..D` all exit `0`; block sizes 3825, 2015,
5132 and 8656 bytes). Measured exit codes and full stdout:

**Gate A — name-level alias map structure**, exit `0`:

```text
name-map gate PASS: 62 unique names, 293 observations, 31/31 alias-bearing sites, findings_merge->finding_merge, 19 example stage_id references resolve in the registry, envelope key contract_version only
```

**Gate B — every evidence locator resolves in the frozen legacy commit**, exit `0`:

```text
evidence gate PASS: 293/293 locators resolve at 32b9d903792b30506048a1d42b0e6b2d07aee403; 256 of them are additionally bound to the legacy file their own declaration site names, the remaining 37 belong to the 6 of 31 sites the accepted inventory names by concern rather than by path
```

**Gate C — independent reviewer checks, made mechanical**, exit `0`:

```text
reviewer gate PASS: 9/9 stages carry accepted capability evidence and name-level evidence, and each stage_id still denotes the stage whose capabilities and produced roles it carries; 11/11 exclusion ids still denote their recorded owning boundary; 31/31 alias-bearing declaration sites bound to concrete names; related_stage_ids is a superset of name evidence on all 31 sites; site distribution {'control_plane': 25, 'sub_pipeline': 2, 'excluded': 3, 'stage': 1}
```

**Gate D — owner decisions transferred by their real state**, exit `0`:

```text
decision-transfer gate PASS: PD-03 has all 9 creation triggers with the complete owner outcome tuple and the exact owner-ruled rule_id on each of them; inputs_changed and repeat_of_terminal_run create a new Run; retry/resume/restart/worker_failover each create exactly one Attempt and no Run; the idempotent replay creates neither; RC-02 beats RC-05, both precedence references resolve to the triggers the ruling is about, and the resolved outcome is the winner outcome; no trigger reopens a terminal Run; both attempt_authority descriptions are identical and complete; PD-05 identifier confirmed
```

All four are byte-identical to the results `docs/program/reviews/W0-QA-01.md` §3.1
records, which is a reproduction of that report's central claim by a stream that did not
write it.

Gate B addresses the legacy repository at
`/root/projects/PDF-proverka/PDF-proverka` and reads immutable Git objects at
`32b9d903792b30506048a1d42b0e6b2d07aee403`. That repository is present in this
environment (`git -C … rev-parse --short HEAD` → `c0771b2e`, exit `0`), which is why the
gate could run at all. Its availability is an environment precondition, not a property
of this repository; see §9.

## 7. The rest of the documented gate surface

The checkpoint's gates are not confined to the analysis README. Every `bash`-fenced block of
the four remaining gate documents was extracted in source order and run, each block's
own exit code measured separately.

```bash
cat > /tmp/extract_blocks.py <<'PY'
import sys
from pathlib import Path
ROOT = Path("/root/projects/PDF-Analysis")
rel, index = sys.argv[1], int(sys.argv[2])
lines = (ROOT / rel).read_text(encoding="utf-8").splitlines()
blocks, i = [], 0
while i < len(lines):
    if lines[i].startswith("```bash"):
        body = []
        i += 1
        while i < len(lines) and not lines[i].startswith("```"):
            body.append(lines[i]); i += 1
        blocks.append("\n".join(body) + "\n")
    i += 1
print(len(blocks)) if index == -1 else sys.stdout.write(blocks[index])
PY
cd /root/projects/PDF-Analysis
for f in contracts/domain/v1/README.md contracts/events/v1/README.md \
         fixtures/golden/SELECTION.md docs/architecture/ARCHITECTURE_LINT_RULES.md; do
  n=$(.venv/bootstrap/bin/python /tmp/extract_blocks.py "$f" -1)
  for i in $(seq 0 $((n-1))); do
    .venv/bootstrap/bin/python /tmp/extract_blocks.py "$f" $i > /tmp/blk.sh
    bash /tmp/blk.sh > /tmp/blk.out 2>&1
    echo "$f block $((i+1))/$n exit=$?"
    cat /tmp/blk.out
  done
done
```

| Document | Block | Exit | Output |
|---|---|---|---|
| `contracts/domain/v1/README.md` | 1/4 | `0` | validator standalone `PASS` |
| | 2/4 | `0` | (no output) |
| | 3/4 | `0` | `guard and run_creation codes OK 13`; `identifier bindings OK 10 \| contract_version OK 1.0.0-draft.1 \| candidate_revision 5` |
| | 4/4 | `0` | `optional-branch policy OK`; `negative probes rejected by the schema: 15 / 15` |
| `contracts/events/v1/README.md` | 1/6 | `0` | (no output) |
| | 2/6 | `0` | (jsonschema CLI deprecation warning only) |
| | 3/6 | `0` | `rejected for schema_version alone: Additional properties are not allowed ('schema_version' was unexpected)` |
| | 4/6 | `0` | (no output) |
| | 5/6 | **`1`** | `AssertionError: [('contracts/events/v1/examples/event-envelope.legacy-schema-version.invalid.json', ['<top>/schema_version'])]` |
| | 6/6 | `0` | validator standalone `PASS` |
| `fixtures/golden/SELECTION.md` | 1/2 | `0` | `True` / `True` |
| | 2/2 | `0` | `U-05 PASS: 11 inventory candidates mapped to 92 assertions; 95 declared in total` |
| `docs/architecture/ARCHITECTURE_LINT_RULES.md` | 1/9 | `0` | (no output) |
| | 2/9 | `0` | (no output) |
| | 3/9 | `0` | `identity pin ok` |
| | 4/9 | `0` | `rename, duplicate, severity flip and removal all rejected` |
| | 5/9 | `0` | `anchor files present at base commit: 13` |
| | 6/9 | `0` | `every cited frozen input is anchored; rules checked: 33` |
| | 7/9 | `0` | `GATE-E rejects a path present only in the working tree: docs/architecture/ARCHITECTURE_LINT_RULES.json` |
| | 8/9 | `0` | validator standalone `PASS` |
| | 9/9 | `0` | `write boundary holds: exactly the two owned files under docs/architecture; git status reports nothing, so both are committed and clean` |

Events block 5 exits `1` **as documented**: it is the negative probe, and the assertion
names exactly the one file whose purpose is to carry the rejected `schema_version` key.
It is recorded as a pass on its documented shape, not as an exit-code pass, and it is
the reason a bare "all gates exit 0" claim would be wrong here.

### 7.1 The analysis README §Gates command list, measured per command

The block under `## Gates` is eight commands in sequence. Running it as one script
reports only the eighth command's status — the pipeline trap in another form — so each
line was measured on its own:

```bash
cd /root/projects/PDF-Analysis
sed -n '619,626p' contracts/analysis/v1/README.md > /tmp/gates_list.sh
i=0
while IFS= read -r line; do
  i=$((i+1)); [ -z "$line" ] && continue
  out=$(eval "$line" 2>&1); echo "cmd $i exit=$?"
done < /tmp/gates_list.sh
```

```text
cmd 1 exit=0
cmd 2 exit=0
cmd 3 exit=0
cmd 4 exit=0
cmd 5 exit=0
cmd 6 exit=0
cmd 7 exit=0
cmd 8 exit=0
```

Six schema/instance validations, one `check_schema` sweep and the standalone validator,
each individually `0`.

## 8. Recomputed counts and hashes

Recomputed from repository data — the JSON artifacts and the Git object database — not
read out of any report, gate output or state document. The right-hand column names where
the program states the number, so that agreement is a reproduction and not a copy.

| Quantity | Recomputed | Stated at | Reproduces |
|---|---|---|---|
| `tested_candidate_digest` | `2b3929be6de447bd1c3a92ff1a9a4fe72bc12d4ee919f3d21af2a979e861582c` over 214 paths | `manifest.json` top level and round-6 entry | **yes** |
| `artifact_manifest_sha256` | `39721aac0ebe1aa5c13d0ae3e01ee93380671daddc5d9f3f3b774997d6f75e08` | `manifest.json` | **yes** |
| `artifact_count` | 100 | `manifest.json` `artifact_count: 100` | **yes** |
| Registry stages | 9 (9 distinct `stage_id`) | `contracts/analysis/v1/README.md` "9 stages" | **yes** |
| Legacy name resolutions | 62 rows — 29 `canonical_stage`, 33 `excluded`; `name_count` field also 62 | README "62 names"; manifest "62 name rows" | **yes** |
| Alias-bearing declaration sites | 31, equal to the set of sites carrying an observation, and a subset of the 31 site-map declarations | README "31/31 sites"; manifest "over 31 alias-bearing sites" | **yes** |
| Immutable evidence locators | 293 observation records, 293 distinct `(evidence, evidence_line, evidence_literal)` triples, all 293 pinned to `32b9d903…` | README "293 locators"; `CURRENT_STATE.md` "293 immutable evidence locators"; `W0.3` wave plan | **yes** |
| Reviewed files, `contracts` | 33 | — | matches at both commits |
| Reviewed files, `fixtures` | 32 | — | matches at both commits |
| Reviewed files, `docs/architecture` | 33 | — | matches at both commits |
| Reviewed files, `scripts` | 2 | — | matches at both commits |
| Reviewed files, total | 100 | `manifest.json` `artifact_count` | **yes** |
| Registry `excluded_scope` ids | 11 | Gate C "11/11" | **yes** |
| Site distribution | `control_plane` 25, `sub_pipeline` 2, `excluded` 3, `stage` 1 | README "the 25/2/3/1 distribution" | **yes** |

**Nothing failed to reproduce.** Every count and hash this stream was asked to recompute
returned the recorded value.

Two clarifications a later reader will want, neither a discrepancy:

* The 293 locators are 293 **observation records**, not 293 distinct file regions. They
  resolve to 39 distinct `commit:path:symbol@span` regions across 21 legacy files;
  several names are evidenced inside one region at different lines and literals. All 293
  `(evidence, evidence_line, evidence_literal)` triples are distinct, so no record is a
  duplicate. The program's "293 locators" and this stream's 293 are the same quantity.
* The frozen legacy commit is one value in three places and they agree:
  `legacy-stage-name-map.json:legacy_source_commit`,
  `legacy-stage-map.json:legacy_source_commit` and
  `manifest.json:frozen_inputs.behavioral_oracle` are all
  `32b9d903792b30506048a1d42b0e6b2d07aee403`, and all 293 locators are prefixed with it.

`artifact_manifest_sha256` was computed by the manifest's own recipe, from Git blobs
rather than from the working tree, at both the audited commit and the reviewed candidate:

```bash
cat > /tmp/recompute_artifact_manifest.py <<'PY'
import hashlib, subprocess, sys
ROOT = "/root/projects/PDF-Analysis"
FAMILIES = ["contracts", "fixtures", "docs/architecture", "scripts"]
commit = sys.argv[1]
names = subprocess.run(["git", "-C", ROOT, "ls-tree", "-r", "--name-only", commit,
                        "--", *FAMILIES], capture_output=True, text=True,
                       check=True).stdout.split("\n")
paths = sorted(p for p in names if p)
outer = hashlib.sha256()
for rel in paths:
    blob = subprocess.run(["git", "-C", ROOT, "show", f"{commit}:{rel}"],
                          capture_output=True, check=True).stdout
    outer.update(rel.encode("utf-8"))
    outer.update(hashlib.sha256(blob).digest())
print(f"commit={commit}")
print(f"artifact_count={len(paths)}")
print(f"artifact_manifest_sha256={outer.hexdigest()}")
PY
cd /root/projects/PDF-Analysis
.venv/bootstrap/bin/python /tmp/recompute_artifact_manifest.py HEAD; echo "exit=$?"
.venv/bootstrap/bin/python /tmp/recompute_artifact_manifest.py \
    92e13fa496a723ed6e4c3adbf138c4f4e1d7c368; echo "exit=$?"
```

```text
commit=HEAD
artifact_count=100
artifact_manifest_sha256=39721aac0ebe1aa5c13d0ae3e01ee93380671daddc5d9f3f3b774997d6f75e08
exit=0
commit=92e13fa496a723ed6e4c3adbf138c4f4e1d7c368
artifact_count=100
artifact_manifest_sha256=39721aac0ebe1aa5c13d0ae3e01ee93380671daddc5d9f3f3b774997d6f75e08
exit=0
```

This is the §5 byte-identity claim restated as arithmetic over content.

## 9. The dependency lock

`requirements/validation.lock` is unchanged since `reviewed_candidate_commit`, and every
pin in it is the version actually installed in the interpreter that ran every gate above.

```bash
cd /root/projects/PDF-Analysis
git diff --name-status 92e13fa496a723ed6e4c3adbf138c4f4e1d7c368 HEAD -- requirements > /tmp/lock.out 2>&1
echo "exit=$?"; echo "changed_paths=$(wc -l < /tmp/lock.out)"
git diff --check -- requirements/validation.in requirements/validation.lock scripts/README.md
echo "diff_check_exit=$?"
sha256sum requirements/validation.lock requirements/validation.in
```

```text
exit=0
changed_paths=0
diff_check_exit=0
01c3f241cf9a3f38fed84c1a7d58f23f0cd7d22b842de40ebba4e3b6c7ac40d8  requirements/validation.lock
14d9df3dade913fe67e8a46bfa061152c88eac6350c28a89bfeecfcaa14cf56d  requirements/validation.in
```

```bash
cd /root/projects/PDF-Analysis
.venv/bootstrap/bin/python - <<'PY'
import re, importlib.metadata as md
from pathlib import Path
lock = Path('requirements/validation.lock').read_text()
pins = dict(re.findall(r'^([A-Za-z0-9_.\-]+)==([^\s\\]+)', lock, re.M))
ok = True
for name, ver in sorted(pins.items()):
    try:
        got = md.version(name)
    except md.PackageNotFoundError:
        got = "NOT INSTALLED"
    ok &= (got == ver)
    print(f"{name:28} locked={ver:12} installed={got:12} match={got == ver}")
print("all locked pins match:", bool(ok))
PY
echo "exit=$?"
```

```text
attrs                        locked=26.1.0       installed=26.1.0       match=True
jsonschema                   locked=4.26.0       installed=4.26.0       match=True
jsonschema-specifications    locked=2025.9.1     installed=2025.9.1     match=True
referencing                  locked=0.37.0       installed=0.37.0       match=True
rpds-py                      locked=2026.6.3     installed=2026.6.3     match=True
typing-extensions            locked=4.16.0       installed=4.16.0       match=True
all locked pins match: True
exit=0
```

`jsonschema` resolves to
`/root/projects/PDF-Analysis/.venv/bootstrap/lib/python3.12/site-packages/jsonschema/__init__.py`,
inside the bootstrap environment the gates name — not to a system installation.

The transitive set is checked, not only the direct pin: a `rpds-py` or `referencing`
substitution would change how every schema validation above behaves while
`jsonschema==4.26.0` still read as correct.

## 10. The declared report-visibility limit, checked

`manifest.json:recorded_limits.evidence_report_visibility` records that the acceptance
digests enumerate `--exclude-standard`, so a report path added to `.gitignore` would
leave every check silent about its content, and asks the next task touching the QA module
to assert that both report paths are tracked and not ignored. That test does not exist
yet, so this stream checked its own path by hand:

```bash
cd /root/projects/PDF-Analysis
git check-ignore -v artifacts/checkpoints/CP-00/automated-report-round-6.md
echo "check_ignore_exit=$?"
git ls-files --error-unmatch artifacts/checkpoints/CP-00/manual-report-round-3.md
echo "ls_files_exit=$?"
```

```text
check_ignore_exit=1
artifacts/checkpoints/CP-00/manual-report-round-3.md
ls_files_exit=0
```

Exit `1` from `git check-ignore` means no ignore rule matches this report's path, so
once the integrator stages it, it enters `evidence_bundle_digest` and is visible to every
later check. `.gitignore` contains no `artifacts/checkpoints/**` rule; the only
`artifacts` rule is `artifacts/local/`. The limit stands as recorded, but it does not
apply to this file.

## 11. Known limitations

1. **This stream is one of two.** The manual round-6 stream is owed separately and this
   report says nothing about it. `manual_acceptance.report_path` is still `null`.
2. **This stream cannot record its own result in the manifest.** Its single allowed write
   is this file. `automated_acceptance.status`, `automated_acceptance.report_path`, the
   round-6 entry's `automated_report` and `streams.automated`, and
   `evidence_bundle_digest` are all still unset, and setting them is the integrator's
   step. Until that happens the manifest does not know this report exists.
3. **`evidence_bundle_digest` is not computed here.** By the recorded digest model it is
   computed after the results are written, over a tree that includes this file, and it
   depends on `tested_candidate_digest` being already frozen. Computing it now would
   describe a tree that does not yet exist.
4. **Gate B depends on an environment precondition outside this repository.** It reads
   `/root/projects/PDF-proverka/PDF-proverka` at `32b9d903…`. That path is present here
   and the gate passed. On a machine without the legacy repository Gate B cannot run, and
   this report would not reproduce. That is a property of the gate as documented, not a
   defect found in it, but a later reader re-deriving these results needs the legacy
   repository.
5. **Byte-identity is asserted against the reviewed families only.** Files outside
   `contracts`, `fixtures`, `docs/architecture` and `scripts` have changed since
   `92e13fa4` by design, and this report makes no byte-identity claim about them.
6. **Test-suite adequacy is not audited here.** This stream ran the suite and measured
   that 281 tests pass; it did not re-derive whether every guard in the suite can fail.
   `docs/program/reviews/W0-QA-01.md` records mutation sweeps to that end and this stream
   did not repeat them.
7. **The known pre-ratification items are not re-adjudicated.** The three items in
   `manifest.json:known_pre_ratification_items` — the PD-02 precondition text, the
   `ARCHITECTURE_LINT_RULES` line-604 prose, and the `ADR_INDEX` decision count — are
   recorded as owned by `W0-INT-01` and deliberately not closed before ratification. This
   stream confirmed they are still open as described and did not treat them as gate
   failures, because no gate asserts them.
8. **`git status --porcelain` was accepted with an empty result**, as instructed. An empty
   result is indistinguishable from a `git status` that reported nothing for another
   reason; the index/HEAD/worktree triple-check in §1 is what makes the empty set load
   bearing.
9. **The tree acquired two untracked evidence files during this audit.** The manual
   stream's `manual-report-round-6.md` appeared at 15:57:42 and this file at 15:59:58,
   both after every measurement above was taken. They are the expected output of round
   six, not drift: they lie outside the four reviewed families, and the scoped path-set
   assertion still returns empty with both present. A reader re-deriving §1's digest must
   do so against the tree without them — for example
   `git stash -u` is *not* available to this stream, so use
   `git show 5b70ee4:…` or a fresh clone of the freeze commit.
10. **This report has not been reviewed by a second party.** It is one stream's record.
   The QA module's own guards were run, not re-derived; see limitation 6.

## 12. Findings

None. No gate failed, no count failed to reproduce, and no command in this report could
not be executed.

## Sensitive-data check

No secret, credential or production payload appears in this report. The only external
path named is the legacy source repository, already recorded in `manifest.json` and
`docs/SOURCE_TRACEABILITY.md`. No legacy file content is reproduced here — Gate B's
output names a commit, counts and site classes, not source text.

## Verdict

`PASS`

The tree at `5b70ee4e6c29931924f0ff56da499c5cfa0ef9a7`, confirmed by independent
recomputation to be the tree round six froze as
`2b3929be6de447bd1c3a92ff1a9a4fe72bc12d4ee919f3d21af2a979e861582c`, passes every
automated gate the checkpoint depends on.

What that rests on: 281 contract tests, none skipped; the bootstrap validator standalone;
an empty working-tree path set, unscoped and scoped to the four reviewed families; the
four reviewed families byte-identical to `reviewed_candidate_commit`, shown both by
`git diff` and by an independent 100-file content digest computed at both commits;
analysis Gates A–D extracted from the contract and run verbatim, all exit `0` with output
matching the QA report; the twenty-one further documented gate blocks across the domain,
events, selection and lint-rule documents, each exit code measured separately, the one
documented non-zero among them landing on exactly the negative fixture it names; the
eight-command analysis gate list measured per command; the dependency lock unchanged and
every transitive pin matching the installed environment; and seven recomputed quantities,
all reproducing.

This verdict certifies the input tree named above. It does not certify the tree that will
carry it — writing this file changes the tree, which is what `evidence_bundle_digest` is
for.
