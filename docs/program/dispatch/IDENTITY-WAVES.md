# Identity programme — W48 closure, then accounts, roles, registration and the shell

**Status:** plan, written 2026-10-05 from the owner's instruction of the same day. Not yet
frozen; no wave below is dispatchable until its own `*-FREEZE-01` records an exact base.
**Supersedes:** the withdrawn normative-corpus plan for wave 49. The owner withdrew it on
2026-10-05 and chose to reuse the number: `dispatch/W49-PLAN.md`, `dispatch/W49-JUDGES.md`,
`W49-PLAN-01.md` and `tasks/W49-PLAN-01.md` of that plan are removed in the commit that adds this
one (their content remains in Git history at `c11f1b6`), and `W49-PLAN.md` below is the identity
wave. `W48-RULE-01` records the withdrawal as `R-54`.
**Handoff:** this document and the four plans it names are the complete brief for the executing
agent. Nothing the executor needs is in a chat transcript.

## 1. What the owner ordered, in the owner's order

1. Close the W48 debts.
2. Rework the user: e-mail is the sign-in identifier; full name (surname, name, patronymic);
   display name; generated avatar; password change stays.
3. Routing: lazy loading, redirects, guards.
4. Screens: sign-in, registration, account.
5. Registration requests, with administrator approval, editing and removal of accounts.
6. Separate the administrator and expert roles.
7. Navigation split into logical groups with dropdowns.
8. A real home page; "Projects" becomes one navigation item.
9. Account actions (sign-in, sign-out, password, future items) under an avatar in the top-right
   corner: a generated coloured circle with initials, a dropdown with an account header.

The sibling repository `/root/projects/technic` is a source of **ideas only**. Its stack
(Vite, Ant Design, Fastify, Drizzle, a shared TypeScript contracts package) does not transfer;
the ideas that do are listed in §6.

## 2. Stage sequence

| Stage | Plan | Enters when | Exits when |
| --- | --- | --- | --- |
| 0 | `W48-CLOSE.md` | now; the unpublished W48 branches are backed up | W48 candidate is on `origin/dev` with literal `GATE OK`; new debts registered; then, on the owner's direct instruction naming that SHA, `origin/main`, live acceptance and `alpha-w48` (P-7) |
| 1 | `W49-PLAN.md` — identity: contract, migration, backend, BFF session, edge throttle | Stage 0 exit; rulings of §4 recorded | resealed contract with roles, profile, registration, user management and the `rate_limited` code on `origin/dev` |
| 2 | `W50-PLAN.md` — shell: route registry, server guards, redirects, lazy loading, grouped navigation, home page, account menu | Stage 1 exit | shell on `origin/dev`; every screen is behind the registry |
| 3 | `W51-PLAN.md` — screens: sign-in/registration/account and administration, end-to-end evidence | Stage 2 exit | screens on `origin/dev`; alpha acceptance pack covers identity |

The stages are sequential because each consumes the previous one's frozen output: W49's
contract, W50's registry and primitives, W51's screens. No lane starts before its own wave's
freeze; the plans' `Depends on` lines are the only schedule.

Tags `alpha-w49`, `alpha-w50`, `alpha-w51` follow the two-level gate of `W48-PLAN.md` §4 and §12
unchanged: `make gate` is hermetic and mandatory; deployed acceptance is mandatory for a tag;
`origin/main` moves only on a separate direct owner instruction naming the exact candidate.
A wave's exit criterion in this programme is **publication to `origin/dev`**, not a tag.

## 3. Decisions already taken (direct poll, 2026-10-05)

| # | Question | Decision |
| --- | --- | --- |
| P-1 | W48 durable effects and migration `0014` | record the owner's migration authority as a ruling, then an **independent** re-judge of the repair before merge |
| P-2 | registration notifications | none by mail; status is visible in the interface; SMTP is a later task |
| P-3 | avatar | generated circle with initials only; file upload is a later wave |
| P-4 | roles | **a set**: one account may hold expert, administrator or both |

### 3.1 Decisions from the second poll (2026-10-05, before the judging gate of this plan)

