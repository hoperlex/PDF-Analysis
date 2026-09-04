# CP-00 automated acceptance — primary report, round 8

**Verdict: `FAIL`.**

Every automated gate passed. Every recomputed count and hash reproduced the recorded
value. No contract, schema, fixture, state-machine, identifier or golden defect was found,
for the eighth consecutive round. The failure is again integrator-owned state metadata, and
one of the three findings is a blocker that round seven named by path and that the
round-eight remediation did not correct.

**Blocking task to reopen: `W0-INT-01`.** All three findings are in paths it owns.

## Start record

| Field | Value |
|---|---|
| `candidate_commit` | `b21e727500287152f258f405333acb9e72c6b311` |
| Commit subject | `chore(CP-00): freeze the round-eight tested candidate` |
| Tree hash | `8cd81916b9e71f1ff87ba4a210e7196d6aad39aa` |
| `tested_candidate_digest`, recorded | `959d5db2551360caf97951f067d551f2d2edb33a76b4ca21e3648f7fb305058f` |
| `tested_candidate_digest`, **recomputed by this stream** | `959d5db2551360caf97951f067d551f2d2edb33a76b4ca21e3648f7fb305058f` — **match** |
| Paths entering the digest | 218 |
| `reviewed_candidate_commit` | `92e13fa496a723ed6e4c3adbf138c4f4e1d7c368` |
| `qa_evidence_commit` | `3da104e5d6fafb2a581bda377a07911183af803f` |
| Contract manifest | domain `1.0.0-draft.1`, analysis `1.0.0-draft.1`, events `1.0.0-draft.1`, golden selection schema `1` |
| `artifact_manifest_sha256`, recomputed | `39721aac0ebe1aa5c13d0ae3e01ee93380671daddc5d9f3f3b774997d6f75e08` — reproduces, at both `HEAD` and `92e13fa` |
| `artifact_count`, recomputed | 100 |
| Branch | `integration/W0.3` |
| First measurement | 2026-09-04T12:03:41Z (2026-09-04T17:03:41+0500) |
| Last measurement | 2026-09-04T12:18:30Z (2026-09-04T17:18:30+0500) |

**Identity and independence.** This stream is `cp00_auto_auditor`, the automated acceptance
stream for round eight. It authored none of the reviewed artifacts under `contracts/`,
`fixtures/`, `docs/architecture/` or `scripts/`; it did not author
`tests/contract/test_cp00_candidate.py`, `tests/contract/test_validate_bootstrap.py` or
`docs/program/reviews/W0-QA-01.md`; and it did not author the round-eight state
reconciliation `a3eaf88` or the freeze `b21e727` that it judges. Its single write to this
repository is this file.

**Nothing was carried forward.** Round seven's report was read for form and for what it
established; every measurement below was re-derived in this stream's own code and
re-executed against this tree. A carried-forward measurement is not a measurement.

**Note for a later reader re-deriving the digest.** The parallel manual stream writes
`artifacts/checkpoints/CP-00/manual-report-round-8.md`, and this file is itself an untracked
addition to the tree. Both lie outside the four reviewed families, but both enter
`git ls-files --others --exclude-standard` and therefore change any digest recomputed after
they land. **A later reader re-deriving `959d5db2…` must work from `b21e727`'s objects or a
fresh clone of that commit, not from the working tree as it will stand once the acceptance
records are written.** At this stream's last check of the directory, no round-8 manual
report was present; the observation is recorded in §4.

## 0. Method: which number is the exit code

`$?` after a pipeline reports the last stage of the pipe, not the failing one, and that has
produced a false finding in this program before. Every exit code in this report is measured
by running the command with its output redirected to a file and reading `$?` on the very
next line. No pipe stands between the measured process and the measurement.

The trap, shown rather than asserted:

```bash
false | true; echo "naive_exit=$?"
( set -o pipefail; false | true; echo "pipefail_exit=$?" )
```

```text
naive_exit=0        <- the failing stage is invisible
pipefail_exit=1
```

The same applies to `git status`, which exits `0` whether the tree is clean or filthy.
§4 therefore asserts a **path set**, accepts the empty set as the passing result, and
demonstrates the trap against a throwaway repository.

## 1. Confirming the input before judging it

Round eight was frozen at `b21e727` with
`tested_candidate_digest = 959d5db2551360caf97951f067d551f2d2edb33a76b4ca21e3648f7fb305058f`.

The recipe was implemented from the prose of `manifest.json:candidate_digest_recipe` alone,
in this stream's own code. `_acceptance_digest` was **not** called: a stream that asks the
artifact under test whether it agrees with itself has measured nothing.

```bash
cat > /tmp/auditor8_digest.py <<'PY'
#!/usr/bin/env python3
"""Independent re-implementation of candidate_digest_recipe (round 8)."""
import hashlib, json, subprocess, sys, os

REPO = "/root/projects/PDF-Analysis"
MANIFEST_REL = "artifacts/checkpoints/CP-00/manifest.json"
FIELD = sys.argv[1] if len(sys.argv) > 1 else "tested_candidate_digest"


def git(*args):
    out = subprocess.run(["git", "-C", REPO] + list(args), check=True,
                         capture_output=True)
    return out.stdout.decode("utf-8").splitlines()


# 1. path set: git ls-files PLUS git ls-files --others --exclude-standard, sorted
paths = git("ls-files") + git("ls-files", "--others", "--exclude-standard")
paths = sorted(paths)
assert len(paths) == len(set(paths)), "duplicate path in the union"

# 2. the manifest's contribution: sha256 of the canonical JSON with ONLY the
#    field being computed blanked to "" -- at top level and in every
#    acceptance_rounds entry. The other digest field keeps its real value.
with open(os.path.join(REPO, MANIFEST_REL), "rb") as fh:
    manifest = json.loads(fh.read().decode("utf-8"))

blanked = json.loads(json.dumps(manifest))  # deep copy
if FIELD in blanked:
    blanked[FIELD] = ""
for entry in blanked.get("acceptance_rounds", []):
    if isinstance(entry, dict) and FIELD in entry:
        entry[FIELD] = ""
manifest_contribution = hashlib.sha256(
    json.dumps(blanked, sort_keys=True, separators=(",", ":")).encode("utf-8")
).digest()

# 3. fold
acc = hashlib.sha256()
for rel in paths:
    acc.update(rel.encode("utf-8"))
    if rel == MANIFEST_REL:
        acc.update(manifest_contribution)                        # RAW 32 bytes
    else:
        with open(os.path.join(REPO, rel), "rb") as fh:
            acc.update(hashlib.sha256(fh.read()).digest())        # RAW 32 bytes

print("field_blanked      :", FIELD)
print("paths_in_digest    :", len(paths))
print("manifest_included  :", MANIFEST_REL in paths)
print("recomputed_digest  :", acc.hexdigest())
print("recorded_in_manifest:", manifest.get(FIELD))
print("MATCH              :", acc.hexdigest() == manifest.get(FIELD))
PY
cd /root/projects/PDF-Analysis
python3 /tmp/auditor8_digest.py tested_candidate_digest > /tmp/d8.out 2>&1
echo "exit=$?"; cat /tmp/d8.out
```

