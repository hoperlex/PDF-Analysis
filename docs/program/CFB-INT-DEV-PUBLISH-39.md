# CFB-INT-DEV-PUBLISH-39 — W58 drill and unserved W56/W57 readers

This candidate builds on published `origin/dev=26a9af241bf81f222304a43b9d14c4d50baffe54`.
The W58 callback fix at `b8a548ce` doubles two literal SQL percent signs
for psycopg's `exec_driver_sql` parser. A real isolated synthetic DB/Blob
drill on a fresh target-02 then restored a PostgreSQL 17 custom dump,
verified migration `0023_norm_citations`, one manifest reference, one
target object and one available Blob with equal full readbacks of 58,978
bytes. The first target's pre-restore failure and exact copy, result and
image digests are in `W58-INT-RELATIONS-PLACEHOLDER-FIX-01.md`. The drill
uses a synthetic local payload, so it does not attest a source S3 mirror or
the alpha stand.

W56b source `414c384f2ae9bd26df561e7e715f459b0ff09b1d` is cherry-picked
as `0ab30213`. Its binary patch SHA-256 on both commits is
`2e52e44c94a0c26b1b9c82a468bcf76ab9920b33a6d8060cce9848800130ce7a`.
The pure window-anchor check refuses a changed saved TEXT-window plan or a
quote from another page and returns the existing literal resolver's original
Unicode offsets. It makes no provider call or cross-window policy decision.

W57a source `d77e4a50c85870e2e25963ff4b03d4f0ffcde65e` is cherry-picked
as `c2dcd7fa`. Its binary patch SHA-256 on both commits is
`2643f4b2d8431c1591d9e589bc1c39ef871bb3c98e07dd0f744ee451364e28ab`.
The additive SELECT-only report reader combines certified citations with
same-Run diagnostics and textless-page context, failing closed on missing
or foreign evidence. This integration added the required `premise` field
to its task metadata after cherry-pick; reader and test bytes are unchanged.
The route stays disabled until registered v3 profile, authorized API owner
and real PostgreSQL readback exist.

The combined W56b/W57a/W58 and programme-governance selection passed
**125 tests**. Direct source patch equality, frozen API/stage/domain/error
and migration hashes, Python compilation, machine-readable handoff, exact
path scope, whitespace and clean-tree checks accompany publication. R-135
defers the complete W56–W63 beta gate. No contract, migration, root lock,
composition root, global style, served route, corpus source or deployment
input changed. The W55b main candidate remains the separate exact clean
`37393a979a430e490843d7f410e9eca9491a4ea1` tree, gate-complete under
R-125 but awaiting the owner's direct exact-SHA publication instruction.
No `origin/main` update or beta claim is made here.