| # | Question | Decision | Binds |
| --- | --- | --- | --- |
| P-5 | numbering after the withdrawal | reuse: identity is W49, shell W50, screens W51; the old W49 documents are deleted | all plans |
| P-6 | where the plan lives | branch `plan/identity-waves` from `c11f1b6`, documents only | this commit |
| P-7 | `alpha-w48` | **included** in W48 closure: the owner supplies the provider credential (outside the repository) and the direct `origin/main` instruction naming the exact candidate | `W48-CLOSE.md` §4 `W48-INT-MAIN-01`, §9 |
| P-8 | A-03, the ALR-05 imports | **repair all now** in W48 closure: per-context public modules, every cross-context import rewritten, an executable guard; no waiver | `W48-CLOSE.md` `W48-PUBLIC-01`; `R-58` |
| P-9 | the seeded `admin` | completes its profile at first sign-in after the upgrade and chooses its e-mail there | `W49-PLAN.md` §3.1; `R-59` |
| P-10 | administrator without the expert role | reads everything, changes nothing | `W49-PLAN.md` §3.2; `R-60` |
| P-11 | navigation groups | as proposed: Главная; Работа; Знания; Система; Администрирование | `W50-PLAN.md` §3.1 |
| P-12 | "delete an account" | archive with restore, **plus** irreversible purge when nothing references the account | `W49-PLAN.md` §3.1; `R-61` |
| P-13 | what a rejected applicant sees (asked at the ACCESS-01 merge, 2026-10-06) | nothing at sign-in — the generic refusal; the reason is for administrators; mail informs the applicant later | `W49-PLAN.md` §3.3, §3.5; `W51-PLAN.md` §3; `R-56` addendum |

Three consequences the polls could not see, each stated where it binds:

- **P-12.** Decision events store `author_label` (a display string, migration `0002`,
  `D-78`/`R-37`) and nothing names the account; "no decisions by this account" cannot be
  evaluated by identity without a column, and by label it would be display-string identity
  (`AGENTS.md` §4). W49 adds `expert_decision_event.author_user_uid` (internal column, written
  from the subject on every new event, NULL for history, no wire change) and defines
  "referenced" over a written register of foreign keys (`W49-PLAN.md` §3.1). An administrator
  who archived, granted or decided anything is therefore unpurgeable, and so is an expert who
  authored a decision; the request that created an account is history, not a reference.
- **P-2.** A rejection reason is free text typed by an administrator, which the error catalog's
  safety rules exclude from `details`, and every detail value is capped at 256 characters, so the
  reason is 1–256 characters. The request's password hash is nulled at the decision, so a
  rejected applicant can no longer prove the pair; the owner ruled on 2026-10-06 (P-13, `R-56`
  addendum) that a rejected applicant sees nothing at sign-in and will learn of the rejection by
  mail once SMTP exists. Only *pending* is shown at sign-in (`W49-PLAN.md` §3.3, §3.5).
- **P-9.** The forced completion applies to every account that exists at upgrade, not only to
  `admin`; the stand stays usable between W49 and the W51 screens through an operator command
  (`W49-PLAN.md` §3.1).
- **P-2, again.** A registration form open to anyone needs a throttle, and a throttle needs a
  refusal the catalog can name: the catalog has no 429 and forbids inventing a code at the edge.
  W49 adds exactly one code, `rate_limited`, as the second reseal of its seal slot
  (`W49-PLAN.md` §3.4).

## 4. Rulings to record before Stage 1 freezes

The current rulings exclude what this programme builds: `R-18` keeps "roles, user management"
out of the alpha; `R-42` says "this programme has no role vocabulary and `T-6` forbids inventing
one here"; `contracts/api/v1/openapi.json` says in at least six sentences across
`info.description`, the `/auth/password` operation description and the `bearerAuth` scheme
description that no role, subject or capability vocabulary — and no rate limiting — exists on
this surface (`rg -n -i -e role -e 'rate limit' contracts/api/v1/openapi.json`);
`ALPHA_ROADMAP.md` §1 lists user management and roles as "not in this road". A contract that adds them while those sentences stand violates the programme's own rule
that a document must not outlive what it describes (`OPERATING_CONSTRAINTS.md` §4.7).

