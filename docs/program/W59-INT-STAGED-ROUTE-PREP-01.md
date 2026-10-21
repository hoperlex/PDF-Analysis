# W59-INT-STAGED-ROUTE-PREP-01 — stage-bound route pin

Base: published `origin/dev` at
`69b923156ea3988dbad3cc378644b9799a6bdd23`.

The new pure `route_staged_section` joins a supplied explicit version P/R
stage with a supplied same-version expert section confirmation. It checks the
stage agreement and confirmer identity before delegating section/profile
selection to the existing fail-closed route guard. Its immutable result pins
the exact `VersionUid`, P/R stage, section code and profile ID for a future
Run start. A mismatch refuses instead of letting a section-only route hide an
unclassified or different stage. PS and PB cannot inherit each other's or
AR's profile.

## Checks

- Focused container-free suite: **14 passed**. It covers both P and R,
  mismatched/unclassified stages, foreign-version and absent confirmation,
  invalid confirmer, unknown section, missing or invalid profile registry,
  and no AR or PS/PB fallback.
- Python compilation, direct task governance, frozen SHA-256 readback,
  whitespace check and exact four-path inspection: passed at commit.
- No Docker, PostgreSQL, S3, provider, network or complete gate was used
  while W55b's gate owned the host. R-135 defers the complete beta gate.

## Contracts and limitations

No contract, migration, existing section module, run path, executable
profile, API/UI, composition, dependency or runtime behavior changed. The
guard accepts caller-supplied facts and **does not prove** they are saved
facts or that the confirmer is currently authorized. The profile map is also
supplied; there is no sealed executable AI/PS/POS/TX profile yet. This is a
useful stage/section consistency check, not SECTION-SEAL or profile
acceptance.

Only these four paths changed:

- `src/auditmanager/sections/staged_routing.py`;
- `tests/integration/sections/test_staged_routing.py`;
- `docs/program/tasks/W59-INT-STAGED-ROUTE-PREP-01.md`;
- this report.

Remove the additive module and test before wiring to roll back. No data
rollback or feature flag is needed.

After W58-code close, the SECTION-SEAL owner must read authoritative
version membership, saved stage and saved expert confirmation in one
authorized transaction, resolve through the sealed executable profile map,
and persist this exact route pin with the Run. Serving must use the staged
guard instead of the earlier section-only guard; otherwise the new refusal
can be bypassed. Authoring and field validation for AI, PS, POS and TX still
need separate reviewed source and recorded cases.
