# CP-00 automated acceptance — primary report, round 7

Round six's automated stream returned `PASS`. That result **does not carry forward**:
the round was voided when the round-six remediation moved two paths outside the
post-freeze delta ceiling, which replaced the tree both streams had judged. Nothing
below is copied from `automated-report-round-6.md`. Every command was re-run against
`c1376e1` and every number re-derived; where a result agrees with round six, it agrees
because it was measured again, not because it was carried.

Written to be re-derived from, not read: every command is copyable, carries its real
output, and carries the exit code of the process that was actually measured.

## Start record

```text
candidate_commit:      c1376e1cf0ca39d137c3f88f1a823757de839bef (integration/W0.3)
                       "chore(CP-00): freeze the round-seven tested candidate"
tested_candidate_digest (recomputed):
                       ad26b42fb99f9ccce7d0bd8ce3b6986e277a29b42d346adc454463aa489092b6
                       recipe: manifest.json candidate_digest_recipe; 216 paths;
                       matches the frozen value in manifest.json and in the round-7
                       acceptance_rounds entry
tree:                  edeefeb7e2cfd488d5fb08c159ad17b2f15a5421
contract_manifest:     domain/analysis/events 1.0.0-draft.1; golden_selection_schema 1;
                       artifact_manifest_sha256 39721aac…, 100 files — recomputed, matches
manifest_blob:         ac9132085276fd293888ea4eeae4ab5ab710c7e6
                       sha256(file) 3a201909d52e03d0ba645b2c764d019c85ccda839c6d2ded5e32d9cddaeb53f0
reviewed_candidate:    92e13fa496a723ed6e4c3adbf138c4f4e1d7c368
qa_evidence_commit:    3da104e5d6fafb2a581bda377a07911183af803f
migration_head:        none (db/migrations holds only README.md)
backend_runtime:       not applicable - architecture-only checkpoint
frontend_runtime:      not applicable - architecture-only checkpoint
local_infra_versions:  not applicable - architecture-only checkpoint
auditor:               cp00_auto_auditor, independent agent; authored none of the
                       reviewed artifacts, the QA test module or the QA report, and
                       holds no write in this repository other than this file
environment:           Python 3.12.3 (.venv/bootstrap), git 2.43.0, GNU bash 5.2.21,
                       Linux 6.8.0-138-generic x86_64
started_at:            2026-09-04T16:29:20+05:00 — first measurement. The freeze commit
                       c1376e1 is timestamped 2026-09-04 16:27:51 +0500, so the whole
                       audit runs after the freeze.
last_measurement_at:   2026-09-04T16:39:00+05:00
report_authored_at:    2026-09-04T16:43:30+05:00 — measured immediately before this
                       file was written
```

Every timestamp in this report was measured by running `date -Iseconds` at the moment
recorded. None is reconstructed, inferred from a commit, or estimated.

Every digest and count was computed against the tree as it stood before this file
existed. Writing this file changes the tree; that is what `evidence_bundle_digest` is
for, and computing it is the integrator's step, not this stream's.

## 0. Method: which number is the exit code

`$?` after a pipeline reports the last stage, not the failure, and that has produced a
false finding in this program before. Every exit code below is measured by running the
command with its output redirected to a file and reading `$?` on the next line — no pipe
stands between the process and the measurement. The trap, shown rather than asserted:

```bash
false | true; echo "naive_exit=$?"
( set -o pipefail; false | true; echo "pipefail_exit=$?" )
```

```text
naive_exit=0        <- the failing stage is invisible
pipefail_exit=1
```

The same applies to `git status`, which exits `0` whether or not the tree is dirty.
Section 4 asserts a path set for that reason and demonstrates the trap.

## 1. Confirming the input before judging it

Round seven was frozen at `c1376e1` with
`tested_candidate_digest = ad26b42fb99f9ccce7d0bd8ce3b6986e277a29b42d346adc454463aa489092b6`.

The recipe was implemented from the manifest prose alone, in this stream's own code. The
module helper `_acceptance_digest` was **not** called: a stream that asks the artifact
under test whether it agrees with itself has measured nothing.

```bash
cat > /tmp/digest_r7.py <<'PY'
#!/usr/bin/env python3
"""Round-7 independent implementation of manifest.json:candidate_digest_recipe."""
import hashlib
import json
import subprocess
import sys

ROOT = "/root/projects/PDF-Analysis"
MANIFEST = "artifacts/checkpoints/CP-00/manifest.json"


def enumerate_paths():
    cached = subprocess.run(
        ["git", "-C", ROOT, "ls-files", "--cached"],
        capture_output=True, text=True, check=True).stdout.splitlines()
    others = subprocess.run(
        ["git", "-C", ROOT, "ls-files", "--others", "--exclude-standard"],
        capture_output=True, text=True, check=True).stdout.splitlines()
    return sorted({p for p in cached + others if p})


def manifest_payload(field):
    with open(f"{ROOT}/{MANIFEST}", "rb") as fh:
        doc = json.loads(fh.read().decode("utf-8"))
    doc[field] = ""
    for entry in doc.get("acceptance_rounds", []):
        if field in entry:
            entry[field] = ""
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")


def main(field):
    paths = enumerate_paths()
    acc = hashlib.sha256()
    for rel in paths:
        if rel == MANIFEST:
            content = manifest_payload(field)
        else:
            with open(f"{ROOT}/{rel}", "rb") as fh:
                content = fh.read()
        acc.update(rel.encode("utf-8"))
        acc.update(hashlib.sha256(content).digest())
    print(f"field={field}")
    print(f"paths_enumerated={len(paths)}")
    print(f"recomputed={acc.hexdigest()}")


main(sys.argv[1] if len(sys.argv) > 1 else "tested_candidate_digest")
PY
cd /root/projects/PDF-Analysis
.venv/bootstrap/bin/python /tmp/digest_r7.py tested_candidate_digest > /tmp/d1.out 2>&1
echo "exit=$?"; cat /tmp/d1.out
```

```text
exit=0
field=tested_candidate_digest
paths_enumerated=216
recomputed=ad26b42fb99f9ccce7d0bd8ce3b6986e277a29b42d346adc454463aa489092b6
```

**The recomputed value equals the frozen value.** The tree in front of this stream is the
tree round seven froze, and everything below is a statement about that tree.

216 paths against round six's 214: the two round-six primary reports are now committed
files. That is the entire difference in the enumeration.

`c1376e1` is the only commit in this repository whose manifest carries this value, so the
freeze commit and the audited commit are the same commit and the post-freeze delta is
empty:

```bash
cd /root/projects/PDF-Analysis
for c in $(git log --format=%H -- artifacts/checkpoints/CP-00/manifest.json); do
  v=$(git show $c:artifacts/checkpoints/CP-00/manifest.json \
      | .venv/bootstrap/bin/python -c "import json,sys; print(json.load(sys.stdin).get('tested_candidate_digest'))")
  echo "$(git log -1 --format='%h %ad' --date=short $c)  tested=$v"
done
```