`W48-RULE-01` (Stage 0) records the first two; `W49-RULE-01` records the rest before the W49
freeze. Numbers are provisional — the recording task takes the next free `R-` number
in `OWNER_RULINGS_2026-09-17.md` and updates the references in these plans in the same commit.

| Provisional | Content | Source |
| --- | --- | --- |
| `R-53` | migration `0014_durable_analysis_effects` was authorised by the owner on 2026-10-02 as a separate contract/migration grant for audit findings `A-01`/`A-02`; `W48-PLAN.md` §9's "frozen/no owner" row is superseded for that one migration; the in-place edit of `0014` means every database migrated to the earlier shape must be recreated, not upgraded | P-1; `tasks/W48-DURABLE-01.md` |
| `R-54` | W49 is withdrawn; the normative corpus stays at migrations `0012`/`0013` with no promotion, no custody writes and no retrieval; its open questions `NORM-Q01..Q09`, `D-59`, `D-71`, `D-119` remain registered, not decided | owner, 2026-10-05 |
| `R-55` | the alpha gains accounts with e-mail sign-in, full names, a role set `{expert, admin}`, registration requests and administrator management of accounts; `R-18`'s exclusion of roles/user management, `R-42`'s role sentence and `T-6`'s "implementation deferred" are superseded for exactly this scope; multi-tenancy stays excluded; the derived name form "Фамилия И. О." takes precedence over `R-37`'s chosen `display_name` where both exist | owner, 2026-10-05; P-4 |
| `R-56` | registration carries no mail; the applicant learns the status at sign-in; SMTP is a later task | P-2 |
| `R-57` | the avatar is generated from the account's initials and e-mail; no upload | P-3 |
| `R-58` | every cross-context import the ALR-05 walk lists on the W48 closure line (16 deep / 22 package-root at `c11f1b6`; 18 / 24 at `411c6d0`) is repaired through `auditmanager.<context>.public` modules and an executable guard; no waiver is granted, `api/composition.py` included | P-8 |
| `R-59` | the seeded `admin` keeps its login until its first sign-in after the upgrade, where the forced completion screen takes an e-mail and the names in one save and rewrites `login` to the e-mail; from then on every account's login is an e-mail | P-9 |
| `R-60` | an active account with any role reads product data; product mutations require `expert`; account management requires `admin` | P-10 |
| `R-61` | "delete an account" is archive with restore; an archived account that nothing references may be purged irreversibly; "references" is the written register of foreign keys in `W49-PLAN.md` §3.1 (`archived_by`, `granted_by`, `decided_by`, `author_user_uid` restrict; the creating request is history) | P-12 |

## 5. Cross-wave invariants the executor must keep

These are the programme's existing rules restated where this work will meet them. Each has a
guard that already exists or a task below that adds one.

- **`make gate` stays hermetic** and ends with the literal `GATE OK`. No wave adds a secret,
  network or deployed host to it (`W48-PLAN.md` §4).
- **A reseal is four documents in one change:** `contracts/api/v1/openapi.json`, the generated
  client under `web/src/shared/api/generated/`, the mirror `web/openapi/openapi.json`, and
  `web/FRONTEND_LOCK.json` (`CURRENT_STATE.md`, `D-18`). A new error code or detail key is a
  second reseal in the same slot, and a code lives in four places — `error-codes.json`,
  `error-envelope.schema.json`, the `== 22` literal in `test_openapi_document.py`, and the
  Russian sentence in `web/src/shared/api/catalog-message.ts`; this programme adds one code
  (`rate_limited`) and one detail key (`conflict_reason`), both in W49.
- **Registers, not rules.** Which operations answer without a credential, which a default
  credential reaches, and now which roles each operation requires, are written sets in
  `src/auditmanager/api/security.py` that a sweep test compares against the served
  application. A new operation is closed by default.
- **Identity by content or opaque id, never by path, filename or display string**
  (`AGENTS.md` §4). E-mail is a sign-in identifier and a unique key; `user_uid` remains the
  identity every row references.
- **No silent fallback.** An unknown role, status or vocabulary value renders a typed fault
  (`W48-WEB` precedent). No `?? rawValue`.
