/**
 * No Latin-script word reaches a reviewer from a **rendered** screen, unless a contract
 * put it there.
 *
 * ## Why this renders instead of reading source
 *
 * `R-18` requires the alpha in Russian. **Three sessions reported the interface translated
 * and three were wrong** (`D-53`). The third round is the one that decides this file's
 * design: `26b960d` scanned `.tsx`, `b0b8148` scanned `.ts`, both were green, and what
 * found the survivors was rendering the six screens -- `Create`, `Start run`, the version
 * panel's `label=` props, `Display title`, `Published findings:`, and four `LoadingState
 * what=` arguments that composed into `Загрузка: the run…`.
 *
 * **The misses are not in the text.** `label="Display title"`, `what="the run"` and the
 * ternaries around them are *arguments*; the string a reviewer reads does not exist until
 * React composes it. A fourth source sweep would have missed a fourth time. So this guard
 * renders the screens, takes the text a browser would show, and judges that.
 *
 * `presentation-language.guard.test.ts` is the other half and neither replaces the other:
 * it reads two owned trees and fails on **English prose** -- two or more function words --
 * which is how it catches a sentence without an allowlist. It cannot see any of `D-53`'s
 * twenty, because none of them is prose: `Create` has no space, `Start run` and `Display
 * title` carry no function word at all. This guard is the complement: **any** Latin word,
 * anywhere on a rendered screen, in **every** module that composes it.
 *
 * ## Why the data is Cyrillic
 *
 * A rendered screen carries two kinds of string: what the application wrote, and what the
 * server sent. Only the first is this programme's to translate -- a finding's text is the
 * analysis's own words and may legitimately be in any language. `tests/unit/review/
 * fixtures.ts` seeds English finding text on purpose, so it is deliberately **not** reused
 * here. Every value this file seeds is Cyrillic, or an identifier, or a contract enum.
 * **Anything Latin left in the output is therefore chrome the application authored**, and
 * the guard needs no rule for telling content from chrome.
 *
 * ## What is allowed to be Latin, and where the permission comes from
 *
 * `W30-LISTS` closed eighteen instances of *a hand-maintained subset standing in for
 * something a contract defines*. An allowlist here is exactly that class, so almost all of
 * it is **read out of `contracts/api/v1/openapi.json` at run time**: every `enum` in every
 * schema. That is the run states, the stage ids, the stage statuses, the finding
 * categories, the verdicts, the decision event types, the provider modes, the cost bases
 * and all 22 error codes -- **in one rule, with no names written down here.** Add a
 * twenty-third error code to the contract and it is allowed the moment it is added; take
 * one away and its appearance on a screen becomes an offence. `DEBT_REGISTER.md` §2 has
 * the open owner question of whether this vocabulary should be translated at all; this
 * guard takes no position on it, which is the point of deriving rather than listing.
 *
 * What is left over is in `NOT_DERIVABLE` below, and **every entry carries the reason no
 * contract can supply it.** A long list there is a defect in this guard, not a fact about
 * the tree.
 */

import { createElement } from 'react';
import type { ComponentType, ReactElement } from 'react';
import { describe, expect, it } from 'vitest';

import { ApiError, TransportError, queryKeys } from '@/shared/api';
import type {
  DashboardSummary,
  DecisionEvent,
  DecisionRecord,
  DocumentVersion,
  ErrorCode,
  ErrorEnvelope,
  Finding,
  FindingDetail,
  Project,
  RunActivity,
  RunStateCount,
  RunStatus,
  SectionReview,
  RunNormReferences,
  SpecificationPrices,
  StageId,
  StageStatus,
  VersionClassification as VersionClassificationRecord,
  Assignment,
  AssignmentDetail,
  VersionComparison,
} from '@/shared/api';
import { RUN_STATE_VALUES } from '@/shared/api';
import { AR_V3_BETA_PROFILE_ID, RUN_PAGE_LIMIT, classifyRunFailure } from '@/entities/audit-run';
import { USER_PAGE_LIMIT } from '@/entities/user';
import { ASSIGNMENT_PAGE_LIMIT } from '@/entities/assignment';
import { REGISTRATION_PAGE_LIMIT } from '@/entities/registration-request';
import { JOURNAL_PAGE_LIMIT } from '@/entities/expert-decision';
import {
  ALREADY_CLASSIFIED_DETAIL, CARRYOVER_CONFLICT_TEXT, CARRYOVER_NOT_PERMITTED_DETAIL,
  CLASSIFY_NOT_PERMITTED_DETAIL, COMPARISON_DIFF_LIMIT, CORRECTION_NOT_CLASSIFIED_DETAIL,
  CORRECTION_NOT_PERMITTED_DETAIL, CORRECTION_REASON_DETAIL, CORRECTION_STALE_DETAIL,
  CORRECTION_UNCHANGED_DETAIL,
  DOCUMENT_PAGE_LIMIT, UPLOAD_CONSTRAINTS_STATED, UPLOAD_ENVELOPE_RULES, VERSION_PAGE_LIMIT, classifyUploadFailure,
  precheckProblemMessage,
} from '@/entities/document-version';
import { PROJECT_PAGE_LIMIT, PROJECT_SECTIONS, PROJECT_STRUCTURE_ORDER, projectSectionOf } from '@/entities/project';
import type { AnalysisProfileListItem, CarryoverCandidate, VersionClassificationRevision } from '@/shared/api';
import { ClassifyVersionFormView } from '@/features/classify-version';
import { CorrectVersionClassificationFormView } from '@/features/correct-version-classification';
import { CarryOverDecisionView } from '@/features/carry-over-decision';
import { VersionClassification, VersionClassificationView } from '@/widgets/version-classification';
import { ProjectStructureView } from '@/widgets/project-sections';
import { SpecificationPricesAnswer, SpecificationPricesSection } from '@/widgets/specification-prices';
import { NormReferencesAnswer, NormReferencesSection } from '@/widgets/norm-references';
import { SPECIFICATION_ROW_LIMIT } from '@/entities/specification-price';
import { SectionSpecificationAnswer, SectionSpecificationSection } from '@/widgets/section-specification';
import { SECTION_ROW_LIMIT } from '@/entities/section-specification';
import { SECTION_NO_ROWS, sectionAnswer, sectionKey, sectionPagedAnswer } from '../unit/section-specification/fixtures';
import { AppFrame } from '@/_app';
import { accountMenuProps } from '@/_app/account-menu';
import { UpdateBannerView, WhatsNewView } from '@/_app/release-notices';
import { FrameNavigationView } from '@/_app/frame-navigation';
import { buildNavigation } from '@/_app/navigation';
import type { DisclosureProps } from '@/shared/ui';
import { DisclosureView } from '@/shared/ui/disclosure';
import { MenuView } from '@/shared/ui/menu';
import { SignInPage } from '@/_pages/sign-in';
import { AccountPage } from '@/_pages/account';
import { RegisterPage } from '@/_pages/register';
import { ChangePasswordPage } from '@/_pages/change-password';
import { LogsPage } from '@/_pages/logs';
import { ManageUserControls } from '@/features/manage-user';
import type { Account } from '@/shared/api';
import type { RegistrationRequest } from '@/shared/api';
import { RegistrationQueue } from '@/widgets/registration-queue';
import { VersionHistoryView } from '@/widgets/version-history';
import { UserCard } from '@/widgets/user-card';
import { AssignmentHistory } from '@/widgets/assignment-board';
import { MY_TASKS_LIMIT } from '@/widgets/my-tasks';
import NotFound from '@/app/not-found';
import ErrorBoundary from '@/app/error';
import { DecisionHistory } from '@/widgets/decision-history';
import { ArV3BetaReview } from '@/widgets/ar-v3-beta-review';
import { ArV3BetaPack } from '@/widgets/ar-v3-beta-pack';
import {
  MALFORMED_GROUP_ANSWER, StartArV3GroupView, classifyArV3GroupStartFailure,
} from '@/features/start-ar-v3-group';
import { ExecutionJournal } from '@/widgets/execution-journal';
import { ExecutionQueue } from '@/widgets/execution-queue';
import { WorkerList } from '@/widgets/worker-list';
import { WorkersPage } from '@/_pages/workers';
import type { WorkersPageProps } from '@/_pages/workers';
import {
  CommandFailure, CreateConnectionForm, HostKeyControl, IssuedTokenView, ReviseConnectionForm,
  SettingsFields, SshKeyControl,
} from '@/features/manage-executor-connection';
import { EXECUTOR_SECRET_OUTCOMES, SetExecutorSecretForm } from '@/features/set-executor-secret';
import { ExecutorSelectView, StartRunControl, StartRunFailureView } from '@/features/start-run';
import { executorChoices } from '@/entities/executor-connection';
import {
  ALL_CASES as EXECUTOR_CASES, PINNED as EXECUTOR_PINNED, READY as EXECUTOR_READY,
  OUTCOME_CASES as EXECUTOR_OUTCOME_CASES, PULL_ONLINE as EXECUTOR_PULL_ONLINE, runnerToken, seedExecutors,
  tokenId as executorTokenId,
} from '../unit/workers/executor-fixtures';
import { RunWorkerLine, WORKER_PAGE_LIMIT } from '@/entities/execution';
import type { ExecutionWorker } from '@/shared/api';
import { EvidenceViewer } from '@/widgets/evidence-viewer';
import { KnowledgeBase } from '@/widgets/knowledge-base';
import { RECENT_PROJECT_LIMIT } from '@/widgets/home-tiles';
import {
  NORM_CATALOGUE_PAGE_LIMIT, NORM_EVENT_PAGE_LIMIT, NORM_PARAGRAPH_PAGE_LIMIT, NORM_SEARCH_PAGE_LIMIT,
  NORM_SNAPSHOT_LIMIT,
} from '@/entities/norms';
import { NormsPage } from '@/_pages/norms';
import { NormSearchResults } from '@/widgets/norm-search';
import { NormCatalogueTable } from '@/widgets/norm-catalogue';
import { NormParagraphList, NormPdf } from '@/widgets/norm-document';
import { NormSnapshotHistory, NormSnapshotList } from '@/widgets/norm-snapshots';
import { VersionBlockViews } from '@/_pages/blocks';
import { portalBlocksQueryOptions } from '@/entities/block';
import { CropFigureView, PortalBlockListView } from '@/widgets/portal-blocks';
import {
  BLOCKS_PROJECT_UID, BLOCKS_RUN_ID, BLOCKS_VERSION_UID, blocksVersion, everyKindOfBlock, notProducedPage, portalPage,
} from '../unit/blocks/fixtures';
import {
  NORM_CATALOGUE_PAGE, NORM_DOCUMENT_ID, NORM_EVENTS, NORM_HITS, NORM_PARAGRAPHS, NORM_QUERY, NORM_SNAPSHOTS,
  normDocument,
} from '../unit/norms/fixtures';

import { CONTRACT_PATH, SEAMS_PATH, readJson, readText, repoRelative, walkFiles } from './lib/repo';
import { join } from 'node:path';
import { REPO_ROOT } from './lib/repo';
import { newClient, renderScreen, seedError } from '../unit/screens/harness';
import {
  NOT_INSTALLED_PACK, installedPackFixture, withoutMember,
} from '../unit/analysis-settings/ar-v3-beta-pack-fixtures';
import { optimisationShapes } from '../unit/optimisation/fixtures';
import { proposalShapes } from '../unit/optimisation-proposals/fixtures';
import { derivedScreens, malformedVariants, wellFormed } from '../unit/screens/route-screens';
import {
  ADMIN_AND_EXPERT,
  DEFAULT_CREDENTIAL,
  EXPERT,
  INCOMPLETE_PROFILE,
  NO_ROLES,
  UNKNOWN_ROLE,
} from '../unit/shell/subjects';
import { yieldToRunnerAfterEachTest } from './lib/yield-to-runner';

// This file computes for ~40-65 s without awaiting I/O; see the helper for why that aborts a run.
yieldToRunnerAfterEachTest();

// ===================================================================== the vocabulary

interface OpenApi {
  readonly components: { readonly schemas: Record<string, { readonly enum?: readonly string[] }> };
}

/**
 * Every enumerated value the API contract publishes, in one read.
 *
 * Derived, not listed: this is `W30-LISTS`'s rule applied to the thing that would
 * otherwise be the largest hand-maintained set in this file.
 */
export function contractEnums(): ReadonlySet<string> {
  const openapi = readJson<OpenApi>(CONTRACT_PATH);
  const values = new Set<string>();
  for (const schema of Object.values(openapi.components.schemas)) {
    for (const value of schema.enum ?? []) values.add(value);
  }
  return values;
}

/**
 * The nineteen CSV column names, parsed out of the seam document that freezes them.
 *
 * `OD-11` freezes them in `docs/program/P02_SEAMS.md` §6, and
 * `web/tests/contract/csv-columns.contract.test.ts` already ties that table,
 * `shared/api/csv-columns.ts` and `exports/serializer.py` together. The export panel
 * prints the list to the reviewer, so those names are on a screen -- and they are machine
 * identifiers, not English prose, so this guard reads the same authority the application
 * does rather than listing them again.
 *
 * **`R-18` separately names printing this list to the user as a defect** -- "documentation
 * standing where an interface should be". That is a question about what the screen shows,
 * not about what language it is in, and it is reported in `docs/program/W32-SEE.md` rather
 * than smuggled into this guard.
 */
export function csvColumnNames(): ReadonlySet<string> {
  const document = readText(SEAMS_PATH);
  const section = document.slice(
    document.indexOf('## 6. The CSV column contract'),
    document.indexOf('## 7. API seam'),
  );
  const columns = new Set<string>();
  for (const line of section.split('\n')) {
    const match = /^\|\s*\d+\s*\|\s*`([a-z0-9_]+)`\s*\|/.exec(line.trim());
    if (match !== null) columns.add(match[1] as string);
  }
  return columns;
}

interface StageRegistry {
  readonly stages?: readonly {
    readonly required_inputs?: readonly { readonly role: string }[];
    readonly produced_outputs?: readonly { readonly role: string }[];
  }[];
  readonly registry?: StageRegistry['stages'];
}

/**
 * The input- and output-manifest role names, read from the analysis contract.
 *
 * A role reaches a screen: the version panel lists the input manifest and prints each
 * entry's role. `documents/models.py` derives `MANIFEST_ROLE_SOURCE_DOCUMENT` from exactly
 * this file and raises at import if the derivation fails -- its docstring records that a
 * previous session restated the spelling as a constant and diverged from the contract
 * silently. This reads the same declarations rather than repeating them, for the same
 * reason.
 *
 * Note the spelling the contract actually uses is `source.document`. `src/auditmanager/
 * documents/models.py:44` separately carries `ROLE_SOURCE_DOCUMENT = "source_document"`,
 * which is the **blob** role in the storage namespace and a different thing.
 */
export function manifestRoles(): ReadonlySet<string> {
  const path = join(REPO_ROOT, 'contracts', 'analysis', 'v1', 'stage-registry.json');
  const registry = readJson<StageRegistry>(path);
  const roles = new Set<string>();
  for (const stage of registry.stages ?? registry.registry ?? []) {
    for (const input of stage.required_inputs ?? []) roles.add(input.role);
    for (const output of stage.produced_outputs ?? []) roles.add(output.role);
  }
  return roles;
}

interface BetaSourcePolicy {
  readonly items: readonly { readonly id: string; readonly sources: readonly string[] }[];
  readonly sources: Readonly<Record<string, unknown>>;
}

interface BetaScopeGroup {
  readonly id: string;
  readonly items: readonly string[];
}

/** The machine labels printed by the frozen AR beta preview, read from its policy. */
export function betaPolicyIdentifiers(): ReadonlySet<string> {
  const canonical = join(REPO_ROOT, 'src/auditmanager/analysis/profiles/ar_v3/norm_map/beta_sources.json');
  const mirror = join(REPO_ROOT, 'web/src/widgets/ar-v3-beta-status/ui/beta_sources.json');
  expect(readText(mirror), 'the rendered beta source policy mirrors the canonical policy').toBe(readText(canonical));
  const policy = readJson<BetaSourcePolicy>(canonical);
  const groups = readJson<readonly BetaScopeGroup[]>(
    join(REPO_ROOT, 'web/src/widgets/ar-v3-beta-status/ui/scope_groups.json'),
  );
  const topics = new Set(policy.items.map((item) => item.id));
  const sources = new Set(Object.keys(policy.sources));
  expect(groups.flatMap((group) => group.items).sort(), 'the preview groups cover the policy once')
    .toEqual([...topics].sort());
  expect(policy.items.flatMap((item) => item.sources).every((source) => sources.has(source)),
    'every displayed source is in the canonical policy').toBe(true);
  return new Set([...topics, ...sources, ...groups.map((group) => group.id)]);
}

/** Everything a contract or a frozen seam document puts on a screen. */
export function contractVocabulary(): ReadonlySet<string> {
  return new Set([...contractEnums(), ...csvColumnNames(), ...manifestRoles(), ...betaPolicyIdentifiers()]);
}

/**
 * The residue: Latin that no contract in this repository defines.
 *
 * Each entry says why the derivation cannot reach it. An entry whose reason is only "it is
 * on a screen" is an offence being laundered, and the next reader should delete it.
 */
const NOT_DERIVABLE: readonly { readonly word: string; readonly why: string }[] = [
  {
    word: 'AuditManager',
    why:
      'The product name, rendered in the application bar by `_app/app-frame.tsx`. No contract ' +
      'declares it -- a product name is not a vocabulary a schema can publish -- and it is not ' +
      'translated for the same reason a trademark is not: it identifies the thing rather than ' +
      'describing it. It became visible to this guard only when `AppFrame` was added to the ' +
      'screen list; before that the entire chrome was outside the ratchet, which is how a ' +
      'judge could mutate a theme label to English and see green.',
  },
  {
    word: 'proxy',
    why:
      'A provider mode the application supports and the contract does not publish: ' +
      '`openapi.json` `ProviderMode` is `live`/`recorded` only, and `W30-LISTS` §1.1 ' +
      'records `_DECLARED_MODES` as "the only extra is proxy". The owner stand at ' +
      '127.0.0.1:31500 runs in it. Derivable the day the contract publishes it.',
  },
  // ------------------------------------------------------------------------------------
  // Names of formats, standards and algorithms.
  //
  // `W30-LISTS` §1.4 ruled a set out of the hand-maintained-subset class when "no contract
  // or catalog in this repository defines them, and no authority here can grow" -- that was
  // AWS's error vocabulary. These are the same shape: the names of things standardised
  // outside this programme. Nothing in `contracts/` defines what SHA-256 is called, and a
  // guard that pinned them to a copy of themselves would prove nothing. They are also not
  // translated in Russian technical writing, which is why they are permitted rather than
  // reported.
  // ------------------------------------------------------------------------------------
  { word: 'PDF', why: 'The document format, and the only one this application accepts. A proper noun in Russian too ("PDF-документ"). `application/pdf` is matched separately as a media type.' },
  { word: 'CSV', why: 'The export format. RFC 4180 names it, no contract here does, and Russian technical writing does not translate it.' },
  { word: 'Excel', why: 'The spreadsheet application the run\'s workbook is made for (`exportRunXlsx`, «Скачать Excel» in `W57-PLAN.md` section B3.7). A product name; Russian writing does not translate it, and no contract here defines the word.' },
  { word: 'ZIP', why: 'The archive format of the portal bundle, the only upload this application accepts (`W55B-INGEST-01`). A proper noun in Russian technical writing ("ZIP-архив"); the container format is fixed by PKWARE\'s APPNOTE, and no contract here defines the word. `application/zip` is matched separately as a media type, and a member\'s name such as `_blocks.json` as a filename.' },
  { word: 'API', why: 'The name of the seam the screens talk to. Universal in Russian technical writing; nothing in `contracts/` defines the word itself.' },
  { word: 'RFC', why: 'The IETF document series, cited by number beside the CSV escaping rule. A citation, not a label.' },
  { word: 'SHA', why: 'The digest algorithm family, shown as SHA-256 beside a version. FIPS 180-4 fixes the spelling; no contract here does.' },
  { word: 'UTF', why: 'The character encoding family, shown as utf-8 in the export description. The IANA charset registry fixes the spelling; matched case-insensitively for that one entry alone.' },
  { word: 'UTC', why: 'The time-scale designator printed after a timestamp. Where a timestamp precedes it the ISO pattern already consumes it; this entry covers the case where it stands alone.' },
  // ------------------------------------------------------------------------------------
  // `EXEC-HTTP-01`: names of protocols, products and files in «Подключения». None is English
  // prose, none is a contract value (the contract publishes `http_api`, `vpn`, `ssh_tunnel`
  // in lower case with underscores, and those are translated, so they are not permitted bare),
  // and none is translated in Russian technical writing.
  // ------------------------------------------------------------------------------------
  { word: 'IP', why: 'The abbreviation in «IP стенда не допущен», the probe outcome the owner worded: the address of the stand that a gateway\'s allow-list refuses. Universal in Russian technical writing; no contract here defines the word.' },
  { word: 'HTTP', why: 'The protocol name in «HTTP API», the kind of connection that calls a model at a web address. A standard name (RFC 9110) that Russian technical writing does not translate; no contract here defines the word.' },
  { word: 'OpenRouter', why: 'The name of the model gateway service a connection can be pointed at, in the label of the request format. A product name, not translated for the reason AuditManager is not; no contract here defines it.' },
  { word: 'VPN', why: 'The abbreviation in «Через VPN», one of the three ways a connection reaches its address. Universal in Russian technical writing; the contract publishes the transport as `vpn`, which is translated and so is not permitted as visible text.' },
  { word: 'SSH', why: 'The protocol name in «Команда по SSH», «Через SSH-туннель», «Узел SSH» and «Ключ SSH». A standard name (RFC 4251) that Russian technical writing does not translate; no contract here defines the word.' },
  { word: 'Claude Code', why: 'The product name of the command-line tool a remote machine runs, in «Claude Code без интерфейса» and «Сеанс Claude Code». A product name, not translated; listed before `Claude` so the pair is consumed whole.' },
  { word: 'Claude', why: 'The model family name in «Формат сообщений Claude». A product name, not translated for the reason AuditManager is not; no contract here defines it.' },
  { word: 'authorized_keys', why: 'The file OpenSSH reads on the remote machine, named where the generated public key is shown so the person knows where to add it. The spelling is fixed by OpenSSH; no contract here defines it, and it is not a filename the extension pattern matches.' },
  {
    word: 'MiB',
    why:
      'A unit symbol. IEC 80000-13 fixes the spelling and it is not localised; the ' +
      'upload envelope states a size in it. `MB`, `KiB`, `GiB` are matched by the unit ' +
      'pattern for the same reason; this entry covers a bare one.',
  },
];

// ===================================================================== the extraction

/**
 * Patterns for text that is legitimately Latin because of what it *is*, not what it says.
 *
 * Each is matched against the rendered text and removed before any word is judged. A
 * pattern is here only where the thing it matches has an authority outside this file --
 * an identifier catalog, an RFC, a checksum algorithm -- so that "what shape is an
 * identifier" is not a question this guard answers by taste.
 */
