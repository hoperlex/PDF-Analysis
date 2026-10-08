# Open alpha — manual acceptance of the public stand

This runbook checks the published alpha's user journey: access, project, PDF, run,
findings, expert decision, CSV, comparison, rejected uploads, sign-out, and account
management. It creates real test records and runs analysis on the named stand. Use only
an authorized alpha origin and the synthetic files in this pack.

Allow 45–70 minutes. Enter the login and password only in the browser. Do not pass them
to a script or put them in a URL, notes, screenshots, or a DevTools export.

## 1. Starting conditions and branch rule

- First publish the integration candidate as an exact SHA in `origin/dev`. This is the
  normal delivery branch for the development environment.
- Moving that SHA to `origin/main` **does not follow automatically from acceptance**. It
  requires a separate direct instruction from the owner and strict adherence to
  `docs/program/MAIN_AUTODEPLOY_POLICY.md`, because a push or merge to `origin/main`
  triggers an external deployment.
- To accept an already deployed version, the operator supplies an **attested deployed
  SHA** from the separate deployment workflow result and
  `infra/deploy/verify-deployed.sh`. It must exactly match the checked `candidate SHA`,
  but the release command only records that attestation: neither a hostname nor a
  supplied argument identifies the revision actually served. The branch is a delivery
  channel; the SHA identifies the version.
- Use a separate reviewer account whose initial password has already been changed.
  If the first sign-in sends you to `/account/password`, change the password, sign out,
  and restart this runbook. That is a required safeguard, not a defect.
- The tester is authorized to create data and make model calls on this stand.
- Use a private browser session with DevTools open. The viewport for overflow checks is
  **780 × 900**.
- Do not put cookies, bearer tokens, passwords, complete request headers, or
  non-synthetic PDFs in the report.

Choose a unique data prefix such as `ALPHA-MANUAL-20261001-1530-<initials>`.
Do not delete or rename another person's projects.

## 2. Test PDF pack

All five files are synthetic: they contain no real project, customer, address, or
personal data. The canonical files are in `fixtures/synthetic/ar/`; the portable
archive is `artifacts/manual-alpha/alpha-test-pdfs.tar.gz`.

| File | Purpose | Size | SHA-256 | Expected result |
| --- | --- | ---: | --- | --- |
| `ar_baseline.pdf` | valid eight-page AR document | 58 978 B | `6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f` | version created |
| `encrypted.pdf` | password-protected PDF | 40 514 B | `9513362c5d85dec1438406ffd4e77fef6d08bb18f104a5b107afc610dde8faba` | 422, `not_encrypted` |
| `image_only.pdf` | two image-only pages | 246 242 B | `8917d48af68cffac071fdf75040d181a548d27d952baa05defbca48a2ca94325` | 422, `every_page_has_extractable_text` |
| `too_many_pages.pdf` | 31 text pages | 66 487 B | `acb3c347dbfe4b38efbc7e56f4389e97725b529966defa2a39c21e34f74da12a` | 422, `1 <= page_count <= 30` |
| `oversize.pdf` | valid 26 MiB PDF | 27 303 204 B | `623bf92bbbf989c1d350f9c8038f9dd6379ee1538100374fd230a81812a665ef` | client refusal `too_large`; no request sent |

The password for `encrypted.pdf` (`synthetic-user-pw`) is only for an independent
check that the file is encrypted. Do not enter it in the application: the file must
be rejected.

## 3. Automated preflight and release command

From the repository root:

```bash
./scripts/manual-alpha-check.sh \
  --origin https://audit.135.106.164.147.sslip.io/ \
  --preflight-only
```

Substitute the actual authorized origin if the temporary address has changed. The
script:

1. checks the SHA-256 and size of all five PDFs;
2. checks TLS and the root response without a session (`307/308` to
   `/login?next=%2F` on the same origin);
3. checks that `/login` is available (`200`);
4. confirms that `/api/v1/openapi.json` answers `401` without a session;
5. saves only a safe summary in `.local/manual-alpha/<UTC timestamp>-<pid>/report.md`.

Require the literal line `PREFLIGHT OK`. Any other outcome is `FAIL` or `BLOCKED`;
do not start the manual journey. Preflight does not establish which SHA is deployed.
The deployment owner runs `infra/deploy/verify-deployed.sh` on the server and
attaches a safe reference to its result.

