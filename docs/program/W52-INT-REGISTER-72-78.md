# W52-INT-REGISTER-72-78 — W41 debt closures reconciled

The register still listed D-72 and D-78 as current defects after `W41-AUTHOR`
had fixed them. Its report identifies `b56d103` as the hostless-proxy-URL
refusal and `14a0913` as the decision-author repair, with `83751df` supplying
the record citation. The current code still refuses hostless URLs and passes
the authenticated subject's display label and opaque identity to the ledger.

The two current-status cells are now closed, and the original opening text is
kept as history under dated closure notes. Adjacent proxy source/test comments
no longer claim a historical `D-70` URL is configured on today's stand.

Changed files: `src/auditmanager/analysis/text/proxy.py`,
`tests/integration/analysis_text/test_proxy_adapter.py`,
`docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`,
`docs/program/tasks/W52-INT-REGISTER-72-78.md` and this report.

The focused hostless-URL tests, Python compilation, governance/prose tests,
frontend lint and `git diff --check` passed. D-78's runtime evidence is W41's
recorded test and mutation; no database, stand, QA or full gate was run now.
The deferred global validation remains D-139/D-140. No contract, migration,
dependency, composition root, global style or runtime statement changed.
Publish only to `origin/dev` after exact remote-ref and fast-forward checks;
revert this one docs commit if rolled back.