- **Business logic lives in the bounded context**, not in the router, the Pydantic schema or
  the React component. Invariants such as "the last administrator cannot be archived" are
  enforced in `auditmanager.access` and proven by a test that bypasses the router.
- **One owner per hotspot per wave:** `contracts/**`, migration head, root locks, composition
  root (`src/auditmanager/bootstrap/**`, `src/auditmanager/api/composition.py`,
  `web/src/_app/providers.tsx`), `web/src/app/globals.css`, `CURRENT_STATE.md`,
  `DEBT_REGISTER.md`.
- **No new frontend dependency without a decision.** `web/package.json` holds four runtime
  dependencies, all pinned exactly, and `pinned-versions.guard.test.ts` plus
  `frontend-lock.guard.test.ts` enforce it. Dropdown, menu and avatar are written in
  `web/src/shared/ui/`; a library would be a separate owner decision and a lock update.
- **The interface is Russian** (`R-18`); `rendered-language.guard.test.ts` and
  `presentation-language.guard.test.ts` fail on English in rendered screens.
- **Every new `page.tsx`** is registered in `web/tests/unit/screens/route-screens.ts` `SEEDS`
  and in `tests/e2e/pc01/journey/manifest.json`, calls the server guard or is named in the
  open-screen register of `web/tests/guards/default-credential-screens.guard.test.ts` (renamed
  `screen-guard.guard.test.ts` by W50), and (from W50) has a row in the screen registry.
- **A judge is never the author.** The durable-effects repair was judged by its own author
  (`W48-DURABLE-REPAIR.md` admits it); P-1 reverses that. Every judge below runs in a fresh
  context that has not read the author's report before its black-box pass.
- **Measured figures carry their method.** Any count in a report names the command and the
  tree it was run on.

## 6. Ideas taken from `technic`, and what is not

Taken as ideas, rewritten for Next.js and Python:

- one declarative section registry drives the menu, the route guards and the start page
  (`packages/contracts/src/portal-sections.ts`); here it becomes
  `web/src/shared/config/screen-registry.ts` (W50);
- full name as three columns with a derived display form and a rule against mixed
  Cyrillic/Latin words (`person-name.ts`); here in `auditmanager.access.models` (W49);
- the avatar palette and hash (`shared/lib/avatar.ts`): fourteen dark colours chosen for white
  text; here hashed from the **e-mail**, not the name, so a corrected name does not recolour
  the account (W50);
- a registration request approved in one transaction under a row lock; rejection is recorded
  with a reason; a race between two identical requests answers a conflict, not a 500 (W49);
- soft deletion with a partial unique index so an archived address can be re-registered and
  sign-in must filter the archive (W49);
- one generic refusal for a wrong e-mail/password pair; the account's existence is not
  revealed (already the rule here);
- a manifest of each operation's required protection with a test that sweeps the served
  application (`route-authorization.test.ts`); here the role register in `security.py` (W49);
- the account menu in one place for desktop and mobile; the trigger is a real `<button>` with
  `aria-expanded` — `technic`'s desktop trigger is a `div` and cannot be opened by keyboard,
  which is the mistake not to copy (W50).

Not taken: Ant Design, react-router gates, the zod contracts package, the fourteen-role
permission catalogue, in-memory access tokens (this BFF keeps the credential server-side and
the browser holds an opaque session id — `app/bff/session/store.ts`), e-mail verification,
captcha, and `technic`'s return-after-login that drops `search` and `hash`.

## 7. Debts to register at Stage 0

Found by the 2026-10-05 revision; registered by `W48-INT-CLOSE` with the next free `D-`
numbers. Each row names its check so the register stays measured, not compiled.

