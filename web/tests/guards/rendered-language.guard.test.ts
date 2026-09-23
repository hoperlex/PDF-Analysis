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
import type { ReactElement } from 'react';
import { describe, expect, it } from 'vitest';

import { AppRouterContext } from 'next/dist/shared/lib/app-router-context.shared-runtime';
import type { AppRouterInstance } from 'next/dist/shared/lib/app-router-context.shared-runtime';

import { ApiError, queryKeys } from '@/shared/api';
import type {
  DecisionEvent,
  DecisionRecord,
  DocumentVersion,
  ErrorCode,
  ErrorEnvelope,
  Finding,
  FindingDetail,
  Project,
  RunStatus,
  StageId,
  StageStatus,
} from '@/shared/api';
import { RUN_PAGE_LIMIT } from '@/entities/audit-run';
import { JOURNAL_PAGE_LIMIT } from '@/entities/expert-decision';
import { DOCUMENT_PAGE_LIMIT, VERSION_PAGE_LIMIT } from '@/entities/document-version';
import { PROJECT_PAGE_LIMIT } from '@/entities/project';
import { DocumentDetailPage } from '@/_pages/document-detail';
import { ProjectDetailPage } from '@/_pages/project-detail';
import { AppFrame } from '@/_app';
import { ProjectsPage } from '@/_pages/projects';
import { KnowledgeBasePage } from '@/_pages/knowledge-base';
import { ReviewPage } from '@/_pages/review';
import { SignInPage } from '@/_pages/sign-in';
import { ChangePasswordPage } from '@/_pages/change-password';
import { RunPage } from '@/_pages/run';
import { VersionDetailPage } from '@/_pages/version-detail';

import { CONTRACT_PATH, SEAMS_PATH, readJson, readText } from './lib/repo';
import { join } from 'node:path';
import { REPO_ROOT } from './lib/repo';
import { newClient, renderWith, seedError } from '../unit/screens/harness';

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
 * The seventeen CSV column names, parsed out of the seam document that freezes them.
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