```text
exit=0
field_blanked      : tested_candidate_digest
paths_in_digest    : 218
manifest_included  : True
recomputed_digest  : 959d5db2551360caf97951f067d551f2d2edb33a76b4ca21e3648f7fb305058f
recorded_in_manifest: 959d5db2551360caf97951f067d551f2d2edb33a76b4ca21e3648f7fb305058f
MATCH              : True
```

**The recomputed value equals the frozen value.** The tree in front of this stream is the
tree round eight froze, and every statement below is a statement about that tree.

218 paths against round seven's 216: the two round-seven primary reports are now committed
files. That is the entire difference in the enumeration.

Index, working tree and `HEAD` are one tree, so "the tree the digest walked" and "the tree
of the commit" are not two different objects:

```bash
cd /root/projects/PDF-Analysis
git rev-parse HEAD; git rev-parse HEAD^{tree}
git status --porcelain -uall | wc -l
```

```text
b21e727500287152f258f405333acb9e72c6b311
8cd81916b9e71f1ff87ba4a210e7196d6aad39aa
0
```

`b21e727` is the freeze commit named in the round-8 dispatch and is `HEAD`, so the
post-freeze delta is empty by construction. The digest was recomputed again as the last
measurement of this run and still returned `959d5db2…` over 218 paths, so **every
measurement in this report was taken against the frozen tree**.

## 2. The contract test suite

```bash
cd /root/projects/PDF-Analysis
.venv/bootstrap/bin/python -m unittest discover -s tests/contract > /tmp/g_suite.out 2>&1
echo "exit=$?"; tail -6 /tmp/g_suite.out
```

```text
exit=0
----------------------------------------------------------------------
Ran 281 tests in 31.753s

OK
```

No test is skipped. `OK` carries no `(skipped=N)`, and the verbose run counts 281 `ok`
results, zero `FAIL`/`ERROR` and zero skips:

```bash
cd /root/projects/PDF-Analysis
.venv/bootstrap/bin/python -m unittest discover -s tests/contract -v > /tmp/g_suite_v.out 2>&1
echo "exit=$?"
echo "ok:              $(grep -c ' \.\.\. ok$' /tmp/g_suite_v.out)"
echo "fail/error:      $(grep -cE '\.\.\. (FAIL|ERROR)' /tmp/g_suite_v.out)"
echo "skipped_results: $(grep -cE '\.\.\. skipped' /tmp/g_suite_v.out)"
tail -4 /tmp/g_suite_v.out
```

```text
exit=0
ok:              281
fail/error:      0
skipped_results: 0
----------------------------------------------------------------------
Ran 281 tests in 31.958s

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
Ran 255 tests in 28.854s

OK
module2_exit=0
----------------------------------------------------------------------
Ran 26 tests in 2.737s

OK
__pycache__
README.md
test_cp00_candidate.py
test_validate_bootstrap.py
```

255 + 26 = 281, and `tests/contract/` holds exactly those two modules, so the discovery run
in §2 covers both and nothing else.

## 3. The bootstrap validator, standalone

```bash
cd /root/projects/PDF-Analysis
.venv/bootstrap/bin/python scripts/validate_bootstrap.py > /tmp/g_boot.out 2>&1
echo "exit=$?"; cat /tmp/g_boot.out
```

```text
exit=0
Bootstrap validation
  json_files=56
  markdown_files=152
  stages=11
  manual_runbooks=11
  adrs=18
PASS
```

`markdown_files` is 152 against round seven's 150: the two round-seven primary reports are
now committed. `stages=11` counts `docs/stages/S\d\d_*.md` files and is a different quantity
from the nine `stage-registry.json` stages recomputed in §8; the two are not in conflict.

## 4. Working tree cleanliness — asserted as a path set

`git status --porcelain` exits `0` on a dirty tree. The assertion is therefore the set of
reported paths, and the empty set is accepted as the passing result.

```bash
cd /root/projects/PDF-Analysis
git status --porcelain -uall > /tmp/st_unscoped.out 2>&1
echo "unscoped_exit=$?"; echo "unscoped_path_count=$(wc -l < /tmp/st_unscoped.out)"
cat /tmp/st_unscoped.out; echo "[end of set]"
git status --porcelain -uall -- contracts fixtures docs/architecture scripts > /tmp/st_scoped.out 2>&1
echo "scoped_exit=$?"; echo "scoped_path_count=$(wc -l < /tmp/st_scoped.out)"
cat /tmp/st_scoped.out; echo "[end of set]"
```

```text
unscoped_exit=0
unscoped_path_count=0
[end of set]
scoped_exit=0
scoped_path_count=0
[end of set]
```

Both path sets are empty — the unscoped one as well as the scoped one. Measured at
2026-09-04T12:03:41Z and re-measured at 2026-09-04T12:11:50Z, `unscoped_path_count=0` on
both occasions, and `git ls-files --others --exclude-standard` returned nothing at either
time. **Every gate measurement in this report was taken while both path sets were empty.**

A third measurement at 2026-09-04T12:18:30Z, taken after this report file had been written,
returns the single path `?? artifacts/checkpoints/CP-00/automated-report-round-8.md` unscoped
and the empty set scoped to the four reviewed families — see §14.

The parallel manual stream then wrote
`artifacts/checkpoints/CP-00/manual-report-round-8.md`. This stream first observed it at
2026-09-04T12:19:11Z (17:19:11+0500); its mtime is 2026-09-04 17:18 +0500, after this
stream's last gate measurement. It lies outside the four reviewed families, and the scoped
assertion still returns the empty set with it and this file both present:

```bash
cd /root/projects/PDF-Analysis
date -u +"%Y-%m-%dT%H:%M:%SZ"
ls -la --time-style=long-iso artifacts/checkpoints/CP-00/manual-report-round-8.md
git status --porcelain -uall -- contracts fixtures docs/architecture scripts | wc -l
```

```text
2026-09-04T12:19:11Z
-rw-r--r-- 1 root root 44528 2026-09-04 17:18 artifacts/checkpoints/CP-00/manual-report-round-8.md
0
```

No gate result in this report was measured after that file appeared, and none depends on it.
Its content was not read by this stream and had no influence on any finding or on the
verdict.

At 2026-09-04T12:11:50Z, no round-8 manual report existed in
`artifacts/checkpoints/CP-00/`:

```bash
cd /root/projects/PDF-Analysis
ls -la artifacts/checkpoints/CP-00/ | grep -i 'round-8' || echo "  no round-8 report present at this moment"
```

```text
  no round-8 report present at this moment
```

The parallel manual stream will write `manual-report-round-8.md` after this measurement, and
this report is itself written after it. Both paths lie outside the four reviewed families,
so the scoped assertion is unaffected by either; the unscoped one and the candidate digest
are not. See the start record and limitation 3.