const MACHINE_SHAPES: readonly { readonly name: string; readonly pattern: RegExp }[] = [
  {
    name: 'prefixed ULID identifiers',
    // `contracts/domain/v1/identifiers.json` fixes the form: a lowercase prefix, an
    // underscore, and 26 Crockford base32 characters. Matched by shape rather than by a
    // list of prefixes, because the catalog gains prefixes and this file must not have to.
    pattern: /\b[a-z][a-z0-9]{1,7}_[0-9A-HJKMNP-TV-Z]{26}\b/g,
  },
  {
    name: 'bare ULIDs and correlation ids',
    pattern: /\b[0-9A-HJKMNP-TV-Z]{26}\b|\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/g,
  },
  { name: 'hex digests', pattern: /\b[0-9a-f]{32,128}\b/g },
  // `W55B-WEB-BLOCKS`. The text-line index's block id, which «Строки текста» prints as the
  // block's identifier: `openapi.json` pins `BlockGeometry.block_id` to `^b_[0-9]{6}$`.
  { name: 'text-line block ids', pattern: /\bb_[0-9]{6}\b/g },
  // RFC 6838. `application/pdf` is the only one this application names, but the shape is
  // the authority, not the value.
  { name: 'media types', pattern: /\b[a-z]+\/[a-z0-9.+-]+\b/g },
  { name: 'URLs and object urls', pattern: /\b(?:https?|blob|data):[^\s"'<>]+/g },
  // A filename is the server's or the user's, never this application's prose. The
  // extension is matched with it, so `.pdf` and `.csv` need no entry of their own. `.md` and
  // `.html` are the suffixes of a portal bundle's members (`_results.md`, `_results.html`),
  // which the upload panel names so a reviewer can tell the files apart (`W55B-INGEST-01`).
  { name: 'filenames', pattern: /\S*[^\s.]\.(?:pdf|csv|json|png|txt|zip|md|html)\b/gi },
  { name: 'absolute paths', pattern: /(?:^|[\s(])\/[A-Za-z0-9._~\-/[\]]*/g },
  // ISO 8601, which is how every timestamp in the contract is written.
  // ISO 8601, and the `UTC` designator the screens print after the local rendering of it.
  // The designator is matched only where a timestamp precedes it, so a bare `UTC` in a
  // sentence is still an offence.
  { name: 'ISO 8601 timestamps', pattern: /\b\d{4}-\d{2}-\d{2}[T ][\d:.]+(?:Z|\s*UTC)?\b/g },
  {
    // `PC-01` is the product; `P02` is the PROGRAMME PHASE, and the evidence viewer names
    // it to the reviewer -- "Шлюз свидетельств P02 делает такое невозможным". Both are
    // designations this programme fixes in `docs/program/`, neither is English, and the
    // shape is the authority rather than a list of them. Narrow on purpose: a bare `P`
    // and a bare `PC` are still offences.
    name: 'the product and phase designations',
    pattern: /\b(?:PC-\d{2}|P\d{2})\b/g,
  },
  {
    name: 'analysis profile version designation',
    // The AR profile is named v3 in its frozen profile and on the beta screen. A bare
    // English `version` remains an offence; only the digit-bound designation is masked.
    pattern: /\bv[1-9][0-9]*\b/g,
  },
  {
    name: 'units attached to a number',
    // A unit is Latin because the unit is Latin. Bound to a preceding number so that a
    // bare `MB` in a sentence is still an offence.
    // `m` and `s` are here because the run screen renders a duration as "4 m 0 s". They
    // are bound to a preceding number like every other unit, so a bare `s` is an offence.
    pattern: /\b\d+(?:[.,]\d+)?\s*(?:[KMGT]i?B|ms|[smhd]|px|rem|%)\b/g,
  },
];

/** Entities `renderToStaticMarkup` writes, decoded so `&amp;` is not read as `amp`. */
function decodeEntities(text: string): string {
  return text
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#x27;/g, "'")
    .replace(/&#(\d+);/g, (_, d: string) => String.fromCharCode(Number(d)))
    .replace(/&amp;/g, '&');
}

/**
 * Attributes a browser shows to a human. Everything else in the markup is machinery.
 *
 * `value` is deliberately absent: on this application's inputs it carries what the *test*
 * typed, not what the application wrote, so including it would make the guard judge its
 * own fixtures.
 */
const VISIBLE_ATTRIBUTES = ['placeholder', 'title', 'alt', 'aria-label'] as const;

/**
 * Everything a reviewer could read off this markup: the text nodes, plus the handful of
 * attributes that are rendered as text.
 *
 * `<style>`, `<script>` and `<code>` are handled by the caller's masking rather than
 * excluded here -- a `<code>` element on these screens carries an identifier or a catalog
 * code, and both are matched as machine shapes, so excluding the element would hide a
 * sentence that was merely put in the wrong tag.
 */
export function visibleText(markup: string): string[] {
  const out: string[] = [];
  const withoutStyle = markup.replace(/<style\b[^>]*>[\s\S]*?<\/style>/g, '');
  for (const match of withoutStyle.matchAll(/>([^<>]+)</g)) {
    const text = decodeEntities(match[1] ?? '').trim();
    if (text.length > 0) out.push(text);
  }
  for (const attribute of VISIBLE_ATTRIBUTES) {
    const pattern = new RegExp(`\\s${attribute}="([^"]*)"`, 'g');
    for (const match of withoutStyle.matchAll(pattern)) {
      const text = decodeEntities(match[1] ?? '').trim();
      if (text.length > 0) out.push(text);
    }
  }
  return out;
}

/**
 * The Latin-script words in one visible string that nothing permits.
 *
 * Masking order matters and is stated because it is the whole allowlist design: the
 * machine *shapes* go first, then the contract's *whole values*, and only what survives
 * both is split into words. `needs_manual_review` is removed as one contract value, so
 * this guard never learns to allow the bare word `review` -- which is the difference
 * between deriving an allowlist and writing a bag of words that stops catching things.
 */
export function unexplainedLatin(text: string, vocabulary: ReadonlySet<string>): string[] {
  let residue = text;
  for (const { pattern } of MACHINE_SHAPES) residue = residue.replace(pattern, ' ');

  // Longest first, so `needs_manual_review` is consumed before `review` could be.
  //
  // AND ON A WORD BOUNDARY, which `split`/`join` did not do. `accept` is a permitted
  // `DecisionEventType`, so a screen rendering `accepted` had its permitted prefix eaten and
  // reported the residue `ed` -- a word no reviewer can see, in a report meant to name what
  // they can. The offence was found; its NAME was wrong, which is worse than a miss because
  // it sends the reader looking for a string that is not there.
  //
  // It is the same defect the wave-33 judges found in `test_pc01_journey_conformance.py`,
  // where `Run` matched inside `RunPage` and let a manifest assert a title no screen renders.
  // **Substring containment deceiving a guard is now this programme's third instance**, so it
  // is fixed here rather than noted.
  const values = [...vocabulary].sort((a, b) => b.length - a.length);
  for (const value of values) {
    const escaped = value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    // A contract value is `[a-z_]`, so a Latin letter on either side means this is a longer
    // word that merely starts or ends with one -- `accepted`, not `accept`.
    residue = residue.replace(new RegExp(`(?<![A-Za-z])${escaped}(?![A-Za-z])`, 'g'), ' ');
  }
  // Case-insensitively, because `utf-8` is written lowercase and `UTF` is the registry's
  // spelling. That is a deliberate widening and it is narrow: it applies only to this
  // short, closed list of external standard names, never to the contract vocabulary --
  // where `Recorded:` as a heading must stay an offence while `recorded` as a run's
  // provider mode does not.
  for (const { word } of NOT_DERIVABLE) {
    residue = residue.replace(new RegExp(word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi'), ' ');
  }

  const words = residue.match(/[A-Za-z][A-Za-z'’]*/g) ?? [];
  return [...new Set(words)];
}

// ===================================================================== the screens

type Client = ReturnType<typeof newClient>;

// --------------------------------------------------------- Cyrillic-only server data

const ULID = '01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const PROJECT_UID = `prj_${ULID}`;
const DOCUMENT_UID = `doc_${ULID}`;
const VERSION_UID = `ver_${ULID}`;
const RUN_ID = `run_${ULID}`;

/** The same four identities, keyed by the names `web/src/app`'s directories give them. */
const IDENTITIES = {
  projectUid: PROJECT_UID,
  documentUid: DOCUMENT_UID,
  versionUid: VERSION_UID,
  runId: RUN_ID,
};
const FINDING_UID = `fnd_${ULID}`;
const OBSERVATION_ID = `fobs_${ULID}`;
const SHA = '6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f';

const project = (): Project => ({
  project_uid: PROJECT_UID,
  name: 'Договор поставки',
  created_at: '2026-09-10T08:00:00.000Z',
  document_count: 2,
});

const version = (over: Partial<DocumentVersion> = {}): DocumentVersion => ({
  version_uid: VERSION_UID,
  document_uid: DOCUMENT_UID,
  project_uid: PROJECT_UID,
  version_ordinal: 1,
  media_type: 'application/pdf',
  byte_size: 58978,
  sha256: SHA,
  page_count: 8,
  published_at: '2026-09-18T06:55:52.642022Z',
  input_manifest: [
    // The contract's spelling, read from `stage-registry.json` -- not the storage
    // namespace's `source_document`, which is a different role.
    { role: 'source.document', media_type: 'application/pdf', sha256: SHA, size_bytes: 58978 },
  ],
  display_title: 'Годовой отчёт',
  source_filename: 'отчёт.pdf',
  ...over,
});

/**
 * `W59-SECTION-UI-01`. A version's stage-and-section classification and its review, with
 * Cyrillic evidence: the patterns and keywords are the server's own words, so a Latin one
 * left on a screen would be chrome the application wrote.
 */
const classification = (
  over: Partial<VersionClassificationRecord> = {},
): VersionClassificationRecord => ({
  version_uid: VERSION_UID,
  project_stage: 'P',
  section_code: 'AR',
  confirmed_at: '2026-10-20T08:00:00Z',
  confirmed_by_user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
  revision: 1,
  ...over,
});

/**
 * `CLASSIFICATION-CORRECTION-01`. A classification's history: the original confirmation and two
 * corrections with the experts' own reasons (Cyrillic, one with a line break), and the Russian
 * sentence of each refusal the correction form can show.
 */
const CLASSIFICATION_HISTORY: VersionClassificationRevision[] = [
  { revision: 1, project_stage: 'P', section_code: 'AR', actor_user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', at: '2026-10-20T08:00:00Z', reason: null },
  { revision: 2, project_stage: 'R', section_code: 'KJ', actor_user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8G', at: '2026-10-21T09:30:00Z', reason: 'Раздел определён по штампу листа неверно,\nэто конструкции железобетонные.' },
];
const CORRECTION_DETAILS = {
  stale: CORRECTION_STALE_DETAIL,
  not_classified: CORRECTION_NOT_CLASSIFIED_DETAIL,
  unchanged: CORRECTION_UNCHANGED_DETAIL,
  reason: CORRECTION_REASON_DETAIL,
  not_permitted: CORRECTION_NOT_PERMITTED_DETAIL,
} as const;

/**
 * `W60-OPT-MATCH-01`. One answer of «Спецификация и цены», every value Cyrillic, an identifier
 * or a contract enum. `ready` carries a row of each status, two currencies, every exclusion,
 * a skipped line and a second page; the other states carry the facts read before they stop.
 */
const SPEC_POSITION = 'prp_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const specificationAnswer = (over: Partial<SpecificationPrices> = {}): SpecificationPrices => ({
  project_uid: PROJECT_UID,
  document_uid: DOCUMENT_UID,
  version_uid: VERSION_UID,
  version_ordinal: 2,
  page_count: 30,
  state: 'ready',
  project_stage: 'R',
  section_code: 'AR',
  price_list: {
    price_list_id: 'prl_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
    revision_number: 3,
    source_filename: 'Прайс проекта',
    uploaded_at: '2026-10-20T08:00:00Z',
    default_currency: 'RUB',
    position_count: 120,
  },
  run_id: RUN_ID,
  text_layer_sha256: SHA,
  extraction: {
    algorithm: 'specification-text-v1',
    table_count: 2,
    row_count: 120,
    skipped_count: 1,
    skipped_by_reason: {
      table_header_ambiguous: 0, text_before_first_row: 0, continuation_limit: 0,
      anchor_ambiguous: 0, position_missing: 1, name_missing: 0, column_numbering: 0,
      rows_over_limit: 0,
    },
    skipped: [{ page_number: 14, line: 298, reason: 'position_missing', excerpt: 'План на отметке 2 Металлический щит 12' }],
    tables: [],
  },
  matching: {
    algorithm: 'price-match-v1',
    counts: { matched: 3, ambiguous: 1, unmatched: 116 },
    totals: [
      { currency: 'EUR', amount: '2550', row_count: 1 },
      { currency: 'RUB', amount: '502006.5', row_count: 2 },
    ],
    excluded: {
      no_position: 110, unit_mismatch: 4, row_unit_missing: 2, ambiguous: 1, quantity_not_numeric: 1,
    },
  },
  rows: {
    offset: SPECIFICATION_ROW_LIMIT,
    limit: SPECIFICATION_ROW_LIMIT,
    total: 120,
    next_offset: SPECIFICATION_ROW_LIMIT * 2,
    items: [
      {
        row_id: `sr-${'a'.repeat(32)}`, page_number: 14, sheet_label: '10', line_start: 297, line_end: 298,
        table_ordinal: 1, group: 'Изделия', position: '1', name: 'Металлический щит МЩ-1',
        unit_text: 'шт.', unit: 'шт', quantity_text: '12', quantity: '12', quantity_issue: null,
        mass_text: '45,5', note: 'по месту', status: 'matched', reason: null, basis: 'name',
        price_position: {
          price_list_position_id: SPEC_POSITION, row_number: 7, code: 'К-1', name: 'Мет. щит МЩ-1',
          mark: 'МЩ-1', unit: 'шт', unit_price: '15000', currency: 'RUB', vendor: 'Завод',
        },
        candidate_position_ids: [SPEC_POSITION], candidate_count: 1, amount: '180000', excluded_reason: null,
      },
      {
        row_id: `sr-${'b'.repeat(32)}`, page_number: 15, sheet_label: null, line_start: 4, line_end: 4,
        table_ordinal: 2, group: null, position: '2', name: 'Лента монтажная',
        unit_text: 'компл.', unit: 'компл', quantity_text: '1 250', quantity: null, quantity_issue: 'ambiguous',
        mass_text: null, note: null, status: 'matched', reason: null, basis: 'mark',
        price_position: {
          price_list_position_id: SPEC_POSITION, row_number: 8, code: null, name: 'Лента',
          mark: null, unit: 'компл', unit_price: '450', currency: 'RUB', vendor: null,
        },
        candidate_position_ids: [SPEC_POSITION], candidate_count: 1, amount: null,
        excluded_reason: 'quantity_not_numeric',
      },
      {
        row_id: `sr-${'c'.repeat(32)}`, page_number: 15, sheet_label: null, line_start: 5, line_end: 5,
        table_ordinal: 2, group: null, position: '3', name: 'Пена монтажная',
        unit_text: 'шт', unit: 'шт', quantity_text: '-', quantity: null, quantity_issue: 'not_numeric',
        mass_text: null, note: null, status: 'ambiguous', reason: 'several_positions', basis: null,
        price_position: null, candidate_position_ids: [SPEC_POSITION, SPEC_POSITION], candidate_count: 2,
        amount: null, excluded_reason: 'ambiguous',
      },
      {
        row_id: `sr-${'d'.repeat(32)}`, page_number: 15, sheet_label: null, line_start: 6, line_end: 6,
        table_ordinal: 2, group: null, position: null, name: 'Профиль направляющий',
        unit_text: 'п. м', unit: 'п.м', quantity_text: '120', quantity: '120', quantity_issue: null,
        mass_text: null, note: null, status: 'unmatched', reason: 'unit_mismatch', basis: null,
        price_position: null, candidate_position_ids: [SPEC_POSITION], candidate_count: 1,
        amount: null, excluded_reason: 'unit_mismatch',
      },
    ],
  },
  ...over,
});
/**
 * `NORM-REFS-RUN-01`. One answer of «Нормативные ссылки», every value Cyrillic, an identifier or
 * a contract enum: a citation of each of the five outcomes (one of them kept at ten of twelve
 * occurrences), a page with no text layer, and a corpus document whose designation is not read.
 */
const NORM_DOC_A = 'ndoc_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const NORM_DOC_B = 'ndoc_01J9ZQ8K7NHVXW3T2R5M6P4Q8G';
const normAnchor = (page: number) => ({ page_number: page, char_start: 10, char_end: 26, quote: 'СП 54.13330.2011' });
const normReferencesAnswer = (over: Partial<RunNormReferences> = {}): RunNormReferences => ({
  run_id: RUN_ID,
  version_uid: VERSION_UID,
  state: 'ready',
  page_count: 12,
  norms_snapshot_id: 'ns_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
  text_layer_sha256: SHA,
  snapshot_document_count: 674,
  counts: { in_corpus: 1, newer_edition: 1, older_edition_only: 1, not_in_corpus: 1, not_recognised: 1 },
  occurrence_count: 15,
  unread_pages: [2, 5],
  items: [
    {
      cited: 'СП 54.13330.2022', outcome: 'in_corpus', occurrence_count: 1, anchors: [normAnchor(3)],
      matched_norm_document_id: NORM_DOC_A, matched_designation: 'СП 54.13330.2022', matched_title: 'Свод правил. Здания жилые',
    },
    {
      cited: 'СП 54.13330.2011', outcome: 'newer_edition', occurrence_count: 12,
      anchors: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(normAnchor),
      matched_norm_document_id: NORM_DOC_B, matched_designation: 'СП 54.13330.2024',
    },
    {
      cited: 'ГОСТ 21.101-2021', outcome: 'older_edition_only', occurrence_count: 1, anchors: [normAnchor(4)],
      matched_norm_document_id: NORM_DOC_A, matched_designation: 'ГОСТ 21.101-2020',
    },
    { cited: 'ГОСТ Р 99999-2020', outcome: 'not_in_corpus', occurrence_count: 1, anchors: [normAnchor(5)] },
    { cited: 'СП 54.13330', outcome: 'not_recognised', occurrence_count: 1, anchors: [normAnchor(6)] },
  ],
  unrecognised: [{ norm_document_id: NORM_DOC_B, slug: 'МДС_12-24_2006', designation: 'МДС 12-24.2006', title: 'Устройство обычных' }],
  ...over,
});
const SPECIFICATION_STOPPED = {
  matching: null, rows: null, extraction: null, run_id: null, text_layer_sha256: null,
} as const;
const specificationSets = (client: Client): void => {
  client.setQueryData(KEYS.documents, {
    items: [version({ display_title: 'Архитектурные решения', classification: classification({ project_stage: 'R' }) })],
    page: { next_cursor: null },
  });
};

const sectionReview = (over: Partial<SectionReview> = {}): SectionReview => ({
  version_uid: VERSION_UID,
  classification: null,
  revisions: [],
  recognised_text_consulted: true,
  options: PROJECT_SECTIONS.map((section) => ({
    section_code: section.code,
    name: section.name,
    // All fifteen sections have a registered profile, including the draft ПБ profile.
    executable: true,
    suggestion:
      section.code === 'AR'
        ? { score: 7, filename_patterns: ['АР'], text_keywords: ['поэтажный план'], name_in_text: true }
        : section.code === 'KJ'
          ? { score: 2, filename_patterns: ['КЖ'], text_keywords: [], name_in_text: false }
          : null,
  })),
  ...over,
});

/*
 * ALL NINE stage ids, and each with a DIFFERENT stage status.
 *
 * It was four, all `succeeded`, and that was five `StageId` members and three
 * `StageStatus` members this guard never rendered. `W41-BLIND` did not find that by
 * reading the list -- a list is exactly what nobody re-reads. The coverage assertion at
 * the foot of this file names every contract member no screen puts on a badge, and it is
 * what this seed answers to.
 *
 * Hand-written on purpose. Deriving the seeds from the contract would make a tenth stage
 * cover itself, silently, with whatever default a builder chose -- which is the shape
 * this task exists to stop. A new member must redden, so that somebody decides what the
 * screen does with it.
 */
const STAGES: readonly { readonly id: StageId; readonly status: StageStatus }[] = [
  { id: 'source_preparation', status: 'succeeded' },
  { id: 'page_geometry_extraction', status: 'succeeded' },
  { id: 'document_context_build', status: 'partial' },
  { id: 'text_analysis', status: 'succeeded' },
  { id: 'block_analysis', status: 'failed' },
  { id: 'finding_merge', status: 'skipped' },
  { id: 'finding_review', status: 'succeeded' },
  { id: 'finding_correction', status: 'skipped' },
  { id: 'norm_verification', status: 'partial' },
];

const run = (over: Partial<RunStatus> = {}): RunStatus => ({
  run_id: RUN_ID,
  project_uid: PROJECT_UID,
  version_uid: VERSION_UID,
  state: 'published',
  provider_mode: 'recorded',
  created_at: '2026-09-10T08:00:00.000Z',
  terminal_at: '2026-09-10T08:04:00.000Z',
  terminal_reason: null,
  interrupted_reason: null,
  stages: STAGES.map(({ id, status }) => ({
    stage_id: id,
    status,
    started_at: '2026-09-10T08:00:00.000Z',
    finished_at: '2026-09-10T08:01:00.000Z',
    error_code: status === 'failed' ? ('analysis_failed' as ErrorCode) : null,
    stage_version: '1.0.0',
  })),
  degradation_set: [],
  published_finding_count: 3,
  diagnostic_observation_count: 1,
  analysis_profile_id: `ap_${ULID}`,
  prompt_bundle_id: `pb_${ULID}`,
  model_call_count: 4,
  cost_micros: 1234,
  cost_basis: 'measured',
  // `EXEC-PAR-WEB-01`: the executor the run froze, in Cyrillic like every server value here. Every
  // run screen in every state names it, and the `queued-run` state says it is waiting for it.
  executor: {
    connection_id: EXECUTOR_READY.connection.connection_id,
    display_name: 'Основной шлюз',
    pin_id: 'модель-основная',
  },
  ...over,
});

const finding = (over: Partial<Finding> = {}): Finding => ({
  finding_uid: FINDING_UID,
  project_uid: PROJECT_UID,
  version_uid: VERSION_UID,
  run_id: RUN_ID,
  category: 'internal_contradiction',
  current_verdict: 'pending',
  latest_decision_id: null,
  decision_recorded_at: null,
  observation: {
    finding_observation_id: OBSERVATION_ID,
    run_id: RUN_ID,
    category: 'internal_contradiction',
    // Cyrillic on purpose: a finding's words are the analysis's, not this programme's.
    finding_text: 'Срок поставки указан как 30 дней в §4 и как 45 дней в §9.',
    recommendation_text: 'Согласуйте два срока поставки до подписания.',
    evidence: [
      {
        evidence_ordinal: 1,
        page_number: 7,
        quote: 'Срок поставки составляет 30 дней.',
        char_start: 1200,
        char_end: 1232,
        block_id: 'b_000042',
      },
    ],
    provenance: {
      analysis_profile_id: `ap_${ULID}`,
      prompt_bundle_id: `pb_${ULID}`,
      stage_id: 'text_analysis',
      provider_mode: 'recorded',
      model_call_id: `mc_${ULID}`,
      model_identity: 'зафиксированная-модель',
    },
  },
  ...over,
});

const detail = (): FindingDetail => ({
  ...finding(),
  decision_event_count: 1,
  latest_comment: 'Замечание проверяющего.',
});

const decision = (over: Partial<DecisionEvent> = {}): DecisionEvent => ({
  decision_id: `dec_${ULID}`,
  finding_uid: FINDING_UID,
  finding_observation_id: OBSERVATION_ID,
  event_type: 'accept',
  verdict: 'accepted',
  comment: 'Подтверждено.',
  author_label: 'проверяющий',
  recorded_at: '2026-09-10T09:00:00.000Z',
  ...over,
});

/*
 * ONE FINDING PER `FindingCategory`, AND ONE PER `Verdict`.
 *
 * The list used to hold a single `internal_contradiction` finding whose verdict was
 * `pending`, so `explicit_placeholder`, `rejected` and `needs_manual_review` never
 * reached a badge -- three contract members with a Russian label each, rendered by no
 * state in this matrix. The coverage assertion at the foot of this file is what now says
 * so out loud, and this is its answer.
 *
 * Hand-written for the reason `STAGES` is: a fifth verdict must redden rather than seed
 * itself.
 */
const FINDINGS: readonly Finding[] = [
  finding({ current_verdict: 'pending' }),
  finding({
    finding_uid: `${FINDING_UID.slice(0, -1)}C`,
    category: 'internal_contradiction',
    current_verdict: 'accepted',
    latest_decision_id: `dec_${ULID}`,
    decision_recorded_at: '2026-09-10T09:00:00.000Z',
  }),
  finding({
    finding_uid: `${FINDING_UID.slice(0, -1)}D`,
    category: 'explicit_placeholder',
    current_verdict: 'rejected',
    latest_decision_id: `dec_${ULID}`,
    decision_recorded_at: '2026-09-10T09:00:00.000Z',
  }),
  finding({
    finding_uid: `${FINDING_UID.slice(0, -1)}E`,
    category: 'explicit_placeholder',
    current_verdict: 'needs_manual_review',
    latest_decision_id: `dec_${ULID}`,
    decision_recorded_at: '2026-09-10T09:00:00.000Z',
  }),
  finding({ finding_uid: `${FINDING_UID.slice(0, -1)}F`, category: 'dimensions' }),
  finding({ finding_uid: `${FINDING_UID.slice(0, -1)}G`, category: 'layout' }),
  finding({ finding_uid: `${FINDING_UID.slice(0, -1)}H`, category: 'facade' }),
  finding({ finding_uid: `${FINDING_UID.slice(0, -1)}J`, category: 'roof' }),
  finding({ finding_uid: `${FINDING_UID.slice(0, -1)}K`, category: 'documentation' }),
  // `W59-SECTION-UI-01`: the five categories `W57A-SEAL-01B` added to the contract were
  // rendered by no state, and the coverage case below was red on the lane's base for it.
  finding({ finding_uid: `${FINDING_UID.slice(0, -1)}M`, category: 'fire_safety' }),
  finding({ finding_uid: `${FINDING_UID.slice(0, -1)}N`, category: 'evacuation' }),
  finding({ finding_uid: `${FINDING_UID.slice(0, -1)}P`, category: 'accessibility' }),
  finding({ finding_uid: `${FINDING_UID.slice(0, -1)}Q`, category: 'insulation' }),
  finding({ finding_uid: `${FINDING_UID.slice(0, -1)}R`, category: 'sound' }),
];

/*
 * ONE ACCEPT PER `Severity` (`WEB-HOOKS-PER-FINDING-01`).
 *
 * `WEB-REVIEW-FOLLOWUPS-01` made the decision history and the knowledge base print the severity
 * the expert decided beside the verdict, as «важность» and the badge's Russian label. This
 * guard rendered both screens with events that carried none, so the new wording was pinned by
 * that slice's own test and not here -- and, worse, `Severity` was not among the translated
 * schemas, so a raw `critical` printed in its place would have been read as contract
 * vocabulary and permitted. The events are hand-written, one per member, for the reason
 * `DECISIONS` is: a sixth severity must redden the coverage case below, not seed itself. The
 * first four events above carry none, so the legacy line of both screens is still rendered.
 * The knowledge base inherits them through the journal rows built from `DECISIONS`.
 */
const SEVERITY_DECISIONS: readonly DecisionEvent[] = [
  decision({ decision_id: `dec_${ULID}E`, severity: 'critical', comment: 'Принято как критичное.' }),
  decision({ decision_id: `dec_${ULID}F`, severity: 'economic', comment: 'Принято как экономическое.' }),
  decision({ decision_id: `dec_${ULID}G`, severity: 'operational', comment: 'Принято как эксплуатационное.' }),
  decision({ decision_id: `dec_${ULID}H`, severity: 'recommendation', comment: 'Принято как рекомендация.' }),
  decision({ decision_id: `dec_${ULID}J`, severity: 'check_adjacent', comment: 'Принято как проверка смежного.' }),
];

/** One decision event per `Verdict`, for the same reason the findings are four. */
const DECISIONS: readonly DecisionEvent[] = [
  decision(),
  decision({ decision_id: `dec_${ULID}B`, event_type: 'reject', verdict: 'rejected', comment: 'Отклонено.' }),
  decision({
    decision_id: `dec_${ULID}C`,
    event_type: 'comment',
    verdict: 'needs_manual_review',
    comment: 'Требует ручной проверки.',
  }),
  decision({ decision_id: `dec_${ULID}D`, event_type: 'revoke', verdict: 'pending', comment: 'Решение отозвано.' }),
  ...SEVERITY_DECISIONS,
];

/**
 * One journal record. Cyrillic everywhere the application did not author the string, and
 * `decision_event_count: 2` on purpose: the singular and the plural of that sentence are
 * different strings, and the plural is the one a knowledge base is read for.
 */
const record = (over: Partial<DecisionRecord> = {}): DecisionRecord => ({
  ...decision(),
  project_uid: PROJECT_UID,
  run_id: RUN_ID,
  category: 'internal_contradiction',
  finding_text: 'Срок поставки указан как 30 дней в §4 и как 45 дней в §9.',
  current_verdict: 'accepted',
  decision_event_count: 2,
  ...over,
});

function apiError(status: number, code: ErrorCode): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.8.0',
    error_code: code,
    message: 'Сообщение об отказе.',
    correlation_id: '0f0e9d8c-7b6a-4948-b726-150413021100',
    retryable: false,
  };
  return new ApiError(status, envelope, '0f0e9d8c-7b6a-4948-b726-150413021100');
}

/** A norms refusal with the one classifier the seal registered for it (`W55A-WEB-NORMS`). */
function normsRefusal(code: ErrorCode, details: Readonly<Record<string, string>>): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.8.0',
    error_code: code,
    message: 'Сообщение об отказе.',
    correlation_id: '0f0e9d8c-7b6a-4948-b726-150413021100',
    retryable: false,
    details,
  };
  return new ApiError(422, envelope, '0f0e9d8c-7b6a-4948-b726-150413021100');
}

/** Every `RunState`, at zero. The base every `run_activity.by_state` fixture starts from. */
const ZERO_BY_STATE: readonly RunStateCount[] = RUN_STATE_VALUES.map((state) => ({
  state,
  count: 0,
}));

/**
 * `run_activity` with `spend` REMOVED, not merely unset — `W46-WIRE`.
 *
 * After `W46-SPEND`'s reseal `run_activity.spend` is optional and absent exactly when the
 * deployment has made no provider call. Seeding that shape is the same move `without()`
 * below makes for `RunStatus`: build the object without the key at all, then assert the
 * shape rather than let the compiler infer it — `exactOptionalPropertyTypes` makes an
 * explicit `spend: undefined` a different type from an absent key, and the whole point
 * here is the absent key.
 */
function runActivityWithoutSpend(byState: readonly RunStateCount[] = ZERO_BY_STATE): RunActivity {
  return { by_state: byState } as unknown as RunActivity;
}

/**
 * `getDashboardSummary`'s whole answer, `W46-WIRE`. One project holding documents, all
 * four verdicts represented, one published run with an estimated cost, and one document
 * recorded against `KM` beside the always-present unclassified row — rich enough that the
 * `loaded` state alone reaches most of the four panels' non-empty branches at once.
 */
function dashboardSummary(over: Partial<DashboardSummary> = {}): DashboardSummary {
  return {
    documents_by_project: [{ project_uid: PROJECT_UID, name: 'Проект', document_count: 2 }],
    findings_by_verdict: [
      { verdict: 'pending', count: 3 },
      { verdict: 'accepted', count: 1 },
      { verdict: 'rejected', count: 1 },
      { verdict: 'needs_manual_review', count: 0 },
    ],
    run_activity: {
      by_state: ZERO_BY_STATE.map((row) => (row.state === 'published' ? { ...row, count: 1 } : row)),
      spend: { model_call_count: 1, cost_micros: 34400, cost_basis: 'estimated' },
    },
    section_breakdown: [
      ...PROJECT_SECTIONS.map((section) => ({
        section: section.code,
        document_count: section.code === 'KM' ? 1 : 0,
      })),
      { document_count: 1 },
    ],
    ...over,
  };
}

/**
 * `W59-ANALYSIS-SETTINGS-01`: the registry «Настройки анализа» lists. АР with no profile
 * (`PROD-11-AR-V1-V2-REMOVAL-01`: it is analysed by the six-check group), ПБ as an authored
 * draft, and the other profiles with their status and legacy sources — server data, seeded
 * Cyrillic so that anything Latin left is chrome.
 */
const ANALYSIS_PROFILES: readonly AnalysisProfileListItem[] = PROJECT_STRUCTURE_ORDER.map((code, index) => {
  const digit = (index % 10).toString();
  const section = projectSectionOf(code);
  if (code === 'AR') return { section_code: code, section_name: section.name, profile: null };
  return {
    section_code: code,
    section_name: section.name,
    profile: {
      analysis_profile_id: `ap_01J9ZQ8K7NHVXW3T2R5M6P4Q8${digit}`,
      prompt_bundle_id: `pb_01J9ZQ8K7NHVXW3T2R5M6P4Q8${digit}`,
      profile_version: '1.0.0',
      status: code === 'PS' ? 'reviewed' : 'draft',
      prompt_bundle_sha256: digit.repeat(64),
      content_sha256: 'a'.repeat(63) + digit,
      source: code === 'PB' ? null : {
        repository: 'прежняя-система',
        commit: 'b'.repeat(40),
        files: [{ path: `prompts/disciplines/${code}/role.md`, sha256: 'c'.repeat(64) }],
      },
    },
  };
});

/** `W54-WORKERS-WEB`: one registered worker per sealed state, the first holding a run. */
const WORKERS: readonly ExecutionWorker[] = [
  {
    worker_id: 'wrk_01J9ZQ8K7NHVXW3T2R5M6P4Q8A', state: 'online', intake_enabled: true,
    slots: 1, version: '0.5.0', started_at: '2026-10-09T10:00:00Z',
    heartbeat_at: '2026-10-09T10:05:00Z', current_run_ids: [RUN_ID],
  },
  {
    worker_id: 'wrk_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', state: 'stale', intake_enabled: false,
    slots: 2, version: '0.5.0', started_at: '2026-10-09T09:00:00Z',
    heartbeat_at: '2026-10-09T09:58:00Z', current_run_ids: [],
  },
  {
    worker_id: 'wrk_01J9ZQ8K7NHVXW3T2R5M6P4Q8C', state: 'offline', intake_enabled: true,
    slots: 1, version: '0.4.0', started_at: '2026-10-08T09:00:00Z',
    heartbeat_at: '2026-10-08T12:00:00Z', current_run_ids: [],
  },
];

const KEYS = {
  projects: queryKeys.projects.list(undefined, PROJECT_PAGE_LIMIT),
  project: queryKeys.projects.detail(PROJECT_UID),
  documents: queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT),
  versions: queryKeys.versions.list(DOCUMENT_UID, undefined, VERSION_PAGE_LIMIT),
  version: queryKeys.versions.detail(VERSION_UID),
  // `W59-SECTION-UI-01`: the version screen's stage-and-section panel.
  sectionReview: queryKeys.versions.sectionReview(VERSION_UID),
  content: queryKeys.versions.content(VERSION_UID),
  runs: queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT),
  run: queryKeys.runs.detail(RUN_ID),
  findings: queryKeys.runs.findings(RUN_ID),
  finding: queryKeys.findings.detail(FINDING_UID),
  decisions: queryKeys.findings.decisions(FINDING_UID),
  journal: queryKeys.findings.journal({ limit: JOURNAL_PAGE_LIMIT }),
  executionQueue: queryKeys.execution.queue(),
  executionJournal: queryKeys.execution.journal(),
  // `W54-WORKERS-WEB`: the «Исполнители» screen's first page.
  workers: queryKeys.execution.workers(undefined, WORKER_PAGE_LIMIT),
  // `EXEC-HTTP-01`: the list of «Подключения» and the routes of «Назначения». Each connection's
  // detail is seeded beside them by `seedExecutors`, under keys that depend on the connection.
  executorConnections: queryKeys.execution.connections(),
  executorRoutes: queryKeys.execution.routes(),
  // `W59-ANALYSIS-SETTINGS-01`: «Настройки анализа», the registry's fifteen rows.
  analysisProfiles: queryKeys.analysis.profiles(),
  // `AR-V3-BETA-PACK-STATUS-WEB-01`: whether the reviewed AR v3 pack is installed. A key of
  // `KEYS` is seeded in the loaded state and ERRORED in `failedClient`, so the settings panel and
  // the version's run list are rendered installed, loading (cold) and failed without a case of their own.
  arV3PackStatus: queryKeys.runs.arV3PackStatus(),
  dashboardSummary: queryKeys.dashboard.summary(),
  // The home page's own two reads (`W50-HOME-01`), seeded by `W50-SHELL-FRAME` so the recent
  // list and the administrator's tile render loaded rather than pending in every state.
  recentProjects: queryKeys.projects.list(undefined, RECENT_PROJECT_LIMIT),
  pendingRegistrations: queryKeys.registrations.list({ status: 'pending', limit: 1 }),
  account: queryKeys.account.me(),
  users: queryKeys.users.list({ includeArchived: false, limit: USER_PAGE_LIMIT }),
  user: queryKeys.users.detail('usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F'),
  registrations: queryKeys.registrations.list({ limit: REGISTRATION_PAGE_LIMIT, status: 'pending' }),
  // `W55A-WEB-NORMS`: the «Нормы» screens' reads, under the keys their seeds ask for. The PDF
  // bytes (`norms.content`) are not seeded, so the document view's PDF panel reads pending.
  normSnapshots: queryKeys.norms.snapshots(undefined, NORM_SNAPSHOT_LIMIT),
  normEvents: queryKeys.norms.events(undefined, NORM_EVENT_PAGE_LIMIT),
  normSearch: queryKeys.norms.search(NORM_QUERY, undefined, NORM_SEARCH_PAGE_LIMIT),
  normDocument: queryKeys.norms.document(NORM_DOCUMENT_ID),
  normParagraphs: queryKeys.norms.paragraphs(NORM_DOCUMENT_ID, undefined, NORM_PARAGRAPH_PAGE_LIMIT),
  // `W57B-NORMS-CATALOGUE-XLSX-01`: the catalogue's first page with no filter.
  normCatalogue: queryKeys.norms.catalogue(undefined, undefined, undefined, NORM_CATALOGUE_PAGE_LIMIT),
  // `W61-DISPATCHER-01`: «Диспетчер»'s first page, the home screen's «Мои задачи», and one
  // assignment's history.
  assignments: queryKeys.assignments.list({ limit: ASSIGNMENT_PAGE_LIMIT }),
  myTasks: queryKeys.assignments.list({ mine: true, limit: MY_TASKS_LIMIT }),
  // The history's assignment is the returned one, `C` in `ASSIGNMENTS` below.
  assignment: queryKeys.assignments.detail(`asg_${'01J9ZQ8K7NHVXW3T2R5M6P4Q8'}C`),
} as const;

/**
 * A client holding a full, plausible, Cyrillic answer to every question the screens ask.
 *
 * **`runs.detail` used to need two builders and now needs one.** `W32-SEE` recorded here
 * that the one cache held a `RunStatus` for the run screen and a `{ data: RunStatus }`
 * envelope for `ReviewPage` under the identical key, that seeding one shape rendered the
 * other screen blank, and that it had no licence to repair it. That was `D-57`, and
 * `W37-D57` repaired it: the key carries its value type, `runStatusQueryOptions` is the
 * only query that fills it, and both screens read the model. `KEYS.run` is therefore
 * seeded once, below, and `loadedReviewClient` no longer overwrites it.
 *
 * **Three keys still hold envelopes**, and that is a property of those keys rather than a
 * disagreement about one: `runs.findings`, `findings.detail` and `findings.decisions` are
 * filled by `ReviewPage`'s own `useQuery`s with the generated `queryFn` and read back as
 * `.data`, by that screen and by nothing else. One writer, one reader, one shape. They
 * are the reason `loadedReviewClient` still exists.
 */
function loadedClient(runOverrides: Partial<RunStatus> = {}): Client {
  const client = newClient();
  const page = { next_cursor: null } as { next_cursor: null };
  client.setQueryData(KEYS.projects, { items: [project()], page });
  client.setQueryData(KEYS.project, project());
  client.setQueryData(KEYS.documents, { items: [version()], page });
  client.setQueryData(KEYS.versions, { items: [version()], page });
  client.setQueryData(KEYS.version, version());
  // Unconfirmed, so the expert's seed draws the form and the reader's seed its sentence.
  client.setQueryData(KEYS.sectionReview, sectionReview());
  client.setQueryData(KEYS.runs, { items: [run(runOverrides)], page });
  client.setQueryData(KEYS.run, run(runOverrides));
  client.setQueryData(KEYS.findings, { items: FINDINGS, page });
  client.setQueryData(KEYS.finding, detail());
  client.setQueryData(KEYS.decisions, { items: DECISIONS, page });
  /*
   * TWO records, and the second one is not decoration.
   *
   * `W38-KB` put an English string in the knowledge base's SINGULAR branch -- "одно решение
   * по находке" against "решений по находке: N" -- and this guard stayed GREEN, because the
   * one seeded record carried `decision_event_count: 2` and the singular arm was never
   * rendered. The mutation was sound; the coverage was not. Same shape as the empty-list
   * branch `W32-SEE` found and the four run states a wave-33 judge found: **a mutation that
   * reddens nothing is a coverage report, not a clean bill.**
   *
   * So one record per arm of that sentence. Both are rendered by one static pass, and an
   * English word in either is now an offence.
   */
  client.setQueryData(KEYS.journal, {
    items: [
      record(),
      record({ decision_id: `dec_${ULID}A`, decision_event_count: 1 }),
      // One row per remaining `Verdict` and per remaining `FindingCategory`, so the
      // knowledge base puts every badge this contract publishes on a screen. Before this
      // the journal held `accepted`/`internal_contradiction` twice and nothing else.
      ...DECISIONS.slice(1).map((event, index) =>
        record({
          ...event,
          decision_id: `${event.decision_id}J`,
          current_verdict: event.verdict ?? 'pending',
          category: index === 0 ? 'explicit_placeholder' : 'internal_contradiction',
          decision_event_count: index + 1,
        }),
      ),
    ],
    page,
  });
  client.setQueryData(KEYS.dashboardSummary, dashboardSummary());
  /*
   * `W50-SHELL-FRAME` (the integrator's ruling of 2026-10-07, Q3): the home page reads five
   * recent projects and, for an administrator, the count of pending requests — keys no other
   * state seeds, so both tiles were pending in every state. Five projects, so the list is the
   * full one; a page whose `pending_total` is two, of which the tile renders the count only.
   */
  client.setQueryData(KEYS.recentProjects, {
    items: Array.from({ length: RECENT_PROJECT_LIMIT }, (_, index) => ({
      ...project(),
      project_uid: `prj_${ULID.slice(0, -1)}${'ABCDE'[index] as string}`,
      name: `Договор поставки ${index + 1}`,
    })),
    page,
  });
  client.setQueryData(KEYS.pendingRegistrations, { items: [], page, pending_total: 2 });
  client.setQueryData(KEYS.account, ADMIN_USER_ACCOUNT);
  client.setQueryData(KEYS.users, { items: [ADMIN_USER_ACCOUNT], page });
  client.setQueryData(KEYS.user, ADMIN_USER_ACCOUNT);
  client.setQueryData(KEYS.registrations, { items: [QUEUE_REQUEST], page, pending_total: 1 });
  client.setQueryData(KEYS.executionQueue, {
    items: [{
      job_id: 'job_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
      run_id: RUN_ID, state: 'queued', priority: 2,
      created_at: '2026-10-09T10:00:00Z', available_at: '2026-10-09T10:00:00Z',
    }],
    page, paused: false,
  });
  client.setQueryData(KEYS.executionJournal, {
    items: [{
      event_id: 'evt_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
      run_id: RUN_ID, aggregate_id: RUN_ID, aggregate_type: 'AuditRun',
      event_type: 'audit_run.transition', occurred_at: '2026-10-09T10:00:00Z',
      payload: { to_state: 'queued' },
    }, {
      // `EXEC-PAR-WEB-01`: the entry a start that names its executor writes.
      event_id: 'evt_01J9ZQ8K7NHVXW3T2R5M6P4Q8G',
      run_id: RUN_ID, aggregate_id: RUN_ID, aggregate_type: 'AuditRun',
      event_type: 'audit_run.executor_chosen', occurred_at: '2026-10-09T09:59:00Z',
      payload: {},
    }],
    page,
  });
  // One worker per state, so every row shape and the collapsed offline group render.
  client.setQueryData(KEYS.workers, { items: WORKERS, page });
  // Every shape of connection and probe, and a route with a standby.
  seedExecutors(client);
  client.setQueryData(KEYS.analysisProfiles, { items: ANALYSIS_PROFILES });
  client.setQueryData(KEYS.arV3PackStatus, installedPackFixture());
  // A current snapshot and the three ways another one can stand; two designations; two hits;
  // a document with a heading, a body paragraph and an unreliable table row.
  client.setQueryData(KEYS.normSnapshots, { items: NORM_SNAPSHOTS, page });
  client.setQueryData(KEYS.normEvents, { items: NORM_EVENTS, page });
  client.setQueryData(KEYS.normSearch, { items: NORM_HITS, page });
  client.setQueryData(KEYS.normDocument, normDocument());
  client.setQueryData(KEYS.normParagraphs, { items: NORM_PARAGRAPHS, page, source_attribution: 'consultant_plus' });
  client.setQueryData(KEYS.normCatalogue, NORM_CATALOGUE_PAGE);
  client.setQueryData(KEYS.assignments, { items: [...ASSIGNMENTS], page });
  client.setQueryData(KEYS.myTasks, { items: [...ASSIGNMENTS], page });
  client.setQueryData(KEYS.assignment, ASSIGNMENT_DETAIL);
  return client;
}

/**
 * The finding readings, in the envelope shape `ReviewPage`'s three finding queries unwrap.
 *
 * `KEYS.run` is deliberately absent: it is seeded by `loadedClient` in the one shape that
 * key now holds, and overwriting it here is what `D-57` looked like from inside a test.
 */
function loadedReviewClient(runOverrides: Partial<RunStatus> = {}): Client {
  const client = loadedClient(runOverrides);
  const page = { next_cursor: null } as { next_cursor: null };
  client.setQueryData(KEYS.findings, { data: { items: FINDINGS, page } });
  client.setQueryData(KEYS.finding, { data: detail() });
  client.setQueryData(KEYS.decisions, { data: { items: DECISIONS, page } });
  return client;
}

/**
 * The review screen with a finding selected but its detail and history still in flight.
 *
 * A state of its own because two `LoadingState what=` arguments live only here: the
 * finding's own panel and the decision history. Seeding the list without the detail is
 * the only way one static pass reaches them.
 */
function reviewDetailPendingClient(): Client {
  const client = loadedReviewClient();
  client.removeQueries({ queryKey: KEYS.finding });
  client.removeQueries({ queryKey: KEYS.decisions });
  return client;
}

/**
 * A client in which every list came back genuinely empty.
 *
 * A state of its own because each of the four list widgets has a third branch -- not
 * pending, not failed, but empty -- and none of it renders while the cache holds items.
 * **It was added because a mutation found it missing**: an English sentence put into
 * `ProjectList`'s `EmptyState` reddened nothing, and the reason was that the guard never
 * rendered that branch. That is `W31-STYLE`'s "insufficient mutation" the other way
 * round: the mutation was sound and the coverage was not.
 */
function emptyClient(): Client {
  const client = newClient();
  const page = { next_cursor: null } as { next_cursor: null };
  client.setQueryData(KEYS.projects, { items: [], page });
  client.setQueryData(KEYS.project, project());
  client.setQueryData(KEYS.documents, { items: [], page });
  client.setQueryData(KEYS.versions, { items: [], page });
  client.setQueryData(KEYS.version, version());
  client.setQueryData(KEYS.runs, { items: [], page });
  client.setQueryData(KEYS.run, run());
  client.setQueryData(KEYS.findings, { data: { items: [], page } });
  client.setQueryData(KEYS.decisions, { data: { items: [], page } });
  client.setQueryData(KEYS.journal, { items: [], page });
  client.setQueryData(KEYS.account, ADMIN_USER_ACCOUNT);
  client.setQueryData(KEYS.users, { items: [], page });
  client.setQueryData(KEYS.user, ADMIN_USER_ACCOUNT);
  client.setQueryData(KEYS.registrations, { items: [], page, pending_total: 0 });
  client.setQueryData(KEYS.executionQueue, { items: [], page, paused: false });
  client.setQueryData(KEYS.executionJournal, { items: [], page });
  client.setQueryData(KEYS.workers, { items: [], page });
  // No connection, no route: the empty branches of both new tabs.
  client.setQueryData(KEYS.executorConnections, { items: [], pinned_models: [...EXECUTOR_PINNED] });
  client.setQueryData(KEYS.executorRoutes, { items: [] });
  // No snapshot loaded, so none is current: «Нормы» renders its refusal, not an empty list.
  client.setQueryData(KEYS.normSnapshots, { items: [], page });
  client.setQueryData(KEYS.normEvents, { items: [], page });
  client.setQueryData(KEYS.normSearch, { items: [], page });
  client.setQueryData(KEYS.normDocument, normDocument({ unreliable_paragraph_count: 0, paragraph_count: 0 }));
  client.setQueryData(KEYS.normParagraphs, { items: [], page, source_attribution: 'consultant_plus' });
  client.setQueryData(KEYS.assignments, { items: [], page });
  client.setQueryData(KEYS.myTasks, { items: [], page });
  client.setQueryData(
    KEYS.dashboardSummary,
    dashboardSummary({
      documents_by_project: [],
      findings_by_verdict: [
        { verdict: 'pending', count: 0 },
        { verdict: 'accepted', count: 0 },
        { verdict: 'rejected', count: 0 },
        { verdict: 'needs_manual_review', count: 0 },
      ],
      run_activity: runActivityWithoutSpend(),
      section_breakdown: PROJECT_SECTIONS.map((section) => ({
        section: section.code,
        document_count: 0,
      })),
    }),
  );
  return client;
}

/**
 * A client in which every listing has a next page.
 *
 * The cursor is opaque and this one is never sent anywhere: it exists so the pager's
 * `next_cursor !== null` branch renders. `page` is the only thing that differs from the
 * loaded client, so anything new on these screens is the pager and nothing else.
 *
 * It takes the loaded builder rather than calling `loadedClient` itself, because the
 * review screen's three finding queries hold the transport envelope and the other screens
 * hold the bare model. Seeding the wrong one renders a screen blank -- which is `D-57`
 * seen from inside a test, and is exactly what the first version of this function did.
 */
function pagedClient(loaded: (over?: Partial<RunStatus>) => Client): Client {
  const client = loaded();
  const page = { next_cursor: 'Y3Vyc29y' } as { next_cursor: string };
  client.setQueryData(KEYS.projects, { items: [project()], page });
  client.setQueryData(KEYS.documents, { items: [version()], page });
  client.setQueryData(KEYS.versions, { items: [version()], page });
  client.setQueryData(KEYS.runs, { items: [run()], page });
  client.setQueryData(KEYS.journal, { items: [record()], page });
  client.setQueryData(KEYS.assignments, { items: [...ASSIGNMENTS], page });
  return client;
}

/**
 * Projects and documents load; the version they point at has never been run.
 *
 * `W46-DASH`, updated at `W46-WIRE` for the dashboard's move onto one read. Every other
 * state seeds `KEYS.runs` with one item — `loadedClient` puts one there and every state
 * built from it inherits it. The dashboard's run-activity panel has a branch that needs
 * the *other* combination: at least one project exists (so it is not the "no projects at
 * all" `EmptyState`) and the deployment-wide read genuinely carries zero runs (so it is
 * not `LoadingState` either). No existing state produces that pair, which is exactly the
 * shape this file exists to catch rather than wave through — a branch with no state that
 * reaches it is a branch no assertion here can see.
 *
 * Before `W46-WIRE` this distinction lived in `KEYS.runs`, which the deleted client-side
 * walk read directly. The dashboard now reads one aggregate instead, so the same pair —
 * projects present, runs absent — is built by overriding `KEYS.dashboardSummary`'s
 * `run_activity` on top of whatever `loaded()` already seeded there, keeping its
 * `documents_by_project` (non-empty) intact. `KEYS.runs` is still emptied too, for the run
 * screen and the comparison screen, which this state also renders.
 *
 * Takes the `loaded` builder rather than calling `loadedClient` itself, for `pagedClient`'s
 * own reason: the review screen's three finding queries hold the transport envelope and
 * every other screen holds the bare model, so calling the wrong one throws inside
 * `review-page.tsx` reading `.data.items` off a bare model — which the first version of
 * this function did.
 */
function runsEmptyClient(loaded: (over?: Partial<RunStatus>) => Client): Client {
  const client = loaded();
  const page = { next_cursor: null } as { next_cursor: null };
  client.setQueryData(KEYS.runs, { items: [], page });
  client.setQueryData(
    KEYS.dashboardSummary,
    dashboardSummary({ run_activity: runActivityWithoutSpend() }),
  );
  return client;
}

/**
 * A reading with named optional fields REMOVED rather than set to `undefined`.
 *
 * `tsconfig.json` sets `exactOptionalPropertyTypes`, under which an omitted property and a
 * property explicitly `undefined` are different types — and the distinction is the whole
 * subject of the rows below: a run that made no provider call does not carry a cost, and
 * one that made free calls carries `0`. The fixture spreads its overrides over defaults,
 * so the only way to seed the first is to take the field off afterwards.
 */
function without(status: RunStatus, fields: readonly (keyof RunStatus)[]): RunStatus {
  const copy = { ...status } as Record<string, unknown>;
  for (const field of fields) delete copy[field];
  return copy as unknown as RunStatus;
}

/**
 * A version with TWO runs of it, which is the one cache state a comparison screen has.
 *
 * `W43-COMPARE`, 2026-09-24. Every other state in this file seeds ONE run, because every
 * other screen reads one; `loadedClient` puts a single item in `KEYS.runs` and `paged`
 * puts the same one behind a cursor. The comparison screen renders its tables only when
 * the version has two, so with the existing states it would have rendered its
 * `NotApplicableState` in all nine of them and **every assertion this guard makes about
 * its tables would have been vacuous** — the shape §12 and this file's own seven
 * sound-and-blind entries are about.
 *
 * The pair is chosen so that **all four comparison verdicts render in one pass**, because
 * each verdict is a Russian sentence and a sentence no state renders is a sentence an
 * English word could sit in:
 *
 *   `differs`     `state`, `created_at`, `terminal_at`, `duration`,
 *                 `published_finding_count`;
 *   `same`        `provider_mode` — both recorded;
 *   `one_sided`   `diagnostic_observation_count`, `model_call_count`, `cost_micros`,
 *                 `terminal_reason`, `terminal_detail`, and every stage the newer run
 *                 reported and the older one did not;
 *   `absent`      `cost_basis` — the newer run reports a cost with no basis beside it and
 *                 the older reports neither, so nothing was compared and the row says so
 *                 rather than «совпадает».
 *
 * `listRuns` answers *newest first* and the screen reads that order rather than re-sorting,
 * so `items[0]` is the run it puts on the RIGHT.
 *
 * **It takes the loaded builder rather than calling `loadedClient` itself**, for the reason
 * `pagedClient` states: the review screen's three finding queries hold the transport
 * envelope and the other screens hold the bare model, so seeding the wrong one renders a
 * screen blank — or, as it did here on the first run of this state, throws inside
 * `review-page.tsx` reading `.data.items` off a bare model. That is `D-57` seen from
 * inside a test, and it is the second time this file's own machinery has produced it.
 */
/**
 * `W59-VERSION-COMPARE-01`. The version in scope and a NEWER version of the same set, both
 * confirmed (П then Р, one section, so the «Стадии П → Р» switch is offered), with the
 * comparison of the pair seeded as given -- or not at all, which is its loading branch.
 *
 * Every value the comparison carries is Cyrillic, an identifier, a digest or a contract
 * enum, for the reason the file header gives: anything Latin left on screen is chrome.
 */
const NEWER_VERSION_UID = `ver_${ULID.slice(0, -1)}C`;

function comparisonBody(over: Partial<VersionComparison> = {}): VersionComparison {
  const finding = (uid: string, text: string, page: number) => ({
    finding_uid: `fnd_${ULID.slice(0, -1)}${uid}`,
    category: 'layout' as const,
    finding_text: text,
    page_numbers: [page],
  });
  return {
    project_uid: PROJECT_UID,
    document_uid: DOCUMENT_UID,
    source_version_uid: VERSION_UID,
    target_version_uid: NEWER_VERSION_UID,
    mode: 'version',
    outcome: 'compared',
    refusal: null,
    source: {
      version_uid: VERSION_UID, version_ordinal: 1, page_count: 4, sha256: SHA,
      project_stage: 'P', section_code: 'AR', run_id: RUN_ID, text_layer_sha256: SHA,
    },
    target: {
      version_uid: NEWER_VERSION_UID, version_ordinal: 2, page_count: 4, sha256: SHA,
      project_stage: 'P', section_code: 'AR', run_id: `run_${ULID.slice(0, -1)}C`,
      text_layer_sha256: SHA,
    },
    comparison_sha256: SHA,
    sheets: [
      { status: 'unchanged', source_page_number: 1, target_page_number: 1, pairing_basis: 'exact_text',
        similarity_permille: 1000, shared_line_count: null, suggestion_sha256: SHA, textless: false },
      { status: 'changed', source_page_number: 2, target_page_number: 2, pairing_basis: 'similar_text',
        similarity_permille: 870, shared_line_count: 12, suggestion_sha256: SHA, textless: false },
      { status: 'removed', source_page_number: 3, target_page_number: null, pairing_basis: null,
        similarity_permille: null, shared_line_count: null, suggestion_sha256: null, textless: true },
      { status: 'added', source_page_number: null, target_page_number: 3, pairing_basis: null,
        similarity_permille: null, shared_line_count: null, suggestion_sha256: null, textless: false },
      { status: 'removed', source_page_number: 4, target_page_number: null, pairing_basis: null,
        similarity_permille: null, shared_line_count: null, suggestion_sha256: null, textless: false },
    ],
    sheet_diffs: {
      offset: 0, limit: COMPARISON_DIFF_LIMIT, total: 13, next_offset: 2,
      items: [
        { status: 'changed', source_page_number: 2, target_page_number: 2, outcome: 'computed',
          too_large_reason: null, source_line_count: 3, target_line_count: 3, added_line_count: 1,
          removed_line_count: 1, evidence_sha256: SHA,
          hunks: [
            { tag: 'equal', source_start: 0, source_end: 2, target_start: 0, target_end: 2,
              source_lines: [], target_lines: [] },
            { tag: 'replace', source_start: 2, source_end: 3, target_start: 2, target_end: 3,
              source_lines: ['Стена 200\n'], target_lines: ['Стена 250\n'] },
          ] },
        { status: 'added', source_page_number: null, target_page_number: 3, outcome: 'too_large',
          too_large_reason: 'target_text_too_many_lines', source_line_count: null,
          target_line_count: null, added_line_count: null, removed_line_count: null,
          evidence_sha256: null, hunks: [] },
      ],
    },
    findings: {
      status: 'compared', unavailable_reason: null, source_finding_count: 3, target_finding_count: 2,
      proposals: [
        { kind: 'unchanged', basis: 'exact_issue_and_quotes', proposal_sha256: SHA,
          source_finding: finding('1', 'Нет дверного проёма', 1),
          target_finding: finding('2', 'Нет дверного проёма', 1) },
        { kind: 'probably_fixed', basis: 'quotes_absent_from_paired_sheets', proposal_sha256: null,
          source_finding: finding('3', 'Толщина стены не совпадает', 2), target_finding: null },
        { kind: 'undetermined', basis: 'evidence_sheet_unpaired', proposal_sha256: null,
          source_finding: finding('4', 'Узел не указан', 4), target_finding: null },
        { kind: 'new', basis: 'no_exact_source_match', proposal_sha256: null,
          source_finding: null, target_finding: finding('5', 'Цвет фасада не согласован', 3) },
      ],
      // `W59-DECISION-CARRYOVER-01`: the unchanged pair is a candidate, so the expert's
      // «Перенести решение» renders in this pass.
      carryover_candidates: [CARRYOVER_CANDIDATE],
    },
    ...over,
  };
}

/** `W59-DECISION-CARRYOVER-01`. The decision on the unchanged pair's older finding. */
const CARRYOVER_CANDIDATE: CarryoverCandidate = {
  proposal_sha256: SHA,
  source_finding_uid: `fnd_${ULID.slice(0, -1)}1`,
  target_finding_uid: `fnd_${ULID.slice(0, -1)}2`,
  source_decision: {
    decision_id: `dec_${ULID}`,
    verdict: 'accepted',
    severity: 'critical',
    comment: 'Проём действительно не показан.',
    author_label: 'Иванова Е. В.',
    recorded_at: '2026-10-20T08:00:00Z',
  },
};

function twoVersionClient(
  loaded: (over?: Partial<RunStatus>) => Client,
  comparison: VersionComparison | null,
): Client {
  const client = loaded();
  const page = { next_cursor: null } as { next_cursor: null };
  const older = version({ classification: classification({ project_stage: 'P' }) });
  const newer = version({
    version_uid: NEWER_VERSION_UID,
    version_ordinal: 2,
    classification: classification({ version_uid: NEWER_VERSION_UID, project_stage: 'R' }),
  });
  client.setQueryData(KEYS.version, older);
  client.setQueryData(KEYS.versions, { items: [newer, older], page });
  if (comparison !== null) {
    client.setQueryData(
      queryKeys.versions.comparison(VERSION_UID, NEWER_VERSION_UID, 'version', 0, COMPARISON_DIFF_LIMIT),
      comparison,
    );
  }
  return client;
}

/** The version is answered and its set's version list is not: the list's loading branch. */
function versionsPendingClient(loaded: (over?: Partial<RunStatus>) => Client): Client {
  const client = loaded();
  client.removeQueries({ queryKey: KEYS.versions, exact: true });
  return client;
}

function twoRunClient(loaded: (over?: Partial<RunStatus>) => Client): Client {
  const client = loaded();
  const page = { next_cursor: null } as { next_cursor: null };
  client.setQueryData(KEYS.runs, {
    items: [
      // No basis beside the figure, on purpose: with neither run reporting one, the
      // `cost_basis` row is the state `absent` exists for.
      without(
        run({
          run_id: RUN_ID,
          state: 'failed',
          terminal_reason: 'dependency_unavailable' as ErrorCode,
          terminal_detail: { dependency: 'provider' },
          published_finding_count: 0,
          diagnostic_observation_count: 2,
          model_call_count: 4,
          cost_micros: 1234,
          created_at: '2026-09-11T09:00:00.000Z',
          terminal_at: '2026-09-11T09:02:30.000Z',
        }),
        ['cost_basis'],
      ),
      without(
        run({
          run_id: `run_${ULID.slice(0, -1)}C`,
          state: 'published',
          published_finding_count: 3,
          created_at: '2026-09-10T08:00:00.000Z',
          terminal_at: '2026-09-10T08:04:00.000Z',
        // Four stages rather than nine, so stage rows in `same`, `differs` and `one_sided`
        // all render — and the "не сообщён" cell with them.
        stages: [
          { stage_id: 'source_preparation', status: 'succeeded', started_at: '2026-09-10T08:00:00.000Z', finished_at: '2026-09-10T08:00:30.000Z', error_code: null, stage_version: '1.0.0' },
          { stage_id: 'page_geometry_extraction', status: 'failed', started_at: '2026-09-10T08:00:30.000Z', finished_at: '2026-09-10T08:01:00.000Z', error_code: 'analysis_failed' as ErrorCode, stage_version: '1.0.0' },
          { stage_id: 'document_context_build', status: 'skipped', started_at: null, finished_at: null, error_code: null, stage_version: '1.0.0' },
          { stage_id: 'text_analysis', status: 'succeeded', started_at: '2026-09-10T08:01:00.000Z', finished_at: '2026-09-10T08:01:00.000Z', error_code: null, stage_version: '1.0.0' },
          ],
        }),
        ['cost_basis', 'cost_micros', 'model_call_count', 'diagnostic_observation_count'],
      ),
    ],
    page,
  });
  return client;
}

/** A client in which every question failed. */
function failedClient(): Client {
  const client = newClient();
  for (const key of Object.values(KEYS)) {
    seedError(client, key, apiError(503, 'dependency_unavailable'));
  }
  return client;
}

/**
 * The screens this guard renders: **the route tree, plus the shapes an address alone does
 * not select.**
 *
 * ## What changed here, and why, `D-88`
 *
 * This was `const SCREENS = [...]` — a hand-written array of page components. It did not
 * read `web/src/app`, so a screen that existed was invisible to this guard until somebody
 * remembered to add it. `W43-JUDGE-A` put a different English sentence on each of four new
 * screens and **the whole frontend suite stayed green — 73 files, 1047 tests, 0 failed.**
 * The nav labels were covered, because `AppFrame` is below; the pages behind them were not,
 * so this guard saw a word in the panel and not one word on the page that panel opens.
 *
 * `derivedScreens()` reads the route tree in `tests/unit/screens/route-screens.ts`, and
 * `screen-set.guard.test.ts` is what makes an address with no seed red **naming the
 * address**. A screen added next wave arrives here whether or not anybody remembers.
 *
 * ## What the derivation CANNOT supply, and is listed below
 *
 * An address selects a screen; it does not select the screen's SHAPE. The entries after
 * the derived set are the shapes a reviewer reads that no address distinguishes — the
 * chrome around every page, a form carrying a refusal, a password screen after it
 * succeeded, two widgets whose failure branches a page only produces from a query state a
 * static pass cannot reach. Each carries the argument for its own existence, unchanged
 * from when it was written.
 *
 * The three `*-bad-address` entries that used to be here are **gone from this list and
 * derived instead**: `malformedVariants()` produces one per (screen, dynamic segment) pair
 * from the directory layout, so eleven refusal branches are now read by this guard where
 * three were before. They are appended once rather than rendered in all seventeen cache
 * states, because the refusal returns before any query is read.
 */
const DERIVED_SCREENS: readonly { readonly name: string; readonly make: () => ReactElement }[] =
  derivedScreens().map((screen) => ({
    name: screen.name,
    make: () =>
      screen.make(
        wellFormed({
          projectUid: PROJECT_UID,
          documentUid: DOCUMENT_UID,
          versionUid: VERSION_UID,
          runId: RUN_ID,
        }),
      ),
  }));

const ADMIN_USER_ACCOUNT: Account = {
  archived_at: null,
  display_label: 'Проверкина А. С.',
  first_name: 'Анна',
  is_default_credential: false,
  last_name: 'Проверкина',
  login: 'проверкина@пример.испытание',
  middle_name: 'Сергеевна',
  profile_complete: true,
  roles: ['admin', 'expert'],
  user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
};

/**
 * `W61-DISPATCHER-01`: one assignment per status, so every status label, every move the two
 * roles are offered, a note, a reason, a document title and a project-wide row render. The
 * first two are the seeded account's own (`KEYS.account`), so the assignee's moves render on
 * the dispatcher's screen too; the rest belong to another expert.
 */
function assignment(letter: string, status: Assignment['status'], over: Partial<Assignment> = {}): Assignment {
  return {
    assignment_uid: `asg_${'01J9ZQ8K7NHVXW3T2R5M6P4Q8'}${letter}`,
    project_uid: PROJECT_UID,
    project_name: 'Договор поставки',
    document_uid: null,
    document_title: null,
    assignee_user_uid: ADMIN_USER_ACCOUNT.user_uid,
    assignee_label: ADMIN_USER_ACCOUNT.display_label,
    created_by_user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8C',
    created_by_label: 'Начальникова Е. В.',
    note: null,
    status,
    status_reason: null,
    created_at: '2026-10-20T08:00:00Z',
    updated_at: '2026-10-20T09:00:00Z',
    ...over,
  };
}

const ASSIGNMENTS: readonly Assignment[] = [
  assignment('A', 'assigned', { note: 'Проверить армирование до пятницы' }),
  assignment('B', 'in_progress', { document_uid: DOCUMENT_UID, document_title: 'Пояснительная записка' }),
  assignment('C', 'returned', {
    assignee_user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8D',
    assignee_label: 'Экспертова Д. Д.',
    status_reason: 'Раздел не мой',
  }),
  assignment('D', 'done', { assignee_user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8D', assignee_label: 'Экспертова Д. Д.' }),
  assignment('E', 'cancelled', { status_reason: 'Проект закрыт' }),
];

const ASSIGNMENT_DETAIL: AssignmentDetail = {
  assignment: ASSIGNMENTS[2] as Assignment,
  history: [
    { event_id: 'evt_01J9ZQ8K7NHVXW3T2R5M6P4Q8A', kind: 'assigned', actor_user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8C', actor_label: 'Начальникова Е. В.', reason: null, new_assignee_user_uid: null, new_assignee_label: null, occurred_at: '2026-10-20T08:00:00Z' },
    { event_id: 'evt_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', kind: 'started', actor_user_uid: ADMIN_USER_ACCOUNT.user_uid, actor_label: ADMIN_USER_ACCOUNT.display_label, reason: null, new_assignee_user_uid: null, new_assignee_label: null, occurred_at: '2026-10-20T08:10:00Z' },
    { event_id: 'evt_01J9ZQ8K7NHVXW3T2R5M6P4Q8C', kind: 'reassigned', actor_user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8C', actor_label: 'Начальникова Е. В.', reason: 'Отпуск', new_assignee_user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8D', new_assignee_label: 'Экспертова Д. Д.', occurred_at: '2026-10-20T08:20:00Z' },
    { event_id: 'evt_01J9ZQ8K7NHVXW3T2R5M6P4Q8D', kind: 'returned', actor_user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8D', actor_label: 'Экспертова Д. Д.', reason: 'Раздел не мой', new_assignee_user_uid: null, new_assignee_label: null, occurred_at: '2026-10-20T08:30:00Z' },
    { event_id: 'evt_01J9ZQ8K7NHVXW3T2R5M6P4Q8E', kind: 'completed', actor_user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8D', actor_label: 'Экспертова Д. Д.', reason: null, new_assignee_user_uid: null, new_assignee_label: null, occurred_at: '2026-10-20T08:40:00Z' },
    { event_id: 'evt_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', kind: 'cancelled', actor_user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8C', actor_label: 'Начальникова Е. В.', reason: 'Проект закрыт', new_assignee_user_uid: null, new_assignee_label: null, occurred_at: '2026-10-20T08:50:00Z' },
  ],
};

const QUEUE_REQUEST: RegistrationRequest = {
  created_user_uid: null,
  decided_at: null,
  decided_by: null,
  display_label: 'Заявкина М. П.',
  first_name: 'Мария',
  last_name: 'Заявкина',
  login: 'заявкина@пример.испытание',
  middle_name: 'Петровна',
  rejection_reason: null,
  request_id: 'reg_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
  status: 'pending',
  submitted_at: '2026-10-08T00:00:00Z',
};

/**
 * A refusal of `startArV3BetaGroup` with the classifiers the server attaches, for the control's
 * failure branches. Cyrillic message: only the sentences this application wrote are judged.
 */
function startRefusal(
  status: number,
  code: ErrorCode,
  details?: Record<string, string | number | boolean | null>,
): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.8.0',
    error_code: code,
    message: 'Сообщение об отказе.',
    correlation_id: '0f0e9d8c-7b6a-4948-b726-150413021100',
    retryable: code === 'dependency_unavailable' || code === 'idempotency_key_in_progress',
    ...(details === undefined ? {} : { details }),
  };
  return new ApiError(status, envelope, '0f0e9d8c-7b6a-4948-b726-150413021100');
}

/**
 * Every state of «Запустить шесть проверок АР v3» that a settled mutation produces: pending, each
 * refusal the start raises, the generic reading of a failure outside that set, and a 202 without a
 * usable group address. The control keeps these in a `useMutation` observer one static pass cannot
 * settle, so the presentational view is rendered once per failure (`D-82`).
 */
function startGroupViews(): ReactElement {
  const failures = [
    startRefusal(503, 'dependency_unavailable', { dependency: 'ar_v3_trusted_pack' }),
    startRefusal(503, 'dependency_unavailable', { dependency: 'metadata_store' }),
    startRefusal(422, 'required_norm_unavailable', { reference_kind: 'norms_snapshot' }),
    startRefusal(422, 'version_classification_required'),
    startRefusal(422, 'section_profile_unavailable'),
    startRefusal(422, 'analysis_input_invalid', { reason: 'missing_required_input' }),
    startRefusal(422, 'analysis_input_budget_exceeded', { character_count: 300000, budget_characters: 152000 }),
    startRefusal(409, 'idempotency_key_reuse'),
    startRefusal(409, 'idempotency_key_in_progress'),
    startRefusal(409, 'idempotency_key_stale'),
    startRefusal(404, 'not_found'),
    startRefusal(401, 'authentication_required'),
    startRefusal(403, 'permission_denied'),
    startRefusal(500, 'internal_error'),
    new TransportError('Запрос не дошёл.', { retryable: true }),
  ].map(classifyArV3GroupStartFailure);
  const view = (key: string, pending: boolean, failure: ReturnType<typeof classifyArV3GroupStartFailure> | null) =>
    createElement(StartArV3GroupView, {
      key, projectUid: PROJECT_UID, versionUid: VERSION_UID, pending, failure, onSend: () => undefined,
    });
  return createElement(
    'div',
    null,
    view('idle', false, null),
    view('pending', true, null),
    ...failures.map((failure, index) => view(`failure-${index}`, false, failure)),
    view('malformed', false, MALFORMED_GROUP_ANSWER),
  );
}

type ScreenCase = {
  readonly name: string;
  readonly make: () => ReactElement;
  readonly seedClient?: (client: ReturnType<typeof newClient>) => void;
};

function queueLanguageShape(request: RegistrationRequest): Pick<ScreenCase, 'make' | 'seedClient'> {
  return {
    make: () => createElement(RegistrationQueue),
    seedClient: (client) => client.setQueryData(KEYS.registrations, {
      items: [request], page: { next_cursor: null }, pending_total: request.status === 'pending' ? 1 : 0,
    }),
  };
}

/*
 * `W55B-WEB-BLOCKS`: «Блоки» once a version is chosen. The page reaches its two tabs only
 * after three clicks (a project, a document, a tab), which one static pass cannot make, so
 * the tabs are rendered here through `VersionBlockViews` -- the component the page itself
 * renders -- over a cache seeded with every answer each tab distinguishes, one version per
 * answer. The loaded portal list is rendered through `PortalBlockListView`, the view the
 * widget renders; a crop's address is built by the seam from the configured base, which
 * `renderedScreens` sets for its pass (`W55B-FIX`, Y-2). Every `PortalBlockType` and
 * `PortalGeometryState` member, every flag the backend emits and one it does not, and a
 * portal status the screen does not know are on screen in the second shape.
 */
const BLOCK_ANSWERS = [
  { tab: 'portal', uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8C', bundle: true, portal: 'not_produced' },
  { tab: 'portal', uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8D', bundle: false, portal: 'not_produced' },
  { tab: 'portal', uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8E', bundle: true, portal: 'empty' },
  { tab: 'portal', uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', bundle: true, portal: 'refused' },
  { tab: 'portal', uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8G', bundle: true, portal: 'pending' },
  { tab: 'lines', uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8H', bundle: true, lines: 'not_produced' },
  { tab: 'lines', uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8J', bundle: true, lines: 'empty' },
  { tab: 'lines', uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8K', bundle: true, lines: 'refused' },
  { tab: 'lines', uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8M', bundle: true, lines: 'pending' },
  { tab: 'lines', uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8N', bundle: true, lines: 'loaded' },
] as const;

function seedBlockAnswers(client: ReturnType<typeof newClient>): void {
  for (const answer of BLOCK_ANSWERS) {
    if ('portal' in answer) {
      const key = portalBlocksQueryOptions(answer.uid).queryKey;
      if (answer.portal === 'not_produced') client.setQueryData(key, { pages: [notProducedPage()], pageParams: [undefined] });
      if (answer.portal === 'empty') client.setQueryData(key, { pages: [portalPage([])], pageParams: [undefined] });
      if (answer.portal === 'refused') seedError(client, key, apiError(503, 'dependency_unavailable'));
    } else {
      const key = queryKeys.versions.blocks(answer.uid);
      const absent = { version_uid: answer.uid, block_count: 0, blocks: [], produced_by_run_id: null, text_layer_sha256: null };
      if (answer.lines === 'not_produced') client.setQueryData(key, { ...absent, status: 'not_produced' });
      if (answer.lines === 'empty') {
        client.setQueryData(key, { ...absent, status: 'produced', produced_by_run_id: RUN_ID, text_layer_sha256: SHA });
      }
      if (answer.lines === 'refused') seedError(client, key, apiError(503, 'dependency_unavailable'));
      if (answer.lines === 'loaded') {
        client.setQueryData(key, {
          ...absent, status: 'produced', produced_by_run_id: RUN_ID, text_layer_sha256: SHA, block_count: 1,
          blocks: [{
            block_id: 'b_000001', page_number: 1, block_ordinal: 0, char_start: 0, char_end: 12,
            bbox: { x0: 10, y0: 20, x1: 200, y1: 32 }, bbox_unit: 'pt', bbox_origin: 'top_left',
          }],
        });
      }
    }
  }
}

const BLOCKS_SHAPES: readonly ScreenCase[] = [
  {
    name: 'blocks-tabs-every-answer',
    make: () =>
      createElement(
        'div',
        null,
        ...BLOCK_ANSWERS.map((answer) =>
          createElement(VersionBlockViews, {
            key: answer.uid,
            version: blocksVersion(answer.bundle, { version_uid: answer.uid }),
            tab: answer.tab,
            onTab: () => {},
          }),
        ),
      ),
    seedClient: seedBlockAnswers,
  },
  {
    name: 'blocks-portal-loaded',
    make: () =>
      createElement(
        'div',
        null,
        createElement(PortalBlockListView, {
          projectUid: BLOCKS_PROJECT_UID, blockCount: 129, producedByRunId: BLOCKS_RUN_ID,
          blocks: everyKindOfBlock(), versionUid: BLOCKS_VERSION_UID, hasMore: true, loadingMore: false,
          moreFailure: null, onMore: () => {},
        }),
        createElement(PortalBlockListView, {
          projectUid: BLOCKS_PROJECT_UID, blockCount: 129, producedByRunId: null,
          blocks: everyKindOfBlock().slice(0, 1), versionUid: BLOCKS_VERSION_UID, hasMore: true, loadingMore: true,
          moreFailure: null, onMore: () => {},
        }),
        createElement(PortalBlockListView, {
          projectUid: BLOCKS_PROJECT_UID, blockCount: 129, producedByRunId: BLOCKS_RUN_ID,
          blocks: everyKindOfBlock().slice(0, 1), versionUid: BLOCKS_VERSION_UID, hasMore: true, loadingMore: false,
          moreFailure: {
            kind: 'dependency_unavailable', title: 'Зависимость, нужная чтобы прочитать следующие блоки портала, недоступна.',
            detail: 'Повторите позже.', correlationId: '0f0e9d8c-7b6a-4948-b726-150413021100', retryable: true,
            errorCode: 'dependency_unavailable',
          },
          onMore: () => {},
        }),
        createElement(CropFigureView, {
          versionUid: BLOCKS_VERSION_UID, portalBlockId: everyKindOfBlock()[1]!.portal_block_id,
          widthPx: 1177, heightPx: 593,
          alt: 'Изображение: фрагмент страницы 1 PDF', failed: true, onError: () => {},
        }),
      ),
  },
];

/*
 * `EXEC-PAR-WEB-01`. The start control's «Исполнитель» and the refusals of a chosen executor.
 *
 * The control itself is rendered in every cache state, so its loading, failed and read shapes
 * (every probe outcome, an archived connection, a connection with no settings) are all on a screen.
 * What a settled `useMutation` or a `useState` decides is not: a refusal of the executor that was
 * chosen, and a select whose value is a connection that cannot serve or has left the list. Those
 * are rendered through the views the control renders (`StartRunFailureView`, `ExecutorSelectView`).
 */
function startRunExecutorShapes(): ReactElement {
  const details = new Map(EXECUTOR_CASES.map((one) => [one.connection.connection_id as string, one.detail]));
  const connections = EXECUTOR_CASES.map((one) => one.connection);
  const choices = executorChoices(connections, details);
  const blocked = choices.find((choice) => choice.blocker === 'probe_failed');
  const archived = choices.find((choice) => choice.archived);
  if (blocked === undefined || archived === undefined) {
    throw new Error('the executor fixtures hold no blocked and no archived connection to choose');
  }
  // A connection whose settings were not read: only the list, with no detail for it.
  const unread = executorChoices([EXECUTOR_READY.connection], new Map());
  const select = (key: string, reading: Parameters<typeof ExecutorSelectView>[0]['reading'], value: string | null) =>
    createElement(ExecutorSelectView, { key, id: `select-${key}`, reading, value, disabled: false, onChange: () => undefined });
  const ready = { phase: 'ready', choices } as const;

  const refusal = (
    code: ErrorCode, status: number, retryable: boolean,
    details: Readonly<Record<string, string>>, message = 'Сообщение об отказе.',
  ): ApiError => new ApiError(status, {
    contract_version: '1.8.0', error_code: code, message, correlation_id: '0f0e9d8c-7b6a-4948-b726-150413021100',
    retryable, details,
  }, '0f0e9d8c-7b6a-4948-b726-150413021100');
  const cannotServe = (reason: string) =>
    refusal('dependency_unavailable', 503, true, { dependency: 'executor_connection' },
      `the chosen executor connection cannot serve a run now (${reason})`);
  const failures = [
    ...['archived', 'kind_not_served', 'not_probed', 'no_revision'].map((reason) => cannotServe(reason)),
    refusal('dependency_unavailable', 503, true, { dependency: 'executor_connection' }),
    ...['unknown_connection', 'pattern', 'kind_not_routable', 'something_else'].map((constraint) =>
      refusal('validation_failed', 422, false, { field: 'executor_connection_id', constraint })),
  ].map(classifyRunFailure);

  return createElement(
    'div',
    null,
    select('ready-default', ready, null),
    select('ready-blocked-chosen', ready, blocked.connectionId),
    select('ready-archived-chosen', ready, archived.connectionId),
    select('ready-chosen-left-the-list', ready, 'exc_01J9ZQ8K7NHVXW3T2R5M6P4Q8Z'),
    select('ready-unread', { phase: 'ready', choices: unread }, null),
    select('ready-empty', { phase: 'ready', choices: [] }, null),
    select('failed', {
      phase: 'failed', detail: 'Сервер не ответил.', correlationId: '0f0e9d8c-7b6a-4948-b726-150413021100',
      onRetry: () => undefined,
    }, null),
    ...failures.map((failure, index) => createElement(StartRunFailureView, {
      key: `failure-${index}`, failure, projectUid: PROJECT_UID, versionUid: VERSION_UID, onRetry: () => undefined,
    })),
  );
}

const EXTRA_SHAPES: readonly ScreenCase[] = [
  {
    name: 'start-run-control',
    make: () => createElement(StartRunControl, { projectUid: PROJECT_UID, versionUid: VERSION_UID }),
  },
  {
    name: 'start-run-executor-shapes',
    make: startRunExecutorShapes,
  },
  // `AR-V3-BETA-SCREEN-GATE-REPAIR-01`: these four branches are conditional on the
  // group ID and its separate read, so the default settings route cannot reach them.
  {
    name: 'ar-v3-group-pending',
    make: () => createElement(ArV3BetaReview, { groupId: 'arg_01M2545JSD15ETSNNV904X991K' }),
  },
  {
    name: 'ar-v3-group-invalid-id',
    make: () => createElement(ArV3BetaReview, { groupId: 'arg_bad' }),
  },
  {
    name: 'ar-v3-group-read-refused',
    make: () => createElement(ArV3BetaReview, { groupId: 'arg_01M2545JSD15ETSNNV904X991K' }),
    seedClient: (client) => seedError(
      client, queryKeys.runs.arV3GroupReview('arg_01M2545JSD15ETSNNV904X991K'),
      apiError(503, 'dependency_unavailable'),
    ),
  },
  {
    name: 'ar-v3-group-inconsistent-answer',
    make: () => createElement(ArV3BetaReview, { groupId: 'arg_01M2545JSD15ETSNNV904X991K' }),
    seedClient: (client) => client.setQueryData(
      queryKeys.runs.arV3GroupReview('arg_01M2545JSD15ETSNNV904X991K'),
      { group_id: 'arg_01M2545JSD15ETSNNV904X991K', version_uid: VERSION_UID, members: [] },
    ),
  },
  // `AR-V3-BETA-PACK-STATUS-WEB-01`: the pack panel in the states a default cache does not
  // select. Loading (cold) and failed (`failedClient`) come from `KEYS`; installed is seeded by
  // `loadedClient`, but these cases seed their own so they do not depend on that.
  {
    name: 'ar-v3-pack-installed',
    make: () => createElement(ArV3BetaPack),
    seedClient: (client) => client.setQueryData(KEYS.arV3PackStatus, installedPackFixture()),
  },
  {
    name: 'ar-v3-pack-not-installed',
    make: () => createElement(ArV3BetaPack),
    seedClient: (client) => client.setQueryData(KEYS.arV3PackStatus, NOT_INSTALLED_PACK),
  },
  {
    name: 'ar-v3-pack-fault-without-review',
    make: () => createElement(ArV3BetaPack),
    seedClient: (client) =>
      client.setQueryData(KEYS.arV3PackStatus, withoutMember(installedPackFixture(), 'review')),
  },
  {
    name: 'ar-v3-pack-fault-unknown-state',
    make: () => createElement(ArV3BetaPack),
    seedClient: (client) => client.setQueryData(KEYS.arV3PackStatus, { state: 'withdrawn' }),
  },
  {
    name: 'ar-v3-pack-fault-wrong-scopes',
    make: () => createElement(ArV3BetaPack),
    seedClient: (client) =>
      client.setQueryData(KEYS.arV3PackStatus, { ...installedPackFixture(), scope_ids: ['F1', 'F2'] }),
  },
  {
    name: 'ar-v3-group-start-states',
    make: startGroupViews,
  },
  // `W60-PRICE-LIST-01`: the project's «Оптимизация» tab in every branch its widgets have.
  ...optimisationShapes(),
  // `W60-OPT-PROPOSALS-01`: «Предложения» in every branch its widget, features and entity have.
  ...proposalShapes(),
  {
    name: 'update-banner',
    make: () => createElement(UpdateBannerView, { onUpdate: () => undefined, onLater: () => undefined }),
  },
  {
    name: 'whats-new',
    make: () => createElement(WhatsNewView, {
      newest: '0.3.0', onClose: () => undefined,
      listing: { whats_new: ['0.3.0'], items: [{
        version: '0.3.0', revision: 1, date: '2026-10-08', title: 'Новые возможности',
        is_archive: false, range_label: null,
        items: [{ kind: 'new', screen: 'home', where: 'Работа › Главная', text: 'Открыта история версий.' }],
      }] },
    }),
  },
  {
    name: 'release-history-loading',
    make: () => createElement(VersionHistoryView, {
      version: null, listing: null, loading: true, error: null,
      onClose: () => undefined, onRetry: () => undefined,
    }),
  },
  {
    name: 'release-history-empty',
    make: () => createElement(VersionHistoryView, {
      version: '0.3.0', listing: { items: [], whats_new: [] }, loading: false, error: null,
      onClose: () => undefined, onRetry: () => undefined,
    }),
  },
  // `C-29` (W53 close): the failed read's title became a literal when the unknown-kind fault
  // left, so its branch is now visible to this matrix and needs a state that renders it.
  {
    name: 'release-history-failed',
    make: () => createElement(VersionHistoryView, {
      version: null, listing: null, loading: false, error: new Error('network'),
      onClose: () => undefined, onRetry: () => undefined,
    }),
  },
  /*
   * `AppFrame` is a SCREEN here, not a wrapper, and that is the repair.
   *
   * This guard rendered the six pages and never the chrome around them, so the product name,
   * the instance label, the theme control and the footer were outside the ratchet
   * STRUCTURALLY rather than by oversight. A wave-33 judge mutated a theme label to English
   * and this guard stayed green — and `W33-THEME` had cited that green as coverage for its
   * own output. Silence from a guard is read as coverage; it was.
   *
   * Wrapping the six pages in it would work too, and is worse: a string would then have to
   * be found somewhere in a whole page's markup, and a chrome regression would look like a
   * page regression. As its own entry it names itself in the failure.
   *
   * It is not an address and never was, which is why it survives the derivation: `AppFrame`
   * is mounted by `app/layout.tsx` around every screen.
   */
  { name: 'app-frame', make: () => createElement(AppFrame, { children: null, session: null }) },
  /*
   * `D-113`. The frame's OTHER states, for the reason the sign-in screen's two other shapes
   * are below: the signed-in bar is selected by a prop and not by an address, so the
   * derivation cannot reach it and an English word in it would redden nothing.
   *
   * `W50-SHELL-FRAME`: the frame is handed the whole subject, and what it renders depends on
   * it — the navigation groups a session may open, the account menu's header (name, e-mail,
   * roles, or the typed fault for a role it cannot name) — so each state is its own entry.
   * The menus a reader opens are drawn open here, with the bar's own props: the account
   * menu's `MenuView` from `accountMenuProps`, and the navigation with every disclosure open.
   */
  { name: 'app-frame-with-a-session', make: () => createElement(AppFrame, { children: null, session: EXPERT }) },
  { name: 'app-frame-admin', make: () => createElement(AppFrame, { children: null, session: ADMIN_AND_EXPERT }) },
  { name: 'app-frame-no-roles', make: () => createElement(AppFrame, { children: null, session: NO_ROLES }) },
  { name: 'app-frame-unknown-role', make: () => createElement(AppFrame, { children: null, session: UNKNOWN_ROLE }) },
  {
    name: 'app-frame-default-credential',
    make: () => createElement(AppFrame, { children: null, session: DEFAULT_CREDENTIAL }),
  },
  {
    name: 'app-frame-incomplete-profile',
    make: () => createElement(AppFrame, { children: null, session: INCOMPLETE_PROFILE }),
  },
  {
    name: 'app-frame-account-menu-open',
    make: () =>
      createElement(MenuView, {
        ...accountMenuProps(ADMIN_AND_EXPERT),
        state: { open: true, active: 0 },
        triggerId: 'language-account-trigger',
        menuId: 'language-account-menu',
      }),
  },
  {
    name: 'app-frame-navigation-open',
    make: () =>
      createElement(FrameNavigationView, {
        navigation: buildNavigation(ADMIN_AND_EXPERT),
        pathname: '/blocks',
        disclosure: (props: DisclosureProps) =>
          createElement(DisclosureView, { ...props, open: true, panelId: `language-${props.label}` }),
      }),
  },
  /*
   * The sign-in screen's two OTHER shapes. The credentials form itself is derived, because
   * `/login` is an address; these two are not, because a refusal and a signed-in panel are
   * selected by props the address does not carry.
   *
   * `W32-SEE` measured the cost of leaving them out — an English sentence in a branch
   * nothing rendered reddened nothing — and the branch here is the whole refusal wording,
   * which is the one string on this screen a reviewer reads only when something has gone
   * wrong.
   *
   * The login is Cyrillic for the reason every fixture in this file is: it is the server's
   * data, not this programme's prose. The other three refusal sentences are judged by
   * `web/tests/unit/session/sign-in-screen.test.ts`, which renders all four.
   */
  { name: 'sign-in-refused', make: () => createElement(SignInPage, { refusal: 'credentials' }) },
  { name: 'sign-in-unknown-refusal', make: () => createElement(SignInPage, { unknownRefusal: true }) },
  { name: 'sign-in-open', make: () => createElement(SignInPage, { login: 'проверяющий' }) },
  { name: 'registration-refused', make: () => createElement(RegisterPage, { refusal: 'validation' }) },
  { name: 'registration-unknown-refusal', make: () => createElement(RegisterPage, { unknownRefusal: true }) },
  /*
   * The password screen's three OTHER shapes, `R-26`. The signed-out shape is derived,
   * because `/account/password` is an address; these three are selected by props:
   *
   *   - signed in, nothing attempted: the form and the sentence that says what pressing the
   *     button will revoke;
   *   - refused: the `ErrorState` wording, which `W32-SEE` measured as the exact place an
   *     English sentence survives -- a branch nothing renders reddens nothing;
   *   - changed: the one outcome that is NOT an error, and therefore the one shape whose
   *     markup this file would otherwise never see.
   *
   * The other four refusal sentences are judged by
   * `web/tests/unit/session/change-password.test.ts`, which renders all six outcomes.
   */
  {
    name: 'change-password',
    make: () => createElement(ChangePasswordPage, { login: 'проверяющий' }),
  },
  {
    name: 'change-password-refused',
    make: () =>
      createElement(ChangePasswordPage, { login: 'проверяющий', outcome: 'credentials' }),
  },
  {
    name: 'change-password-changed',
    make: () =>
      createElement(ChangePasswordPage, { login: 'проверяющий', outcome: 'changed' }),
  },
  {
    name: 'manage-user-active',
    make: () => createElement(ManageUserControls, { account: ADMIN_USER_ACCOUNT }),
  },
  {
    name: 'manage-user-archived',
    make: () => createElement(ManageUserControls, { account: { ...ADMIN_USER_ACCOUNT, archived_at: '2026-10-08T00:00:00Z' } }),
  },
  { name: 'registration-queue-pending', ...queueLanguageShape(QUEUE_REQUEST) },
  { name: 'registration-queue-approved', ...queueLanguageShape({ ...QUEUE_REQUEST, status: 'approved', decided_at: '2026-10-08T01:00:00Z' }) },
  { name: 'registration-queue-rejected', ...queueLanguageShape({ ...QUEUE_REQUEST, status: 'rejected', decided_at: '2026-10-08T01:00:00Z', rejection_reason: 'Проверка не пройдена.' }) },
  {
    name: 'execution-journal-invalid-run-filter',
    make: () => createElement(LogsPage, { initialRunId: 'некорректный' }),
  },
  {
    name: 'execution-journal-known',
    make: () => createElement(ExecutionJournal, {
      entries: [{
        event_id: 'evt_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
        run_id: RUN_ID,
        aggregate_id: RUN_ID,
        aggregate_type: 'AuditRun',
        event_type: 'audit_run.transition',
        occurred_at: '2026-10-09T10:00:00Z',
        payload: { to_state: 'queued' },
      }],
      onNext: null, onPrevious: null,
    }),
  },
  {
    name: 'execution-journal-empty-paged',
    make: () => createElement(ExecutionJournal, {
      entries: [], onNext: null, onPrevious: () => {},
    }),
  },
  {
    name: 'execution-queue-admin',
    make: () => createElement(ExecutionQueue, {
      items: [{
        job_id: 'job_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
        run_id: RUN_ID,
        state: 'queued',
        priority: 2,
        created_at: '2026-10-09T10:00:00Z',
        available_at: '2026-10-09T10:00:00Z',
      }],
      roles: ['admin'], asOf: Date.parse('2026-10-09T10:05:00Z'),
      busy: false, workerOf: () => ({ kind: 'pending' as const }), onCancel: () => {}, onReaudit: () => {},
      onPriority: () => {}, onNext: null, onPrevious: null,
    }),
  },
  {
    name: 'execution-queue-unknown-state',
    make: () => createElement(ExecutionQueue, {
      items: [{
        job_id: 'job_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
        run_id: RUN_ID,
        state: 'unknown_state',
        priority: 2,
        created_at: '2026-10-09T10:00:00Z',
        available_at: '2026-10-09T10:00:00Z',
      }],
      roles: ['admin'], asOf: null,
      busy: false, workerOf: () => ({ kind: 'pending' as const }), onCancel: () => {}, onReaudit: () => {},
      onPriority: () => {}, onNext: null, onPrevious: null,
    }),
  },
  {
    name: 'execution-queue-empty-paged',
    make: () => createElement(ExecutionQueue, {
      items: [], roles: [], asOf: null,
      busy: false, workerOf: () => ({ kind: 'pending' as const }), onCancel: () => {}, onReaudit: () => {},
      onPriority: () => {}, onNext: null, onPrevious: () => {},
    }),
  },
  /*
   * `W54-WORKERS-WEB`. The worker list's branches the «Исполнители» page reaches only from
   * a page the cache states do not hold: a state outside the sealed set, an empty later
   * page, a page with no worker on line; and every sentence a queue or run row uses to name
   * (or not name) the worker holding a run.
   */
  {
    name: 'worker-list-unknown-state',
    make: () => createElement(WorkerList, {
      items: [{ ...(WORKERS[0] as ExecutionWorker), state: 'future' as ExecutionWorker['state'] }],
      roles: ['admin'], busy: false, onIntake: () => {}, onNext: null, onPrevious: null,
    }),
  },
  {
    name: 'worker-list-empty-paged',
    make: () => createElement(WorkerList, {
      items: [], roles: [], busy: false, onIntake: () => {}, onNext: null, onPrevious: () => {},
    }),
  },
  {
    name: 'worker-list-none-active',
    make: () => createElement(WorkerList, {
      items: WORKERS.filter((worker) => worker.state === 'offline'),
      roles: ['expert'], busy: false, onIntake: () => {}, onNext: null, onPrevious: null,
    }),
  },
  {
    name: 'run-worker-lines',
    make: () => createElement('div', null,
      createElement(RunWorkerLine, { worker: { kind: 'held', workerId: 'wrk_01J9ZQ8K7NHVXW3T2R5M6P4Q8A' } }),
      createElement(RunWorkerLine, { worker: { kind: 'unheld' } }),
      createElement(RunWorkerLine, { worker: { kind: 'beyond' } }),
      createElement(RunWorkerLine, { worker: { kind: 'unreadable' } }),
      createElement(RunWorkerLine, { worker: { kind: 'pending' } }),
    ),
  },
  /*
   * `EXEC-HTTP-01`. «Исполнители» on its other two tabs, as an administrator and as an expert,
   * with the key form opened for a connection; every outcome of the key post (the form is a
   * server component, so its eight sentences are rendered here on their own); a refused
   * command; and the forms and controls a tab reaches only after a press or a choice, rendered
   * through the views the cards draw.
   */
  {
    name: 'workers-connections',
    make: () => createElement(WorkersPage as ComponentType<WorkersPageProps>, { initialTab: 'connections' }),
  },
  {
    name: 'workers-connections-key',
    make: () => createElement(WorkersPage as ComponentType<WorkersPageProps>, {
      initialTab: 'connections',
      secretConnectionId: EXECUTOR_READY.connection.connection_id,
      secretForm: createElement(SetExecutorSecretForm, { connectionId: EXECUTOR_READY.connection.connection_id, outcome: 'saved' }),
    }),
  },
  {
    name: 'workers-connections-expert',
    make: () => createElement(WorkersPage as ComponentType<WorkersPageProps>, { initialTab: 'connections' }),
    seedClient: (client) => client.setQueryData(KEYS.account, { ...ADMIN_USER_ACCOUNT, roles: ['expert'] }),
  },
  {
    name: 'workers-routes',
    make: () => createElement(WorkersPage as ComponentType<WorkersPageProps>, { initialTab: 'routes' }),
  },
  {
    name: 'workers-routes-expert',
    make: () => createElement(WorkersPage as ComponentType<WorkersPageProps>, { initialTab: 'routes' }),
    seedClient: (client) => client.setQueryData(KEYS.account, { ...ADMIN_USER_ACCOUNT, roles: ['expert'] }),
  },
  {
    // A route with no standby configured: the editor shows the unticked choice only.
    name: 'workers-routes-no-standby',
    make: () => createElement(WorkersPage as ComponentType<WorkersPageProps>, { initialTab: 'routes' }),
    seedClient: (client) => seedExecutors(client, EXECUTOR_CASES, [{
      work_kind: 'text_analysis', primary_connection_id: EXECUTOR_READY.connection.connection_id,
      set_at: '2026-10-21T10:00:00Z', set_by: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
    }]),
  },
  {
    // No route at all: a run would be refused, and the screen says so.
    name: 'workers-routes-unassigned',
    make: () => createElement(WorkersPage as ComponentType<WorkersPageProps>, { initialTab: 'routes' }),
    seedClient: (client) => seedExecutors(client, EXECUTOR_CASES, []),
  },
  ...EXECUTOR_SECRET_OUTCOMES.map((outcome) => ({
    name: `executor-secret-form-${outcome}`,
    make: () => createElement(SetExecutorSecretForm, { connectionId: EXECUTOR_READY.connection.connection_id, outcome }),
  })),
  {
    name: 'executor-secret-form-fresh',
    make: () => createElement(SetExecutorSecretForm, { connectionId: EXECUTOR_READY.connection.connection_id }),
  },
  {
    name: 'executor-command-failure',
    make: () => createElement(CommandFailure, {
      failure: { kind: 'refusal', detail: 'Модель: эта модель не закреплена в замке провайдера, выберите модель из списка.', correlationId: '3f2504e0-4f89-41d3-9a0c-0305e82c3301' },
    }),
  },
  {
    name: 'executor-create-form',
    make: () => createElement(CreateConnectionForm, { pinnedModels: EXECUTOR_PINNED }),
  },
  ...(['http_api', 'ssh_command', 'pull'] as const).map((kind) => ({
    name: `executor-settings-fields-${kind}`,
    make: () => createElement('form', null, createElement(SettingsFields, { kind, pinnedModels: EXECUTOR_PINNED, idPrefix: `lang-${kind}` })),
  })),
  {
    // A tunnelled HTTP API connection and a revision of it: the SSH endpoint fields appear.
    name: 'executor-settings-fields-tunnel',
    make: () => {
      const tunnel = EXECUTOR_CASES.find((one) => one.detail.revisions[0]?.transport === 'ssh_tunnel');
      return createElement('form', null, createElement(SettingsFields, {
        kind: 'http_api', pinnedModels: EXECUTOR_PINNED, initial: tunnel?.detail.revisions[0], idPrefix: 'lang-tunnel',
      }));
    },
  },
  {
    name: 'executor-revise-form',
    make: () => createElement(ReviseConnectionForm, {
      connection: EXECUTOR_READY.connection, revision: EXECUTOR_READY.detail.revisions[0],
      pinnedModels: EXECUTOR_PINNED, holdsKey: true, onClose: () => {},
    }),
  },
  ...([false, true] as const).map((changed) => ({
    name: `executor-host-key-control-${changed ? 'changed' : 'unpinned'}`,
    make: () => {
      const ssh = EXECUTOR_OUTCOME_CASES.find(([outcome]) => outcome === 'host_key_unpinned')![1];
      return createElement(HostKeyControl, {
        connectionId: ssh.connection.connection_id, revision: ssh.detail.revisions[0]!,
        observedHostKey: 'наблюдаемый-отпечаток-узла', changed,
      });
    },
  })),
  {
    // `EXEC-PULL-01`: the box a freshly issued runner token appears in, which a press reaches.
    name: 'executor-runner-token-shown',
    make: () => createElement(IssuedTokenView, {
      issued: {
        token: 'токен-значение-для-показа',
        runner_token: runnerToken({
          token_id: executorTokenId(9), connection_id: EXECUTOR_PULL_ONLINE.connection.connection_id,
          token_prefix: 'токен-НОВ9',
        }),
      },
      onClose: () => {},
    }),
  },
  ...([false, true] as const).map((hasKey) => ({
    name: `executor-ssh-key-control-${hasKey ? 'replace' : 'first'}`,
    make: () => createElement(SshKeyControl, { connectionId: EXECUTOR_READY.connection.connection_id, hasKey }),
  })),
  /*
   * `W55A-WEB-NORMS`. The «Нормы» branches a cache state does not select: the three ways a
   * search is refused by the server, the empty first and later pages of each list, and the
   * PDF panel's other shapes (no binding, a page past the end, no page asked for, open).
   */
  ...(['norms_search_too_broad', null] as const).map((constraint) => ({
    name: `norms-search-refused-${constraint ?? 'request'}`,
    make: () => createElement(NormsPage, { roles: ['expert'], query: NORM_QUERY }),
    seedClient: (client: Client) => seedError(client, KEYS.normSearch, normsRefusal(
      'validation_failed', constraint === null ? {} : { constraint },
    )),
  })),
  {
    name: 'norms-search-no-current-snapshot',
    make: () => createElement(NormsPage, { roles: ['expert'], query: NORM_QUERY }),
    seedClient: (client: Client) => seedError(client, KEYS.normSearch, normsRefusal(
      'required_norm_unavailable', { reference_kind: 'norms_snapshot' },
    )),
  },
  /*
   * `W57B-NORMS-CATALOGUE-XLSX-01`. The catalogue view of «Нормы»: loaded, refused, failed
   * and pending, and the table's empty pages.
   */
  {
    name: 'norms-catalogue-loaded',
    make: () => createElement(NormsPage, { roles: ['expert'], catalogue: { q: null, kind: null } }),
  },
  {
    name: 'norms-catalogue-refused',
    make: () => createElement(NormsPage, { roles: ['expert'], catalogue: { q: null, kind: null } }),
    seedClient: (client: Client) => seedError(client, KEYS.normCatalogue, normsRefusal(
      'validation_failed', { field: 'q', constraint: 'format' },
    )),
  },
  {
    name: 'norms-catalogue-failed',
    make: () => createElement(NormsPage, { roles: ['expert'], catalogue: { q: null, kind: null } }),
    seedClient: (client: Client) => seedError(client, KEYS.normCatalogue, normsRefusal(
      'dependency_unavailable', {},
    )),
  },
  {
    name: 'norms-catalogue-pending',
    make: () => createElement(NormsPage, { roles: ['expert'], catalogue: { q: null, kind: null } }),
    seedClient: (client: Client) => { client.removeQueries({ queryKey: KEYS.normCatalogue }); },
  },
  {
    name: 'norm-catalogue-nothing-kept',
    make: () => createElement(NormCatalogueTable, { items: [], total: 0, filtered: true, onFirst: null, onNext: null }),
  },
  {
    name: 'norm-catalogue-empty-snapshot',
    make: () => createElement(NormCatalogueTable, { items: [], total: 0, filtered: false, onFirst: null, onNext: null }),
  },
  {
    name: 'norm-catalogue-empty-later-page',
    make: () => createElement(NormCatalogueTable, { items: [], total: 3, filtered: false, onFirst: () => {}, onNext: null }),
  },
  {
    name: 'norm-search-nothing-found',
    make: () => createElement(NormSearchResults, { items: [], onFirst: null, onNext: null }),
  },
  {
    name: 'norm-search-empty-later-page',
    make: () => createElement(NormSearchResults, { items: [], onFirst: () => {}, onNext: null }),
  },
  {
    name: 'norm-paragraphs-empty-later-page',
    make: () => createElement(NormParagraphList, {
      normDocumentId: NORM_DOCUMENT_ID, items: [], onFirst: () => {}, onNext: null,
    }),
  },
  {
    name: 'norm-history-empty-later-page',
    make: () => createElement(NormSnapshotHistory, { items: [], onFirst: () => {}, onNext: null }),
  },
  {
    name: 'norm-snapshots-current-beyond',
    make: () => createElement(NormSnapshotList, {
      items: NORM_SNAPSHOTS.slice(1), current: { kind: 'beyond' }, canDesignate: true, busy: false,
      onDesignate: () => {},
    }),
  },
  ...([
    ['unbound', normDocument({ content_available: false }), 12, null],
    ['page-beyond', normDocument(), 99, null],
    ['closed', normDocument(), null, null],
    ['open', normDocument(), 12, 'blob:http://web.test/0f0e9d8c-7b6a-4948-b726-150413021100'],
  ] as const).map(([shape, document, page, documentUrl]) => ({
    name: `norm-pdf-${shape}`,
    make: () => createElement(NormPdf, { document, page, documentUrl, isLoading: false, error: null }),
  })),
  /*
   * `app/not-found.tsx` is a FILE in the route tree and not an address, so no derivation
   * reaches it and it stays a hand-written entry. It carried a WHOLE ENGLISH SENTENCE to a
   * reviewer who had mistyped an address until the wave that first rendered it — `D-53`
   * again, on a screen nobody had rendered, three waves after `D-53` was closed.
   */
  { name: 'not-found', make: () => createElement(NotFound, {}) },
  /*
   * `app/error.tsx`, for the same reason as `not-found` (granted at the `W50-REGISTRY-01`
   * merge, ruling 2): a file in the route tree, not an address. Rendered with a thrown error
   * whose message is English and a numeric digest, so a leak of the message would read here.
   */
  {
    name: 'error-boundary',
    make: () =>
      createElement(ErrorBoundary, {
        error: Object.assign(new TypeError('Cannot read properties of undefined'), { digest: '3141592653' }),
        reset: () => {},
      }),
  },
  /*
   * The evidence viewer and the decision history are rendered here as widgets rather
   * than through the review page, because their failure branches are chosen by props
   * the page only produces from a query state a static pass cannot put it in.
   * `tests/unit/styles/screens.ts` has rendered widgets directly since wave 32 for the
   * same reason.
   */
  {
    name: 'evidence-viewer-no-evidence',
    make: () =>
      createElement(EvidenceViewer, {
        observation: { ...finding().observation, evidence: [] },
        activePage: 1,
        onPageChange: () => {},
        documentUrl: null,
      }),
  },
  {
    name: 'evidence-viewer-no-document',
    make: () =>
      createElement(EvidenceViewer, {
        observation: finding().observation,
        activePage: 7,
        onPageChange: () => {},
        documentUrl: null,
      }),
  },
  {
    name: 'decision-history-pending',
    make: () => createElement(DecisionHistory, { events: [], isLoading: true }),
  },
  {
    name: 'knowledge-base-invalid-vocabulary',
    make: () =>
      createElement(KnowledgeBase, {
        records: [
          { ...record(), current_verdict: 'guessed' } as unknown as DecisionRecord,
        ],
      }),
  },
  ...BLOCKS_SHAPES,
  /*
   * `W59-SECTION-UI-01`. The stage-and-section panel's shapes an address does not select:
   * the confirmed classification (with a synthetic section lacking a profile, and after the
   * reader's own confirmation was refused with `409`), the expert's form in flight and
   * refused (`409`, `403`), a review that could not be read, and the project structure with
   * documents confirmed under both stages. Each is a branch chosen by a settled mutation or
   * by a review this matrix's shared seeds keep unconfirmed.
   */
  {
    name: 'version-classification-confirmed',
    make: () =>
      createElement(VersionClassificationView, {
        address: { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID, versionUid: VERSION_UID },
        review: sectionReview({
          classification: classification({ project_stage: 'R', section_code: 'GP' }),
          options: sectionReview().options.map((option) => ({
            ...option, executable: option.section_code !== 'GP',
          })),
        }),
        roles: ['expert'],
        conflict: true,
        onConflict: () => undefined,
      }),
  },
  /*
   * `CLASSIFICATION-CORRECTION-01`. The confirmed panel after a correction (revision, history
   * with reasons, the «Исправить» control), with the correction form open, and the form in
   * flight and refused in every way a reader can be shown.
   */
  ...([false, true] as const).map((correcting) => ({
    name: `version-classification-corrected${correcting ? '-correcting' : ''}`,
    make: () =>
      createElement(VersionClassificationView, {
        address: { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID, versionUid: VERSION_UID },
        review: sectionReview({
          classification: classification({
            project_stage: 'R',
            section_code: 'KJ',
            revision: 2,
          }),
          revisions: CLASSIFICATION_HISTORY,
        }),
        roles: ['expert'],
        conflict: false,
        onConflict: () => undefined,
        correcting,
        onCorrecting: () => undefined,
      }),
  })),
  {
    name: 'correct-version-classification-form-pending',
    make: () =>
      createElement(CorrectVersionClassificationFormView, {
        review: sectionReview(),
        current: classification({ project_stage: 'R', section_code: 'KJ', revision: 2 }),
        stage: 'P',
        section: 'KJ',
        reason: 'Лист относится к проектной документации',
        pending: true,
        failure: null,
        onStage: () => undefined,
        onSection: () => undefined,
        onReason: () => undefined,
        onSubmit: () => undefined,
        onCancel: () => undefined,
      }),
  },
  ...(['stale', 'not_classified', 'unchanged', 'reason', 'not_permitted'] as const).map((kind) => ({
    name: `correct-version-classification-form-${kind}`,
    make: () =>
      createElement(CorrectVersionClassificationFormView, {
        review: sectionReview(),
        current: classification({ project_stage: 'R', section_code: 'KJ', revision: 2 }),
        stage: 'P',
        section: 'AR',
        reason: kind === 'reason' ? '...' : 'Лист относится к проектной документации',
        pending: false,
        failure: {
          kind,
          detail: CORRECTION_DETAILS[kind],
          correlationId: '0f0e9d8c-7b6a-4948-b726-150413021100',
          retryable: false,
        },
        onStage: () => undefined,
        onSection: () => undefined,
        onReason: () => undefined,
        onSubmit: () => undefined,
        onCancel: () => undefined,
      }),
  })),
  {
    name: 'classify-version-form-pending',
    make: () =>
      createElement(ClassifyVersionFormView, {
        review: sectionReview({ recognised_text_consulted: false }),
        stage: 'R',
        section: 'PB',
        pending: true,
        failure: null,
        onStage: () => undefined,
        onSection: () => undefined,
        onConfirm: () => undefined,
      }),
  },
  ...(['already_classified', 'not_permitted'] as const).map((kind) => ({
    name: `classify-version-form-${kind}`,
    make: () =>
      createElement(ClassifyVersionFormView, {
        review: sectionReview({
          options: sectionReview().options.map((option) => ({ ...option, suggestion: null })),
        }),
        stage: 'P',
        section: 'AR',
        pending: false,
        failure: {
          kind,
          detail: kind === 'already_classified' ? ALREADY_CLASSIFIED_DETAIL : CLASSIFY_NOT_PERMITTED_DETAIL,
          correlationId: '0f0e9d8c-7b6a-4948-b726-150413021100',
          retryable: false,
        },
        onStage: () => undefined,
        onSection: () => undefined,
        onConfirm: () => undefined,
      }),
  })),
  /*
   * `W59-DECISION-CARRYOVER-01`. «Перенести решение»: the confirmation (with a severity and a
   * comment), in flight, carried, already carried, and every refusal a reader can be shown.
   */
  ...([false, true] as const).map((pending) => ({
    name: `carry-over-decision-confirming${pending ? '-pending' : ''}`,
    make: () =>
      createElement(CarryOverDecisionView, {
        candidate: CARRYOVER_CANDIDATE,
        target: { finding_uid: CARRYOVER_CANDIDATE.target_finding_uid, category: 'layout',
          finding_text: 'Нет дверного проёма', page_numbers: [1] },
        confirming: true,
        pending,
        result: null,
        failure: null,
        onOpen: () => undefined,
        onConfirm: () => undefined,
        onCancel: () => undefined,
      }),
  })),
  ...([false, true] as const).map((replayed) => ({
    name: `carry-over-decision-${replayed ? 'replayed' : 'carried'}`,
    make: () =>
      createElement(CarryOverDecisionView, {
        candidate: CARRYOVER_CANDIDATE,
        target: { finding_uid: CARRYOVER_CANDIDATE.target_finding_uid, category: 'layout',
          finding_text: 'Нет дверного проёма', page_numbers: [1] },
        confirming: false,
        pending: false,
        result: {
          event: {
            decision_id: `dec_${ULID.slice(0, -1)}9`, finding_uid: CARRYOVER_CANDIDATE.target_finding_uid,
            finding_observation_id: `fobs_${ULID}`, event_type: 'accept', verdict: 'accepted',
            severity: 'critical', comment: 'Решение перенесено из версии 1.', author_label: 'Иванова Е. В.',
            recorded_at: '2026-10-20T09:00:00Z',
          },
          current_verdict: 'accepted',
          replayed,
          source_finding_uid: CARRYOVER_CANDIDATE.source_finding_uid,
          source_decision_id: CARRYOVER_CANDIDATE.source_decision.decision_id,
          source_version_uid: VERSION_UID,
          source_version_ordinal: 1,
          target_version_uid: NEWER_VERSION_UID,
          mode: 'version',
        },
        failure: null,
        onOpen: () => undefined,
        onConfirm: () => undefined,
        onCancel: () => undefined,
      }),
  })),
  ...([
    ...(Object.keys(CARRYOVER_CONFLICT_TEXT) as (keyof typeof CARRYOVER_CONFLICT_TEXT)[]).map(
      (kind) => ({ kind, detail: CARRYOVER_CONFLICT_TEXT[kind] }),
    ),
    { kind: 'not_permitted' as const, detail: CARRYOVER_NOT_PERMITTED_DETAIL },
  ]).map(({ kind, detail }) => ({
    name: `carry-over-decision-${kind}`,
    make: () =>
      createElement(CarryOverDecisionView, {
        candidate: CARRYOVER_CANDIDATE,
        target: { finding_uid: CARRYOVER_CANDIDATE.target_finding_uid, category: 'layout',
          finding_text: 'Нет дверного проёма', page_numbers: [1] },
        confirming: false,
        pending: false,
        result: null,
        failure: { kind, detail, correlationId: '0f0e9d8c-7b6a-4948-b726-150413021100', retryable: false },
        onOpen: () => undefined,
        onConfirm: () => undefined,
        onCancel: () => undefined,
      }),
  })),
  /*
   * `W60-OPT-MATCH-01`. «Спецификация и цены» is a widget the «Оптимизация» tab mounts, so no
   * address selects it yet: its container in every documents state (pending, no АР set,
   * refused), its own read pending and refused, and the answer in every state it can carry.
   */
  { name: 'specification-prices-section', make: () => createElement(SpecificationPricesSection, { projectUid: PROJECT_UID }) },
  {
    name: 'specification-prices-pending',
    make: () => createElement(SpecificationPricesSection, { projectUid: PROJECT_UID }),
    seedClient: specificationSets,
  },
  {
    name: 'specification-prices-refused',
    make: () => createElement(SpecificationPricesSection, { projectUid: PROJECT_UID }),
    seedClient: (client) => {
      specificationSets(client);
      seedError(
        client,
        queryKeys.optimisation.specificationPrices(PROJECT_UID, DOCUMENT_UID, 0, SPECIFICATION_ROW_LIMIT),
        apiError(503, 'dependency_unavailable'),
      );
    },
  },
  {
    name: 'specification-prices-ready',
    make: () => createElement(SpecificationPricesAnswer, { answer: specificationAnswer(), onPage: () => undefined }),
  },
  {
    name: 'specification-prices-ready-empty',
    make: () =>
      createElement(SpecificationPricesAnswer, {
        answer: specificationAnswer({
          extraction: { ...specificationAnswer().extraction!, table_count: 0, row_count: 0, skipped_count: 0, skipped: [] },
          matching: {
            algorithm: 'price-match-v1',
            counts: { matched: 0, ambiguous: 0, unmatched: 0 },
            totals: [],
            excluded: { no_position: 0, unit_mismatch: 0, row_unit_missing: 0, ambiguous: 0, quantity_not_numeric: 0 },
          },
          rows: { offset: 0, limit: SPECIFICATION_ROW_LIMIT, total: 0, next_offset: null, items: [] },
        }),
        onPage: () => undefined,
      }),
  },
  ...(['version_unclassified', 'section_not_ar', 'price_list_missing', 'analysis_missing', 'text_unavailable', 'specification_too_large'] as const).map(
    (state) => ({
      name: `specification-prices-${state}`,
      make: () =>
        createElement(SpecificationPricesAnswer, {
          answer: specificationAnswer({
            ...SPECIFICATION_STOPPED,
            state,
            ...(state === 'version_unclassified' ? { project_stage: null, section_code: null, price_list: null } : {}),
            ...(state === 'section_not_ar' ? { section_code: 'KJ', price_list: null } : {}),
            ...(state === 'price_list_missing' ? { price_list: null } : {}),
            ...(state === 'text_unavailable' ? { run_id: RUN_ID } : {}),
          }),
          onPage: null,
        }),
    }),
  ),
  /*
   * `NORM-REFS-RUN-01`. «Нормативные ссылки» is a section of the run page's progress widget for a
   * finished run: its container pending and refused, and the answer in every state it can carry.
   */
  { name: 'norm-references-section', make: () => createElement(NormReferencesSection, { runId: RUN_ID }) },
  {
    name: 'norm-references-section-ready',
    make: () => createElement(NormReferencesSection, { runId: RUN_ID }),
    seedClient: (client) => client.setQueryData(queryKeys.runs.normReferences(RUN_ID), normReferencesAnswer()),
  },
  {
    name: 'norm-references-refused',
    make: () => createElement(NormReferencesSection, { runId: RUN_ID }),
    seedClient: (client) => seedError(client, queryKeys.runs.normReferences(RUN_ID), apiError(503, 'dependency_unavailable')),
  },
  { name: 'norm-references-ready', make: () => createElement(NormReferencesAnswer, { answer: normReferencesAnswer() }) },
  {
    name: 'norm-references-ready-empty',
    make: () =>
      createElement(NormReferencesAnswer, {
        answer: normReferencesAnswer({
          counts: { in_corpus: 0, newer_edition: 0, older_edition_only: 0, not_in_corpus: 0, not_recognised: 0 },
          occurrence_count: 0, unread_pages: [], items: [], unrecognised: [],
        }),
      }),
  },
  ...(['snapshot_not_pinned', 'text_unavailable', 'too_many_citations'] as const).map((state) => ({
    name: `norm-references-${state}`,
    make: () =>
      createElement(NormReferencesAnswer, {
        answer: { run_id: RUN_ID, version_uid: VERSION_UID, state, page_count: 12 },
      }),
  })),
  /*
   * `W63-SECTION-FORM7-01`. «Оптимизация разделов» is the whole of `/section-optimisation`, whose
   * route-derived screen is its read pending; its own read refused, and the answer in every
   * shape it can carry, are rendered here through the widget's parts.
   */
  { name: 'section-specification-section', make: () => createElement(SectionSpecificationSection) },
  {
    name: 'section-specification-refused',
    make: () => createElement(SectionSpecificationSection),
    seedClient: (client) => seedError(client, sectionKey(), apiError(503, 'dependency_unavailable')),
  },
  {
    name: 'section-specification-ready',
    make: () => createElement(SectionSpecificationAnswer, { answer: sectionAnswer(), onPage: () => undefined, onSelectProject: () => undefined }),
  },
  {
    name: 'section-specification-paged',
    make: () => createElement(SectionSpecificationAnswer, { answer: sectionPagedAnswer(), onPage: () => undefined, onSelectProject: () => undefined }),
  },
  {
    name: 'section-specification-narrowed',
    make: () =>
      createElement(SectionSpecificationAnswer, {
        answer: sectionAnswer({
          project_filter: PROJECT_UID as never, excluded: [], excluded_count: 0, source_count: 4, row_count: 4,
          projects: [sectionAnswer().projects[0]!],
          rows: { ...sectionAnswer().rows!, offset: 0, total: 4, next_offset: null, items: sectionAnswer().rows!.items.slice(0, 4) },
        }),
        onPage: null,
        onSelectProject: null,
      }),
  },
  {
    name: 'section-specification-searched-nothing',
    make: () =>
      createElement(SectionSpecificationAnswer, {
        answer: sectionAnswer({
          query: 'ёлочка',
          rows: { offset: 0, limit: SECTION_ROW_LIMIT, total: 0, next_offset: null, items: [] },
        }),
        onPage: () => undefined,
        onSelectProject: () => undefined,
      }),
  },
  {
    name: 'section-specification-no-rows',
    make: () =>
      createElement(SectionSpecificationAnswer, {
        answer: sectionAnswer({ row_count: 0, rows: { offset: 0, limit: SECTION_ROW_LIMIT, total: 0, next_offset: null, items: [] } }),
        onPage: () => undefined,
        onSelectProject: () => undefined,
      }),
  },
  {
    name: 'section-specification-empty',
    make: () =>
      createElement(SectionSpecificationAnswer, {
        answer: sectionAnswer({
          projects: [], excluded: [], excluded_count: 0, source_count: 0, row_count: 0,
          rows: { offset: 0, limit: SECTION_ROW_LIMIT, total: 0, next_offset: null, items: [] },
        }),
        onPage: () => undefined,
        onSelectProject: () => undefined,
      }),
  },
  {
    name: 'section-specification-empty-project',
    make: () =>
      createElement(SectionSpecificationAnswer, {
        answer: sectionAnswer({
          project_filter: PROJECT_UID as never, projects: [], excluded: [], excluded_count: 0, source_count: 0, row_count: 0,
          rows: { offset: 0, limit: SECTION_ROW_LIMIT, total: 0, next_offset: null, items: [] },
        }),
        onPage: null,
        onSelectProject: null,
      }),
  },
  ...(['projects', 'sources', 'rows'] as const).map((reason) => ({
    name: `section-specification-too-large-${reason}`,
    make: () =>
      createElement(SectionSpecificationAnswer, {
        answer: sectionAnswer({
          ...SECTION_NO_ROWS,
          state: 'section_too_large',
          limit_reason: reason,
          ...(reason === 'projects' ? { projects: [], excluded: [], excluded_count: 0, source_count: 0 } : {
            projects: sectionAnswer().projects.map((item) => ({
              ...item, price_state: 'not_read' as const, price_list: null, matching: null, row_count: 0,
              sources: item.sources.map((source) => ({
                ...source, state: 'not_read' as const, run_id: null, text_layer_sha256: null, row_count: null,
                table_count: null, skipped_by_reason: null,
              })),
            })),
          }),
        }),
        onPage: null,
        onSelectProject: () => undefined,
      }),
  })),
  {
    name: 'version-classification-read-failed',
    make: () =>
      createElement(VersionClassification, {
        address: { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID, versionUid: VERSION_UID },
        roles: ['expert'],
      }),
    seedClient: (client) => seedError(client, KEYS.sectionReview, apiError(503, 'dependency_unavailable')),
  },
  {
    name: 'project-structure-classified',
    make: () =>
      createElement(ProjectStructureView, {
        projectUid: PROJECT_UID,
        items: [
          version({ classification: classification() }),
          version({
            document_uid: `doc_${ULID.slice(0, -1)}C`,
            version_uid: `ver_${ULID.slice(0, -1)}C`,
            classification: classification({ project_stage: 'R', section_code: 'KJ' }),
          }),
          version({ document_uid: `doc_${ULID.slice(0, -1)}D`, version_uid: `ver_${ULID.slice(0, -1)}D` }),
        ],
        hasNextPage: true,
      }),
  },
];

const SCREENS: readonly ScreenCase[] = [
  ...DERIVED_SCREENS,
  ...EXTRA_SHAPES,
];

/**
 * Every screen in every cache state one static render pass can reach.
 *
 * Three states and not one, because `D-53`'s survivors were spread across them: `Загрузка:
 * the run…` exists only while a question is unanswered, the version panel's labels exist
 * only once it is answered, and the failure layer -- where `Correlation id` survived two
 * reports of a translated interface -- exists only when it is refused.
 */
export const CACHE_STATES: readonly {
  readonly state: string;
  readonly run: Partial<RunStatus> | null;
}[] = [
  { state: 'cold', run: null },
  { state: 'loaded', run: {} },
  { state: 'failed-run', run: { state: 'failed', terminal_reason: 'analysis_failed', published_finding_count: 0 } },
  /*
   * `BETA-CONTRACT-SEAL-01` (`D-179`). The two run-routing codes can name a stopped run's reason
   * only if a later path stores one (the stored vocabulary admits them), and `terminal-reason.ts`
   * has a sentence for each. A screen that renders that sentence is judged here like any other,
   * so an English word in either one reddens the guard instead of waiting for a stored row.
   */
  { state: 'failed-run-unclassified', run: { state: 'failed', terminal_reason: 'version_classification_required', published_finding_count: 0 } },
  { state: 'failed-run-no-profile', run: { state: 'failed', terminal_reason: 'section_profile_unavailable', published_finding_count: 0 } },
  { state: 'partial-run', run: { state: 'partial', degradation_set: ['text_analysis'] } },
  {
    state: 'ar-v3-beta-published',
    run: {
      state: 'published', analysis_profile_id: AR_V3_BETA_PROFILE_ID,
      published_finding_count: 0,
      stages: [{ stage_id: 'ar_v3_citation_review', status: 'succeeded' }],
    },
  },
  { state: 'running', run: { state: 'running', terminal_at: null, published_finding_count: 0 } },
  { state: 'refused', run: null },
  { state: 'empty', run: null },
  /*
   * `W46-DASH`, 2026-09-25. Everything else loads; the version in scope has zero runs.
   * See `runsEmptyClient` for why `empty` (which also empties `KEYS.projects`) does not
   * already cover this — a screen that reads a listing rather than a route param renders
   * differently when a project exists and its runs do not than when nothing does.
   */
  { state: 'runs-empty', run: null },
  /*
   * A state in which every listing has a NEXT page, added 2026-09-22 by `W38-KB`.
   *
   * Eight English words were on these screens -- `Next page` and `First page` in four list
   * widgets -- and this guard rendered none of them, because every seeded page carried
   * `next_cursor: null` and the pager renders nothing at all when it does. Same shape as
   * the empty branch `W32-SEE` found and the four run states a wave-33 judge found: the
   * guard was sound and BLIND, and the blind spot was a whole control rather than a label.
   *
   * `First page` is still beyond a static pass: it renders only when the widget's own
   * `cursor` state is set, and one render cannot set it. That half is stated as a limit
   * rather than left to look like coverage.
   */
  { state: 'paged', run: null },
  /*
   * The other four run states, added 2026-09-22 after a mutation failed to redden.
   *
   * Putting `cancelled` back as a raw contract value left this guard GREEN, and the rule is
   * to establish whether the guard is weak or the mutation insufficient. It was the
   * mutation: the `cancelled` arm is reached only by a cancelled run, and this matrix
   * rendered four of the eight run states. The guard was sound and BLIND — four arms of
   * `run-progress` had never been rendered by it, and an English string in any of them would
   * have passed.
   *
   * Same shape as `W32-SEE`'s own first mutation, which reddened nothing because no list
   * widget's empty branch was ever rendered. **A mutation that dies quietly is a coverage
   * report, not a clean bill.**
   */
  { state: 'cancelled-run', run: { state: 'cancelled', published_finding_count: 0 } },
  { state: 'created-run', run: { state: 'created', terminal_at: null, published_finding_count: 0 } },
  { state: 'queued-run', run: { state: 'queued', terminal_at: null, published_finding_count: 0 } },
  { state: 'validating-run', run: { state: 'validating', terminal_at: null, published_finding_count: 0 } },
  /*
   * The OTHER provider mode and the OTHER cost basis, added by `W41-BLIND`.
   *
   * Every other state in this matrix seeds `provider_mode: 'recorded'` and
   * `cost_basis: 'measured'`, so `live` and `estimated` -- two contract members that the
   * owner's ruling puts on screen in Russian, and that a PHOTOGRAPH of the run screen
   * caught in English once already -- were rendered by no state here. The guard was sound
   * and blind, for the seventh and eighth time, and in the same file.
   *
   * One state rather than two: they are independent fields of the same reading, and
   * nothing on the screen couples them.
   */
  {
    state: 'live-estimated-run',
    run: { provider_mode: 'live', cost_basis: 'estimated' },
  },
  /*
   * `EXEC-SEAL-01` (`R-143f`): the third cost basis. A run on a connection that has no per-call
   * cost is `unmetered`; the run screen prints the caption «не тарифицируется» and no figure.
   */
  { state: 'unmetered-run', run: { cost_basis: 'unmetered' } },
  /*
   * A version with TWO runs of it, added 2026-09-24 by `W43-COMPARE`. See `twoRunClient`
   * for why one run is not enough and for which verdict each fact of the pair reaches.
   *
   * `run: null` because this state builds its own pair rather than overriding the single
   * seeded run, the way `empty`, `refused` and `paged` do.
   */
  { state: 'two-runs', run: null },
  /*
   * `W59-VERSION-COMPARE-01`. The version comparison's four static branches: the set's
   * version list in flight, two versions with the comparison in flight, the comparison
   * answered (every sheet status, a diff page with a too-large sheet and a next page, every
   * finding proposal kind) and the comparison refused. See `twoVersionClient`.
   */
  { state: 'versions-pending', run: null },
  { state: 'two-versions', run: null },
  { state: 'two-versions-compared', run: null },
  { state: 'two-versions-refused', run: null },
];

export function renderedScreens(): readonly { readonly where: string; readonly markup: string }[] {
  // `W55B-FIX` (Y-2): a portal crop's address is built in the transport seam from the
  // configured base, as the deployed build has it; set for this pass only and restored.
  const base = process.env.NEXT_PUBLIC_API_BASE_URL;
  process.env.NEXT_PUBLIC_API_BASE_URL = '/bff/v1';
  try {
    return renderEveryScreen();
  } finally {
    if (base === undefined) delete process.env.NEXT_PUBLIC_API_BASE_URL;
    else process.env.NEXT_PUBLIC_API_BASE_URL = base;
  }
}

function renderEveryScreen(): readonly { readonly where: string; readonly markup: string }[] {
  const out: { where: string; markup: string }[] = [];
  const states = CACHE_STATES;
  for (const screen of SCREENS) {
    const loaded = screen.name === 'review' ? loadedReviewClient : loadedClient;
    for (const { state, run: overrides } of states) {
      const client =
        state === 'cold'
          ? newClient()
          : state === 'refused'
            ? failedClient()
            : state === 'empty'
              ? emptyClient()
              : state === 'runs-empty'
                ? runsEmptyClient(loaded)
                : state === 'paged'
                  ? pagedClient(loaded)
                  : state === 'two-runs'
                    ? twoRunClient(loaded)
                    : state === 'versions-pending'
                      ? versionsPendingClient(loaded)
                      : state === 'two-versions'
                        ? twoVersionClient(loaded, null)
                        : state === 'two-versions-compared'
                          ? twoVersionClient(loaded, comparisonBody())
                          : state === 'two-versions-refused'
                            ? twoVersionClient(
                                loaded,
                                comparisonBody({
                                  outcome: 'refused',
                                  refusal: { reason: 'project_stage_mismatch', side: null },
                                  comparison_sha256: null,
                                  sheets: [],
                                  sheet_diffs: null,
                                  findings: null,
                                }),
                              )
                            : loaded(overrides ?? {});
      screen.seedClient?.(client);
      out.push({ where: `${screen.name} (${state})`, markup: renderScreen(client, screen.make()) });
    }
  }
  const badAccount = { ...ADMIN_USER_ACCOUNT, display_label: '' };
  const accountClient = loadedClient();
  accountClient.setQueryData(KEYS.account, badAccount);
  out.push({ where: 'account (invalid data)', markup: renderScreen(accountClient, createElement(AccountPage, { profileComplete: true })) });
  const userClient = loadedClient();
  userClient.setQueryData(KEYS.user, badAccount);
  out.push({ where: 'user-card (invalid data)', markup: renderScreen(userClient, createElement(UserCard, { userUid: badAccount.user_uid })) });
  /*
   * `W61-DISPATCHER-01`: an assignment's history opens only when its row's «История» is
   * pressed, which one static render cannot do — so the widget is rendered on its own, in
   * the three states a cache can hold: in flight, answered and failed.
   */
  const historyOf = (client: Client) =>
    renderScreen(client, createElement(AssignmentHistory, { assignmentUid: ASSIGNMENT_DETAIL.assignment.assignment_uid }));
  out.push({ where: 'assignment-history (cold)', markup: historyOf(newClient()) });
  out.push({ where: 'assignment-history (loaded)', markup: historyOf(loadedClient()) });
  out.push({ where: 'assignment-history (failed)', markup: historyOf(failedClient()) });
  /*
   * The review screen with its detail and history still in flight, appended once.
   *
   * It is looked up BY NAME. This read `SCREENS[5]!.make()`, which made the position of
   * every entry load-bearing -- the old list carried three comments warning that a screen
   * inserted anywhere but the end would silently render a different page under the review
   * screen's name. The derived set is sorted by address, so the index would now be wrong
   * as well as fragile. A name that no longer exists throws here rather than rendering the
   * wrong screen quietly.
   */
  const review = SCREENS.find((screen) => screen.name === 'review');
  if (review === undefined) {
    throw new Error(
      'no screen named `review` is in the derived set, so the detail-pending state below ' +
        'would render nothing. The review address was renamed or removed; say which.',
    );
  }
  out.push({
    where: 'review (detail-pending)',
    markup: renderScreen(reviewDetailPendingClient(), review.make()),
  });
  /*
   * Every (screen, dynamic segment) pair with that ONE segment malformed, derived from the
   * directory layout in `tests/unit/screens/route-screens.ts`.
   *
   * Three of these were hand-written entries in `SCREENS` -- `project-detail-bad-address`
   * and two siblings -- and the comparison screen's two, the run screen's two and the
   * review screen's two were rendered by nothing. The refusal wording is prose a reviewer
   * reads only when they have mistyped an address, which is exactly the class `W32-SEE`
   * measured as the place an English sentence survives.
   *
   * Appended once rather than multiplied by `CACHE_STATES`: a screen that refuses its own
   * address returns before it reads a cache, and a screen that does not refuse renders the
   * same markup the well-formed pass already covers in all seventeen states.
   */
  for (const variant of malformedVariants(IDENTITIES)) {
    out.push({ where: variant.name, markup: renderScreen(newClient(), variant.make()) });
  }
  return out;
}

// ===================================================================== the assertions

/**
 * The enumerated schemas the owner's 2026-09-22 ruling put ON SCREEN IN RUSSIAN.
 *
 * WHY THIS SET HAS TO EXIST, and it is the guard correcting itself rather than being
 * extended. `contractVocabulary()` permits every `enum` value in `openapi.json` as visible
 * text. Under the previous rule -- contract vocabulary is not translated, because the
 * certification was driven by reading those words off the badges -- that was exactly right.
 *
 * The owner then ruled the other way: translate everything visible, and keep the machine
 * value in the `data-` attribute. `W30-CERT3` re-drove `PA-01` criterion 4 by reading
 * `[data-run-state]`, which is why that ruling costs the certification nothing.
 *
 * **And this guard went on permitting the English.** A whole integration pass translated
 * `published`, `pending`, `partial` and `accepted`, and the guard stayed green throughout --
 * green because it could not see a difference it was built to see. A judge then mutated a
 * label back to English and it stayed green again. **A guard that legitimises the class it
 * was built to catch is worse than no guard, because its silence is read as coverage.**
 *
 * **`StageId` joined them in wave 35, and the argument that kept it out was mine and was
 * wrong.** When the four above were removed I left `StageId` permitted, on the reasoning that
 * a stage id is an identifier a reviewer is deliberately shown beside a sentence. That is true
 * of `terminal_reason`, where `terminal-reason.ts` renders the code AND its meaning. It was
 * false of the stage table, where `<code>{row.stageId}</code>` was the ENTIRE first column and
 * no sentence accompanied any row -- so this allowlist excused the largest block of
 * untranslated text on the run screen, and `D-62` had to be opened by a person reading the
 * screen because the guard could not see it. `STAGE_LABELS` now names the nine stages and the
 * contract value keeps its home in `data-stage-id`.
 *
 * The others stay permitted and each for a stated reason: `ErrorCode` is the identifier case
 * that really does hold -- the code is rendered next to its meaning -- and `CostBasis` and
 * `DecisionEventType` are not rendered as bare words today, and forbidding a value nothing
 * renders would be a claim this guard cannot support.
 *
 * `visibleText()` reads text nodes and four attributes and **never `data-*`**, so the machine
 * value keeps its home and only the rendered word is judged.
 */
/*
 * `ProviderMode` and `CostBasis` joined this list on 2026-09-22, and the reason is a
 * correction to my own argument. When the list was written I left them out saying they are
 * "not rendered as bare words today, and forbidding a value nothing renders would be a claim
 * this guard cannot support."
 *
 * A PHOTOGRAPH OF THE RUN SCREEN FALSIFIED THAT. `live` rendered twice and `measured` once,
 * in Russian sentences, to a Russian reviewer — and this guard permitted every one of them
 * because they were in the permitted vocabulary. It rendered the screen, saw the words, and
 * had been told they were allowed.
 *
 * That is the second time an argument of mine about what renders excused real untranslated
 * text — `StageId` was the first. **I reasoned about what renders instead of looking.**
 */
const TRANSLATED_SCHEMAS = [
  'RunState',
  'StageStatus',
  'Verdict',
  'FindingCategory',
  'StageId',
  'ProviderMode',
  'CostBasis',
  // `W55B-WEB-BLOCKS`: the portal block's type and its page's geometry verdict, both rendered
  // by «Блоки» in Russian (`entities/block`'s vocabulary) with the value in a `data-` attribute.
  'PortalBlockType',
  'PortalGeometryState',
  // `W59-SECTION-UI-01`: a version's stage and section, said as «Стадия: П» and «Архитектурные
  // решения (АР)» with the contract value in a `data-` attribute. The Latin code is never text.
  'ProjectStage',
  'ProjectSection',
  // `WEB-HOOKS-PER-FINDING-01`: the severity the expert decided, said beside the verdict in the
  // decision history and the knowledge base as «важность Критическое» (`SEVERITY_LABELS`), with
  // the contract value in `data-severity` only. Left out, `critical` printed in its place would
  // have been read as contract vocabulary and permitted.
  'Severity',
  // `EXEC-HTTP-01`: «Подключения» says every kind, format, transport, billing, profile, client,
  // key purpose, probe state, probe outcome, identity basis, rate check and kind of work in
  // Russian, with the contract value in a `data-` attribute. Several are plain English words
  // (`direct`, `pull`, `timeout`, `mismatch`, `agent`), which must not be permitted bare.
  'ExecutorKind',
  'ExecutorApiFlavour',
  'ExecutorTransport',
  'ExecutorBilling',
  'ExecutorSshProfile',
  'ExecutorPullClient',
  'ExecutorSecretPurpose',
  'ExecutorProbeState',
  'ExecutorProbeOutcome',
  'ExecutorIdentityBasis',
  'ExecutorRateCheck',
  'ExecutorWorkKind',
] as const;

function translatedVocabulary(): ReadonlySet<string> {
  const openapi = readJson<OpenApi>(CONTRACT_PATH);
  const values = new Set<string>();
  for (const name of TRANSLATED_SCHEMAS) {
    const schema = openapi.components.schemas[name];
    if (schema === undefined) {
      throw new Error(
        `openapi.json declares no schema ${name}. This guard names it because the owner's ` +
          'ruling reaches it; a renamed schema must be re-argued here, not silently dropped.',
      );
    }
    for (const value of schema.enum ?? []) values.add(value);
  }
  return values;
}

const TRANSLATED = translatedVocabulary();

const VOCABULARY = new Set([...contractVocabulary()].filter((word) => !TRANSLATED.has(word)));

describe('the guard reads a contract rather than a list of words', () => {
  it('derives the whole published vocabulary from openapi.json', () => {
    // A relationship, never a count: `W30-LISTS`'s rule. These are read back out of the
    // derivation, so a contract that loses a code makes this red rather than merely
    // narrowing the allowlist in silence.
    // Still permitted as visible text, and each for a stated reason: identifiers a reviewer
    // is deliberately shown, and modes nothing renders as a bare word.
    for (const value of ['analysis_failed', 'accept']) {
      expect(VOCABULARY.has(value), `${value} is not in the contract's enums`).toBe(true);
    }
    // NO LONGER permitted as visible text, because the owner ruled them translated. The
    // assertion runs in both directions on purpose: the value is still in the contract, and
    // it is no longer in the permitted set. A schema renamed out of `TRANSLATED_SCHEMAS`
    // would make the first half red rather than silently re-permitting the word.
    for (const value of ['published', 'partial', 'failed', 'cancelled', 'queued', 'running',
      'validating', 'accepted', 'rejected', 'pending', 'needs_manual_review',
      'internal_contradiction', 'explicit_placeholder', 'succeeded', 'skipped',
      // `StageId`, wave 35. All nine, so a schema that lost a member is red here rather
      // than quietly re-permitting the word on a screen.
      'source_preparation', 'page_geometry_extraction', 'document_context_build',
      'text_analysis', 'block_analysis', 'finding_merge', 'finding_review',
      'finding_correction', 'norm_verification',
      // `ProviderMode` and `CostBasis`, added the same day after a PHOTOGRAPH of the run
      // screen showed `live` twice and `measured` once as bare words in Russian prose --
      // which this guard had rendered, seen, and been told to permit.
      'live', 'recorded', 'measured', 'estimated',
      // `Severity`, `WEB-HOOKS-PER-FINDING-01`: all five, so a schema that lost a member is red
      // here rather than quietly re-permitting the word beside a verdict.
      'critical', 'economic', 'operational', 'recommendation', 'check_adjacent']) {
      expect(TRANSLATED.has(value), `${value} left the translated schemas`).toBe(true);
      expect(VOCABULARY.has(value), `${value} is permitted as visible text again`).toBe(false);
    }
    // The two derivations that are not openapi enums, asserted as relationships so a
    // parser that silently returned nothing is red rather than merely permissive.
    expect(csvColumnNames().size, 'OD-11 and W56a declare nineteen CSV columns').toBe(19);
    expect(csvColumnNames().has('finding_uid')).toBe(true);
    expect(manifestRoles().has('source.document'), 'the stage registry declares it').toBe(true);
    expect(betaPolicyIdentifiers().has('C01')).toBe(true);
    expect(betaPolicyIdentifiers().has('D1_LOCAL')).toBe(true);
    expect(betaPolicyIdentifiers().has('F1')).toBe(true);
    expect(betaPolicyIdentifiers().has('C23')).toBe(false);

    // `proxy` must NOT be derivable, or `NOT_DERIVABLE`'s first entry is stale.
    expect(VOCABULARY.has('proxy'), 'proxy is now in the contract; delete it from NOT_DERIVABLE').toBe(false);
  });

  it('keeps the hand-written residue small, and every entry reasoned', () => {
    expect(NOT_DERIVABLE.length).toBeLessThanOrEqual(20);
    for (const { word, why } of NOT_DERIVABLE) {
      expect(why.length, `${word} has no reason`).toBeGreaterThan(60);
    }
  });
});

describe('the guard can tell an English label from a legitimate Latin string', () => {
  // Anti-vacuity, in the file itself. A guard whose discriminator nobody exercised is a
  // guard nobody has watched work.
  it('calls an English label English', () => {
    expect(unexplainedLatin('Create', VOCABULARY)).toEqual(['Create']);
    // `running` is a contract run state; the bare verb `run` is not, and must not become
    // allowed by being a prefix of one.
    expect(unexplainedLatin('Start run', VOCABULARY)).toEqual(['Start', 'run']);
    expect(unexplainedLatin('Display title', VOCABULARY)).toEqual(['Display', 'title']);
    expect(unexplainedLatin('Загрузка: the run…', VOCABULARY)).toEqual(['the', 'run']);
    expect(unexplainedLatin('Published findings: 3', VOCABULARY)).toEqual(['Published', 'findings']);
    expect(unexplainedLatin('Correlation id', VOCABULARY)).toEqual(['Correlation', 'id']);
  });

  it('does not redden a run state, a verdict, an identifier or a digest', () => {
    // `published` and `needs_manual_review` USED TO BE HERE, asserting that a run state and
    // a verdict never redden. Under the 2026-09-22 ruling they must, so they moved to the
    // case below rather than being deleted -- a control that quietly loses a case is how a
    // guard stops proving what its name says.
    // `analysis_failed` is an `ErrorCode` and stays permitted; `text_analysis` was here
    // beside it until wave 35 and has moved to the case below, because a stage id is now
    // translated. A control that quietly loses a case is how a guard stops proving what its
    // name says, so it moved rather than being deleted.
    expect(unexplainedLatin('analysis_failed', VOCABULARY)).toEqual([]);
    expect(unexplainedLatin(`prj_${ULID}`, VOCABULARY)).toEqual([]);
    expect(unexplainedLatin(SHA, VOCABULARY)).toEqual([]);
    expect(unexplainedLatin('application/pdf', VOCABULARY)).toEqual([]);
    expect(unexplainedLatin('Не более 25 MiB.', VOCABULARY)).toEqual([]);
    expect(unexplainedLatin('PC-01', VOCABULARY)).toEqual([]);
    expect(unexplainedLatin('АР v3, F1, C01, D1_LOCAL', VOCABULARY)).toEqual([]);
    expect(unexplainedLatin('АР v3, F3, C23, D7_LOCAL', VOCABULARY)).toEqual(['F', 'C', 'D', 'LOCAL']);
    expect(unexplainedLatin('2026-09-10T08:00:00.000Z', VOCABULARY)).toEqual([]);
    expect(unexplainedLatin('Один PDF за загрузку.', VOCABULARY)).toEqual([]);
    expect(unexplainedLatin('Один ZIP-архив за загрузку.', VOCABULARY)).toEqual([]);
    expect(unexplainedLatin('окончаниями _blocks.json и _results.md', VOCABULARY)).toEqual([]);
    expect(unexplainedLatin('файл с окончанием _results.html', VOCABULARY)).toEqual([]);
    expect(unexplainedLatin('0f0e9d8c-7b6a-4948-b726-150413021100', VOCABULARY)).toEqual([]);
    // `W55B-WEB-BLOCKS`: the text-line block id in the contract's own shape, and only in it.
    expect(unexplainedLatin('b_000003', VOCABULARY)).toEqual([]);
    expect(unexplainedLatin('блок b_12', VOCABULARY)).toEqual(['b']);
  });

  it('reads every upload rule and every upload refusal as Russian prose (W55B-INGEST-01)', () => {
    // A refused upload is held in a mutation's state, which no seed reaches, so the screens
    // above cannot render it. Its sentences are judged here as the form prints them: the
    // classifier's detail for each constraint the client states, the pre-check messages and
    // the rules shown before a file is chosen. The 2.5-line failure of this case is a word
    // like `HTML` or `Markdown` put in a sentence, which the vocabulary does not permit.
    const rendered: string[] = [...UPLOAD_ENVELOPE_RULES];
    for (const problem of ['not_zip', 'too_large', 'empty_file'] as const) {
      rendered.push(precheckProblemMessage(problem));
    }
    // `D-173`: the envelope's one table, which since `WEB-FOLLOWUPS-01` holds `W55B-FIX`'s six too.
    for (const constraint of [
      ...UPLOAD_CONSTRAINTS_STATED,
      '1 <= page_count <= 500',
      'byte_size <= 262144000',
    ]) {
      const failure = classifyUploadFailure(
        new ApiError(
          422,
          {
            contract_version: '1.8.0',
            error_code: 'validation_failed',
            message: 'A caller-safe sentence.',
            correlation_id: '0f0e9d8c-7b6a-4948-b726-150413021100',
            retryable: false,
            details: { constraint, field: 'file' },
          },
          '0f0e9d8c-7b6a-4948-b726-150413021100',
        ),
      );
      // The trailing `(constraint: ..., field: file)` is the classifiers' own rendering of
      // the contract's machine values (`classifiers()` in `upload-failure.ts`), printed by
      // every classifier of this application and pinned by the journey's
      // `expects_rendered_from_envelope`. It is not prose, so the prose is judged without it.
      rendered.push(failure.title, failure.detail.replace(/ \(constraint: [^)]*\)$/, ''));
    }
    // `W55B-FIX` (`W55B-QA-01` O-1): the upload gate's busy refusal, with and without a wait.
    for (const wait of [5, null]) {
      const busy = classifyUploadFailure(
        new ApiError(
          503,
          {
            contract_version: '1.8.0',
            error_code: 'dependency_unavailable',
            message: 'A caller-safe sentence.',
            correlation_id: '0f0e9d8c-7b6a-4948-b726-150413021100',
            retryable: true,
            details: { dependency: 'upload_capacity' },
          },
          '0f0e9d8c-7b6a-4948-b726-150413021100',
          wait,
        ),
      );
      rendered.push(busy.title, busy.detail);
    }
    // `WEB-FOLLOWUPS-01`: what the web server in front of the API said, in a user's words.
    for (const status of [413, 502, 503, 504]) {
      const edge = classifyUploadFailure(
        new TransportError(`HTTP ${status}: тело ответа не является конвертом ошибки по контракту.`, { status }),
      );
      rendered.push(edge.title, edge.detail);
    }
    const offences = rendered
      .map((text) => ({ text, words: unexplainedLatin(text, VOCABULARY) }))
      .filter((entry) => entry.words.length > 0)
      .map((entry) => `${JSON.stringify(entry.text.slice(0, 60))}: ${entry.words.join(', ')}`);
    expect(offences).toEqual([]);
  });

  it('still reddens a file format the vocabulary does not name', () => {
    expect(unexplainedLatin('Файл распознанного текста в формате Markdown', VOCABULARY)).toEqual(['Markdown']);
    expect(unexplainedLatin('Версия в виде HTML', VOCABULARY)).toEqual(['HTML']);
    expect(unexplainedLatin('архив в формате ZIP', VOCABULARY)).toEqual([]);
  });

  it('now reddens the contract words the owner ruled translated', () => {
    // The other direction, and the reason this guard was changed at all: it permitted these
    // while an entire integration pass translated them, and stayed green when a judge put one
    // back in English. Silence from a guard is read as coverage, so a guard that cannot see
    // the class it was built for is worse than none.
    expect(unexplainedLatin('published', VOCABULARY)).toEqual(['published']);
    expect(unexplainedLatin('needs_manual_review', VOCABULARY)).toEqual(['needs', 'manual', 'review']);
    expect(unexplainedLatin('→ accepted', VOCABULARY)).toEqual(['accepted']);
    expect(unexplainedLatin('internal_contradiction', VOCABULARY)).toEqual(['internal', 'contradiction']);
    // `D-62`: the stage table's whole first column. `analysis` alone is already an offence
    // below, so this also shows the compound is not teaching the guard a bare word.
    //
    // `W55B-SEAL-01` published a bare `text` (`PortalBlockType`) and this read `['analysis']`
    // until `W55B-WEB-BLOCKS` registered the two portal schemas above with their markers: the
    // bare `text` is translated again, so both halves of the compound redden as they did.
    expect(unexplainedLatin('text_analysis', VOCABULARY)).toEqual(['text', 'analysis']);
    // And the other portal values the screen translates are offences as bare words too.
    for (const value of ['text', 'image', 'stamp', 'ok']) {
      expect(unexplainedLatin(value, VOCABULARY)).toEqual([value]);
    }
    expect(unexplainedLatin('geometry_mismatch', VOCABULARY)).toEqual(['geometry', 'mismatch']);
    expect(unexplainedLatin('source_preparation', VOCABULARY)).toEqual(['source', 'preparation']);
    // And the machine value keeps its home: `visibleText` reads text nodes and four
    // attributes and never `data-*`, so a badge carrying its contract value is untouched.
    expect(visibleText('<span data-run-state="published">Опубликован</span>')).toEqual([
      'Опубликован',
    ]);
  });

  it('does not learn a bare word from a compound contract value', () => {
    // The masking-order claim, asserted rather than described. If `needs_manual_review`
    // were split into words, `review` alone would pass -- and a screen saying `review`
    // would stop being an offence.
    expect(unexplainedLatin('review', VOCABULARY)).toEqual(['review']);
    expect(unexplainedLatin('manual', VOCABULARY)).toEqual(['manual']);
    expect(unexplainedLatin('analysis', VOCABULARY)).toEqual(['analysis']);
  });
});

describe('the guard renders the screens it claims to render', () => {
  const screens = renderedScreens();

  it('reaches every screen in every state, and none of them throws', () => {
    // A RELATIONSHIP, not a number. This read `SCREENS.length * 7 + 1` and went red the
    // moment the matrix grew, which teaches the next reader to update a literal — exactly how
    // a vacuity check stops checking. `W30-LISTS` ruled against hard-coded counts two waves
    // ago and this was one of them.
    expect(screens.length).toBe(
      // `+ 3`: the account and user-card invalid-data shapes and the review's detail-pending
      // one; `+ 3` more since `W61-DISPATCHER-01`: an assignment's history, cold, loaded
      // and failed.
      SCREENS.length * CACHE_STATES.length + 6 + malformedVariants(IDENTITIES).length,
    );
    // The derived half is non-trivial too: a route walk that returned nothing would leave
    // this file rendering only the shapes below the derivation and still satisfy the
    // relationship above.
    expect(derivedScreens().length, 'the route tree contributed no screens').toBeGreaterThan(10);
    expect(
      malformedVariants(IDENTITIES).length,
      'no malformed-segment variant was derived',
    ).toBeGreaterThan(8);
    // And both factors are non-trivial, so a matrix that silently emptied is red rather than
    // trivially satisfied.
    expect(SCREENS.length).toBeGreaterThan(1);
    expect(CACHE_STATES.length).toBeGreaterThan(1);
    /*
     * The floor is 100 and it used to be 200. It is here to catch a screen that rendered
     * NOTHING, and three entries in `SCREENS` are now widgets rendered directly -- a
     * pending decision history is one `am-state` block, 122 characters, and legitimately
     * so. A floor tuned to the largest page would have refused the branches this matrix
     * was extended to reach, which is the wrong direction for a coverage guard.
     */
    for (const { where, markup } of screens) {
      expect(markup.length, `${where} rendered nothing`).toBeGreaterThan(100);
    }
    // And the pages are still pages: the floor above cannot be met by a matrix that
    // quietly became a list of state blocks.
    const substantial = screens.filter((screen) => screen.markup.length > 2000);
    expect(substantial.length, 'no screen rendered a whole page').toBeGreaterThan(20);
  });

  /**
   * `D-88`: this guard renders every screen the product offers.
   *
   * The case above asks whether the matrix is BIG. This asks whether it is the right set,
   * of `web/src/app` and not of this file's own list. `W43-JUDGE-A` put a different English
   * sentence on each of four screens and the whole suite stayed green; the reason was
   * neither soundness nor blindness in the rules below but that the SUBJECT was a literal.
   */
  it('renders every address web/src/app offers, derived rather than listed', () => {
    // `where` is `"<name> (<state>)"` for the matrix and the variant's own name for the
    // appended ones, so both spellings are kept and each list is matched against the one
    // it is about.
    const where = new Set(screens.map((screen) => screen.where));
    const rendered = new Set(screens.map((screen) => screen.where.replace(/ \([^()]*\)$/, '')));
    const derived = derivedScreens();
    expect(derived.length, 'the route tree contributed no screens').toBeGreaterThan(10);
    expect(
      derived.filter((screen) => !rendered.has(screen.name)).map((screen) => screen.address).sort(),
      'these addresses exist in `web/src/app` and this guard renders no screen for them, so ' +
        'an entirely English page behind a Russian nav label is green here. The derived set ' +
        'comes from `tests/unit/screens/route-screens.ts`; a screen missing here means the ' +
        'spread that consumes it was removed.',
    ).toEqual([]);
    expect(
      malformedVariants(IDENTITIES).filter((v) => !where.has(v.name)).map((v) => v.name).sort(),
      'a malformed-segment refusal is no longer rendered by this guard',
    ).toEqual([]);
  });

  it('reaches past the loading state into a real reading', () => {
    // Without this the whole suite could be six spinners and report a clean interface --
    // the `W12-WEB` failure mode, one level up.
    const loaded = screens.filter((s) => s.where.endsWith('(loaded)'));
    expect(loaded.some((s) => s.markup.includes(`data-run-id="${RUN_ID}"`))).toBe(true);
    expect(loaded.some((s) => s.markup.includes('Договор поставки'))).toBe(true);
    expect(loaded.some((s) => s.markup.includes('Срок поставки'))).toBe(true);
  });
});

// ================================================== the matrix's COVERAGE is an assertion

/**
 * `D-69`, and the reason this section exists rather than one more seeded state.
 *
 * Seven waves running, a guard on this programme has been **sound and blind**: it
 * rendered, saw, and permitted, because the state that carries the defect was never
 * reached. Three of the seven are this file. Each repair was *"seed one more state"*, and
 * each fixed the instance and left the cause:
 *
 * > **a guard's seed matrix is a hand-written literal, and nothing anywhere checks that
 * > the literal covers the space.**
 *
 * A guard answers, and an answer is read as coverage. So the coverage is asserted here,
 * against the contract rather than against a list: every member of every schema the
 * owner's ruling put on screen in Russian must be **rendered by some state in this
 * matrix**, and a member that is not makes this file red **naming the member**.
 *
 * ## Why a `data-` attribute is the evidence, and not the label
 *
 * A translated screen renders `Опубликован`, not `published`, so the rendered *word*
 * cannot say which contract member reached the screen. The machine value keeps its home
 * in a `data-` attribute — that is the whole of `D-62`'s repair and `PA-01` criterion 4
 * is re-driven from those attributes — so the attribute is where a member's arrival is
 * observable, and it is read from the raw markup rather than through `visibleText`,
 * which never reads `data-*` by design.
 *
 * Reading the LABEL instead would break `OPERATING_CONSTRAINTS.md` §12: the label is
 * produced by the same map the language half of this file judges, so the query would
 * share an assumption with its subject and could not see the subject being wrong.
 *
 * ## Why the seeds are still hand-written
 *
 * Deriving the fixtures from the contract would make a new member seed itself, and this
 * assertion would go green over a state nobody had looked at — the same silence, one
 * level up. A new member must redden, so that somebody decides what the screen does with
 * it. The derivation is on the **question**, never on the answer.
 */
const SCHEMA_MARKERS: readonly {
  readonly schema: (typeof TRANSLATED_SCHEMAS)[number];
  readonly attribute: string;
  readonly why: string;
}[] = [
  {
    schema: 'RunState',
    attribute: 'data-run-state',
    why: '`shared/ui/run-state-badge.tsx` and every sentence in `run-progress` that names an outcome.',
  },
  {
    schema: 'StageStatus',
    attribute: 'data-stage-status',
    why: '`shared/ui/stage-status-badge.tsx`, one per row of the stage table.',
  },
  {
    schema: 'Verdict',
    attribute: 'data-verdict',
    why: '`entities/expert-decision/ui/verdict-badge.tsx`, the decision history and the knowledge base.',
  },
  {
    schema: 'FindingCategory',
    attribute: 'data-category',
    why: "`widgets/finding-list`'s group heading and the knowledge base's row.",
  },
  {
    schema: 'StageId',
    attribute: 'data-stage-id',
    why: '`entities/audit-run/ui/stage-table.tsx`, one row per stage. `D-62` put the id here.',
  },
  {
    schema: 'ProviderMode',
    attribute: 'data-provider-mode',
    why: 'the run screen twice, the run-state badge qualifier and the evidence viewer.',
  },
  {
    schema: 'CostBasis',
    attribute: 'data-cost-basis',
    why: "the run screen's cost block, which prints the basis beside the amount.",
  },
  {
    schema: 'PortalBlockType',
    attribute: 'data-portal-block-type',
    why: '`widgets/portal-blocks/ui/portal-block-card.tsx`, one per block, its type said as Текст / Изображение / Штамп.',
  },
  {
    schema: 'ProjectStage',
    attribute: 'data-project-stage',
    why: '`entities/document-version/ui/classification-badges.tsx`, the stage badge on the version screen, every version row and the project structure.',
  },
  {
    schema: 'ProjectSection',
    attribute: 'data-section-group',
    why: "`widgets/project-sections/ui/project-sections.tsx`, one group per section of the project structure, every one of the fifteen present even when empty.",
  },
  {
    schema: 'Severity',
    attribute: 'data-severity',
    why: "`entities/finding/ui/severity-badge.tsx`, beside the verdict in the decision history and the knowledge base, one event per member.",
  },
  {
    schema: 'PortalGeometryState',
    attribute: 'data-portal-geometry',
    why: "`widgets/portal-blocks/ui/portal-block-card.tsx`, one per block; a mismatch page's sentence is said beside it.",
  },
  {
    schema: 'ExecutorKind',
    attribute: 'data-executor-kind',
    why: '`widgets/executor-connections/ui/connection-card.tsx`, one card per connection, its kind said as HTTP API / Команда по SSH / Клиент забирает задания.',
  },
  {
    schema: 'ExecutorApiFlavour',
    attribute: 'data-executor-flavour',
    why: "`widgets/executor-connections/ui/connection-card.tsx`, the revision's request format of an HTTP API connection.",
  },
  {
    schema: 'ExecutorTransport',
    attribute: 'data-executor-transport',
    why: "`widgets/executor-connections/ui/connection-card.tsx`, the revision's way of reaching its address: directly, over VPN or through an SSH tunnel.",
  },
  {
    schema: 'ExecutorBilling',
    attribute: 'data-executor-billing',
    why: "`widgets/executor-connections/ui/connection-card.tsx`, the revision's billing: at the pinned rates, or not billed.",
  },
  {
    schema: 'ExecutorSshProfile',
    attribute: 'data-executor-ssh-profile',
    why: "`widgets/executor-connections/ui/connection-card.tsx`, the command profile of an SSH connection's current revision.",
  },
  {
    schema: 'ExecutorPullClient',
    attribute: 'data-executor-pull-client',
    why: "`widgets/executor-connections/ui/connection-card.tsx`, the client of a connection a remote runner pulls tasks through.",
  },
  {
    schema: 'ExecutorSecretPurpose',
    attribute: 'data-executor-secret',
    why: '`widgets/executor-connections/ui/connection-card.tsx`, one line per key a connection holds or still needs, said as the key to the model or the SSH key.',
  },
  {
    schema: 'ExecutorProbeState',
    attribute: 'data-executor-probe-state',
    why: "`widgets/executor-connections/ui/connection-card.tsx`, the latest probe of the current revision: requested, running or finished.",
  },
  {
    schema: 'ExecutorProbeOutcome',
    attribute: 'data-executor-probe-outcome',
    why: "`widgets/executor-connections/ui/connection-card.tsx`, a finished probe's outcome said as a Russian sentence in a badge.",
  },
  {
    schema: 'ExecutorIdentityBasis',
    attribute: 'data-executor-identity-basis',
    why: "`widgets/executor-connections/ui/connection-card.tsx`, whether the model of a probe was reported by the answer or declared by the executor.",
  },
  {
    schema: 'ExecutorRateCheck',
    attribute: 'data-executor-rate-check',
    why: "`widgets/executor-connections/ui/connection-card.tsx`, the comparison of a probe's reported cost with the pinned rates.",
  },
  {
    schema: 'ExecutorWorkKind',
    attribute: 'data-executor-route',
    why: "`widgets/executor-routes/ui/executor-routes.tsx`, the summary of the route for one kind of model work, «Анализ текста».",
  },
];

/** `data-x="y"` pairs, read out of the raw markup of every screen in every state. */
function markerValuesOnScreens(): Map<string, Set<string>> {
  const out = new Map<string, Set<string>>();
  for (const { attribute } of SCHEMA_MARKERS) out.set(attribute, new Set<string>());
  for (const { markup } of renderedScreens()) {
    for (const [attribute, values] of out) {
      for (const match of markup.matchAll(new RegExp(`\\s${attribute}="([^"]*)"`, 'g'))) {
        values.add(match[1] ?? '');
      }
    }
  }
  return out;
}

describe('the matrix covers the contract, and says which member it does not', () => {
  const observed = markerValuesOnScreens();
  const openapi = readJson<OpenApi>(CONTRACT_PATH);

  it('decides for every translated schema HOW a member becomes observable', () => {
    // A schema added to `TRANSLATED_SCHEMAS` with no marker would be excused by silence,
    // which is the class of defect this section exists to close. Both directions.
    const marked = SCHEMA_MARKERS.map((entry) => entry.schema);
    expect([...TRANSLATED_SCHEMAS].filter((name) => !marked.includes(name))).toEqual([]);
    expect(marked.filter((name) => !([...TRANSLATED_SCHEMAS] as string[]).includes(name))).toEqual([]);
    for (const { schema, why } of SCHEMA_MARKERS) {
      expect(why.length, `${schema} names no module that renders it`).toBeGreaterThan(40);
    }
  });

  it('renders every attribute it claims to read, so a renamed one is red and not merely empty', () => {
    // Anti-vacuity, and it is not the same case as the one below. An attribute that was
    // renamed in `web/src` makes EVERY member of its schema look unseeded; this case says
    // which of the two happened, instead of leaving a reader to seed nine states that were
    // already seeded.
    const silent = SCHEMA_MARKERS.filter(({ attribute }) => (observed.get(attribute)?.size ?? 0) === 0);
    expect(
      silent.map(({ schema, attribute }) => `${schema} -> ${attribute}`),
      'no rendered screen carries this attribute at all. Either the application renamed ' +
        'it -- in which case fix the name here and the coverage below is unaffected -- or ' +
        'the component that carried it stopped being rendered by this matrix.',
    ).toEqual([]);
  });

  it('renders every member of every translated schema, and NAMES the one it does not', () => {
    /*
     * THE ASSERTION THIS SECTION EXISTS FOR.
     *
     * Measured at `295ff04`, before this was written: 18 of 31 members reached a screen.
     * `StageId` 4/9, `StageStatus` 1/4, `Verdict` 2/4, `FindingCategory` 1/2,
     * `ProviderMode` 1/2, `CostBasis` 1/2 -- thirteen contract members, every one of them
     * carrying a Russian label a mutation could have put back into English with this file
     * staying green. `RunState` was the only schema at 8/8, and only because a wave-33
     * judge's mutation died quietly and somebody chased it.
     */
    const unseeded: string[] = [];
    for (const { schema, attribute } of SCHEMA_MARKERS) {
      const declared = openapi.components.schemas[schema]?.enum ?? [];
      const seen = observed.get(attribute) ?? new Set<string>();
      for (const member of declared) {
        if (!seen.has(member)) unseeded.push(`${schema}.${member} (no ${attribute}="${member}")`);
      }
    }
    expect(
      unseeded.sort(),
      'the contract publishes these members and NO state in CACHE_STATES renders one. ' +
        'They are not "allowed" and they are not "absent" -- they are UNSEEDED, and every ' +
        'assertion in this file about them is vacuous. Seed a state that puts each on a ' +
        'screen; do not delete it from TRANSLATED_SCHEMAS, and do not derive the fixtures ' +
        'from the contract, which would make the next member cover itself in silence.',
    ).toEqual([]);

    // And the question itself is non-trivial: a contract that parsed to nothing would
    // otherwise satisfy the line above by asking nothing.
    const total = SCHEMA_MARKERS.reduce(
      (sum, { schema }) => sum + (openapi.components.schemas[schema]?.enum ?? []).length,
      0,
    );
    expect(total, 'the translated schemas declare no members at all').toBeGreaterThan(20);
  });
});

/**
 * The Latin `D-53` left behind at `cd475cc`, as this guard sees it.
 *
 * **Why this list exists rather than an empty assertion.** The guard is red on the tree it
 * was written against, and `W32-SEE` may not fix what it finds: `web/src` belongs to
 * another live session this wave. Committing a red gate is not an option, and neither is
 * weakening the guard until it passes. So the outstanding set is written down, and it is
 * asserted **in both directions**:
 *
 *   - nothing outside it  -- a **new** English string on a screen reddens the gate today,
 *     which is the whole of what `D-53` asked for;
 *   - nothing missing from it -- **translating one of these also reddens the gate**, with
 *     a message saying to delete its line.
 *
 * That second direction is deliberate. `MEMORY.md`: *characterization can freeze a defect
 * -- assert, don't just re-capture.* A list that only capped the damage would quietly
 * outlive the repair and this guard would go back to proving nothing. This one cannot: it
 * is a ratchet, it may only shrink, and when it is empty the skipped test below is the one
 * to unskip.
 *
 * Each entry carries the module that renders it. Every one of them is another session's to
 * repair, and `docs/program/W32-SEE.md` §4 names whose.
 */
/*
 * RATCHET MOVED, 2026-09-21, by the integrator at merge. Eight entries deleted because the
 * guard said they were gone, not because a diff looked right:
 *
 *   All versions of this document · Create · Display title · Published findings: # ·
 *   Start run · — this run's provider mode is · Загрузка: the document page… ·
 *   Загрузка: the run…
 *
 * They were repaired by `3bd2c82`, the wave-31 tail, which landed AFTER this guard's base at
 * `cd475cc`. The integrator had told this session "your lane does not read those files, do
 * not rebase" -- which was wrong, and the session said so: the guard's subject IS `web/src`.
 * The base it was given is exactly why these eight read as outstanding when they were not.
 *
 * The list may only shrink. Nothing was added here and the assertion was not relaxed; the
 * both-directions check is what forced this edit, by refusing to stay green over a register
 * describing defects that no longer exist.
 *
 * RATCHET MOVED AGAIN, 2026-09-22, by `W33-SECT`. Nine entries deleted, each because the
 * guard named it and demanded the deletion — not because a translation looked done:
 *
 *   Recorded: · Terminal reason: · The run terminated · . Nothing was published. ·
 *   provider mode: · Загрузка: findings… · Загрузка: projects… · Загрузка: the finding… ·
 *   the version-list sentence addressed to a developer
 *
 * All nine were in that session's own territory — `web/src/widgets`, `web/src/_pages` —
 * and were repaired there in the same commit that deleted these lines. The two that
 * remain are not: `Correlation id` is `shared/ui` and `features`, `Upload` is
 * `features/upload-document`, and the second is additionally named as a control's text by
 * `tests/e2e/pc01/journey/manifest.json`, so translating it moves a browser-journey handle
 * and has to move both files at once.
 *
 * Nothing was added, no assertion was relaxed and no permission was widened.
 */
const OUTSTANDING: readonly { readonly text: string; readonly module: string }[] = [
  /*
   * EMPTY, 2026-09-22. `D-53` is closed: nineteen strings became eleven, then two, then none.
   *
   * The list may only shrink and it never grew. Everything removed from it was removed
   * because the guard said the string was gone from a RENDERED screen, never because a diff
   * looked convincing -- which is the whole reason three earlier sessions each reported the
   * interface translated and each were wrong.
   *
   * `finds none at all` below is no longer skipped. From here a single English word reaching
   * a reviewer is a red gate, and this array staying empty is the assertion.
   */
];

/**
 * One offence, keyed so the key is stable against the fixture.
 *
 * Digits become `#`: `Published findings: 3` is the same defect whatever number the
 * seeded run carries, and a key that moved with the fixture would make this list a record
 * of the harness rather than of the application.
 */
function offenceKey(text: string): string {
  return text.slice(0, 120).replace(/\d+/g, '#');
}

function offencesOnScreens(): Map<string, { readonly words: Set<string>; readonly where: Set<string> }> {
  const found = new Map<string, { words: Set<string>; where: Set<string> }>();
  for (const { where, markup } of renderedScreens()) {
    for (const text of visibleText(markup)) {
      const words = unexplainedLatin(text, VOCABULARY);
      if (words.length === 0) continue;
      const key = offenceKey(text);
      const entry = found.get(key) ?? { words: new Set<string>(), where: new Set<string>() };
      for (const word of words) entry.words.add(word);
      entry.where.add(where.replace(/ \(.*$/, ''));
      found.set(key, entry);
    }
  }
  return found;
}

describe('R-18: no Latin word reaches a reviewer that a contract did not put there', () => {
  const found = offencesOnScreens();
  const known = new Set(OUTSTANDING.map((entry) => offenceKey(entry.text)));

  it('finds no English on a rendered screen that D-53 has not already recorded', () => {
    const fresh = [...found.entries()]
      .filter(([key]) => !known.has(key))
      .map(([key, { words, where }]) =>
        `${JSON.stringify(key)}  ${[...words].sort().join(' ')}  [${[...where].sort().join(', ')}]`,
      )
      .sort();
    expect(
      fresh,
      'R-18 requires the alpha in Russian, and these words are on a RENDERED screen — a ' +
        'source scan cannot see them, which is why three sessions missed them (D-53). ' +
        'Translate them. If one is genuinely machine vocabulary it belongs in a contract, ' +
        'and then this guard allows it without being edited.',
    ).toEqual([]);
  });

  it('still finds every string the outstanding list claims, and no stale ones', () => {
    const repaired = OUTSTANDING.filter((entry) => !found.has(offenceKey(entry.text))).map(
      (entry) => `${JSON.stringify(entry.text)}  (${entry.module})`,
    );
    expect(
      repaired,
      'These strings are in OUTSTANDING and are no longer on any rendered screen. They ' +
        'have been translated — delete their lines from OUTSTANDING. The list is a ' +
        'ratchet and may only shrink; leaving a repaired entry in it is how a guard goes ' +
        'back to proving nothing.',
    ).toEqual([]);
  });

  // The state `R-18` actually requires. Skipped, not deleted, and not weakened: it is the
  // assertion this guard exists to make, and it goes green the day `OUTSTANDING` is empty.
  it('every button the browser journey presses by text is actually rendered', () => {
    /*
     * `D-61`'s open half, closed with the instrument that already exists.
     *
     * `tests/e2e/pc01/journey/manifest.json` drives the real browser and finds two of its
     * controls BY THEIR TEXT. `tests/e2e/test_pc01_journey_conformance.py` checks those
     * strings by substring containment against a CONCATENATION of `web/src` -- so when the
     * upload button became `Загрузить`, the manifest still said `Upload`, the journey would
     * have failed to find the button, and the guard stayed green because `Upload` still
     * occurs inside `uploadDocument` and `UploadFailure`. The wave-33 judges found the same
     * shape with `Run` matching inside `RunPage`.
     *
     * A source scan cannot tell a label from an identifier. A render can: this asserts the
     * click target exists in the markup a browser would receive.
     */
    const manifest = readJson<{
      readonly write?: { readonly steps?: readonly { readonly actions?: readonly { readonly text?: string }[] }[] };
    }>(join(REPO_ROOT, 'tests/e2e/pc01/journey/manifest.json'));

    const texts = (manifest.write?.steps ?? [])
      .flatMap((step) => step.actions ?? [])
      .map((action) => action.text)
      .filter((text): text is string => typeof text === 'string' && text.length > 0);

    // Non-vacuous: a manifest that stopped naming click targets would otherwise pass here
    // by having nothing to check, which is the failure mode this case exists to prevent.
    expect(texts.length, 'the manifest names no click target by text').toBeGreaterThan(1);

    const markup = renderedScreens().map((s) => s.markup).join('\n');
    for (const text of texts) {
      expect(
        markup.includes(`>${text}<`) || markup.includes(`>${text} <`) || markup.includes(`> ${text}<`),
        `the journey presses a control labelled "${text}" and no rendered screen carries it ` +
          'as element text. Either the label moved and the manifest did not, or the reverse. ' +
          'A substring check against web/src cannot see this -- it is why D-61 exists.',
      ).toBe(true);
    }
  });

  it('finds none at all', () => {
    expect([...offencesOnScreens().keys()]).toEqual([]);
  });
});

// ======================================= the WIDGETS' branches, derived from the tree

/**
 * Every branch a widget actually has is rendered by some state in this matrix.
 *
 * ## The other half of `D-69`, and the contract cannot express it
 *
 * The coverage assertion above answers *"is every contract member seeded"*. It says
 * nothing about the branches a widget has that no schema declares: **pending, error,
 * empty, non-empty, and a listing with a next page.** Four of the seven blindnesses in
 * the register are exactly those — `W32-SEE`'s empty branch, `W37`'s empty branch again,
 * `W38-KB`'s `next_cursor: null`, and `W38-KB`'s singular arm.
 *
 * ## What identifies a branch, derived rather than listed
 *
 * `shared/ui/states.tsx` declares the five mandatory states, and every list, panel and
 * viewer in PC-01 renders one of them when it has no content to show. Each is given a
 * `title` (or, for `LoadingState`, a `what`), and **where that argument is a literal it
 * names the branch uniquely**. So the required set is read out of `web/src` by scanning
 * for those five component names and taking the literal argument beside each — the
 * filesystem decides it, and a widget added next wave brings its own branches with it.
 *
 * The same scan takes the **pager's** two controls, which are the `next_cursor` branch
 * and the first-page branch that `D-69`'s wave-38 row is about.
 *
 * A literal that no rendered screen carries is a branch this guard does not reach, and
 * **every assertion it makes about that branch is vacuous** — which is how an English
 * sentence in `ProjectList`'s `EmptyState` survived until a mutation died quietly.
 */
const STATE_COMPONENTS = ['LoadingState', 'EmptyState', 'ErrorState', 'UnsupportedState', 'NotApplicableState'] as const;

/** `title="…"`/`what="…"` on a mandatory state, plus the two pager controls, from `web/src`. */
export function branchLabelsInSource(): readonly { readonly label: string; readonly module: string }[] {
  const out: { label: string; module: string }[] = [];
  const seen = new Set<string>();
  const add = (label: string, module: string): void => {
    const trimmed = label.trim();
    if (trimmed.length === 0 || seen.has(trimmed)) return;
    seen.add(trimmed);
    out.push({ label: trimmed, module });
  };
  const files = walkFiles(join(REPO_ROOT, 'web', 'src'), (path) => path.endsWith('.tsx'));
  const opening = new RegExp(`<(${STATE_COMPONENTS.join('|')})\\b([\\s\\S]*?)(?:/>|>)`, 'g');
  for (const file of files) {
    const source = readText(file);
    const module = repoRelative(file);
    for (const match of source.matchAll(opening)) {
      const body = match[2] ?? '';
      const title = /\stitle="([^"]+)"/.exec(body);
      const what = /\swhat="([^"]+)"/.exec(body);
      if (title !== null) add(title[1] as string, module);
      else if (what !== null) add(`Загрузка: ${what[1] as string}…`, module);
    }
    // The pager. `className="am-pager"` wraps two buttons whose text is a literal, and a
    // listing renders each only in one of the two `next_cursor` / cursor states.
    for (const pager of source.matchAll(/className="am-pager"[\s\S]*?<\/div>/g)) {
      for (const button of (pager[0] ?? '').matchAll(/>\s*([^<>{}\n]+?)\s*<\/button>/g)) {
        add(button[1] as string, module);
      }
    }
  }
  return out;
}

/**
 * Branches one static render pass cannot select. Each says why, and the list may only shrink.
 *
 * `W32-SEE` measured this boundary and `contrast.ts` restates it: the harness renders one
 * pass and cannot fire an event, run an effect, or render an instance twice. So a branch
 * chosen by `useState` after a click, or by a `useMutation` that has settled, is out of
 * reach — and **saying so by name is the whole point**, because the alternative is a
 * matrix that looks complete.
 *
 * **Three of these WERE English strings on a screen a reviewer can reach**, carried here
 * for three waves with the words *reported and not repaired*. `D-82`. The reading that
 * kept them was that this list excuses a branch from everything, and it only ever excused
 * it from COVERAGE — `no branch label carries English, reachable or not`, below, is the
 * assertion that says so, and it was committed RED over all three before they were
 * translated. Their entries are unchanged except for the label, so the ratchet's reverse
 * direction still holds them: a state that starts rendering one of these makes this file
 * red rather than leaving a stale excuse in place.
 */
const UNREACHABLE_IN_ONE_PASS: readonly { readonly label: string; readonly why: string }[] = [
  {
    label: 'Действие не выполнено.',
    why: '«Диспетчер» and «Мои задачи» show this only after the transitionAssignment mutation settles with a failure. One static render cannot press a move button or seed the mutation observer through a query cache.',
  },
  {
    label: 'Назначение не создано.',
    why: 'The dispatcher\'s creation form shows this only after the createAssignment mutation settles with a failure. One static render cannot submit the form or seed the mutation observer through a query cache.',
  },
  {
    label: 'Команда отклонена',
    why: 'QueuePage can show this only after a command mutation settles with a typed refusal. The static harness cannot fire its confirmation or seed the mutation observer through a query cache.',
  },
  {
    label: 'Команда исполнителю отклонена',
    why: 'WorkersPage shows this only after the setWorkerIntake mutation settles with a typed refusal, past the confirmation step. One static render cannot press the switch, confirm it or seed the mutation observer through a query cache.',
  },
  {
    label: 'Снимок не назначен',
    why: 'NormsPage shows this only after the setCurrentNormSnapshot mutation settles with a typed refusal, past the confirmation step. One static render cannot press «Сделать текущим», confirm it or seed the mutation observer through a query cache.',
  },
  {
    label: 'Назначение не выполнено',
    why: 'NormsPage shows this only after the setCurrentNormSnapshot mutation rejects with a failure that is not a refusal. Same mechanism as the entry above: a settled mutation observer cannot be seeded through a query cache.',
  },
  {
    label: 'Заявка не одобрена',
    why: 'The approval form sets its local roles failure only after submit with no role selected. One static server render cannot fire that submit handler or seed component useState.',
  },
  {
    label: 'Заявка не отклонена',
    why: 'The rejection form sets its local reason failure only after submit with an invalid reason. One static server render cannot fire that submit handler or seed component useState.',
  },
  {
    label: 'Изменение не выполнено',
    why: 'ManageUserControls shows this only after its useMutation observer receives a failed command. A seeded query cache does not set mutation observer state in one static render.',
  },
  {
    label: 'Пароль не сброшен',
    why: 'ManageUserControls sets the mismatch state only in the password form submit handler. A single static render cannot submit the form or assign this local useState value.',
  },
  {
    label: 'Профиль не сохранён',
    why: 'EditProfileForm shows this after the profile mutation rejects. A static render can seed query answers but cannot run the submit handler or settle its useMutation observer.',
  },
  {
    label: 'Решение не сохранено',
    why: 'RegistrationDecisionControls shows this after an approve or reject mutation fails. Its useMutation observer cannot be put into an error state by seeding a query cache.',
  },
  {
    label: 'Загрузка: новый проект…',
    why:
      "`create-project-form.tsx`, while its `useMutation` is in flight. One server pass " +
      'never has a settled mutation, and the harness cannot fire the submit that starts ' +
      'one. `useMutation` builds its own observer and reads no cache, so there is nothing ' +
      'to seed: unlike a query, a pending mutation cannot be put into a client. `D-82`.',
  },
  {
    label: 'Загрузка: загружаемый файл…',
    why:
      '`upload-outcome.tsx`, under either upload form while the upload is in flight (the ' +
      'first version or, `W59-VERSION-UPLOAD-01`, the next one); same mechanism as the ' +
      'new project, and the same reason no seed reaches it. The words it carries are ' +
      'judged by `no branch label carries English, reachable or not`. `D-82`.',
  },
  {
    label: 'Загрузка: запрос на прогон…',
    why:
      '`start-run-control.tsx`, between the press and the run id. Same mechanism, same ' +
      'reason no seed reaches it, and the words it carries are judged by `no branch label ' +
      'carries English, reachable or not` rather than by this matrix. `D-82`.',
  },
  {
    label: 'Файл выходит за допустимые ограничения.',
    why:
      'The upload pre-check panel, selected by a `useState` the harness cannot set: it is ' +
      'written by the file input\'s change handler. This is the branch the journey\'s six ' +
      'refusal cases drive in a real browser, and `tests/e2e/pc01/journey/refusals.mjs` is ' +
      'the only instrument that reaches it.',
  },
  // `В начало` left this list in `W55A-WEB-NORMS`: the norms lists take their first-page
  // control as a prop (`onFirst`), so a static pass of their later-page shapes renders it,
  // and the ratchet below said so. The other lists still hold it in their own `cursor` state.
  // `W45-BLOCKS`. `blocks-page.tsx` picks a version in three client-side steps — a
  // project, then one of its documents, then the block index for that document's
  // version — and each step mounts a component that calls its own query only after a
  // `useState` set by the PREVIOUS step's button click. The harness renders one static
  // pass with one seeded cache; it cannot click through project -> document -> blocks
  // to make the second and third steps' components exist at all, so none of their
  // branches can be selected by seeding a cache differently. The first step (the
  // project list itself) needs no click and IS reached by this matrix, which is why it
  // carries no entry here. The words below are judged by `no branch label carries
  // English, reachable or not` rather than by this matrix, same as every entry above.
  //
  // `W55B-WEB-BLOCKS` deleted the four `BlockMarkup` entries that stood after these three,
  // because this guard said a state now renders them: the chosen version's two tabs are
  // exported as `VersionBlockViews`, and `BLOCKS_SHAPES` renders the «Строки текста» tab over
  // every answer `getVersionBlocks` distinguishes. The document chooser below still needs a
  // click on a project row before it exists, so its three stay.
  {
    label: 'Список документов не удалось прочитать.',
    why:
      "`DocumentChooser`, mounted only after a project is chosen by clicking a project " +
      'row in `VersionChooser` — a `useState` the harness cannot set, the same mechanism ' +
      'as every entry above it. `useDocumentList` is never even called in a pass that has ' +
      'not clicked a project, so there is no query to seed an error into.',
  },
  {
    label: 'Загрузка: документы проекта…',
    why:
      "`DocumentChooser`'s pending read, reached only once a project is chosen. Same " +
      'mechanism as the entry above it: the component does not exist, and its query does ' +
      'not exist, until a click this harness cannot fire has happened.',
  },
  {
    label: 'В этом проекте нет опубликованных документов.',
    why:
      "`DocumentChooser`'s empty answer, reached only once a project is chosen and that " +
      'project turns out to have published nothing. Same mechanism: the component that ' +
      'would render it is never mounted by a single static pass.',
  },
];

/**
 * The home page's two branches no literal names (`W50-SHELL-FRAME`, the integrator's ruling of
 * 2026-10-07, Q3): the administrator's tile and the loaded recent-projects list. Their words are
 * constants (`HOME_TILE_COPY`), so {@link branchLabelsInSource} cannot require them; this case
 * requires the two MARKERS instead, so the `home-admin` seed and the loaded state's home keys
 * cannot be dropped in silence.
 */
export function homeBranchesMissing(markups: readonly string[]): string[] {
  const markers = ['data-home-tile="registrations"', 'data-recent-project-count="5"'];
  return markers.filter((marker) => !markups.some((markup) => markup.includes(marker)));
}

describe("the home page's administrator tile and recent-projects list are rendered by some state", () => {
  it('can fail: a matrix without them names both', () => {
    expect(homeBranchesMissing(['<section data-home-tile="summary"></section>'])).toEqual([
      'data-home-tile="registrations"',
      'data-recent-project-count="5"',
    ]);
  });

  it('renders both', () => {
    expect(
      homeBranchesMissing(renderedScreens().map((screen) => screen.markup)),
      'no state renders this home-page branch: the `home-admin` seed in route-screens.ts or ' +
        "the loaded state's home keys are gone, and the language guard no longer reads it",
    ).toEqual([]);
  });
});

describe('every branch the widgets have is rendered by some state in this matrix', () => {
  const labels = branchLabelsInSource();

  it('finds the branches by scanning web/src, not by listing them', () => {
    // Non-vacuous in both factors: a scan that stopped matching would otherwise make the
    // case below pass by having nothing to require.
    expect(labels.length, 'no mandatory-state branch was found in web/src at all').toBeGreaterThan(15);
    expect(
      labels.filter((entry) => entry.label.includes('Загрузка: ')).length,
      'no LoadingState `what=` was found; the scan has stopped matching',
    ).toBeGreaterThan(3);
    expect(
      labels.some((entry) => entry.label === 'Дальше'),
      'the pager scan found no next-page control',
    ).toBe(true);
  });

  it('renders every one of them, and NAMES the branch it does not reach', () => {
    const rendered = renderedScreens()
      .flatMap((screen) => visibleText(screen.markup))
      .join('\n');
    const excused = new Set(UNREACHABLE_IN_ONE_PASS.map((entry) => entry.label));
    const unreached = labels
      .filter(({ label }) => !excused.has(label) && !rendered.includes(label))
      .map(({ label, module }) => `${JSON.stringify(label)}  (${module})`)
      .sort();
    expect(
      unreached,
      'a widget has this branch and NO state in CACHE_STATES renders it, so every ' +
        'assertion this guard makes about it is vacuous — which is how an English sentence ' +
        "in ProjectList's EmptyState survived until a mutation died quietly. Seed a state " +
        'that reaches it, or add it to UNREACHABLE_IN_ONE_PASS with the reason one pass ' +
        'cannot select it.',
    ).toEqual([]);

    // The other direction: the ratchet may only shrink.
    expect(
      [...excused].filter((label) => rendered.includes(label)).sort(),
      'these are excused as unreachable and a state now renders them. Delete their entries.',
    ).toEqual([]);

    for (const { label, why } of UNREACHABLE_IN_ONE_PASS) {
      expect(why.length, `${label} carries no reason`).toBeGreaterThan(80);
    }
  });

  /**
   * `D-82`: **being unrenderable excuses COVERAGE, and it does not excuse LANGUAGE.**
   *
   * Three English strings — `Загрузка: the new project…`, `Загрузка: the upload…`,
   * `Загрузка: the run request…` — sat in the list above for three waves, each carrying
   * the words *ENGLISH ON A SCREEN, reported and not repaired here*. The row was opened
   * deliberately unrepaired, because `D-53` closed three times on repairs that looked
   * convincing in a diff and this register's rule is that a string is removed **because a
   * guard says it is gone**, never because a diff read well. The row asks for an
   * instrument, not an edit.
   *
   * ## Why this instrument is not the source scan `D-53` proved useless
   *
   * `D-53`'s three failed rounds each grepped `web/src` for English and each missed the
   * survivors, because *the string a reviewer reads does not exist until React composes
   * it*: `what="the run"` is an ARGUMENT, and `Загрузка: the run…` is the sentence.
   *
   * This reads the argument and **composes the sentence the way the component does** —
   * `branchLabelsInSource()` builds `Загрузка: ${what}…` — so its subject is the rendered
   * string and not the literal. That composition is a claim, and a claim this file makes
   * about the thing it is measuring is `OPERATING_CONSTRAINTS.md` §12 waiting to happen,
   * so it is **proved rather than assumed**: the case below requires the composed form of
   * every label a screen DOES render to appear verbatim in that screen's text. If
   * `LoadingState` changed its wording, the formula would stop matching the markup and
   * this file would go red before it could judge anything by it.
   *
   * ## What it still cannot do, stated rather than left to look like coverage
   *
   * It judges the WORDS in an argument that reaches a mandatory state. It does not render
   * the branch, so it cannot see a sentence composed some other way, and it is not a
   * replacement for the matrix above — it is the half of the matrix's subject that one
   * static pass cannot select, judged by the only means available.
   */
  it('proves its composition against the screens that DO render a loading label', () => {
    const rendered = renderedScreens()
      .flatMap((screen) => visibleText(screen.markup))
      .join('\n');
    const composed = labels
      .filter((entry) => entry.label.startsWith('Загрузка: '))
      .map((entry) => entry.label);
    expect(composed.length, 'the scan found no LoadingState argument at all').toBeGreaterThan(3);
    // POSITIVE evidence only, and deliberately so: *"which branches are unreached"* is the
    // case above and this one must not restate it, or a new unreachable branch would fail
    // here with a message about the formula that is not true of it.
    const verbatim = composed.filter((label) => rendered.includes(label));
    expect(
      verbatim.length,
      '`branchLabelsInSource()` composes `Загрузка: ${what}…` the way `LoadingState` does, ' +
        'and NO screen carries the sentence it composes. The formula and the component have ' +
        'diverged, so every language judgement made through the formula is about a string ' +
        'no reviewer reads.',
    ).toBeGreaterThan(3);
    // And the match is the composition rather than the argument: a formula that had lost
    // its prefix or its ellipsis would still contain the noun and would satisfy the line
    // above by accident.
    const sample = verbatim[0] as string;
    expect(sample.startsWith('Загрузка: ') && sample.endsWith('…')).toBe(true);
    expect(rendered).not.toContain(sample.replace('Загрузка: ', 'Загрузка ['));
  });

  it('D-82: no branch label carries English, reachable or not', () => {
    const offences = labels
      .map(({ label, module }) => ({ label, module, words: unexplainedLatin(label, VOCABULARY) }))
      .filter((entry) => entry.words.length > 0)
      .map((entry) => `${JSON.stringify(entry.label)}  ${entry.words.join(' ')}  (${entry.module})`)
      .sort();
    expect(
      offences,
      'a widget passes this literal to a mandatory state and it carries a Latin word no ' +
        'contract put there. `UNREACHABLE_IN_ONE_PASS` excuses a branch from the COVERAGE ' +
        'assertion above — it says one static pass cannot select the branch — and it has ' +
        'never excused the branch from R-18. A reviewer reaches these branches in a browser.',
    ).toEqual([]);
  });
});

// ============================== D-61's third instance: the journey's own sentences

/**
 * `tests/e2e/pc01/journey/manifest.json` declares, per step, the sentences a screen must
 * render once that step has run. **This is the check that they are evidence of anything.**
 *
 * ## What was there, and why a word boundary could not fix it
 *
 * `tests/e2e/test_pc01_journey_conformance.py` asserted them by substring containment
 * against a **concatenation of every `.ts`/`.tsx` byte under `web/src`**. That is `D-61`:
 * the manifest asserted `"Run"` and passed, because `Run` occurs inside `RunPage`, and no
 * screen renders it. Containment had already deceived two guards before it and both were
 * repaired by matching on a word boundary. **This one is not**, because the subject is
 * wrong rather than the matcher: it read source where the claim is about a screen.
 *
 * ## What a renderer can decide here, and what it cannot — measured, because the brief
 * assumed it could decide more
 *
 * Measured at `abe1c15` over `renderedScreens()`: of the manifest's **15** declared
 * sentences, **11 are rendered by no screen this harness can reach**, and it is not
 * because the manifest is wrong. They live in the upload form's pre-check panel, the
 * created-project panel and the version panel — branches driven by `useState` and by a
 * settled `useMutation`, which one static pass cannot select. `contrast.ts` says the same
 * thing in its own words about `.am-form__created`, `.am-form__problem` and
 * `.am-form__chosen`. **A renderer cannot confirm those sentences positively**, and a
 * check that claimed to would be the same false affordance one layer along.
 *
 * ## What it CAN decide, and it is the half that was actually wrong
 *
 * The other **4 of 15 passed by matching text the screen renders whatever happened**:
 *
 * | declared | matched | what it really is |
 * |---|---|---|
 * | `Создан` | `Создан 2026-09-10 08:00:00 UTC · документов 2` | every project row's created date |
 * | `Эта версия` | `Эта версия и её манифест неизменяемы.` | the version panel's standing prose |
 * | `Прогон` | `Прогон использует тот режим провайдера…` | the start-run control's own note |
 * | `25 MiB` | `Не более 25 MiB.` | the upload envelope, printed before any file is chosen |
 *
 * **Every one of those passes in the live browser too**, because `write.mjs` and
 * `refusals.mjs` test `bodyText.includes(needle)` against the page the journey is already
 * on. So the deception was not only in the gate: four of the journey's own assertions
 * could not fail.
 *
 * The corpus this guard renders performs **no write at all** — it is the application
 * before any of these steps has run. So:
 *
 * > **a sentence offered as evidence that a step happened must not be on the screen
 * > before it happens.**
 *
 * That is decidable from rendered output, it is derived from the manifest rather than
 * listed here, and it is what this case asserts.
 */
const STILL_EVIDENCE_THOUGH_RENDERED: readonly { readonly text: string; readonly why: string }[] = [
  /*
   * EMPTY, and the empty is the assertion.
   *
   * An entry would be legitimate in exactly one shape: a sentence this corpus renders only
   * because its FIXTURE seeds a state the journey's own fresh project cannot be in. `Прогон
   * завершился как` is the candidate — this matrix seeds a published run, and the journey's
   * project has no run until it starts one. Nothing needs the exemption today, and a reader
   * adding one must make that argument in writing rather than silencing a red.
   */
];

interface JourneyManifest {
  readonly write?: { readonly steps?: readonly { readonly name?: string; readonly expects_rendered?: readonly string[] }[] };
  readonly refusals?: { readonly cases?: readonly { readonly fixture?: string; readonly expects_rendered?: readonly string[] }[] };
}

/** Every `expects_rendered` sentence the manifest declares, with the step that declares it. */
export function journeySentences(): readonly { readonly where: string; readonly text: string }[] {
  const manifest = readJson<JourneyManifest>(
    join(REPO_ROOT, 'tests/e2e/pc01/journey/manifest.json'),
  );
  const out: { where: string; text: string }[] = [];
  for (const step of manifest.write?.steps ?? []) {
    for (const text of step.expects_rendered ?? []) out.push({ where: step.name ?? 'write', text });
  }
  for (const item of manifest.refusals?.cases ?? []) {
    for (const text of item.expects_rendered ?? []) out.push({ where: item.fixture ?? 'refusal', text });
  }
  return out;
}

describe('D-61: every sentence the journey calls evidence is evidence', () => {
  const sentences = journeySentences();

  it('reads sentences out of the manifest at all', () => {
    // Non-vacuous: a manifest that stopped declaring them would otherwise satisfy the case
    // below by having nothing to check, which is the failure mode it exists to prevent.
    expect(sentences.length, 'the manifest declares no expects_rendered sentence').toBeGreaterThan(5);
  });

  it('finds none of them already on a screen before the step that is supposed to produce it', () => {
    const excused = new Set(STILL_EVIDENCE_THOUGH_RENDERED.map((entry) => entry.text));
    const screens = renderedScreens().map((screen) => ({
      where: screen.where.replace(/ \(.*$/, ''),
      text: visibleText(screen.markup).join(' '),
    }));

    const vacuous = sentences
      .filter(({ text }) => !excused.has(text))
      .map(({ where, text }) => {
        const on = [...new Set(screens.filter((s) => s.text.includes(text)).map((s) => s.where))];
        return on.length === 0 ? null : `${where}: ${JSON.stringify(text)} is already on [${on.sort().join(', ')}]`;
      })
      .filter((entry): entry is string => entry !== null)
      .sort();

    expect(
      vacuous,
      'the journey declares these as proof that a step succeeded, and the application ' +
        'renders them with no step having run. The assertion cannot fail, in the gate or ' +
        'in the browser. Declare a sentence only that outcome renders, or drop the ' +
        'sentence and say in the step why its marker is the evidence -- do not reach for ' +
        'a longer substring of the same standing prose.',
    ).toEqual([]);

    // The other direction, so the exemption list is a ratchet and may only shrink.
    expect(
      [...excused].filter((text) => !screens.some((s) => s.text.includes(text))).sort(),
      'these are excused from the rule and no screen renders them any more. Delete their ' +
        'entries.',
    ).toEqual([]);
  });
});
