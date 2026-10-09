# W53-EXEC-01 narrow stop: own-proxy HTTP 503 evidence

Captured 2026-10-09 on Stage-B dispatch base
`6b110c9478c301a9b1436c589803a639124647d6`.

`R-79` permits automatic retry of HTTP 503 only when the response is the
proxy's own envelope and proves that the upstream model call was not made.
The judged W53 plan names `fixtures/proxy/error-envelope-503.json` as a new
fixture, but gives no measured body or stable discriminator. On the frozen
tree, `git ls-files fixtures/proxy` returned no paths, and
`test -e fixtures/proxy/error-envelope-503.json` returned false. A scoped
`git grep -n -i -E 'proxy.{0,60}503|503.{0,60}proxy'` over the plan, owner
ruling and current proxy code found only the rule and proposed fixture,
not an observed envelope. The current `proxy.py` maps every 503 to
`dependency_unavailable` with the claim that the call was not made; that
claim is too broad for the new retry rule.

**Boundary:** No agent may invent an envelope code or treat any arbitrary
503 as safe to retry. Until a real, redacted proxy-owned response is
provided and verified, W53-EXEC-01 must classify 503 as ambiguous
`outcome_unknown`, with zero automatic repeat. This is a narrow stop for
the own-503 retry case and its fixture/test, not a stop for the queue,
lease, journal, cancellation, re-audit, 429 or provably pre-send cases.
The integrator has requested the missing response or its verifiable source
from the owner. On receipt, issue an exact repair grant for the fixture,
classifier and tests; then repeat the fault rehearsal before acceptance.
No release or gate verdict may state that the own-503 retry case passed
while this record is open.