That the exit code proves nothing on its own, shown against a throwaway repository
deliberately made dirty — the audited tree is never touched:

```bash
T=$(mktemp -d); git -C "$T" init -q; echo x > "$T/f"; git -C "$T" add f
git -C "$T" -c user.email=a@b -c user.name=a commit -qm i > /dev/null
echo CHANGED > "$T/f"; echo untracked > "$T/newfile"
git -C "$T" status --porcelain -uall; echo "dirty_repo_status_exit=$?"; rm -rf "$T"
```

```text
 M f
?? newfile
dirty_repo_status_exit=0
```

A stream that had asserted the exit code would have called that tree clean.

## 5. The four reviewed families against `reviewed_candidate_commit`

```bash
cd /root/projects/PDF-Analysis
git diff --name-only 92e13fa496a723ed6e4c3adbf138c4f4e1d7c368 HEAD \
    -- contracts fixtures docs/architecture scripts > /tmp/fam.out 2>&1
echo "diff_exit=$?"; echo "changed_paths=$(wc -l < /tmp/fam.out)"; cat /tmp/fam.out; echo "[end]"
for f in contracts fixtures docs/architecture scripts; do
  a=$(git rev-parse 92e13fa496a723ed6e4c3adbf138c4f4e1d7c368:"$f")
  b=$(git rev-parse HEAD:"$f")
  echo "$f  reviewed=$a  head=$b  identical=$([ "$a" = "$b" ] && echo yes || echo NO)"
done
```

```text
diff_exit=0
changed_paths=0
[end]
contracts  reviewed=aec72d5d2459afa9dfddaf314643e9878600b5fe  head=aec72d5d2459afa9dfddaf314643e9878600b5fe  identical=yes
fixtures  reviewed=eb613d2c79e436b2c348388dc0574d1cafdb907e  head=eb613d2c79e436b2c348388dc0574d1cafdb907e  identical=yes
docs/architecture  reviewed=93c7ec2e692c5f6af58b59fbdddba0156498827d  head=93c7ec2e692c5f6af58b59fbdddba0156498827d  identical=yes
scripts  reviewed=565e07afe8fb6d9cc9bdc81b9ddc40ddef533d34  head=565e07afe8fb6d9cc9bdc81b9ddc40ddef533d34  identical=yes
```

Three independent statements of the same fact: an empty `git diff`, four identical subtree
object ids, and — in §8 — the `artifact_manifest_recipe` digest recomputed from blob content
at both commits to the same value. The last does not depend on `git diff` having been asked
the right question.

**The `W0-QA-01` contract-level `ACCEPT` therefore still holds for this candidate.**

## 6. Analysis gates A–D, extracted from the contract and run verbatim

The gate text is not restated in this report. It is read out of
`contracts/analysis/v1/README.md` at run time by heading, so a gate that is edited, renamed
or removed changes what runs and this report stops reproducing.

```bash
cat > /tmp/extract_gate.py <<'PY'
#!/usr/bin/env python3
"""Round-8: extract the single fenced block under '### Gate <L> ' from the analysis README."""
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
grep -n '^### Gate ' contracts/analysis/v1/README.md
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
669:### Gate A — name-level alias map structure
739:### Gate B — every evidence locator resolves in the frozen legacy commit
783:### Gate C — independent reviewer checks, made mechanical
867:### Gate D — owner decisions are transferred completely and by their real state
```

Each gate is located exactly once — the extractor raises if it is not. Measured exit codes
and full stdout:

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

All four gates exit `0`, and the four outputs are identical to the values round seven
measured — expected, since the `contracts/` subtree is byte-identical between the two
rounds, and it is worth stating that this stream re-derived them rather than copied them.

## 7. The rest of the documented gate surface