After the deployment owner independently obtains evidence and attests the
`deployed SHA`, run the full automated journey from a **clean checkout of the same
candidate SHA**. Supply `E2E_PC01_LOGIN` and `E2E_PC01_PASSWORD` to the process in
advance through an approved secret channel. The command accepts neither as an
argument and provides no default.

```bash
make alpha-acceptance \
  ALPHA_ORIGIN=https://audit.135.106.164.147.sslip.io \
  ALPHA_CANDIDATE_SHA=<полный-candidate-sha-из-origin/dev> \
  ALPHA_DEPLOYED_SHA=<полный-sha-из-deployment-evidence>
```

The command runs preflight, signs in through the application screen, performs all
three PC-01 write steps, cold-loads every route in the journey manifest at 780 ×
900, checks `provider_mode=live`, and runs all six refusal scenarios. It stores
raw browser envelopes, safe logs, `report.md`, and a machine-readable
`automated-verdict.json` with schema `w48-alpha-acceptance/v1` and separate
`candidateSha` and `deployedSha` in `.local/manual-alpha/<UTC timestamp>-<pid>/`.

- `ALPHA ACCEPTANCE PASS` means the automated phases completed. It is **not** a
  human sign-off for A01–A20.
- `ALPHA ACCEPTANCE FAIL` means observed behavior or evidence completeness
  violated the contract.
- `ALPHA ACCEPTANCE BLOCKED` means required access or a tool is unavailable,
  or a new run returned typed `dependency_unavailable`. This is not `PASS`.

`make alpha-acceptance` is intentionally outside `make gate`: the former changes
an authorized alpha stand and needs a credential; the latter remains reproducible
without a host.

For the interactive record, run the same script with `--interactive`. After
preflight it accepts only `PASS`, `FAIL`, or `BLOCKED` and a one-line safe note:

```bash
./scripts/manual-alpha-check.sh \
  --origin https://audit.135.106.164.147.sslip.io/ \
  --interactive
```

## 4. Manual journey

### A01 — deployed version and sign-in

Compare the accepted `candidate SHA` from `origin/dev` with the successful
deployment workflow SHA and the result of `verify-deployed.sh`. If the version
was moved to `origin/main`, separately attach the direct instruction that
authorized that deployment action. In a private window open the origin, go to
`/login`, enter the credentials, and sign in.

**PASS:** the SHAs match; sign-in opens `/` (home); neither password nor token
appears in the URL or page; there is no redirect loop or unhandled error. If
the application permits work with the unchanged initial password, this is
**FAIL**.

### A02 — create a test project

At `/projects`, create one project with the unique prefix from §1. Record only
its `project_uid` from the URL or link.

**PASS:** exactly one new project row appears with no alert; its identifier has
the form `prj_<ULID>`; the project opens after a full page reload.

### A03 — valid upload

Open the project, choose `ar_baseline.pdf`, enter a synthetic title, and click
«Загрузить» (Upload).

**PASS:** the browser navigates to
`/projects/<project_uid>/versions/<version_uid>`; the version remains available
after a full reload; `version_uid` has the form `ver_<ULID>`; no
`data-upload-failure` or `data-precheck-problem` message appears.

### A04 — run and four stages

Click «Запустить прогон» (Start run). In Network expect `POST /api/v1/runs` →
`202` with `state: queued`, then wait no more than 150 seconds for a terminal
state.

**PASS:** the result is `published` or `partial`; polling stops;
`data-run-failure` is absent; all four stage results are visible; and
`provider_mode` is **`live`**. A run through the model proxy
(`AUDITMANAGER_PROVIDER_MODE=proxy`, `R-65`) also records **`live`**: this
field describes whether a model produced the result, rather than the call's
transport; replay is `recorded` and remains **FAIL**. On this public alpha,
`recorded`, `failed`, a hang, or `dependency_unavailable` is **FAIL** and
calls for checking D-70/provider connectivity. Save the failing request's
correlation ID, without its Authorization header.

### A05 — PC-01 findings and evidence quality

Open the review screen and each published finding. The reference document
contains:

1. `SI-01`: fire-resistance class `II` for one building on page 2 and `III`
   on page 6;
2. `SI-02`: two evacuation exits on page 3 and three on page 7;
3. `SI-03`: the literal fixture placeholder «уточнить» (clarify) on page 8.