```text
c1376e1 2026-09-04  tested=ad26b42fb99f9ccce7d0bd8ce3b6986e277a29b42d346adc454463aa489092b6
afe1895 2026-09-04  tested=2b3929be6de447bd1c3a92ff1a9a4fe72bc12d4ee919f3d21af2a979e861582c
85a52ce 2026-09-04  tested=2b3929be6de447bd1c3a92ff1a9a4fe72bc12d4ee919f3d21af2a979e861582c
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

`2b3929be…` is round six's digest, recorded `failed`; `22e3027b…` is round five's,
recorded `void`. Both are history and neither is the input here.

Index, working tree and `HEAD` are one tree, so "the tree the digest walked" and "the tree
of the commit" are not two different things:

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
echo "exit=$?"; tail -6 /tmp/g1.out
```

```text
exit=0
----------------------------------------------------------------------
Ran 281 tests in 32.764s

OK
```

No test is skipped. `OK` carries no `(skipped=N)`, and the verbose run counts 281 `ok`
results, zero `FAIL`/`ERROR` and zero skip results:

```bash
cd /root/projects/PDF-Analysis
.venv/bootstrap/bin/python -m unittest discover -s tests/contract -v > /tmp/gv.out 2>&1
echo "exit=$?"
echo "ok:              $(grep -c ' \.\.\. ok$' /tmp/gv.out)"
echo "fail/error:      $(grep -cE '\.\.\. (FAIL|ERROR)' /tmp/gv.out)"
echo "skipped_results: $(grep -cE '\.\.\. skipped' /tmp/gv.out)"
tail -4 /tmp/gv.out
```

```text
exit=0
ok:              281
fail/error:      0
skipped_results: 0
----------------------------------------------------------------------
Ran 281 tests in 30.793s

OK
```

### 2.1 Per module

```bash
cd /root/projects/PDF-Analysis
.venv/bootstrap/bin/python -m unittest discover -s tests/contract \
    -p 'test_cp00_candidate.py' -v > /tmp/m1.out 2>&1
echo "module1_exit=$?"; tail -4 /tmp/m1.out
.venv/bootstrap/bin/python -m unittest discover -s tests/contract \
    -p 'test_validate_bootstrap.py' -v > /tmp/m2.out 2>&1
echo "module2_exit=$?"; tail -4 /tmp/m2.out
ls tests/contract/
```

```text
module1_exit=0
----------------------------------------------------------------------
Ran 255 tests in 29.780s

OK
module2_exit=0
----------------------------------------------------------------------
Ran 26 tests in 2.912s

OK
__pycache__
README.md
test_cp00_candidate.py
test_validate_bootstrap.py
```

255 + 26 = 281, and the directory holds exactly those two modules, so the discovery run in
§2 covers both and nothing else.

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
  markdown_files=150
  stages=11
  manual_runbooks=11
  adrs=18
PASS
```

`markdown_files` is 150 against round six's 148: the two round-six primary reports are now
committed. `stages=11` counts `docs/stages/S\d\d_*.md` files and is a different quantity
from the nine `stage-registry.json` stages recomputed in §8; the two are not in conflict.

## 4. Working tree cleanliness — asserted as a path set

`git status --porcelain` exits `0` on a dirty tree. The assertion is therefore the set of
reported paths, and the empty set is accepted as the passing result.

```bash
cd /root/projects/PDF-Analysis
git status --porcelain -uall > /tmp/g4a.out 2>&1
echo "exit=$?"; echo "path_count=$(wc -l < /tmp/g4a.out)"; cat /tmp/g4a.out
git status --porcelain -uall -- contracts fixtures docs/architecture scripts > /tmp/g4b.out 2>&1
echo "exit=$?"; echo "path_count=$(wc -l < /tmp/g4b.out)"; cat /tmp/g4b.out
```

```text
exit=0
path_count=0
exit=0
path_count=0
```

Both path sets are empty. Measured at 2026-09-04T16:32:47+05:00 and re-measured at
2026-09-04T16:38:38+05:00, still `path_count=0` on both. **Every measurement in this
report was taken while both path sets were empty**, the last of them at
2026-09-04T16:39:00+05:00.

The parallel manual stream then wrote
`artifacts/checkpoints/CP-00/manual-report-round-7.md`; this stream first observed it at
2026-09-04T16:43:48+05:00, and its mtime is 2026-09-04 16:40:37 +0500 — after this
stream's last measurement. It lies outside the four reviewed families, and the scoped
assertion still returns the empty set with it and this file both present:

```bash
cd /root/projects/PDF-Analysis
git status --porcelain -uall -- contracts fixtures docs/architecture scripts
echo "reviewed_family_path_count=$(git status --porcelain -uall -- contracts fixtures docs/architecture scripts | wc -l)"
```

```text
reviewed_family_path_count=0
```

See limitation 9.

That the exit code proves nothing on its own, shown against a throwaway repository
deliberately made dirty:

```bash
T=$(mktemp -d); git -C "$T" init -q; echo x > "$T/f"; git -C "$T" add f
git -C "$T" -c user.email=a@b -c user.name=a commit -qm i > /dev/null
echo CHANGED > "$T/f"
git -C "$T" status --porcelain -uall; echo "dirty_repo_status_exit=$?"; rm -rf "$T"
```

```text
 M f
dirty_repo_status_exit=0
```

A stream that had asserted the exit code would have called that tree clean.

## 5. The four reviewed families against `reviewed_candidate_commit`

```bash
cd /root/projects/PDF-Analysis
git rev-parse --verify 92e13fa496a723ed6e4c3adbf138c4f4e1d7c368^{commit}; echo "rev_parse_exit=$?"
git diff --name-status 92e13fa496a723ed6e4c3adbf138c4f4e1d7c368 HEAD \
    -- contracts fixtures docs/architecture scripts > /tmp/g5.out 2>&1
echo "diff_exit=$?"; echo "changed_paths=$(wc -l < /tmp/g5.out)"; cat /tmp/g5.out
```

```text
92e13fa496a723ed6e4c3adbf138c4f4e1d7c368
rev_parse_exit=0
diff_exit=0
changed_paths=0
```

The empty diff is corroborated by content rather than by Git's own comparison: the
`artifact_manifest_recipe` digest over the four families is computed independently at both
commits in §8 and is the same value. A digest over 100 files, computed from blob contents
at two commits, agreeing bit for bit is a byte-identity statement that does not depend on
`git diff` being asked the right question.

## 6. Analysis gates A–D, extracted from the contract and run verbatim

The gate text is not restated in this report. It is read out of
`contracts/analysis/v1/README.md` at run time by heading, so a gate that is edited,
renamed or removed changes what runs and this report stops reproducing.

```bash
cat > /tmp/extract_gate.py <<'PY'
#!/usr/bin/env python3
"""Extract the single fenced block under '### Gate <L> ' from the analysis README."""
import sys
from pathlib import Path
README = Path("/root/projects/PDF-Analysis/contracts/analysis/v1/README.md")
letter = sys.argv[1]
lines = README.read_text(encoding="utf-8").splitlines()
heading, blocks, i = None, [], 0
while i < len(lines):
    if lines[i].startswith("#"):
        heading = lines[i].strip()
    if lines[i].startswith("```"):
        body, i = [], i + 1
        while i < len(lines) and not lines[i].startswith("```"):
            body.append(lines[i]); i += 1
        blocks.append((heading, "\n".join(body) + "\n"))
    i += 1