| Finding | Check that shows it | Owner |
| --- | --- | --- |
| deploy is not bound to a gate: any commit on `main` deploys; the workflow proves only ancestry | `sed -n 1,12p .github/workflows/deploy-auto.yml`; `grep -c 'make gate' .github/workflows/deploy-auto.yml` → 0 | owner decision; W48-CLOSE registers |
| `test_deploy_auto_workflow.py` matches substrings; `pull_request_target:` added to the workflow stays green | mutation: add the trigger in a copy, run the test | `W48-GUARDS-2` |
| `ALPHA ACCEPTANCE PASS` attests the deployed SHA from operator input; no endpoint or served file names the running revision | on `03c04a1` (the files exist only on the W48 branches): `grep -n 'deployed-sha' scripts/manual-alpha-check.sh tests/e2e/pc01/journey/verify-acceptance.mjs` | `W48-GUARDS-2` rewords; endpoint deferred |
| audit questions `reviews/W48-AUDIT.md` §7 still untested: browser layout at 780 × 900 with hostile strings, online CVE/licence/image scan, MinIO volume inventory and restore rehearsal | the section itself | 780 × 900 → `W48-JUDGE-Z`; the other two registered |
| registration can be flooded to the 100-request cap by anyone; rejection is one request at a time | `W49-PLAN.md` §3.3, §3.5 | register at W49 (bulk rejection, retention of decided requests) |
| an administrator who resets a password knows the temporary password | `W49-PLAN.md` §3.4 | register at W49 |
| migration `0015` cannot be downgraded on any real database after its backfill | `W49-PLAN.md` §4 `ACCESS-01a` | register at W49 |
| sixteen ALR-05 deep imports, plus twenty-two through package `__init__` — **repaired, not registered**: the guard `tests/contract/architecture/test_alr05_boundaries.py` is the check | AST walk in `reviews/W48-AUDIT.md` A-03; re-run at `c11f1b6`: 16 / 22; must read 0 / 0 after `W48-PUBLIC-01` | `W48-PUBLIC-01` |
| fail-open closed-vocabulary lookups outside the two widgets W48-WEB repaired | `rg -n 'LABELS\[|_LABEL\[|as ProviderMode' web/src/widgets web/src/entities web/src/shared/ui -l` → 12 files at `c11f1b6`, two of them already repaired on `03c04a1`; TAILS classifies every hit | `W48-TAILS` |
| `norms` HNSW index is one per table, filtered after the scan, `hnsw.ef_search` never set; a second snapshot shrinks `nearest()` results | `git grep -n 'ef_search\|iterative_scan' -- src tools tests db` → empty | register; the old W49 withdrawn |
| corpus load re-reads files after `snapshot_of` hashed them without re-verifying | `src/auditmanager/norms/corpus_source.py` `iter_documents` | register |
| snapshot `content_key` excludes `segmentation_profile`; raising the version makes `ensure_snapshot` conflict | `rg -n 'segmentation_profile' src/auditmanager/norms/repository.py src/auditmanager/norms/loader.py` | register |
| embedding build completeness accepts a one-character window; `embedding_set_sha256` includes a private bigint | `src/auditmanager/norms/embedding_repository.py` `ensure_build` | register |
| `infra/local/README.md` and `bucket-init.sh` still name `FOUNDATION_S3_IMAGE` as a live input | `rg -n 'FOUNDATION_S3_IMAGE' infra/local` | `W48-TAILS` |
| D-52 is repaired (`web/NOTICE`) but open in the register | `rg -n 'D-52' docs/program/DEBT_REGISTER.md` | `W48-INT-CLOSE` addendum |
| `W48-PLAN-01.md` cites unreachable `cf63d31` and says both deploy runs failed | `git merge-base --is-ancestor cf63d31 HEAD` → false | `W48-INT-CLOSE` addendum |
| `is_default_credential` will also mean "administrator reset this password"; the wire name is kept, the meaning widens | `W49-SEAL-01` documents it | register at W49 |

## 8. Roles and protocol

Two roles, fixed by the owner on 2026-10-05:

- **The executor** (the external agent) runs lane tasks, QA tasks, judge tasks and FIX slots.
  Each runs in its own worktree from the frozen base named in its task file, runs its own lane
  gate, and **hands back** a branch `agent/<TASK_ID>` at a recorded SHA plus the report
  `docs/program/<TASK_ID>.md` (or `reviews/<TASK_ID>.md` for a judge). The executor never merges
  into an `integration/*` branch, never pushes any ref to `origin`, never creates a tag, and never
  edits `CURRENT_STATE.md`, `DEBT_REGISTER.md`, `PORT_REGISTRY.md`, `OWNER_RULINGS_*.md` or
  `CHECKPOINT_REGISTRY.md` unless a task file names an exact sentence.