**PASS for a live provider:** at least two of the three issues are found;
every quotation occurs literally on its declared PDF page; none of the six
near-miss controls in `fixtures/synthetic/ar/expected_issues.json` is
published as a finding. A general finding without a verifiable quotation and
page is **FAIL**. Record the found `SI-*` issues and any false positives; do
not substitute model prose for expert judgment.

### A06 — expert decision and journal

On one finding click «Принять» (Accept), then add a unique synthetic comment.
On another click «Отклонить» (Reject). Fully reload the page and open
`/knowledge-base`.

**PASS:** each action appends a separate event; the comment does not replace
the earlier verdict; history, author, and time survive the reload; the
knowledge base displays the current verdicts.

### A07 — CSV

On the review screen click «Скачать <run_id>-findings.csv» (Download).

**PASS:** the file downloads; UTF-8 includes a BOM; the first row has exactly
17 columns; each row represents one evidence item; `run_id`,
`provider_mode`, pages, quotations, and current verdicts agree with the
screen. Downloading again without new decisions produces byte-identical
content.

### A08 — second run and comparison

Start a second run of the same immutable version. After it reaches a terminal
state, open `/projects/<project_uid>/versions/<version_uid>/comparison`.

**PASS:** exactly two runs of one version are compared; the screen distinguishes
`same`, `changed`, `only_left`, and `only_right`; an absent row is not shown as
a match; both run IDs are visible.

### A09 — all screens and width

Follow the application links and cold-reload the addressable screens. Their
number equals the routes in `tests/e2e/pc01/journey/manifest.json`:

1. `/` — home, including the administrator's pending-registration count;
2. `/projects`;
3. project;
4. document;
5. version;
6. version comparison;
7. run;
8. review;
9. `/login` in a separate private window (with an open session, `/login`
   redirects to `/`);
10. `/knowledge-base`;
11. `/account/password`;
12. `/blocks`;
13. `/optimisation` (absent from the menu but still addressable);
14. `/logs`;
15. `/workers`;
16. `/dashboard`;
17. `/403`;
18. `/account`;
19. `/section-optimisation`;
20. `/norms`;
21. `/analysis-settings`;
22. `/queue`;
23. `/register` in a separate private window;
24. `/register/submitted` after submitting a test registration;
25. `/admin/users` with an administrator session;
26. `/admin/users/<user_uid>` through the list link;
27. `/admin/registrations` with an administrator session.

**PASS:** no blank screen, unhandled error, or unexpected request with status
`>=400`; no horizontal scrolling at a 780 × 900 viewport. Preparatory
screens may honestly show «не реализовано» (not implemented); that does not
permit a crash or invented data.

### A10 — four rejected PDFs

Record the document count in the test project. Select each of the four PDFs
from the §2 table in turn; after each refusal use the form's retry or reset
control without reloading another person's file.

**PASS:** the browser rejects `oversize.pdf` as `too_large` and sends no upload
request; the other three return HTTP 422 `validation_failed` with their exact
`details.constraint` from the table. Document and version counts remain
unchanged after every case. One generic error without a rule-specific value,
HTTP 500, or a created object is **FAIL**.

### A11 — dashboard and persistence

Open `/dashboard`, then return to the project through the list without using
a saved deep link.

**PASS:** all four dashboard panels load without a fault; the test project,
version, both runs, findings, and decision journal remain available after a
cold reload; zero is not used to mask an error.

### A12 — sign-out and closed session

Click «Выйти» (Sign out), then try the saved review URL using Back and by
pasting it directly.

**PASS:** protected data cannot be read without a session; the application
sends the user to sign-in or shows authentication required; signing in again
restores access to the saved data. Do not include a cookie or token in the
report.

### A13 — registration and pending sign-in

In a separate private window submit `/register` with a unique synthetic
address, first name, last name, and password. Do not record the password.
Reach `/register/submitted` through the form response, then try signing in
with this pair before an administrator decides.

**PASS:** the form reaches confirmation; sign-in displays «Заявка на регистрацию ещё не
рассмотрена: войти можно будет, когда администратор её одобрит. Подавать заявку повторно
не нужно.» (the registration is pending; do not submit it again). No future
rejection reason is disclosed here.