/** Everything a contract or a frozen seam document puts on a screen. */
export function contractVocabulary(): ReadonlySet<string> {
  return new Set([...contractEnums(), ...csvColumnNames(), ...manifestRoles()]);
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
  { word: 'API', why: 'The name of the seam the screens talk to. Universal in Russian technical writing; nothing in `contracts/` defines the word itself.' },
  { word: 'RFC', why: 'The IETF document series, cited by number beside the CSV escaping rule. A citation, not a label.' },
  { word: 'SHA', why: 'The digest algorithm family, shown as SHA-256 beside a version. FIPS 180-4 fixes the spelling; no contract here does.' },
  { word: 'UTF', why: 'The character encoding family, shown as utf-8 in the export description. The IANA charset registry fixes the spelling; matched case-insensitively for that one entry alone.' },
  { word: 'UTC', why: 'The time-scale designator printed after a timestamp. Where a timestamp precedes it the ISO pattern already consumes it; this entry covers the case where it stands alone.' },
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
  // RFC 6838. `application/pdf` is the only one this application names, but the shape is
  // the authority, not the value.
  { name: 'media types', pattern: /\b[a-z]+\/[a-z0-9.+-]+\b/g },
  { name: 'URLs and object urls', pattern: /\b(?:https?|blob|data):[^\s"'<>]+/g },
  // A filename is the server's or the user's, never this application's prose. The
  // extension is matched with it, so `.pdf` and `.csv` need no entry of their own.
  { name: 'filenames', pattern: /\S*[^\s.]\.(?:pdf|csv|json|png|txt|zip)\b/gi },
  { name: 'absolute paths', pattern: /(?:^|[\s(])\/[A-Za-z0-9._~\-/[\]]*/g },
  // ISO 8601, which is how every timestamp in the contract is written.
  // ISO 8601, and the `UTC` designator the screens print after the local rendering of it.
  // The designator is matched only where a timestamp precedes it, so a bare `UTC` in a
  // sentence is still an offence.
  { name: 'ISO 8601 timestamps', pattern: /\b\d{4}-\d{2}-\d{2}[T ][\d:.]+(?:Z|\s*UTC)?\b/g },
  { name: 'the product designation', pattern: /\bPC-\d{2}\b/g },
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

function stubRouter(): AppRouterInstance {
  return {
    push: () => {}, replace: () => {}, back: () => {}, forward: () => {},
    refresh: () => {}, prefetch: () => {},
  } as unknown as AppRouterInstance;
}

type Client = ReturnType<typeof newClient>;

function renderScreen(client: Client, element: ReactElement): string {
  return renderWith(
    client,
    createElement(AppRouterContext.Provider, { value: stubRouter() }, element),
  );
}

// --------------------------------------------------------- Cyrillic-only server data

const ULID = '01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const PROJECT_UID = `prj_${ULID}`;
const DOCUMENT_UID = `doc_${ULID}`;
const VERSION_UID = `ver_${ULID}`;
const RUN_ID = `run_${ULID}`;
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
    contract_version: '1.0.0-draft.1',
    error_code: code,
    message: 'Сообщение об отказе.',
    correlation_id: '0f0e9d8c-7b6a-4948-b726-150413021100',
    retryable: false,
  };
  return new ApiError(status, envelope, '0f0e9d8c-7b6a-4948-b726-150413021100');
}

const KEYS = {
  projects: queryKeys.projects.list(undefined, PROJECT_PAGE_LIMIT),
  project: queryKeys.projects.detail(PROJECT_UID),
  documents: queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT),
  versions: queryKeys.versions.list(DOCUMENT_UID, undefined, VERSION_PAGE_LIMIT),
  version: queryKeys.versions.detail(VERSION_UID),
  content: queryKeys.versions.content(VERSION_UID),
  runs: queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT),
  run: queryKeys.runs.detail(RUN_ID),
  findings: queryKeys.runs.findings(RUN_ID),
  finding: queryKeys.findings.detail(FINDING_UID),
  decisions: queryKeys.findings.decisions(FINDING_UID),
  journal: queryKeys.findings.journal({ limit: JOURNAL_PAGE_LIMIT }),
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

const SCREENS: readonly { readonly name: string; readonly make: () => ReactElement }[] = [
  { name: 'projects', make: () => createElement(ProjectsPage, {}) },
  {
    name: 'project-detail',
    make: () => createElement(ProjectDetailPage, { projectUid: PROJECT_UID }),
  },
  {
    name: 'document-detail',
    make: () =>
      createElement(DocumentDetailPage, { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID }),
  },
  {
    name: 'version-detail',
    make: () =>
      createElement(VersionDetailPage, { projectUid: PROJECT_UID, versionUid: VERSION_UID }),
  },
  { name: 'run', make: () => createElement(RunPage, { projectUid: PROJECT_UID, runId: RUN_ID }) },
  {
    name: 'review',
    make: () => createElement(ReviewPage, { projectUid: PROJECT_UID, runId: RUN_ID }),
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
   */
  { name: 'app-frame', make: () => createElement(AppFrame, { children: null }) },
  /*
   * The sign-in screen, and its two other shapes, APPENDED.
   *
   * Appended and not inserted: `renderedScreens()` reaches the review screen by index --
   * `SCREENS[5]!.make()` for the detail-pending pass -- so a screen put anywhere but the end
   * silently renders a different page under the review screen's name. That is a footgun of
   * this file's own making and it is cheaper to write the rule down than to remove the index.
   *
   * Three entries rather than one because the screen has three shapes and a static pass
   * renders exactly what its props select: the credentials form, the form carrying a
   * refusal, and the panel a signed-in reviewer sees. `W32-SEE` measured the cost of the
   * opposite choice -- an English sentence in a branch nothing rendered reddened nothing --
   * and the branch here is the whole refusal wording, which is the one string on this
   * screen a reviewer reads only when something has gone wrong.
   *
   * The login is Cyrillic for the reason every fixture in this file is: it is the server's
   * data, not this programme's prose. The other three refusal sentences are judged by
   * `web/tests/unit/session/sign-in-screen.test.ts`, which renders all four.
   */
  { name: 'sign-in', make: () => createElement(SignInPage, {}) },
  { name: 'sign-in-refused', make: () => createElement(SignInPage, { refusal: 'credentials' }) },
  { name: 'sign-in-open', make: () => createElement(SignInPage, { login: 'проверяющий' }) },
  /*
   * The knowledge base, `R-23`, APPENDED for the reason stated above: `renderedScreens()`
   * reaches the review screen by index, so a screen inserted anywhere but the end renders
   * a different page under the review screen's name.
   *
   * One entry and not three, unlike the sign-in screen: its two filters are `select`
   * elements whose every option is rendered in a single static pass, so the labels a
   * reviewer can choose between are all in this markup. What one pass cannot reach is the
   * *result* of choosing one, and that is a query key rather than a string.
   */
  { name: 'knowledge-base', make: () => createElement(KnowledgeBasePage, {}) },
  /*
   * The password screen, `R-26`, APPENDED for the reason stated twice above:
   * `renderedScreens()` reaches the review screen by index, so a screen inserted anywhere
   * but the end renders a different page under the review screen's name.
   *
   * FOUR entries, one more than the sign-in screen, because this screen has four shapes a
   * static pass can select between and all four carry prose a reviewer reads:
   *
   *   - signed out: no form at all, because a form that could only be refused teaches a
   *     reviewer that a refusal means nothing;
   *   - signed in, nothing attempted: the form and the sentence that says what pressing the
   *     button will revoke;
   *   - refused: the `ErrorState` wording, which `W32-SEE` measured as the exact place an
   *     English sentence survives -- a branch nothing renders reddens nothing;
   *   - changed: the one outcome that is NOT an error, and therefore the one shape whose
   *     markup this file would otherwise never see.
   *
   * The other four refusal sentences are judged by
   * `web/tests/unit/session/change-password.test.ts`, which renders all six outcomes.
   * The login is Cyrillic for the reason every fixture in this file is: it is the server's
   * data, not this programme's prose.
   */
  { name: 'change-password-signed-out', make: () => createElement(ChangePasswordPage, {}) },
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
  { state: 'partial-run', run: { state: 'partial', degradation_set: ['text_analysis'] } },
  { state: 'running', run: { state: 'running', terminal_at: null, published_finding_count: 0 } },
  { state: 'refused', run: null },
  { state: 'empty', run: null },
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
];

export function renderedScreens(): readonly { readonly where: string; readonly markup: string }[] {
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
              : state === 'paged'
                ? pagedClient(loaded)
                : loaded(overrides ?? {});
      out.push({ where: `${screen.name} (${state})`, markup: renderScreen(client, screen.make()) });
    }
  }
  out.push({
    where: 'review (detail-pending)',
    markup: renderScreen(reviewDetailPendingClient(), SCREENS[5]!.make()),
  });
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
      'live', 'recorded', 'measured', 'estimated']) {
      expect(TRANSLATED.has(value), `${value} left the translated schemas`).toBe(true);
      expect(VOCABULARY.has(value), `${value} is permitted as visible text again`).toBe(false);
    }
    // The two derivations that are not openapi enums, asserted as relationships so a
    // parser that silently returned nothing is red rather than merely permissive.
    expect(csvColumnNames().size, 'OD-11 freezes seventeen CSV columns').toBe(17);
    expect(csvColumnNames().has('finding_uid')).toBe(true);
    expect(manifestRoles().has('source.document'), 'the stage registry declares it').toBe(true);

    // `proxy` must NOT be derivable, or `NOT_DERIVABLE`'s first entry is stale.
    expect(VOCABULARY.has('proxy'), 'proxy is now in the contract; delete it from NOT_DERIVABLE').toBe(false);
  });

  it('keeps the hand-written residue small, and every entry reasoned', () => {
    expect(NOT_DERIVABLE.length).toBeLessThanOrEqual(12);
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
    expect(unexplainedLatin('2026-09-10T08:00:00.000Z', VOCABULARY)).toEqual([]);
    expect(unexplainedLatin('Один PDF за загрузку.', VOCABULARY)).toEqual([]);
    expect(unexplainedLatin('0f0e9d8c-7b6a-4948-b726-150413021100', VOCABULARY)).toEqual([]);
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
    expect(unexplainedLatin('text_analysis', VOCABULARY)).toEqual(['text', 'analysis']);
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

  it('reaches all six screens in every state, and none of them throws', () => {
    // A RELATIONSHIP, not a number. This read `SCREENS.length * 7 + 1` and went red the
    // moment the matrix grew, which teaches the next reader to update a literal — exactly how
    // a vacuity check stops checking. `W30-LISTS` ruled against hard-coded counts two waves
    // ago and this was one of them.
    expect(screens.length).toBe(SCREENS.length * CACHE_STATES.length + 1);
    // And both factors are non-trivial, so a matrix that silently emptied is red rather than
    // trivially satisfied.
    expect(SCREENS.length).toBeGreaterThan(1);
    expect(CACHE_STATES.length).toBeGreaterThan(1);
    for (const { where, markup } of screens) {
      expect(markup.length, `${where} rendered nothing`).toBeGreaterThan(200);
    }
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