Every ` ```bash ` fenced block of the four remaining gate documents, extracted in source
order and run, **each block's own exit code measured separately**.

```bash
cat > /tmp/extract_block.py <<'PY'
#!/usr/bin/env python3
"""Round-8: extract the Nth ```bash fenced block of a document, in source order.
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
| `contracts/domain/v1/README.md` | 1/4 | `0` | validator standalone `PASS` (`json_files=56 markdown_files=152 stages=11 manual_runbooks=11 adrs=18`) |
| | 2/4 | `0` | (no output) |
| | 3/4 | `0` | `guard and run_creation codes OK 13`; `identifier bindings OK 10 \| contract_version OK 1.0.0-draft.1 \| candidate_revision 5` |
| | 4/4 | `0` | full text below |
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

Domain block 4/4 in full:

```text
optional-branch policy OK
  table total over 6 input combinations, no default branch
  any_unsuccessful -> terminal ['failed', 'partial'] | forbidden ['partial', 'published']
  core published + any_unsuccessful -> partial | refused with partial_result_not_publishable
  typed reasons named: analysis_failed, partial_result_not_publishable, validation_failed
  negative probes rejected by the schema: 15 / 15
```

Events block 5/6 exits `1` **as documented**: it is the negative probe, and its assertion
names exactly the one file whose purpose is to carry the rejected `schema_version` key. It
is recorded here as a pass on its documented shape, not as an exit-code pass, and it is
precisely why a bare "all gates exit 0" claim would be a false statement about this tree.
Had the blocks been run as one script, or had `$?` been read after a pipe, this `1` would
have been invisible — the trap of §0 in its natural habitat.

### 7.1 The analysis README §Gates command list, measured per command

The block under `## Gates` is eight commands in sequence. Running it as one script reports
only the eighth command's status, so each line was measured on its own.

```bash
cd /root/projects/PDF-Analysis
grep -n '^## Gates' contracts/analysis/v1/README.md
sed -n '619,626p' contracts/analysis/v1/README.md > /tmp/gates_list.sh
echo "lines=$(wc -l < /tmp/gates_list.sh)"
i=0
while IFS= read -r line; do
  i=$((i+1)); [ -z "$line" ] && continue
  eval "$line" > /tmp/cmd$i.out 2>&1
  echo "cmd $i exit=$?  :: $(echo "$line" | cut -c1-90)"
done < /tmp/gates_list.sh
```

```text
614:## Gates
lines=8
cmd 1 exit=0  :: .venv/bootstrap/bin/python -c "import glob,json; from jsonschema import Draft202012Validat
cmd 2 exit=0  :: .venv/bootstrap/bin/python -m jsonschema -i contracts/analysis/v1/stage-registry.json cont
cmd 3 exit=0  :: .venv/bootstrap/bin/python -m jsonschema -i contracts/analysis/v1/legacy-stage-map.json co
cmd 4 exit=0  :: .venv/bootstrap/bin/python -m jsonschema -i contracts/analysis/v1/legacy-stage-name-map.js
cmd 5 exit=0  :: .venv/bootstrap/bin/python -m jsonschema -i contracts/analysis/v1/examples/job-package.exa
cmd 6 exit=0  :: .venv/bootstrap/bin/python -m jsonschema -i contracts/analysis/v1/examples/stage-result.ex
cmd 7 exit=0  :: .venv/bootstrap/bin/python -m jsonschema -i contracts/analysis/v1/examples/result-package.
cmd 8 exit=0  :: .venv/bootstrap/bin/python scripts/validate_bootstrap.py
```

Six schema/instance validations, one `check_schema` sweep and the standalone validator, each
individually `0`. The `## Gates` heading was located at line 614 before the extraction, so
the hard-coded line range was confirmed against the document rather than assumed.

### 7.2 The negative half of that block

The same section states: "The three `examples/*.invalid.json` fixtures must exit
**non-zero** against their schema." A gate list where only the positive half runs cannot
fail on a schema that accepts everything, so the negative half was measured too:

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

All three exit non-zero, as the contract requires. Together with the 15/15 domain negative
probes and the events negative probe, the negative surface is exercised and not merely
declared.

## 8. Recomputed counts and hashes

Recomputed from repository data — the JSON artifacts and the Git object database — not read
out of any report, gate output or state document. The right-hand column names where the
program states the number, so agreement is a reproduction and not a copy.

| Quantity | Recomputed | Stated at | Reproduces |
|---|---|---|---|
| `tested_candidate_digest` | `959d5db2…` over 218 paths | `manifest.json` top level and round-8 entry | **yes** |
| `artifact_manifest_sha256` | `39721aac0ebe1aa5c13d0ae3e01ee93380671daddc5d9f3f3b774997d6f75e08` | `manifest.json` | **yes** |
| `artifact_count` | 100 | `manifest.json` `artifact_count: 100` | **yes** |
| Registry stages | 9 records, 9 distinct `stage_id` | README "9 stages" | **yes** |
| Registry `excluded_scope` ids | 11, 11 distinct `excluded_scope_id` | Gate C "11/11" | **yes** |
| Legacy name resolutions | 62 rows, 62 distinct names — 29 `canonical_stage`, 33 `excluded`; `name_count` field also 62 | README "62 names"; manifest "62 name rows" | **yes** |
| Alias-bearing declaration sites | 31 `alias_bearing_declaration_ids`, exactly equal to the set of sites carrying an observation, and a subset of the 31 site-map declarations | README "31/31 sites"; manifest "over 31 alias-bearing sites" | **yes** |
| Immutable evidence locators | 293 observation records, 293 distinct `(evidence, evidence_line, evidence_literal)` triples, 293/293 pinned to `32b9d903…` | README "293 locators"; `CURRENT_STATE.md:129`; Gate B | **yes** |
| Site distribution | `control_plane` 25, `sub_pipeline` 2, `excluded` 3, `stage` 1 | `ID-03` "25/2/3/1 distribution" | **yes** |
| Reviewed files, `contracts` | 33 | — | matches at both commits |
| Reviewed files, `fixtures` | 32 | — | matches at both commits |
| Reviewed files, `docs/architecture` | 33 | — | matches at both commits |
| Reviewed files, `scripts` | 2 | — | matches at both commits |
| Reviewed files, total | 100 | `manifest.json` `artifact_count` | **yes** |

**Every count and hash this stream was asked to recompute returned the recorded value. None
failed to reproduce.**

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

Two clarifications a later reader will want, neither a discrepancy:

* The 293 locators are 293 **observation records**, not 293 distinct file regions. They
  resolve to 39 distinct `commit:path:symbol@span` regions across 21 legacy files; several
  names are evidenced inside one region at different lines and literals. All 293
  `(evidence, evidence_line, evidence_literal)` triples are distinct, so no record is a
  duplicate of another.
* The frozen legacy commit is one value in three places and they agree:
  `legacy-stage-name-map.json:legacy_source_commit`,
  `legacy-stage-map.json:legacy_source_commit` and
  `manifest.json:frozen_inputs.behavioral_oracle` are all
  `32b9d903792b30506048a1d42b0e6b2d07aee403`.

`artifact_manifest_sha256` was computed by the manifest's own recipe, from Git blobs rather
than from the working tree, at both the audited commit and the reviewed candidate:

```bash
cat > /tmp/artifact_manifest_r8.py <<'PY'
#!/usr/bin/env python3
"""Round-8 independent implementation of manifest.json:artifact_manifest_recipe."""
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
print(f"unclassified={len(paths) - sum(per_family.values())}")
print(f"artifact_manifest_sha256={acc.hexdigest()}")
PY
cd /root/projects/PDF-Analysis
.venv/bootstrap/bin/python /tmp/artifact_manifest_r8.py HEAD; echo "exit=$?"
.venv/bootstrap/bin/python /tmp/artifact_manifest_r8.py \
    92e13fa496a723ed6e4c3adbf138c4f4e1d7c368; echo "exit=$?"
```

```text
commit=HEAD
  contracts=33
  fixtures=32
  docs/architecture=33
  scripts=2
artifact_count=100
unclassified=0
artifact_manifest_sha256=39721aac0ebe1aa5c13d0ae3e01ee93380671daddc5d9f3f3b774997d6f75e08
exit=0
commit=92e13fa496a723ed6e4c3adbf138c4f4e1d7c368
  contracts=33
  fixtures=32
  docs/architecture=33
  scripts=2
artifact_count=100
unclassified=0
artifact_manifest_sha256=39721aac0ebe1aa5c13d0ae3e01ee93380671daddc5d9f3f3b774997d6f75e08
exit=0
```

`unclassified=0` confirms every one of the 100 paths falls under one of the four families,
so `33 + 32 + 33 + 2` is the whole set and not a subset of it. This is the §5 byte-identity
claim restated as arithmetic over content.

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
`jsonschema==4.26.0` still read as correct. The exit code is load-bearing here — the script
raises `SystemExit(1)` on any mismatch rather than printing `False` and exiting `0`.

## 10. The declared report-visibility limit, checked

`manifest.json:recorded_limits.evidence_report_visibility` records that the acceptance
digests enumerate `--exclude-standard`, so a report path added to `.gitignore` would leave
every check silent about its content. That test still does not exist, so this stream checked
by hand:

```bash
cd /root/projects/PDF-Analysis
git check-ignore -v artifacts/checkpoints/CP-00/automated-report-round-8.md
echo "check_ignore_exit=$?"
git ls-files --error-unmatch artifacts/checkpoints/CP-00/automated-report-round-7.md \
                             artifacts/checkpoints/CP-00/manual-report-round-7.md
echo "ls_files_exit=$?"
grep -n "artifacts" .gitignore
```

```text
check_ignore_exit=1
artifacts/checkpoints/CP-00/automated-report-round-7.md
artifacts/checkpoints/CP-00/manual-report-round-7.md
ls_files_exit=0
21:artifacts/local/
```

Exit `1` from `git check-ignore` means no ignore rule matches this report's path, so once
the integrator stages it, it enters `evidence_bundle_digest` and is visible to every later
check. Both round-seven primary reports are tracked. The only `artifacts` rule is
`artifacts/local/`. The limit stands as recorded but does not apply to these files.

## 11. The round-eight state reconciliation, audited rather than assumed

Commit `a3eaf88` is the round-eight remediation; `b21e727` froze this round on top of it.
Its message claims a great deal, and one claim in particular is an evidentiary claim:

> Completeness is shown, not asserted. `scratchpad/check_stale.py` sweeps every tracked file
> and requires each occurrence of a superseded evidence commit to be either committed
> acceptance evidence, which documents the defect on purpose, or labelled superseded within
> three lines. **It reports zero, and it fails when given the tree as it stood before this
> commit.** Two earlier commits declared an exhaustive sweep with no such check and were
> wrong both times.

Round seven's automated stream caught round six's remediation by checking it rather than
taking it as given. This section does the same to round eight's.

### 11.1 The check, run

```bash
cd /root/projects/PDF-Analysis
.venv/bootstrap/bin/python /tmp/claude-0/.../scratchpad/check_stale.py > /tmp/stale.out 2>&1
echo "exit=$?"; cat /tmp/stale.out
```

```text
exit=0
occurrences of a superseded commit presented as live: 0

live evidence commit 3da104e5d6fa is named in:
    artifacts/checkpoints/CP-00/manifest.json
    docs/program/CURRENT_STATE.md
    docs/program/reviews/W0-QA-01.md
    docs/program/tasks/W0-INT-01.md
    docs/program/tasks/W0-QA-01.md
    docs/program/waves/W0.3_ratification_integration.md
```

It reports zero on this tree. That half of the claim is true.

### 11.2 Is its rule the right one?

Read as code rather than as prose, the rule is: for each line of each tracked file
containing one of **two hard-coded 12-hex prefixes**, skip the line if any of seven label
substrings appears anywhere in a **±3-line window**; skip the file entirely if its path
starts with one of three evidence prefixes. Four properties of that rule are worth naming.

1. **The label is not bound to the occurrence.** The window is proximity-only. A line that
   correctly labels commit *X* as superseded licenses an adjacent line that wrongly presents
   commit *Y* as live. §11.4 shows this is not hypothetical — it is exactly why the check
   does not fire on the defect it was written for.
2. **`history` is one of the labels.** It is an ordinary English word that appears
   constantly in these documents, so the window frequently contains a licence granted by
   accident rather than by intent.
3. **The superseded set is hard-coded**, not derived from
   `manifest.json:qa_evidence_history`. A third superseded value, or a stale reference to a
   *task integration* commit rather than a QA evidence commit, is outside the rule's reach.
4. **`artifacts/checkpoints/CP-00/acceptance.md` is on the skip list.** It is grouped with
   the round reports as "committed acceptance evidence, which documents the defect on
   purpose". But `acceptance.md` is not a round report: it is a live state document making
   present-tense claims, and §11.5 finds that it carries the round-accounting defect this
   round should have caught. The one state document the check excuses is the one still
   wrong.

The second half of the script — the list of files naming the live commit — is printed but
**not asserted**. `sys.exit` depends only on `problems`. Nothing checks that the live commit
is stated correctly anywhere; only that the old ones are labelled.

**Judgement: the rule is a reasonable first cut on one axis and is not the right rule for
the claim made of it.** It checks a necessary condition on the presentation of two specific
superseded SHAs. It is not a completeness check over programme state, and the commit message
uses it as though it were.

### 11.3 Can it fail? Four mutations

A check that cannot fail is the defect this checkpoint has spent twelve review rounds
eliminating, so the question was answered by experiment. All four mutations were applied to
a **throwaway clone** in the scratchpad; the audited tree was never modified.

```bash
S=/tmp/.../scratchpad
git clone -q /root/projects/PDF-Analysis $S/clone_head
cd $S/clone_head
# mutation 1: a bare false claim, no label anywhere near
printf '\nThe live QA evidence commit is e7f39890211b52e10d2619c5ddcb85a3d8c7df22.\n' >> docs/INDEX.md
.../python $S/check_stale.py > $S/mut1.out 2>&1; echo "MUT1_EXIT=$?"; head -3 $S/mut1.out
git checkout -q docs/INDEX.md
# mutation 2: the same false claim with the word 'history' within three lines
printf '\nThis section is programme history.\n\nThe live QA evidence commit is e7f39890211b52e10d2619c5ddcb85a3d8c7df22.\n' >> docs/INDEX.md
.../python $S/check_stale.py > $S/mut2.out 2>&1; echo "MUT2_EXIT=$?"; head -3 $S/mut2.out
git checkout -q docs/INDEX.md
# mutation 3: the same false claim inside acceptance.md, which the check skips
printf '\nThe live QA evidence commit is e7f39890211b52e10d2619c5ddcb85a3d8c7df22.\n' >> artifacts/checkpoints/CP-00/acceptance.md
.../python $S/check_stale.py > $S/mut3.out 2>&1; echo "MUT3_EXIT=$?"; head -3 $S/mut3.out
git checkout -q artifacts/checkpoints/CP-00/acceptance.md
# mutation 4: a different wrong commit, not one of the two hard-coded prefixes
printf '\nThe live QA evidence commit is 23dddf99f833d12cd4cc22d11e224d4b278872bf.\n' >> docs/INDEX.md
.../python $S/check_stale.py > $S/mut4.out 2>&1; echo "MUT4_EXIT=$?"; head -3 $S/mut4.out
git checkout -q docs/INDEX.md
echo "worktree clean again: [$(git status --porcelain)]"
```

```text
MUT1_EXIT=1
occurrences of a superseded commit presented as live: 1
  ! docs/INDEX.md:59: The live QA evidence commit is e7f39890211b52e10d2619c5ddcb85a3d8c7df22.

MUT2_EXIT=0
occurrences of a superseded commit presented as live: 0

MUT3_EXIT=0
occurrences of a superseded commit presented as live: 0

MUT4_EXIT=0
occurrences of a superseded commit presented as live: 0

worktree clean again: []
```

| Mutation | A false "live evidence commit" claim… | Caught |
|---|---|---|
| 1 | in a state document, unlabelled | **yes**, exit `1` |
| 2 | in a state document, with the word `history` three lines away | no |
| 3 | in `acceptance.md` | no |
| 4 | naming a commit outside the two hard-coded prefixes | no |

**The check is not vacuous** — mutation 1 proves it can fail, which is more than either of
the two earlier "exhaustive sweep" declarations could say. **But it is porous**: three of
four false claims of exactly the shape it exists to prevent pass it silently.

### 11.4 The claim that it fails on the previous tree — measured, and false

The commit message says: "it fails when given the tree as it stood before this commit."
`a3eaf88^` is `bde3af3`. The tree was checked out into a fresh clone in the scratchpad and
the script run against it, unmodified.

```bash
S=/tmp/.../scratchpad
git clone -q /root/projects/PDF-Analysis $S/clone_pre
git -C $S/clone_pre checkout -q a3eaf88^
cd $S/clone_pre
echo "cwd=$(pwd)"
echo "tree_under_test=$(git rev-parse HEAD)"
echo "a3eaf88^        =$(git -C /root/projects/PDF-Analysis rev-parse a3eaf88^)"
/root/projects/PDF-Analysis/.venv/bootstrap/bin/python $S/check_stale.py > $S/stale_pre.out 2>&1
echo "EXIT_ON_PREVIOUS_TREE=$?"
sed -n 1,2p $S/stale_pre.out
```

```text
cwd=/tmp/.../scratchpad/clone_pre
tree_under_test=bde3af3bb2b2bf2b9aabead294b5e43387932e7a
a3eaf88^        =bde3af3bb2b2bf2b9aabead294b5e43387932e7a
EXIT_ON_PREVIOUS_TREE=0
occurrences of a superseded commit presented as live: 0
```

**The check exits `0` on the previous tree. It does not fail on it.** The claim is false as
written, and it is false in the direction that matters: the demonstration offered as
evidence of completeness demonstrates nothing.

Why it misses, at the two sites round seven failed on — `docs/program/reviews/W0-QA-01.md`
lines 3245–3246 and 3281–3282, which were genuinely wrong in that tree:

```bash
cd $S/clone_pre
.../python - <<'PY'
SUPERSEDED = ("e7f39890211b", "854a68201cdd")
LABELS = ("supersed", "history", "first qa evidence", "second qa evidence",
          "earlier evidence commit", "rounds two to six", "round-one deliverables")
path = "docs/program/reviews/W0-QA-01.md"
lines = open(path, encoding="utf-8").read().split("\n")
for target in (3245, 3246, 3281, 3282):
    i = target - 1
    line = lines[i]
    if not any(s in line for s in SUPERSEDED):
        print(f"--- line {target}: no superseded token on this line, not examined"); continue
    window = " ".join(lines[max(0, i-3):i+4]).lower()
    hit = [lab for lab in LABELS if lab in window]
    print(f"--- line {target}")
    print(f"    text   : {line.strip()[:110]}")
    print(f"    labels found in +-3 window: {hit}")
    print(f"    verdict: {'SKIPPED (treated as fine)' if hit else 'FLAGGED'}")
PY
```

```text
--- line 3245
    text   : committed at the superseded `854a68201cdd…`; the live `qa_evidence_commit` is
    labels found in +-3 window: ['supersed']
    verdict: SKIPPED (treated as fine)
--- line 3246
    text   : `e7f39890211b52e10d2619c5ddcb85a3d8c7df22`, and the working tree carries the round-twelve
    labels found in +-3 window: ['supersed']
    verdict: SKIPPED (treated as fine)
--- line 3281
    text   : exists. It currently names the live `e7f39890211b…` and the superseded
    labels found in +-3 window: ['supersed', 'history']
    verdict: SKIPPED (treated as fine)
--- line 3282
    text   : `854a68201cdd…`, both labelled; the round-twelve commit supersedes the former in
    labels found in +-3 window: ['supersed', 'history']
    verdict: SKIPPED (treated as fine)
```

This is property 1 of §11.2 in the wild. Line 3245 correctly labels `854a68201cdd…` as
superseded; line 3246 then presents `e7f39890211b…` as live. The label on the first licenses
the falsehood on the second, because the window does not know which commit the label is
about.

**The substance of the remediation is nevertheless correct.** `a3eaf88` really did fix those
sites — §12.1 now reads "The live `qa_evidence_commit` is `3da104e5d6fa…`; `e7f39890211b…`
carried rounds two to six and is superseded in turn", and §12.5 is marked **Done**. This
stream confirms the text is right. What is wrong is the *evidence offered for its
completeness*: the check named as demonstrating it is silent on the very defect it was
written to catch. The remediation is correct **and** unverified, which are not the same
thing, and the commit message asserts the second on the strength of a demonstration that
does not run.

**This claim is not confined to a commit message.** It is carried into the tree, in the
manifest's round-8 entry — see finding **F-2**.

### 11.5 This stream's own sweep of programme-state claims

Independently of the check, every state document was read and every claim on the six named
axes — live evidence commit, round accounting, integrated tasks, ratification/tag status,
counts, and internal consistency — was checked against the tree.

**Axes that hold.**

* *Live evidence commit.* `3da104e5d6fafb2a581bda377a07911183af803f` is named consistently in
  the manifest, `CURRENT_STATE.md`, `W0-QA-01.md` §1 and §12, `W0-INT-01.md`,
  `W0-QA-01` task file and the wave document. Both superseded values are labelled everywhere
  they appear outside the round reports. Round six's and round seven's failing axis is
  genuinely closed. The two false statements `afe1895` introduced — "rounds two to eleven"
  and "eight further reopenings" — are corrected to two-to-six and six.
* *Integrated tasks.* The six `integrated_w03_tasks` SHAs in the manifest all resolve, and
  match the wave document's execution table, `CURRENT_STATE.md`, `W0-INT-01.md` §Depends-on
  and the `S00` stage-two table. Round seven's F-4 (integration order reading three finished
  tasks as pending) and the `S00` column header are corrected.
* *Ratification and tag.* `ratified: false` in the manifest; `git tag -l` is empty; every
  document that mentions the state says not ratified and not tagged. No document claims
  otherwise. `W0-INT-01`'s banner (round seven's F-2) no longer contradicts its own body.
* *Counts.* Every count in §8 reproduces. The `293`, `62`, `31`, `9`, `11`, `100` and
  `25/2/3/1` figures agree between the artifacts, the gates, the READMEs, `CURRENT_STATE.md`
  and the manifest.
* *Round-seven findings F-2, F-3, F-4.* All three verified corrected in the tree.

**Axes that do not hold.** Three findings, below.

#### F-1 — `acceptance.md` round accounting: a round-seven blocker, named by path, not corrected

Round seven's manual stream recorded finding F-1 as "Round accounting two rounds stale; one
document routes work already done", over **three** paths:

```text
docs/program/CURRENT_STATE.md:232-234,236,245-247
docs/program/CHECKPOINT_REGISTRY.md:5
artifacts/checkpoints/CP-00/acceptance.md:7-8,11
```

The round-eight remediation corrected the first two. It did not touch the third:

```bash
cd /root/projects/PDF-Analysis
git show --stat --format='' a3eaf88 | grep -c 'acceptance.md'
git log --oneline -2 -- artifacts/checkpoints/CP-00/acceptance.md
sed -n '1,15p' artifacts/checkpoints/CP-00/acceptance.md | cat -n
```

```text
0
ae59d8b docs(W0.3): void round four and sync the checkpoint state
a667a4b docs(W0.3): record CP-00 acceptance; ratification blocked
     1	# CP-00 acceptance record
     2	
     3	> **Round 3 is spent; this document is history, not current acceptance.** Both streams
     4	> returned `PASS` on 2026-09-02, then two things moved the tree: `W0-QA-01` was reopened
     5	> because its suite accepted a ratification that is declared and not performed, and the
     6	> digest model was corrected. Acceptance certifies a tree; both changes replaced it.
     7	> Round 4 was prepared and then voided before dispatch for the same reason. Round 5 is
     8	> owed and neither earlier `PASS` transfers to it.
     9	>
    10	> Primary reports: `manual-report-round-3.md`. No primary automated report exists for
    11	> round 3 — that stream reported to the integrator only, which round 5 must not repeat.
    12	
    13	Three rounds ran. Rounds one and two returned `FAIL` from both streams; round three
    14	returned `PASS` from both. Every blocker across all three sat in integrator-owned
    15	metadata, gate text or state documents. None was a contract, fixture, schema or test
```

The last commit to touch the file is `ae59d8b`, the commit that voided round four. Three
present-tense claims are false against this tree:

| Line | Text | Reality at `b21e727` |
|---|---|---|
| 7–8 | "Round 5 is owed and neither earlier `PASS` transfers to it" | round 5 is **void**; round **8** is owed and frozen |
| 11 | "which round 5 must not repeat" | applies to round 8 |
| 13 | "Three rounds ran" | **five** rounds have run — 1, 2, 3, 6, 7; 4 and 5 were voided |

Round seven flagged this as "two rounds behind". It is now **three** rounds behind, and the
document is the one a reader reaches from `CHECKPOINT_REGISTRY.md` for the acceptance
record. The header does declare the document history, and round seven's manual stream
called this "the mildest case" for that reason — but "Round 5 is owed" is a present-tense
claim about the current state, and it is wrong. A named blocker from the previous round,
surviving a remediation that claims to correct "both axes plus five more", is a blocker
regardless of its mildness.

The `check_stale.py` sweep offered as proof of completeness cannot reach this file: it is on
the skip list (§11.2 property 4), and its rule covers only superseded SHAs, not round
accounting — the axis round seven actually failed on.

**Owning task: `W0-INT-01`**; `artifacts/checkpoints/CP-00/**` is in its declared allowed
paths.

#### F-2 — the manifest asserts a demonstration that does not run

`artifacts/checkpoints/CP-00/manifest.json`, `acceptance_rounds[round 8].note`:

```text
"Frozen after the round-eight state reconciliation. […] The reconciliation was produced by
an independent auditor reading every state document end to end, and its completeness is
shown by a check that fails on the previous tree rather than asserted in prose. No earlier
result carries forward."
```

§11.4 measures that check exiting `0` on the previous tree. **"a check that fails on the
previous tree" is false**, and unlike the commit-message version it is committed programme
state — inside the very object the acceptance digests certify, in the field a later reader
consults to learn what round eight rests on.

The failure mode is precisely the one the program has been reopening tasks over: a guarantee
stated in prose, backed by a mechanism that does not provide it. `afe1895` declared an
exhaustive sweep and was wrong; `a3eaf88` replaced the declaration with a check and then
made a false claim about what the check does. That is one layer deeper, not one layer out.

The wave document, at
`docs/program/waves/W0.3_ratification_integration.md`, states the weaker and **true**
version — "replaced that declaration with a check that can fail" — which §11.3 mutation 1
confirms. The manifest's stronger claim is the one that is false, and the two documents do
not say the same thing.

**Owning task: `W0-INT-01`.**

#### F-3 — the manifest contradicts itself about whether round eight is frozen

```bash
cd /root/projects/PDF-Analysis
.venv/bootstrap/bin/python -c "
import json
m=json.load(open('artifacts/checkpoints/CP-00/manifest.json'))
r8=[r for r in m['acceptance_rounds'] if r['round']==8][0]
print('top-level status      :', m['status'])
print('round-8 entry status  :', r8['status'])
print('round-8 digest present:', bool(r8['tested_candidate_digest']))
"
git log -1 --format='%s' HEAD
```

```text
top-level status      : acceptance_round_8_pending_freeze
round-8 entry status  : frozen
round-8 digest present: True
chore(CP-00): freeze the round-eight tested candidate
```

One file says the round-eight freeze is **pending** at line 5 and, at line 217, that round
eight is **frozen** with its digest recorded — in the commit whose subject is
"freeze the round-eight tested candidate". `b21e727` advanced `current_round`,
`manual_acceptance`, `automated_acceptance`, `tested_candidate_digest` and the
`acceptance_rounds` array, and left `status` at the value `a3eaf88` had set for the
pre-freeze state.

The same staleness appears in two more places, both written before the freeze and not
advanced by it:

| Path | Text | Reality at `b21e727` |
|---|---|---|
| `docs/program/waves/W0.3_ratification_integration.md:5` | "The candidate is assembled and awaiting the round-eight freeze." | the freeze is `b21e727`, this commit |
| `docs/program/CURRENT_STATE.md:249` | "Order from here: freeze `tested_candidate_digest` for round eight on the remediated tree; run both streams…" | the freeze is done; it routes the reader to committed work |

This is the same shape as round seven's F-1 — "one document routes work already done" —
one round later and one step smaller. Individually each is minor; collectively they mean a
reader entering through the state layer still cannot learn from it whether round eight has
been frozen, and must go to the `acceptance_rounds` array, which contradicts the `status`
field at the top of the same file.

**Owning task: `W0-INT-01`.**

### 11.6 Known pre-ratification items, still open as recorded

The five entries in `manifest.json:known_pre_ratification_items` were re-read and all five
remain accurately described: the `PD-02` precondition text, the `ARCHITECTURE_LINT_RULES`
line-604 probe prose, the `ADR_INDEX` decision count, the integrator edit to an accepted
deliverable, and the stale `PD-01`–`PD-04` enumeration inside the frozen candidate. None is
a new finding; each is disclosed rather than hidden, and none is a gate failure. The two
`open_escalations`, `E-05` and `E-06`, are likewise still open and still accurately stated.
`E-06` remains blocking at the task layer and routed to W1; it is not a CP-00 gate failure
and this stream does not treat it as one.

## 12. Known limitations

Stated so a later reader weighs this evidence for what it is.

1. **Scratchpad paths are abbreviated in this report.** `check_stale.py` and the clones live
   under this stream's session scratchpad, whose full path is long and session-specific;
   `/tmp/.../scratchpad/` stands for it in the transcripts above. The script is **not a
   tracked repository artifact** — it is not in `git ls-files`, is not covered by any digest,
   and will not exist for a later reader. A completeness check that lives outside the tree
   cannot be re-run by anyone auditing the tree, which is an independent reason not to rest a
   committed claim on it (F-2).
2. **This stream ran no gate that does not already exist.** It executed the documented gate
   surface and re-derived the recorded quantities. It did not write new tests, and a defect
   in a region no documented gate covers would not be found here.
3. **The digest is a statement about the tree at measurement time.** Once this report and
   the manual round-8 report land, `git ls-files --others --exclude-standard` changes and any
   recomputation over the working tree will differ from `959d5db2…`. Re-derivation must use
   `b21e727`'s objects or a fresh clone. This is the recorded
   `evidence_report_visibility` limit's neighbour, not the limit itself.
4. **`E-06` is out of scope here.** The unsanitised Git environment in
   `scripts/validate_bootstrap.py:116` and `tests/contract/test_validate_bootstrap.py:32` is
   recorded as blocking at the task layer and routed to W1. It sits inside the frozen
   `scripts/` family, so correcting it would break the byte-identity that carries the
   `W0-QA-01` `ACCEPT`. This stream reports it as recorded and does not re-litigate it.
5. **`prefix_widening_unpinned` and `dynamic_dispatch_unenumerable`** remain as recorded in
   `manifest.json:recorded_limits`; neither was re-measured by this stream, and both are
   properties of the QA module rather than of the candidate.
6. **Mutation testing of `check_stale.py` was four mutations, not exhaustive.** Three of the
   four passed silently. A larger set would very likely find more holes; the four were chosen
   to test the four rule properties named in §11.2, and three of the four confirmed a hole on
   the first attempt.
7. **This stream is an agent, not a human reviewer.** For an architecture-only checkpoint the
   automated stream is document analysis and command execution, which is what it claims to
   be; it is not a substitute for the independent manual stream running in parallel.

## 13. Findings

| # | Finding | Severity | Command that showed it | Owning task |
|---|---|---|---|---|
| F-1 | `acceptance.md:7-8,11,13` round accounting is three rounds stale — "Round 5 is owed", "round 5 must not repeat", "Three rounds ran". Named by path in round seven's F-1; the round-eight remediation corrected the other two paths and did not touch this one. | **blocking** | `git show --stat --format='' a3eaf88 \| grep -c 'acceptance.md'` → `0`; `sed -n '1,15p' artifacts/checkpoints/CP-00/acceptance.md` | `W0-INT-01` |
| F-2 | `manifest.json` round-8 note states completeness "is shown by a check that fails on the previous tree". The check exits `0` on that tree. A false evidentiary claim in committed programme state. | **blocking** | `git -C clone_pre checkout a3eaf88^ && python check_stale.py` → `EXIT_ON_PREVIOUS_TREE=0` | `W0-INT-01` |
| F-3 | `manifest.json:status` is `acceptance_round_8_pending_freeze` while `acceptance_rounds[8].status` is `frozen` in the same file, in the freeze commit itself; `W0.3` wave document line 5 and `CURRENT_STATE.md:249` carry the same pre-freeze staleness. | **blocking** | the `status` vs `acceptance_rounds[8].status` probe in §11.3 | `W0-INT-01` |

**No contract, schema, fixture, state-machine, identifier or golden defect was found.** For
the eighth consecutive round, every failure is in integrator-owned state metadata. The four
reviewed families reproduce `artifact_manifest_sha256` exactly at both commits, so the
`W0-QA-01` `ACCEPT` still holds and nothing here requires re-running QA.

**What this stream judges about the state reconciliation.** `a3eaf88` is a substantial and
mostly successful piece of work: it closed round six's axis and round seven's axis, corrected
two false statements the previous remediation had introduced, and repaired seven state
records this stream verified individually. Its defect is not in what it changed but in what
it claims. It replaced "I swept exhaustively" with "a check shows I swept exhaustively", and
the check neither covers the axis that failed nor fails on the tree the message says it fails
on. Substituting an unfalsifiable claim for a claim whose falsification this stream could
perform in one command is a smaller error than the two before it — and it is the same error.

The correct claim, available at no cost, was the one the wave document already makes: a check
that *can* fail, covering *one* axis, over *two* known SHAs. That claim is true, and §11.3
mutation 1 proves it.

## 14. Closing measurement — the digest caveat, demonstrated

The start record warns that a later reader must re-derive `959d5db2…` from `b21e727`'s
objects or a fresh clone, not from the working tree. That warning was then measured rather
than left as prose. After this report file was written, and before it was staged:

```bash
cd /root/projects/PDF-Analysis
date -u +"%Y-%m-%dT%H:%M:%SZ"
git rev-parse HEAD
git status --porcelain -uall
git status --porcelain -uall -- contracts fixtures docs/architecture scripts | wc -l
python3 /tmp/.../scratchpad/auditor8_digest.py tested_candidate_digest | tail -3
```

```text
2026-09-04T12:18:30Z
b21e727500287152f258f405333acb9e72c6b311
?? artifacts/checkpoints/CP-00/automated-report-round-8.md
0
recomputed_digest  : f20dd45449699a4955ea0255ca76390514f943e8f21a6be528e66771586a6498
recorded_in_manifest: 959d5db2551360caf97951f067d551f2d2edb33a76b4ca21e3648f7fb305058f
MATCH              : False
```

`HEAD` has not moved, the four reviewed families are still clean, and the only path in the
unscoped set is this report. The working-tree digest is nevertheless now `f20dd454…`, because
this file entered `git ls-files --others --exclude-standard`.

**This `MATCH: False` is not a finding.** It is the expected and intended consequence of
writing acceptance evidence into the tree, and it is exactly why the manifest splits
`tested_candidate_digest` from `evidence_bundle_digest`. It is recorded here so that a reader
who recomputes the digest after the round-8 reports land, gets `f20dd454…` — or some later
value once the manual report lands too — and concludes the freeze was tampered with, has the
explanation in front of them. **The frozen input this stream judged is the tree of
`b21e727`, whose digest is `959d5db2…`, reproduced in §1 while the untracked set was empty.**

## Sensitive-data check

No credential, token, personal datum or production payload appears in this report. Every
value quoted is a Git object id, a content digest, a file path, a package version or output
this stream produced from the repository. The repository holds no production payloads; the
`frozen_inputs` commits of the separate legacy repository are named but not reproduced.

## Verdict

# `FAIL`

Round eight fails the automated acceptance stream on three findings, all in integrator-owned
programme state, all owned by **`W0-INT-01`**, which must be reopened:

* **F-1** — `artifacts/checkpoints/CP-00/acceptance.md` round accounting is three rounds
  stale. This is a round-seven blocker, named by path in that round's report, carried into
  round eight uncorrected.
* **F-2** — `artifacts/checkpoints/CP-00/manifest.json` asserts, in committed state, a
  demonstration of completeness that this stream measured exiting `0` on the tree it is said
  to fail on.
* **F-3** — `manifest.json` contradicts itself on whether round eight is frozen, and two
  further state documents still describe the freeze as pending.

Every automated gate passed, every documented gate block was executed with its own exit code
measured, every negative probe behaved as documented, and every recomputed count and hash
reproduced the recorded value. The candidate's contracts are not the problem and have not
been the problem in any of the eight rounds. `CP-00` cannot be ratified or tagged on this
tree.

*Report written 2026-09-04 by `cp00_auto_auditor`, automated acceptance stream, round 8.
Every timestamp in this report was measured by this stream with `date`: 2026-09-04T12:03:41Z
first measurement, 2026-09-04T12:11:50Z last gate measurement, 2026-09-04T12:18:30Z closing
measurement (17:03:41, 17:11:50 and 17:18:30 +0500 local). No timestamp here was invented,
estimated, or carried forward from another document.*
