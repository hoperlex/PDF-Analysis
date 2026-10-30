# HOTFIX-AR-WORKFLOW-UI-1030

The existing canonical stage rail is preserved and labelled «Базовые этапы анализа». The adjacent full-workflow block renders only the server's `extended-review-v2` procedure IDs, titles and actual queued/running/completed/partial/failed/unavailable/skipped statuses. A planned receipt is visible before the result artifact. No fabricated StageResults or v2 plan is assigned to historical v1/legacy-consent Runs; the server's reason is explained with a fresh-consent/new-Run path.

The active→terminal transition explicitly refetches the extended receipt. Pending results continue polling for at most8terminal reads, including failed reads, then show an unconfirmed-result notice and manual refresh. Available data remains visible during refresh failure. Final failed/partial/skipped/unavailable states are rendered rather than hidden.

Native-page images are labelled «страница PDF», with page, source version, hash and a link to that version. They never invoke the portal-block crop URL. Actual portal IMAGE sources retain their existing crop display. Source text remains escaped; blob internals are not rendered.

Owned UI/docs/tests only; owner85ab presentation styling retained. Verification passed: TypeScript typecheck, scoped ESLint and116tests across the new8workflow/native-source/poll controls plus existing85run-progress/12stage-row/11terminal-vocabulary checks. No backend/contracts/generated/production/DB/Git/provider changes. Browser execution, real asynchronous artifact timing and live model quality remain unverified; no full-gate claim.
