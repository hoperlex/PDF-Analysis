# CFB-INT-DEV-PUBLISH-41 — W54 and W56b development candidate

The published `origin/dev` base is
`72fa7f69afc93890b9e0c50fb1b4ccd66ee810e8`. Reviewed source commits
`503428cf` and `4c2a8b24` were fetched from isolated local clones and
cherry-picked as `519a8672` and `01c7e71a`. Their nine changed paths are
exactly those in their tasks. No merge conflict or forbidden hotspot was
encountered.

W54's offline preflight now requires the frozen `SHA256SUMS` listing digest
for every step after `source-sums`, including base load, restore verification
and bundle export. It remains a cheap metadata guard and does not prove the
listed source files' byte hashes. The real preflight's latest read-only
sample was blocked only by available RAM below 6 GiB; the corpus has not
been promoted to product DB/S3.

W56b's pure binder requires exactly one supplied reply for each saved TEXT
window in order. It allows an explicitly empty reply, checks each quote's
page boundary and retains global Unicode offsets or a specific unresolved
reason. The module is unserved and does not authenticate the replies; future
Run/Attempt and effect-journal integration must do that before publication.

The combined targeted test selection passed **75 tests** (W54 preflight,
W56b cohort, window anchor and chunk preflight, plus task governance).
The frozen API SHA is
`7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`.
The frozen 48/55/131 API surface, 25 errors and migration head
`0023_norm_citations` are unchanged. No contract, migration, dependency,
composition root, global style, served route, provider, production DB/S3,
deployment workflow, main ref or tag changes in this candidate.

Clean-tree handoff, fresh remote refs and exact `origin/dev` publication
are recorded by the integrator after this report is committed. The full
beta gate is deferred under R-135 for these unserved slices. No beta or
deployed-corpus claim is made.