want = f"### Gate {letter} "
hits = [b for h, b in blocks if h and h.startswith(want)]
if len(hits) != 1:
    raise SystemExit(f"Gate {letter}: found {len(hits)} blocks, expected 1")
sys.stdout.write(hits[0])
PY
cd /root/projects/PDF-Analysis
for L in A B C D; do
  .venv/bootstrap/bin/python /tmp/extract_gate.py $L > /tmp/gate$L.sh
  echo "extract_${L}_exit=$? bytes=$(wc -c < /tmp/gate$L.sh)"
done
for L in A B C D; do
  bash /tmp/gate$L.sh > /tmp/gate$L.out 2>&1
  echo "GATE_${L}_EXIT=$?"
  cat /tmp/gate$L.out
done
```

```text
extract_A_exit=0 bytes=3825
extract_B_exit=0 bytes=2015
extract_C_exit=0 bytes=5132
extract_D_exit=0 bytes=8656
```

Each gate located exactly once. Measured exit codes and full stdout:

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

**Gate D — owner decisions are transferred completely and by their real state**, exit `0`:

```text
decision-transfer gate PASS: PD-03 has all 9 creation triggers with the complete owner outcome tuple and the exact owner-ruled rule_id on each of them; inputs_changed and repeat_of_terminal_run create a new Run; retry/resume/restart/worker_failover each create exactly one Attempt and no Run; the idempotent replay creates neither; RC-02 beats RC-05, both precedence references resolve to the triggers the ruling is about, and the resolved outcome is the winner outcome; no trigger reopens a terminal Run; both attempt_authority descriptions are identical and complete; PD-01 approved_with_modification on XS-01/XS-04; U-06 closed on XS-11 (OPT / contracts/optimization/v1/** / W5-OPT-01 / disabled); FS-04 norm_core owned here, 2 parts elsewhere; PD-05 identifier confirmed
```

### 6.1 Agreement with the QA report, measured rather than asserted

`docs/program/reviews/W0-QA-01.md` §3.1 records these four results. Round six's report
claimed all four "byte-identical" to that record. That claim is imprecise and this stream
does not repeat it: §3.1 records Gates C and D **with ellipses**, so an exact comparison
is not available for those two. What was measured instead — each non-elided fragment of
the recorded text located in this run's output:

```bash
cd /root/projects/PDF-Analysis
.venv/bootstrap/bin/python - <<'PY'
import re
from pathlib import Path
qa = Path("docs/program/reviews/W0-QA-01.md").read_text(encoding="utf-8").splitlines()
rows = {}
for line in qa:
    m = re.match(r"\|\s*([A-D])\s+—.*?\|\s*`(0)`\s*\|\s*`(.+)`\s*\|\s*$", line)
    if m:
        rows[m.group(1)] = m.group(3)
for L in "ABCD":
    got = Path(f"/tmp/gate{L}.out").read_text(encoding="utf-8").strip()
    recorded = rows[L]
    frags = [f.strip() for f in recorded.split("…") if f.strip()]
    missing = [f for f in frags if f not in got]
    print(f"Gate {L}: recorded_is_elided={'…' in recorded} fragments={len(frags)} "
          f"missing={len(missing)} exact_match={recorded == got}")
PY
echo "exit=$?"
```

```text
Gate A: recorded_is_elided=False fragments=1 missing=0 exact_match=True
Gate B: recorded_is_elided=False fragments=1 missing=0 exact_match=True
Gate C: recorded_is_elided=True fragments=3 missing=0 exact_match=False
Gate D: recorded_is_elided=True fragments=3 missing=0 exact_match=False
exit=0
```

Gates A and B reproduce the QA report exactly. Gates C and D reproduce every fragment
§3.1 actually spells out; `exact_match=False` is the ellipses, not a divergence.

Noted for the record, not as a finding against this candidate: round six's report
transcribed Gate D's output without an ellipsis and without three segments the gate
actually emits (`PD-01 approved_with_modification on XS-01/XS-04`, `U-06 closed on XS-11`,
`FS-04 norm_core owned here`). The gate block is byte-identical at both commits (8656
bytes) and the contracts are byte-identical, so the gate cannot have changed its output;
round six's transcription was incomplete. That report is committed history and is not
edited here.

Gate B addresses the legacy repository at `/root/projects/PDF-proverka/PDF-proverka` and
reads immutable Git objects at `32b9d903…`:

```bash
git -C /root/projects/PDF-proverka/PDF-proverka rev-parse --short HEAD; echo "legacy_exit=$?"
git -C /root/projects/PDF-proverka/PDF-proverka rev-parse --verify \
    32b9d903792b30506048a1d42b0e6b2d07aee403^{commit}; echo "legacy_commit_exit=$?"
```

```text
c0771b2e
legacy_exit=0
32b9d903792b30506048a1d42b0e6b2d07aee403
legacy_commit_exit=0
```

Its availability is an environment precondition, not a property of this repository; see
limitation 4.

## 7. The rest of the documented gate surface

Every `bash`-fenced block of the four remaining gate documents, extracted in source order
and run, each block's own exit code measured separately.

```bash
cat > /tmp/extract_block.py <<'PY'
#!/usr/bin/env python3
"""Extract the Nth ```bash fenced block of a document, in source order.
With index -1, print how many such blocks exist."""
import sys
from pathlib import Path
ROOT = Path("/root/projects/PDF-Analysis")
rel, index = sys.argv[1], int(sys.argv[2])
lines = (ROOT / rel).read_text(encoding="utf-8").splitlines()
blocks, i = [], 0
while i < len(lines):
    if lines[i].startswith("```bash"):
        body, i = [], i + 1
        while i < len(lines) and not lines[i].startswith("```"):
            body.append(lines[i]); i += 1
        blocks.append("\n".join(body) + "\n")
    i += 1
if index == -1:
    print(len(blocks))
else:
    sys.stdout.write(blocks[index])
PY
cd /root/projects/PDF-Analysis
for f in contracts/domain/v1/README.md contracts/events/v1/README.md \
         fixtures/golden/SELECTION.md docs/architecture/ARCHITECTURE_LINT_RULES.md; do
  n=$(.venv/bootstrap/bin/python /tmp/extract_block.py "$f" -1)
  for i in $(seq 0 $((n-1))); do
    .venv/bootstrap/bin/python /tmp/extract_block.py "$f" $i > /tmp/blk.sh
    bash /tmp/blk.sh > /tmp/blk.out 2>&1
    echo "=== $f block $((i+1))/$n exit=$?"
    cat /tmp/blk.out
  done
done
```

| Document | Block | Exit | Output |
|---|---|---|---|
| `contracts/domain/v1/README.md` | 1/4 | `0` | validator standalone `PASS` |
| | 2/4 | `0` | (no output) |
| | 3/4 | `0` | `guard and run_creation codes OK 13`; `identifier bindings OK 10 \| contract_version OK 1.0.0-draft.1 \| candidate_revision 5` |
| | 4/4 | `0` | `optional-branch policy OK` … `negative probes rejected by the schema: 15 / 15` |
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

Domain block 4/4 in full, since round six's table abbreviated it:

```text
optional-branch policy OK
  table total over 6 input combinations, no default branch
  any_unsuccessful -> terminal ['failed', 'partial'] | forbidden ['partial', 'published']
  core published + any_unsuccessful -> partial | refused with partial_result_not_publishable
  typed reasons named: analysis_failed, partial_result_not_publishable, validation_failed
  negative probes rejected by the schema: 15 / 15
```

Events block 5/6 exits `1` **as documented**: it is the negative probe, and the assertion
names exactly the one file whose purpose is to carry the rejected `schema_version` key. It
is recorded as a pass on its documented shape, not as an exit-code pass, and it is the
reason a bare "all gates exit 0" claim would be wrong here.

### 7.1 The analysis README §Gates command list, measured per command

The block under `## Gates` is eight commands in sequence. Running it as one script reports
only the eighth command's status — the pipeline trap in another form — so each line was
measured on its own.

```bash
cd /root/projects/PDF-Analysis
sed -n '619,626p' contracts/analysis/v1/README.md > /tmp/gates_list.sh
echo "lines=$(wc -l < /tmp/gates_list.sh)"
i=0
while IFS= read -r line; do
  i=$((i+1)); [ -z "$line" ] && continue
  eval "$line" > /tmp/cmd$i.out 2>&1
  echo "cmd $i exit=$?"
done < /tmp/gates_list.sh
```

```text
lines=8
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

### 7.2 The negative half of that block, which round six did not run

The same section states: "The three `examples/*.invalid.json` fixtures must exit
**non-zero** against their schema." A gate list where only the positive half is executed
cannot fail on a schema that accepts everything, so the negative half was measured too:

```bash
cd /root/projects/PDF-Analysis
for p in contracts/analysis/v1/examples/*.invalid.json; do
  base=$(basename "$p"); schema=""
  case "$base" in
    job-package*)    schema=contracts/analysis/v1/job-package.schema.json;;
    stage-result*)   schema=contracts/analysis/v1/stage-result.schema.json;;
    result-package*) schema=contracts/analysis/v1/result-package.schema.json;;
  esac
  .venv/bootstrap/bin/python -m jsonschema -i "$p" "$schema" > /tmp/inv.out 2>&1
  echo "$base exit=$?  schema=$schema"
done
```

```text
result-package.missing-attempt-authority.invalid.json exit=1  schema=contracts/analysis/v1/result-package.schema.json
stage-result.failed-missing-error.invalid.json exit=1  schema=contracts/analysis/v1/stage-result.schema.json
stage-result.succeeded-with-error.invalid.json exit=1  schema=contracts/analysis/v1/stage-result.schema.json
```

All three exit non-zero, as the contract requires.

## 8. Recomputed counts and hashes

Recomputed from repository data — the JSON artifacts and the Git object database — not
read out of any report, gate output or state document. The right-hand column names where
the program states the number, so agreement is a reproduction and not a copy.

| Quantity | Recomputed | Stated at | Reproduces |
|---|---|---|---|
| `tested_candidate_digest` | `ad26b42f…` over 216 paths | `manifest.json` top level and round-7 entry | **yes** |
| `artifact_manifest_sha256` | `39721aac0ebe1aa5c13d0ae3e01ee93380671daddc5d9f3f3b774997d6f75e08` | `manifest.json` | **yes** |
| `artifact_count` | 100 | `manifest.json` `artifact_count: 100` | **yes** |
| Registry stages | 9 records, 9 distinct `stage_id` | README "9 stages" | **yes** |
| Registry `excluded_scope` ids | 11, 11 distinct `excluded_scope_id` | Gate C "11/11" | **yes** |
| Legacy name resolutions | 62 rows, 62 distinct names — 29 `canonical_stage`, 33 `excluded`; `name_count` field also 62 | README "62 names"; manifest "62 name rows" | **yes** |
| Alias-bearing declaration sites | 31 `alias_bearing_declaration_ids`, exactly equal to the set of sites carrying an observation, and a subset of the 31 site-map declarations | README "31/31 sites"; manifest "over 31 alias-bearing sites" | **yes** |
| Immutable evidence locators | 293 observation records, 293 distinct `(evidence, evidence_line, evidence_literal)` triples, 293/293 pinned to `32b9d903…` | README "293 locators"; `CURRENT_STATE.md:127`; `W0.3` wave plan line 182 | **yes** |
| Site distribution | `control_plane` 25, `sub_pipeline` 2, `excluded` 3, `stage` 1 | README:279 "the 25/2/3/1 distribution" | **yes** |
| Reviewed files, `contracts` | 33 | — | matches at both commits |
| Reviewed files, `fixtures` | 32 | — | matches at both commits |
| Reviewed files, `docs/architecture` | 33 | — | matches at both commits |
| Reviewed files, `scripts` | 2 | — | matches at both commits |
| Reviewed files, total | 100 | `manifest.json` `artifact_count` | **yes** |

**Every count and hash this stream was asked to recompute returned the recorded value.
None failed to reproduce.**

Two clarifications a later reader will want, neither a discrepancy:

* The 293 locators are 293 **observation records**, not 293 distinct file regions. They
  resolve to 39 distinct `commit:path:symbol@span` regions across 21 legacy files; several
  names are evidenced inside one region at different lines and literals. All 293
  `(evidence, evidence_line, evidence_literal)` triples are distinct, so no record is a
  duplicate.
* The frozen legacy commit is one value in three places and they agree:
  `legacy-stage-name-map.json:legacy_source_commit`,
  `legacy-stage-map.json:legacy_source_commit` and
  `manifest.json:frozen_inputs.behavioral_oracle` are all
  `32b9d903792b30506048a1d42b0e6b2d07aee403`.

The counts script and its output:

```bash
cd /root/projects/PDF-Analysis
.venv/bootstrap/bin/python - <<'PY'
import json, collections
from pathlib import Path
A = Path("contracts/analysis/v1")
FROZEN = "32b9d903792b30506048a1d42b0e6b2d07aee403"
registry = json.loads((A / "stage-registry.json").read_text())
namemap  = json.loads((A / "legacy-stage-name-map.json").read_text())
sitemap  = json.loads((A / "legacy-stage-map.json").read_text())
stages = registry["stages"]
print("registry stage records          :", len(stages))
print("registry distinct stage_id      :", len({s["stage_id"] for s in stages}))
print("registry excluded_scope ids     :", len(registry["excluded_scope"]))
print("registry distinct exclusion ids :",
      len({e["excluded_scope_id"] for e in registry["excluded_scope"]}))
names = namemap["names"]
print("name rows                       :", len(names))
print("name_count field                :", namemap["name_count"])
print("distinct legacy_stage_name      :", len({n["legacy_stage_name"] for n in names}))
print("resolutions                     :",
      dict(collections.Counter(n["resolution"] for n in names)))
obs = []
for n in names:
    obs.append((n["evidence"], n["evidence_line"], n["evidence_literal"]))
    for a in n.get("additional_observations", []):
        obs.append((a["evidence"], a["evidence_line"], a["evidence_literal"]))
print("observation records             :", len(obs))
print("distinct (ev,line,literal)      :", len(set(obs)))
print("pinned to frozen legacy commit  :",
      f'{sum(1 for e, _, _ in obs if e.startswith(FROZEN))}/{len(obs)}')
print("distinct evidence regions       :", len({e for e, _, _ in obs}))
print("distinct legacy files evidenced :", len({e.split(":")[1] for e, _, _ in obs}))
decls = sitemap["declarations"]
alias_ids = set(namemap["alias_bearing_declaration_ids"])
observed = set()
for n in names:
    observed.add(n["source_declaration_id"])
    observed.update(n.get("observed_declaration_ids", []))
print("site-map declarations           :", len(decls))
print("alias_bearing_declaration_ids   :", len(alias_ids))
print("sites carrying an observation   :", len(observed))
print("alias set == observed set       :", alias_ids == observed)
print("alias set subset of declarations:",
      alias_ids <= {d["source_declaration_id"] for d in decls})
print("site distribution (target_kind) :",
      dict(collections.Counter(d["target_kind"] for d in decls)))
print("legacy_source_commit agreement  :",
      namemap["legacy_source_commit"] == sitemap["legacy_source_commit"] == FROZEN)
PY
echo "exit=$?"
```

```text
registry stage records          : 9
registry distinct stage_id      : 9
registry excluded_scope ids     : 11
registry distinct exclusion ids : 11
name rows                       : 62
name_count field                : 62
distinct legacy_stage_name      : 62
resolutions                     : {'canonical_stage': 29, 'excluded': 33}
observation records             : 293
distinct (ev,line,literal)      : 293
pinned to frozen legacy commit  : 293/293
distinct evidence regions       : 39
distinct legacy files evidenced : 21
site-map declarations           : 31
alias_bearing_declaration_ids   : 31
sites carrying an observation   : 31
alias set == observed set       : True
alias set subset of declarations: True
site distribution (target_kind) : {'control_plane': 25, 'sub_pipeline': 2, 'excluded': 3, 'stage': 1}
legacy_source_commit agreement  : True
exit=0
```

`artifact_manifest_sha256` was computed by the manifest's own recipe, from Git blobs rather
than from the working tree, at both the audited commit and the reviewed candidate:

```bash
cat > /tmp/artifact_manifest_r7.py <<'PY'
#!/usr/bin/env python3
"""Independent implementation of manifest.json:artifact_manifest_recipe."""
import hashlib, subprocess, sys
ROOT = "/root/projects/PDF-Analysis"
FAMILIES = ["contracts", "fixtures", "docs/architecture", "scripts"]
commit = sys.argv[1]
listing = subprocess.run(
    ["git", "-C", ROOT, "ls-tree", "-r", "--name-only", commit, "--", *FAMILIES],
    capture_output=True, text=True, check=True).stdout.splitlines()
paths = sorted(p for p in listing if p)
per_family = {f: sum(1 for p in paths if p.startswith(f + "/")) for f in FAMILIES}
acc = hashlib.sha256()
for rel in paths:
    blob = subprocess.run(["git", "-C", ROOT, "cat-file", "blob", f"{commit}:{rel}"],
                          capture_output=True, check=True).stdout
    acc.update(rel.encode("utf-8"))
    acc.update(hashlib.sha256(blob).digest())
print(f"commit={commit}")
for f in FAMILIES:
    print(f"  {f}={per_family[f]}")
print(f"artifact_count={len(paths)}")
print(f"artifact_manifest_sha256={acc.hexdigest()}")
PY
cd /root/projects/PDF-Analysis
.venv/bootstrap/bin/python /tmp/artifact_manifest_r7.py HEAD; echo "exit=$?"
.venv/bootstrap/bin/python /tmp/artifact_manifest_r7.py \
    92e13fa496a723ed6e4c3adbf138c4f4e1d7c368; echo "exit=$?"
```

```text
commit=HEAD
  contracts=33
  fixtures=32
  docs/architecture=33
  scripts=2
artifact_count=100
artifact_manifest_sha256=39721aac0ebe1aa5c13d0ae3e01ee93380671daddc5d9f3f3b774997d6f75e08
exit=0
commit=92e13fa496a723ed6e4c3adbf138c4f4e1d7c368
  contracts=33
  fixtures=32
  docs/architecture=33
  scripts=2
artifact_count=100
artifact_manifest_sha256=39721aac0ebe1aa5c13d0ae3e01ee93380671daddc5d9f3f3b774997d6f75e08
exit=0
```

This is the §5 byte-identity claim restated as arithmetic over content.

## 9. The dependency lock

```bash
cd /root/projects/PDF-Analysis
git diff --name-status 92e13fa496a723ed6e4c3adbf138c4f4e1d7c368 HEAD -- requirements > /tmp/lock.out 2>&1
echo "exit=$?"; echo "changed_paths=$(wc -l < /tmp/lock.out)"
sha256sum requirements/validation.lock requirements/validation.in
```

```text
exit=0
changed_paths=0
01c3f241cf9a3f38fed84c1a7d58f23f0cd7d22b842de40ebba4e3b6c7ac40d8  requirements/validation.lock
14d9df3dade913fe67e8a46bfa061152c88eac6350c28a89bfeecfcaa14cf56d  requirements/validation.in
```

```bash
cd /root/projects/PDF-Analysis
.venv/bootstrap/bin/python - > /tmp/pins.out 2>&1 <<'PY'
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
raise SystemExit(0 if ok else 1)
PY
echo "exit=$?"; cat /tmp/pins.out
.venv/bootstrap/bin/python -c "import jsonschema, sys; print(jsonschema.__file__); print(sys.executable)"
```

```text
exit=0
attrs                        locked=26.1.0       installed=26.1.0       match=True
jsonschema                   locked=4.26.0       installed=4.26.0       match=True
jsonschema-specifications    locked=2025.9.1     installed=2025.9.1     match=True
referencing                  locked=0.37.0       installed=0.37.0       match=True
rpds-py                      locked=2026.6.3     installed=2026.6.3     match=True
typing-extensions            locked=4.16.0       installed=4.16.0       match=True
all locked pins match: True
/root/projects/PDF-Analysis/.venv/bootstrap/lib/python3.12/site-packages/jsonschema/__init__.py
/root/projects/PDF-Analysis/.venv/bootstrap/bin/python
```

The lock is unchanged since `reviewed_candidate_commit`, every pin matches the installed
environment, and the interpreter is the bootstrap venv the gates name — not a system
installation. The transitive set is checked, not only the direct pin: an `rpds-py` or
`referencing` substitution would change how every schema validation above behaves while
`jsonschema==4.26.0` still read as correct. The exit code is load bearing here — the
script raises `SystemExit(1)` on any mismatch rather than printing `False` and exiting `0`.

## 10. The declared report-visibility limit, checked

`manifest.json:recorded_limits.evidence_report_visibility` records that the acceptance
digests enumerate `--exclude-standard`, so a report path added to `.gitignore` would leave
every check silent about its content. That test still does not exist, so this stream
checked by hand:

```bash
cd /root/projects/PDF-Analysis
git check-ignore -v artifacts/checkpoints/CP-00/automated-report-round-7.md
echo "check_ignore_exit=$?"
git ls-files --error-unmatch artifacts/checkpoints/CP-00/automated-report-round-6.md \
                             artifacts/checkpoints/CP-00/manual-report-round-6.md
echo "ls_files_exit=$?"
grep -n "artifacts" .gitignore
```

```text
check_ignore_exit=1
artifacts/checkpoints/CP-00/automated-report-round-6.md
artifacts/checkpoints/CP-00/manual-report-round-6.md
ls_files_exit=0
21:artifacts/local/
```

Exit `1` from `git check-ignore` means no ignore rule matches this report's path, so once
the integrator stages it, it enters `evidence_bundle_digest` and is visible to every later
check. Both round-six primary reports are tracked. The only `artifacts` rule is
`artifacts/local/`. The limit stands as recorded but does not apply to these files.

## 11. The round-six remediation, verified

Round six failed `MT00-01`: the superseded QA evidence commit
`e7f39890211b52e10d2619c5ddcb85a3d8c7df22` was presented as current in five sites while
the task and wave layers named it superseded. Commit `afe1895` is the remediation and
`c1376e1` froze this round on top of it.

### 11.1 The five named sites — all corrected

```bash
cd /root/projects/PDF-Analysis
grep -n 'qa_evidence_commit\|"W0-QA-01"' artifacts/checkpoints/CP-00/manifest.json
grep -n 'qa_evidence_commit' docs/program/CURRENT_STATE.md
grep -n 'accepted and integrated at' docs/program/tasks/W0-INT-01.md
sed -n '68p' docs/stages/S00_architecture_and_behavior_freeze.md
sed -n '71p' docs/program/reviews/W0-QA-01.md | cut -c1-120
```

```text
7:  "qa_evidence_commit": "3da104e5d6fafb2a581bda377a07911183af803f",
29:    "W0-QA-01": "3da104e5d6fafb2a581bda377a07911183af803f"
56:- `qa_evidence_commit` `3da104e5d6fafb2a581bda377a07911183af803f` — where its test and
36:- `W0-QA-01`, accepted and integrated at `3da104e5d6fafb2a581bda377a07911183af803f` with an
| W0-QA-01 | QA | Independent cross-family verification | W0-ARC-02, W0-CLN-01 | Accepted after twelve review rounds; evidence at `3da104e5`. |
| `qa_evidence_commit` | `3da104e5d6fafb2a581bda377a07911183af803f` — the accepted evidence
```

All five now name `3da104e5d6fafb2a581bda377a07911183af803f`. The S00 row also corrects
"six review rounds" to "twelve", agreeing with the task layer. `3da104e5…` resolves to a
real commit (`git rev-parse --verify … ^{commit}` exit `0`, dated 2026-09-04 15:44:33
+0500, "test(W0-QA-01): accept the cross-family verification after twelve rounds").

### 11.2 `qa_evidence_history` — both values carried

```bash
cd /root/projects/PDF-Analysis
.venv/bootstrap/bin/python - <<'PY'
import json
m = json.load(open('artifacts/checkpoints/CP-00/manifest.json'))
h = m['qa_evidence_history']
print("entries:", len(h))
for i, e in enumerate(h):
    print(f"  [{i}] keys={sorted(e.keys())} commit={e.get('commit')} status={e.get('status')!r}")
print("current value present in history?",
      any(e.get('commit') == m['qa_evidence_commit'] for e in h))
PY
echo "exit=$?"
grep -c "qa_evidence_history" tests/contract/test_cp00_candidate.py
```

```text
entries: 2
  [0] keys=['commit', 'note', 'status'] commit=854a68201cdd857abf6a12989f254f5d2e0928af status='superseded'
  [1] keys=['commit', 'note'] commit=e7f39890211b52e10d2619c5ddcb85a3d8c7df22 status=None
current value present in history? False
exit=0
0
```

Both superseded values are carried, which is what round six asked for. Two observations,
neither a failure and neither blocking:

* Entry `[1]` has no `status` key. Its supersession is stated in the `note` prose
  ("Second QA evidence. Superseded after eight further reopenings…") while entry `[0]`
  states it in structure. A structural reader cannot tell that `[1]` is superseded. This
  is the "stated in prose beside a check that cannot read it" shape the program has spent
  rounds on, in a small place.
* `grep -c` returns `0`: **no test in the suite reads `qa_evidence_history` at all.** The
  field is unguarded, so this round's correction of it is not protected against
  regression. Neither observation is a gate failure, because no gate asserts either.

### 11.3 The exhaustive sweep — and where it fails

The remediation commit message states: *"This time the sweep was exhaustive and its result
is recorded: every remaining occurrence of the superseded commit is either the round-six
evidence documenting the defect, or a row that names it as superseded on purpose."*

That claim was tested rather than accepted. Every occurrence of either superseded value
was enumerated repository-wide and classified, excluding the round-six reports:

```bash
cd /root/projects/PDF-Analysis
grep -rn "live \`e7f39890\|live \`854a6820\|is \`e7f39890\|qa_evidence_commit\` is" \
     --exclude-dir=.git . | grep -v "round-6.md"
```

```text
docs/program/reviews/W0-QA-01.md:3245:   committed at the superseded `854a68201cdd…`; the live `qa_evidence_commit` is
docs/program/reviews/W0-QA-01.md:3281:     exists. It currently names the live `e7f39890211b…` and the superseded
```

**Two occurrences survive, and both present the superseded commit as the current one.**
Both are in `## 12. Handoff — AGENTS.md §5` of `docs/program/reviews/W0-QA-01.md`
(section heading at line 3242). In full:

```bash
cd /root/projects/PDF-Analysis
sed -n '3244,3246p' docs/program/reviews/W0-QA-01.md
echo "---"
sed -n '3280,3282p' docs/program/reviews/W0-QA-01.md
```

```text
1. **Changed files** — exactly two, both **modified**, not new. They were first
   committed at the superseded `854a68201cdd…`; the live `qa_evidence_commit` is
   `e7f39890211b52e10d2619c5ddcb85a3d8c7df22`, and the working tree carries the round-twelve
---
   - update `qa_evidence_commit` in section 1 of this report after the new commit
     exists. It currently names the live `e7f39890211b…` and the superseded
     `854a68201cdd…`, both labelled; the round-twelve commit supersedes the former in
```

Neither is round-six evidence, and neither names the value as superseded. Line 3245 says
in the present tense that the live `qa_evidence_commit` **is** `e7f39890211b…`. It is not;
it is `3da104e5…`, as §1 of the same document, the manifest, `CURRENT_STATE.md`,
`W0-INT-01` and `S00` all now say. This is the same statement, in the same defect class,
that failed round six in five other places.

Line 3281 is worse than stale: it is a present-tense claim about §1 of its own document
that the remediation commit itself falsified. `afe1895` rewrote §1 to name `3da104e5…`
and left line 3281 asserting that §1 "currently names the live `e7f39890211b…`". The two
statements are 36 lines apart in one file and contradict each other.

The file was not out of reach. `afe1895` edited this exact file:

```bash
cd /root/projects/PDF-Analysis
git show --stat --format="%H %s" afe1895 | head -10
```

```text
afe1895d9d46cfe2af7ff6d54dbddcac0f3b6d4d docs(W0.3): carry the accepted QA evidence commit into every record that names it

 artifacts/checkpoints/CP-00/manifest.json           | 8 ++++++--
 docs/program/CURRENT_STATE.md                       | 2 +-
 docs/program/reviews/W0-QA-01.md                    | 4 ++--
 docs/program/tasks/W0-INT-01.md                     | 2 +-
 docs/stages/S00_architecture_and_behavior_freeze.md | 2 +-
 5 files changed, 11 insertions(+), 7 deletions(-)
```

The remediation opened `docs/program/reviews/W0-QA-01.md`, corrected the two rows of §1,
and stopped — while §12 of the same file continued to name the value §1 had just retired.
The commit's own recorded exception describes the edit as being "in one row of section
one", so the narrow scope was deliberate; the exhaustiveness claim in the same message is
what is false.

The correction §1 received is exactly the correction §12 needs, and it does not regress
infinitely: §1's row carries the note "This row was corrected by the integrator after
acceptance", which is a form §12 can take without a new evidence commit.

### 11.4 What correcting it costs

`docs/program/reviews/W0-QA-01.md` is tracked, so it is inside `_digest_paths` and inside
`tested_candidate_digest`. It is **not** inside `POST_FREEZE_DELTA_CEILING`, which the QA
module pins as `{CHECKPOINT_MANIFEST, CHECKPOINT_REGISTRY, PROGRAM_STATE_DOCUMENT}` plus
the five `RATIFICATION_DELTA_CEILING` files under `docs/architecture/`
(`tests/contract/test_cp00_candidate.py:85-86,116-124,146,188-190`):

```text
artifacts/checkpoints/CP-00/manifest.json
docs/program/CHECKPOINT_REGISTRY.md
docs/program/CURRENT_STATE.md
docs/architecture/ADR_INDEX.md
docs/architecture/ARCHITECTURE_LINT_RULES.md
docs/architecture/CP00_ARCHITECTURE_REVIEW.json
docs/architecture/CP00_ARCHITECTURE_REVIEW.md
docs/architecture/CP00_OWNER_DECISIONS.md
```

`docs/program/reviews/W0-QA-01.md` is not in that set. So correcting §12 moves a path
outside the ceiling, which by the manifest's own rule — "if it must change, the round is
void and a new one begins" — **voids round seven and opens a round eight.** That is the
same shape as round six's void, and it is stated plainly here rather than left for the
integrator to discover after acting.

### 11.5 Everything else that names a superseded value is correctly labelled

For completeness, the remaining occurrences, all of which do name the value as superseded
or as history and are **not** findings:

| Site | Character |
|---|---|
| `docs/program/tasks/W0-QA-01.md:4-6` | header, both values explicitly "superseded" |
| `docs/program/reviews/W0-QA-01.md:73` | §1 "superseded" row, both values labelled |
| `docs/program/reviews/W0-QA-01.md:3128-3130` | §11 round-narrative, past tense, describes the round-three state |
| `docs/program/waves/W0.3_ratification_integration.md:124` | "Earlier evidence commits `854a682` and `e7f3989` are superseded" |
| `artifacts/checkpoints/CP-00/manifest.json:215,220` | `qa_evidence_history` |
| `artifacts/checkpoints/CP-00/manifest.json:192` | round-six entry, describing the defect |
| `artifacts/checkpoints/CP-00/manual-report-round-3.md:31` | a digest-discrimination list, historical |
| `tests/contract/test_cp00_candidate.py:9399` | "tracked since `854a6820`" — a statement about trackedness, not about the live value |
| both round-six reports | excluded by instruction; they document the defect on purpose |

### 11.6 Known pre-ratification items, still open as recorded

Not re-adjudicated, only confirmed still in the state `manifest.json` describes:

```bash
cd /root/projects/PDF-Analysis
.venv/bootstrap/bin/python -c "import json;print('ratified =', json.load(open('docs/architecture/CP00_ARCHITECTURE_REVIEW.json')).get('ratified'))"
sed -n '604p' docs/architecture/ARCHITECTURE_LINT_RULES.md
grep -c "Nothing is ratified, nothing is tagged" docs/program/CURRENT_STATE.md
git merge-base --is-ancestor main integration/W0.3; echo "is_ancestor_exit=$?"
```

```text
ratified = False
own JSON, still untracked - and asserts that the gate reports exactly that path as
1
is_ancestor_exit=0
```

`ratified` is still `false`, the `GATE-E` line-604 prose is still stale as recorded, the
state document's standing denial is present, and `main` is an ancestor of
`integration/W0.3`, so the planned fast-forward is genuine. None of these is a gate
failure and none is treated as one.

## 12. Known limitations

1. **This stream is one of two.** The manual round-7 stream is owed separately and this
   report says nothing about it. `manual_acceptance.report_path` is still `null`.
2. **This stream cannot record its own result in the manifest.** Its single allowed write
   is this file. `automated_acceptance.status`, `automated_acceptance.report_path`, the
   round-7 entry's `automated_report` and `streams.automated`, and
   `evidence_bundle_digest` are all still unset; setting them is the integrator's step.
3. **`evidence_bundle_digest` is not computed here.** By the recorded digest model it is
   computed after the results are written, over a tree that includes this file. Computing
   it now would describe a tree that does not yet exist.
4. **Gate B depends on an environment precondition outside this repository.** It reads
   `/root/projects/PDF-proverka/PDF-proverka` at `32b9d903…`. That path is present here
   and the gate passed. On a machine without the legacy repository Gate B cannot run and
   this report would not reproduce.
5. **Byte-identity is asserted against the reviewed families only.** Files outside
   `contracts`, `fixtures`, `docs/architecture` and `scripts` have changed since
   `92e13fa4` by design, and this report makes no byte-identity claim about them.
6. **Test-suite adequacy is not audited here.** This stream ran the suite and measured
   that 281 tests pass; it did not re-derive whether every guard in it can fail.
   `docs/program/reviews/W0-QA-01.md` records mutation sweeps to that end and this stream
   did not repeat them. The §11.2 observation that `qa_evidence_history` is read by no
   test is a coverage gap this stream happened to cross, not the result of a sweep.
7. **The known pre-ratification items are not re-adjudicated**, only confirmed still open
   as recorded (§11.6).
8. **`git status --porcelain` was accepted with an empty result**, as instructed. An empty
   result is indistinguishable from a `git status` that reported nothing for another
   reason; the index/HEAD/worktree triple-check in §1 is what makes the empty set load
   bearing.
9. **The working tree was clean for every measurement in this report.** It was measured
   empty at 2026-09-04T16:29:54+05:00, 16:32:47 and 16:38:38, and this stream's last
   measurement was at 16:39:00. The parallel manual stream's
   `manual-report-round-7.md` appeared afterwards — mtime 2026-09-04 16:40:37 +0500,
   first observed by this stream at 16:43:48 — and this file was written at 16:43:30.
   Both are the expected output of round seven, not drift: they lie outside the four
   reviewed families and the scoped path-set assertion still returns empty with both
   present (§4). **A later reader re-deriving §1's digest must work from
   `c1376e1`'s objects or a fresh clone of that commit** — once this file and any manual
   report exist on disk, the working-tree walk enumerates 217 or more paths and will not
   return `ad26b42f…`. `git stash -u` is not available to this stream.
10. **The §11.3 finding is a documentation-consistency finding, not a gate failure.** No
    automated gate in this checkpoint asserts anything about §12 of the QA report; it was
    found because this round's instructions asked for the remediation to be verified
    rather than assumed. Every automated gate this checkpoint depends on passed.
11. **This report has not been reviewed by a second party.** It is one stream's record.

## 13. Findings

**One finding, blocking.**

* **F-01 — the round-six remediation is incomplete; a superseded QA evidence commit is
  still presented as the live value.**
  `docs/program/reviews/W0-QA-01.md` §12, lines 3245 and 3281, state in the present tense
  that the live `qa_evidence_commit` is `e7f39890211b52e10d2619c5ddcb85a3d8c7df22`. It is
  `3da104e5d6fafb2a581bda377a07911183af803f`. Line 3281 additionally asserts that §1 of
  the same document names `e7f39890211b…`, which the remediation commit `afe1895`
  falsified when it rewrote §1 — the contradiction was created inside the commit that was
  meant to close this defect, in the same file, 36 lines apart.
  * **Command that showed it**:
    `grep -rn "live \`e7f39890\|live \`854a6820\|is \`e7f39890\|qa_evidence_commit\` is" --exclude-dir=.git . | grep -v "round-6.md"`
  * **Class**: identical to round six's `MT00-01` — a superseded commit presented as
    current — which is the failure this round exists to have remediated.
  * **Owning task to reopen**: `W0-QA-01`. `docs/program/reviews/W0-QA-01.md` is one of its
    two allowed paths (`docs/program/tasks/W0-QA-01.md:71-76`) and is **not** in
    `W0-INT-01`'s allowed paths (`docs/program/tasks/W0-INT-01.md:50-64`). If the
    integrator instead corrects §12 directly, as it already corrected §1, that is a second
    allowed-path deviation on the same file and must be recorded as an exception the way
    the §1 edit was — not absorbed silently.
  * **Consequence**: the file is outside `POST_FREEZE_DELTA_CEILING` (§11.4), so the
    correction voids round seven and a round eight is owed.

Two non-blocking observations, recorded so they are not lost (§11.2): `qa_evidence_history`
entry `[1]` states its supersession in prose while entry `[0]` states it in structure, and
no test in the suite reads `qa_evidence_history` at all, so this round's correction of that
field is unguarded against regression.

No gate failed. No count failed to reproduce. No command in this report could not be
executed.

## Sensitive-data check

No secret, credential or production payload appears in this report. The only external path
named is the legacy source repository, already recorded in `manifest.json` and
`docs/SOURCE_TRACEABILITY.md`. No legacy file content is reproduced — Gate B's output names
a commit, counts and site classes, not source text.

## Verdict

`FAIL`

Every automated gate this checkpoint depends on passes on the tree at
`c1376e1cf0ca39d137c3f88f1a823757de839bef`, confirmed by independent recomputation to be
the tree round seven froze as
`ad26b42fb99f9ccce7d0bd8ce3b6986e277a29b42d346adc454463aa489092b6`: 281 contract tests,
none skipped, 255 + 26 across exactly two modules; the bootstrap validator standalone; an
empty working-tree path set, unscoped and scoped to the four reviewed families, measured
three times; the four reviewed families byte-identical to `reviewed_candidate_commit`,
shown both by `git diff` and by an independent 100-file content digest computed at both
commits; analysis Gates A–D extracted from the contract and run verbatim, all exit `0`,
with Gates A and B reproducing the QA report exactly and C and D reproducing every fragment
it does not elide; the twenty-one further documented gate blocks, each exit code measured
separately, the one documented non-zero among them landing on exactly the negative fixture
it names; the eight-command analysis gate list measured per command, plus the three
`*.invalid.json` fixtures confirmed non-zero; the dependency lock unchanged with every
transitive pin matching the installed environment; and every recomputed quantity — nine
stages, sixty-two names, 293 locators, 31/31 sites, the 25/2/3/1 distribution, eleven
exclusion ids, 100 reviewed files and `artifact_manifest_sha256` — reproducing.

The verdict is nonetheless `FAIL`, on `F-01`. This round exists because round six failed
on a superseded QA evidence commit presented as current, and this round was asked to verify
that the remediation holds. It does not hold: the same value is still presented as live in
`docs/program/reviews/W0-QA-01.md` §12, in a file the remediation commit opened and
partially corrected, and the remediation commit's own claim that its sweep was exhaustive
is false as a result. A stream that reported `PASS` here would be certifying the very
condition round six was voided over, and would be repeating round six's automated blind
spot — that stream returned `PASS` while the defect stood, because nothing asked it to look.

Reopen `W0-QA-01` for the §12 correction, or record a second integrator exception on that
file. Either way the correction lands outside the post-freeze delta ceiling, so round seven
is void once it is made and round eight is owed.

This verdict certifies the input tree named above. It does not certify the tree that will
carry it — writing this file changes the tree, which is what `evidence_bundle_digest` is
for.