### A14 — queue and approval

Sign in as an administrator and open `/admin/registrations`. Find the request
by its synthetic address and check the aggregate pending count on home.
Click «Одобрить заявку» (Approve request) without selecting a role; then
select only «Эксперт» (Expert) and approve it.

**PASS:** before role selection the screen shows «Выберите хотя бы одну роль. Запрос не отправлен.»
(choose at least one role; no request was sent), and no API request is made.
After approval the request has status «Одобрена» (Approved), a link to the new
account appears, and the queue and home count update. The administrator
never sees the applicant's password.

### A15 — approved expert sign-in and profile

In a new private window sign in with the A13 address and password. Open
`/account` and reload the page.

**PASS:** sign-in succeeds; last name, first name, and middle name, if supplied,
carry over from the request; the profile is complete; the role appears as
«Эксперт» (Expert). There is no need to enter the same details again.

### A16 — verdict and author

As the expert from A15, open the test run's review screen with a finding and
record «Принять» (Accept). Reload review and open the decision history.

**PASS:** the verdict event persists; the author appears as «Фамилия И. О.»
(Last name I. M.) based on A13 profile fields. Raw identifiers and the sign-in
address do not replace the author label.

### A17 — role revocation and the next operation

As administrator open `/admin/users/<user_uid>` for the A15 expert and
remove the «Эксперт» (Expert) role. In the expert's old window make the next
BFF request. In the server session register check that this session's exact
row disappeared; do not copy its cookie or credential into the report.
Then sign in again and retry recording a verdict.

**PASS:** the first request after revocation returns HTTP 401 with the
`authentication_required` envelope, the session row is removed, and the
screen shows the signed-out state and a sign-in link. Signing in again is
possible, but the new write attempt returns HTTP 403 `permission_denied`.
The old session does not continue with its previous privileges.

### A18 — rejection and indistinguishable sign-in refusal

Submit a second synthetic request and have an administrator reject it with
a reason. In a new private window try signing in once with the rejected
pair and once with a definitely unknown pair. Compare the refusal code and
all visible text byte for byte. Check the reason only in the administrator's
queue.

**PASS:** both sign-ins show the same general refusal, «Войти не удалось: такая пара
имени пользователя и пароля не принята.» (these credentials were not
accepted), with no distinction based on whether the request exists. The
reason is visible to the administrator and absent for the applicant.

### A19 — administrator self-archive

Attempt to archive your own administrator account. Do not remove roles from
working accounts to perform this step. In a separate QA fixture check the
last-administrator safeguard: ordinary UI cannot create that condition
alongside another active administrator because removing your own role is
already forbidden.

**PASS:** self-archiving returns `permission_denied`; administrator access
remains. A separate QA check for `last_admin` shows the
`conflict_reason: last_admin` conflict; until that check is attached, this
part remains debt `D-137`.

### A20 — archive and protected decision author

As administrator archive the expert from A16. Try signing in with that
expert's pair, then on the archived user's card confirm «Удалить навсегда»
(Delete permanently).

**PASS:** sign-in gets the same general refusal as A18; deletion gets
`account_referenced` because the user recorded a verdict; the archived row
remains.

## 5. Verdict

- `PASS`: `make alpha-acceptance` ended with `ALPHA ACCEPTANCE PASS` for the
  exact candidate SHA and attested deployed SHA, and a human signed off all
  A01–A20 steps.
- `FAIL`: at least one required step missed its expectation. Record the step,
  time, correlation ID, and a safe screenshot; do not blindly retry a model
  call.
- `BLOCKED`: a step cannot run because of access or an external dependency.
  This is not `PASS`; name the owner of the blocker.

The interactive script saves its final report in `.local/manual-alpha/`.
Check it manually for secrets before publishing. `.local/` is excluded from
Git.

## 6. What this runbook does not establish

- Infrastructure backup, restore, or rollback;
- load handling, multi-user isolation, or hostile security testing;
- quality on real project documents;
- OCR: the image-only PDF must be explicitly rejected;
- the origin and correspondence of the deployed SHA: the release command
  links supplied SHAs to evidence only as an operator attestation. Establish
  `origin/dev` publication, `origin/main` authorization, and the revision
  actually served separately from the Git remote ref, deployment workflow,
  and `infra/deploy/verify-deployed.sh`.