- **The integrator** (the owner's own session) runs every `*-FREEZE-01`, `W48-SAFE-01`,
  `W48-RULE-01`, every merge, the final full `make gate` on each merged candidate, every
  `*-INT-CLOSE`, `W48-INT-MAIN-01`, publication to `origin/dev` and — on instruction —
  `origin/main` and tags. Publication rules bind the integrator: `origin/dev` only after literal
  `GATE OK` on the exact candidate, fast-forward only; `origin/main` never without a direct owner
  instruction naming the candidate (`AGENTS.md` §6, `MAIN_AUTODEPLOY_POLICY.md`) — P-7 is the
  owner's intent, not that instruction, and `W48-INT-MAIN-01` asks for it quoting the exact SHA
  once the candidate exists. The provider credential (`D-70`) is placed by the owner in the
  host's `provider.env`; it never enters the repository, a worktree, a report or a chat.

The integrator hands the executor `docs/program/dispatch/EXECUTOR-PROMPT.md` verbatim with the
first task file; it restates this section for an agent that has nothing but the repository.

Hand-back format, per task: branch and SHA; the report with the six items of `AGENTS.md` §5;
the lane gate's literal `GATE OK` tied to that SHA (or the focused commands the task names);
`git diff --name-only <base>..<sha>` shown to lie inside `allowed_paths`; every mutation the task
required with its red output; open questions as a list, not as decisions taken.

Protocol for the executor:

1. **Read first:** `AGENTS.md`, `docs/program/CURRENT_STATE.md`, this file, the stage plan,
   `docs/program/dispatch/OPERATING_CONSTRAINTS.md` §1–§10, `docs/program/dispatch/PORT_REGISTRY.md`.
2. **Worktree per task** from the frozen base, under `.local/worktrees/<task>`, provisioned with
   `make bootstrap FOUNDATION_PYTHON=<python3.12 path>` and `npm --prefix web ci`; a unique
   `FOUNDATION_INSTANCE`, `POSTGRES_PORT`, `S3_API_PORT`, `S3_CONSOLE_PORT`, `POSTGRES_DB` and
   `S3_BUCKET`; the ports taken from `PORT_REGISTRY.md` and written there in the dispatch
   commit. The ignored real corpus under `.local/norms/corpus` must be attached read-only to a
   worktree before `make gate`, or the gate fails on a precondition that is not a defect
   (`W48-FREEZE-01.md`).
3. **One measurement per lane.** Never edit a tree while its gate runs. A gate result is tied to
   the SHA it measured; a commit after the gate needs a new gate.
4. **Never kill a process by pattern.** The host runs other projects' test suites. Kill only a
   PID this task started and recorded.
5. **Reports:** every task ends with the six items of `AGENTS.md` §5 in
   `docs/program/<TASK_ID>.md`; judges write `docs/program/reviews/<TASK_ID>.md` and change
   nothing else. Reports to the owner are in Russian; repository artifacts stay English.
6. **Hand-back, not publication:** the executor's work ends at the branch and report of the
   hand-back format above; merging, gating the merged candidate and publishing are the
   integrator's.
7. **Stop conditions** are per plan; on any of them the executor stops, writes what it found and
   asks. "Continue" is not an instruction to publish `main` or to widen a contract.
8. **Questions** are collected and asked in one batch at the gate the plan names; a lane does not
   decide a product question by choosing the convenient default.
9. **A judge's context** receives only its own task file and the subject SHA. The authors'
   reports and the finding lists in these plans are withheld until the judge has written its own
   black-box pass; it then reads them and cross-examines.

## 9. Not in this programme

SMTP and any mail; avatar upload; e-mail verification; captcha; password reset by link;
multi-tenancy; the normative corpus promotion, custody and retrieval (withdrawn with W49);
a MinIO successor; a version endpoint for the deployed SHA (registered, not built).

## 10. Standard task forms

The wave plans name these tasks by role and do not repeat their fields; `*-FREEZE-01` generates
each task file from `docs/templates/TASK_TEMPLATE.md` with the fields below plus the wave's exact
SHAs. Rollback for every form is the revert of the task's commits; none changes stored data,
except where a form says otherwise.

### `W*-RULE-01` (integrator)
- **Outcome:** the rulings a wave depends on exist in `OWNER_RULINGS_2026-09-17.md` with their
  dates and sources, after the owner has confirmed the text; every provisional `R-` number in the
  plans is replaced by the recorded one.
- **Allowed paths:** `docs/program/OWNER_RULINGS_2026-09-17.md`, the plan documents under
  `docs/program/dispatch/` (number replacement only), `docs/program/W*-RULE-01.md`.
- **Required checks:** each new `R-` number is found once in the rulings file; `git diff --check`.
- **Integration contract:** no task of the wave starts before this one hands back.

### `W*-FREEZE-01` (integrator)
- **Outcome:** the exact base is recorded, the plan's provisional numbers are replaced, task
  files exist with exact `allowed_paths`, ports are taken.
- **Allowed paths:** `docs/program/tasks/W*-*.md`, `docs/program/W*-FREEZE-01.md`, the wave's
  plan in `docs/program/dispatch/`, `docs/program/dispatch/PORT_REGISTRY.md`, `origin/dev`
  (docs-only dispatch tip, fast-forward).
- **Required checks:** fetched refs equal the recorded ones; full `make gate` at the base with
  the real corpus attached, literal `GATE OK`; contract triple, catalog, identifiers and
  migration head measured by command; `git diff --check`; clean status.
- **Integration contract:** every lane starts from the recorded SHA and nothing else.
- **Failure cases:** a moved remote ref, a red gate at the base, or an unrecorded ruling stops the
  freeze.

### `W*-QA-01` (executor, fresh context)
- **Outcome:** independent tests written without reading lane reports, under the wave's
  `qa_w<NN>/**` directories only.
- **Allowed paths:** the directories the plan names; `docs/program/W*-QA-01.md`.
- **Required checks:** the new files; the suites they live in; `git diff --check`.
- **Integration contract:** a QA test that fails is a finding, not a repair; QA never edits the
  subject.
- **Failure cases:** a QA test that cannot fail (shown by one mutation) is removed by QA itself.

### `W*-JUDGE-*` (executor, fresh context)
- **Outcome:** one report `docs/program/reviews/<TASK_ID>.md` with subject SHA, environment,
  commands with exit status, findings (path/line/consequence/reproduction), mutation results,
  untested questions, verdict, and `git diff --name-only <subject>..HEAD` proving report-only.
- **Allowed paths:** that report. Probes are restored; disposable services only; no credential
  in evidence.
- **Integration contract:** the integrator opens a FIX slot only for upheld release-blocking
  findings; cross-examination between two judges follows `W48-JUDGES.md`.

### `W*-FIX` (executor)
- **Outcome:** every upheld release-blocking finding is closed by a change whose revert makes a
  named test red.
- **Allowed paths:** the explicit grant the integrator writes per finding; nothing else.
- **Required checks:** the judge's probe re-run green; the affected suites; `make gate`;
  `git diff --check`.
- **Failure cases:** a repair that needs a contract, migration or hotspot outside the grant stops
  and returns to the integrator.

### `W*-INT-CLOSE` (integrator)
- **Outcome:** the merged candidate is published to `origin/dev` with literal `GATE OK` tied to
  its SHA.
- **Allowed paths:** the `integration/w<NN>` branch, `docs/program/CURRENT_STATE.md`,
  `docs/program/DEBT_REGISTER.md`, `docs/program/dispatch/PORT_REGISTRY.md`,
  `docs/program/W*-INT-CLOSE.md`, `origin/dev`.
- **Steps:** merge in the plan's order with no semantic resolution inside merge commits; full
  `make gate` on the exact candidate; counts by test id against the freeze baseline with every
  delta explained; `CURRENT_STATE.md` live section rewritten by measured value; debts registered
  with their check commands; ports released; fast-forward `origin/dev`; `git ls-remote origin dev`
  equals the candidate; worktrees removed only after that.
- **Stops at `origin/dev`.** `origin/main` and a tag need the owner's direct instruction naming
  the exact SHA and the two-level gate of `W48-PLAN.md` §12; that is a separate `W*-INT-MAIN-*`
  task, as `W48-INT-MAIN-01` in `W48-CLOSE.md`.
