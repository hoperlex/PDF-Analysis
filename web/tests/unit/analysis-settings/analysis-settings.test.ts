/**
 * «Настройки анализа» (`W59-ANALYSIS-SETTINGS-01`): the fifteen sections and their analysis
 * profiles, read-only.
 *
 * Rendered, not read from source (`D-53`): every assertion is on markup a reviewer would see.
 * The fixture is the shape `listAnalysisProfiles` answers for this tree — АР with no profile
 * (`PROD-11-AR-V1-V2-REMOVAL-01`), and every other section with the status and version its line of
 * `section_profile_expectations.json` names (`PROD-14-0-EXPECTATIONS-01`), ПБ with no source.
 * That file is the one a section lane edits when its profile leaves `draft`; the fixture
 * mirrors the packages, and a case below fails when the file and a `profile.json` disagree.
 * The wording of a draft, of a reviewed profile and of a version is tested on synthetic
 * variants of one row, independent of what any real section's status is. A missing profile
 * is tested separately.
 */

import { existsSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import { describe, expect, it, vi } from 'vitest';

// `REVIEW-INDICATION-SWITCH-01` (`R-146ba`): this file asserts the wording of the screens with
// `SHOW_REVIEW_INDICATION` ON, the words the tree had before the beta, so it pins the switch ON and
// leaves every assertion as it was. The beta default (OFF) and both states of each string are in
// `tests/unit/review-indication/`.
vi.mock('@/shared/config/review-indication', () => ({ SHOW_REVIEW_INDICATION: true }));

import type { AnalysisProfileListItem, AnalysisProfileStatus } from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import {
  ANALYSIS_PROFILE_STATUS_LABELS,
  AR_NO_TEXT_PROFILE_LABEL,
  NO_PROFILE_LABEL,
  UNKNOWN_STATUS_LABEL,
  analysisProfileStatusLabel,
  analysisProfilesQueryOptions,
  isKnownAnalysisProfileStatus,
  shortDigest,
} from '@/entities/analysis-profile';
import { PROJECT_STRUCTURE_ORDER, projectSectionOf } from '@/entities/project';
import { AnalysisProfileTable } from '@/widgets/analysis-profile-table';
import { ArV3BetaStatus } from '@/widgets/ar-v3-beta-status';
import { AnalysisSettingsPage } from '@/_pages/analysis-settings';

import { newClient, renderScreen, seedError } from '../screens/harness';
import { REPO_ROOT, readJson } from '../../guards/lib/repo';

const LEGACY_COMMIT = '16ba8e5d23e4782550e79355002fde1365f682b7';
const ROLE_FILE_SHA = '9999c2e3398db818d1b85941473db785b8b132558c95661c016ad845a437b7fa';

/** One line per non-AR package: the status and version its `profile.json` must declare. */
const EXPECTATIONS_PATH = join(
  REPO_ROOT, 'tests', 'unit', 'analysis', 'text_profiles', 'section_profile_expectations.json',
);
const PACKAGES_PATH = join(REPO_ROOT, 'src', 'auditmanager', 'analysis', 'text', 'profiles');

interface PackageProfile {
  readonly status: string;
  readonly profile_version: string;
}

function expectedPackages(): Map<string, PackageProfile> {
  const document = readJson<{ sections: { code: string; status: string; profile_version: string }[] }>(
    EXPECTATIONS_PATH,
  );
  return new Map(document.sections.map((line) => [
    line.code, { status: line.status, profile_version: line.profile_version },
  ]));
}

/** What every `profile.json` under the packages root declares, by `section_code`. */
function declaredPackages(): Map<string, PackageProfile> {
  const found = new Map<string, PackageProfile>();
  for (const entry of readdirSync(PACKAGES_PATH, { withFileTypes: true }).filter((e) => e.isDirectory())) {
    const manifest = join(PACKAGES_PATH, entry.name, 'profile.json');
    if (!existsSync(manifest)) continue;
    const data = readJson<{ section_code: string; status: string; profile_version: string }>(manifest);
    found.set(data.section_code, { status: data.status, profile_version: data.profile_version });
  }
  return found;
}

/** Every way the expectations file and the packages disagree; empty when they agree. */
function disagreements(
  expected: ReadonlyMap<string, PackageProfile>,
  declared: ReadonlyMap<string, PackageProfile>,
): string[] {
  const found: string[] = [];
  for (const [code, profile] of declared) {
    const line = expected.get(code);
    if (line === undefined) found.push(`${code}: a package has no line in the expectations file`);
    else if (line.status !== profile.status) {
      found.push(`${code}: status ${line.status} in the file, ${profile.status} in profile.json`);
    } else if (line.profile_version !== profile.profile_version) {
      found.push(`${code}: version ${line.profile_version} in the file, ${profile.profile_version} in profile.json`);
    }
  }
  for (const code of expected.keys()) {
    if (!declared.has(code)) found.push(`${code}: a line of the expectations file has no package`);
  }
  return found;
}

const EXPECTED = expectedPackages();

/** The status of a real package line: one of the contract's two (`builtin` left the contract with АР's profile). */
function packageStatus(code: string, value: string): AnalysisProfileStatus {
  if (!isKnownAnalysisProfileStatus(value)) {
    throw new Error(`expectations file: ${code} has status ${value}, not a package status`);
  }
  return value;
}

function expectedOf(code: string): PackageProfile {
  const line = EXPECTED.get(code);
  if (line === undefined) throw new Error(`expectations file: no line for ${code}`);
  return line;
}

function item(code: (typeof PROJECT_STRUCTURE_ORDER)[number], index: number): AnalysisProfileListItem {
  const section = projectSectionOf(code);
  const digit = (index % 10).toString();
  // `PROD-11-AR-V1-V2-REMOVAL-01`: АР has no text profile, so its row carries none.
  if (code === 'AR') return { section_code: code, section_name: section.name, profile: null };
  const line = expectedOf(code);
  return {
    section_code: code,
    section_name: section.name,
    profile: {
      analysis_profile_id: `ap_01M5AXG1K22R027A33VTKZ468${digit}`,
      prompt_bundle_id: `pb_01M5AXG1K2JQQH7R4ACTBW897${digit}`,
      profile_version: line.profile_version,
      status: packageStatus(code, line.status),
      prompt_bundle_sha256: digit.repeat(64),
      content_sha256: 'e'.repeat(63) + digit,
      source: code === 'PB' ? null : {
        repository: 'PDF-proverka',
        commit: LEGACY_COMMIT,
        files: [
          { path: `prompts/disciplines/${code}/role.md`, sha256: ROLE_FILE_SHA },
          { path: `prompts/disciplines/${code}/checklist.md`, sha256: 'c'.repeat(64) },
        ],
      },
    },
  };
}

const ITEMS: readonly AnalysisProfileListItem[] = PROJECT_STRUCTURE_ORDER.map(item);

/** The fixture with one section's profile changed: a synthetic variant for a wording case. */
function withProfile(
  code: string,
  patch: { status?: AnalysisProfileStatus; profile_version?: string },
): readonly AnalysisProfileListItem[] {
  return ITEMS.map((entry) => entry.section_code === code && entry.profile !== null
    ? { ...entry, profile: { ...entry.profile, ...patch } }
    : entry);
}

function table(items: readonly AnalysisProfileListItem[] = ITEMS): string {
  return renderToStaticMarkup(createElement(AnalysisProfileTable, { items }));
}

/** The `data-section` of every body row, in document order. */
function rowCodes(markup: string): string[] {
  return [...markup.matchAll(/<tr data-section="([A-Z]+)"/g)].map((match) => match[1] as string);
}

/** The markup of one section's row. */
function row(markup: string, code: string): string {
  const start = markup.indexOf(`<tr data-section="${code}"`);
  expect(start, `no row for ${code}`).toBeGreaterThan(-1);
  return markup.slice(start, markup.indexOf('</tr>', start));
}

describe('the fifteen sections, in the order the server answers', () => {
  it('renders one row per section in the project-structure order, titled in Cyrillic', () => {
    const markup = table();
    expect(rowCodes(markup)).toEqual([...PROJECT_STRUCTURE_ORDER]);
    expect(row(markup, 'PS')).toContain('<strong>ПЗ</strong>');
    expect(row(markup, 'PS')).toContain('Пояснительная записка');
  });

  it('can fail: a row dropped or reordered is visible to the order check', () => {
    expect(rowCodes(table(ITEMS.slice(1)))).not.toEqual([...PROJECT_STRUCTURE_ORDER]);
    expect(rowCodes(table([...ITEMS].reverse()))).not.toEqual([...PROJECT_STRUCTURE_ORDER]);
  });
});

describe('the fixture mirrors the section packages of this tree', () => {
  it('has a line for exactly the packages that exist, with the status and version each declares', () => {
    expect(disagreements(EXPECTED, declaredPackages())).toEqual([]);
  });

  it('can fail: a changed status or version, a missing line and a line without a package are all seen', () => {
    const declared = new Map<string, PackageProfile>([
      ['KJ', { status: 'reviewed', profile_version: '2.0.0' }],
      ['OV', { status: 'draft', profile_version: '1.0.0' }],
      ['PB', { status: 'draft', profile_version: '1.0.0' }],
    ]);
    expect(disagreements(new Map(declared), declared)).toEqual([]);

    const changeStatus = new Map(declared).set('KJ', { status: 'draft', profile_version: '2.0.0' });
    expect(disagreements(changeStatus, declared)).toEqual(['KJ: status draft in the file, reviewed in profile.json']);

    const changeVersion = new Map(declared).set('OV', { status: 'draft', profile_version: '9.9.9' });
    expect(disagreements(changeVersion, declared))
      .toEqual(['OV: version 9.9.9 in the file, 1.0.0 in profile.json']);

    const dropLine = new Map(declared);
    dropLine.delete('PB');
    expect(disagreements(dropLine, declared)).toEqual(['PB: a package has no line in the expectations file']);

    const extraLine = new Map(declared).set('ZZ', { status: 'draft', profile_version: '1.0.0' });
    expect(disagreements(extraLine, declared)).toEqual(['ZZ: a line of the expectations file has no package']);
  });

  it('renders every package row with the status, its words and the version its line names', () => {
    const markup = table();
    for (const [code, line] of EXPECTED) {
      const html = row(markup, code);
      expect(html, code).toContain(`data-profile="${line.status}"`);
      expect(html, code).toContain(`data-profile-status="${line.status}"`);
      expect(html, code).toContain(analysisProfileStatusLabel(line.status));
      expect(html, code).toContain(`версия ${line.profile_version}`);
    }
  });

  it('shows the authored ПБ profile as its line names it, with no legacy source', () => {
    const line = expectedOf('PB');
    const pb = row(table(), 'PB');
    expect(pb).toContain(`data-profile="${line.status}"`);
    expect(pb).toContain(analysisProfileStatusLabel(line.status));
    expect(pb).toContain('data-profile-source="authored"');
    expect(pb).toContain(`версия ${line.profile_version}`);
    expect(pb).not.toContain(NO_PROFILE_LABEL);
  });
});

describe('what each row says', () => {
  it('marks a draft as needing an expert review, in words', () => {
    const ps = row(table(withProfile('PS', { status: 'draft', profile_version: '7.3.1' })), 'PS');
    expect(ps).toContain('черновик, требует экспертной проверки');
    expect(ps).toContain('data-profile="draft"');
    expect(ps).toContain('версия 7.3.1');
  });

  it('shows the authored ПБ draft and its required expert review', () => {
    const pb = row(table(withProfile('PB', { status: 'draft', profile_version: '7.3.1' })), 'PB');
    expect(pb).toContain('data-profile="draft"');
    expect(pb).toContain('черновик, требует экспертной проверки');
    expect(pb).toContain('data-profile-source="authored"');
    expect(pb).toContain('версия 7.3.1');
    expect(pb).not.toContain(NO_PROFILE_LABEL);
  });

  it('explains a profile-less section only when the server returns one', () => {
    const items = ITEMS.map((entry) => entry.section_code === 'GP' ? { ...entry, profile: null } : entry);
    const gp = row(table(items), 'GP');
    expect(gp).toContain(NO_PROFILE_LABEL);
    expect(gp).toContain('Прогон версии этого раздела будет отклонён.');
    expect(gp).toContain('data-profile="none"');
    expect(gp).not.toContain('версия');
    expect(gp).not.toContain('<details');
  });

  it('shows АР without a profile: no text profile, analysed by the six-check group', () => {
    const ar = row(table(), 'AR');
    expect(ar).toContain('data-profile="none"');
    expect(ar).toContain('data-profile-absent="ar-v3"');
    expect(ar).toContain(AR_NO_TEXT_PROFILE_LABEL);
    expect(ar).toContain('группой из шести проверок АР v3');
    expect(ar).not.toContain(NO_PROFILE_LABEL);
    expect(ar).not.toContain('встроенный');
    expect(ar).not.toContain('<details');
    expect(ar).not.toContain('PDF-proverka');
  });

  it('keeps the generic wording for any other section the server leaves without a profile', () => {
    const items = ITEMS.map((entry) => entry.section_code === 'GP' ? { ...entry, profile: null } : entry);
    const gp = row(table(items), 'GP');
    expect(gp).toContain('data-profile-absent="unregistered"');
    expect(gp).not.toContain(AR_NO_TEXT_PROFILE_LABEL);
  });

  it('labels a reviewed profile and shows its own version', () => {
    expect(row(table(withProfile('POS', { status: 'reviewed' })), 'POS')).toContain('проверка человеком не проводилась');
    expect(row(table(withProfile('TX', { profile_version: '1.2.0' })), 'TX')).toContain('версия 1.2.0');
  });

  it('shows the prompt-bundle hash short in the row and in full in the details', () => {
    const kj = row(table(), 'KJ');
    const index = PROJECT_STRUCTURE_ORDER.indexOf('KJ');
    const full = (index % 10).toString().repeat(64);
    expect(kj).toContain(`>${shortDigest(full)}</code>`);
    expect(kj).toContain(`<code>${full}</code>`);
  });

  it('puts the identities, the legacy repository, commit and every file hash in the details', () => {
    const vk = row(table(), 'VK');
    const details = vk.slice(vk.indexOf('<details'));
    expect(details).toContain('<summary>Подробнее</summary>');
    expect(details).toMatch(/ap_01M5AXG1K22R027A33VTKZ468\d/);
    expect(details).toMatch(/pb_01M5AXG1K2JQQH7R4ACTBW897\d/);
    expect(details).toContain('PDF-proverka');
    expect(details).toContain(LEGACY_COMMIT);
    expect(details).toContain('prompts/disciplines/VK/role.md');
    expect(details).toContain(ROLE_FILE_SHA);
    expect(details).toContain('prompts/disciplines/VK/checklist.md');
  });

  it('labels every contract status, and an unknown one as unknown rather than a guess', () => {
    expect(Object.keys(ANALYSIS_PROFILE_STATUS_LABELS).sort()).toEqual(['draft', 'reviewed']);
    expect(analysisProfileStatusLabel('builtin')).toBe(UNKNOWN_STATUS_LABEL);
    expect(analysisProfileStatusLabel('draft')).toBe('черновик, требует экспертной проверки');
    expect(analysisProfileStatusLabel('retired')).toBe(UNKNOWN_STATUS_LABEL);
  });
});

describe('read-only', () => {
  it('offers no control that could write: no form, input, select or button in the table', () => {
    const markup = table();
    expect(markup).not.toMatch(/<(form|input|select|textarea|button)\b/);
  });

  it('can fail: the same check sees a button', () => {
    expect('<td><button type="button">Изменить</button></td>').toMatch(/<(form|input|select|textarea|button)\b/);
  });
});

describe('the page', () => {
  it('reads the registry under its own key', () => {
    expect(analysisProfilesQueryOptions().queryKey).toEqual(queryKeys.analysis.profiles());
  });

  it('renders the table once the registry is read', () => {
    const client = newClient();
    client.setQueryData(queryKeys.analysis.profiles(), { items: ITEMS });
    const markup = renderScreen(client, createElement(AnalysisSettingsPage));
    expect(markup).toContain('Настройки анализа');
    expect(rowCodes(markup)).toEqual([...PROJECT_STRUCTURE_ORDER]);
  });

  it('says it is loading before the registry is read', () => {
    const markup = renderScreen(newClient(), createElement(AnalysisSettingsPage));
    expect(markup).toContain('Загрузка: профилей анализа…');
    expect(rowCodes(markup)).toEqual([]);
  });

  it('renders a refusal in Russian with its correlation id, and no table', () => {
    const client = newClient();
    seedError(client, queryKeys.analysis.profiles(), new ApiError(403, {
      contract_version: '1.8.0', error_code: 'permission_denied',
      message: 'permission denied', correlation_id: 'cid-analysis-settings-1', retryable: false,
    }, null));
    const markup = renderScreen(client, createElement(AnalysisSettingsPage));
    expect(markup).toContain('Профили анализа не прочитаны');
    expect(markup).toContain('data-analysis-profiles-failure="permission_denied"');
    expect(markup).toContain('cid-analysis-settings-1');
    expect(rowCodes(markup)).toEqual([]);
  });
});

describe('the AR v3 beta source preview', () => {
  it('shows all six scopes and every topic exactly once, with no runnable control', () => {
    const markup = renderToStaticMarkup(createElement(ArV3BetaStatus));
    expect([...markup.matchAll(/data-ar-v3-scope="([A-Z][0-9])"/g)].map((match) => match[1]))
      .toEqual(['F1', 'F2', 'A1', 'A2', 'S1', 'S2']);
    const ids = [...markup.matchAll(/data-ar-v3-item="(C\d\d)"/g)].map((match) => match[1]);
    expect(ids).toEqual(Array.from({ length: 22 }, (_, index) => `C${String(index + 1).padStart(2, '0')}`));
    expect(markup).toContain('предварительные ссылки: 14; только контекст: 8');
    expect(markup).toContain('Она не запускает прогон v3');
    expect(markup).not.toMatch(/<(form|input|select|textarea|button)\b/);
  });

  it('does not present a context-only topic as a numeric check', () => {
    const markup = renderToStaticMarkup(createElement(ArV3BetaStatus));
    expect(markup).toContain('data-ar-v3-item="C15" data-ar-v3-mode="context_only"');
    expect(markup).toContain('Только контекст — требуется проверка эксперта');
    expect(markup).toContain('не выдаёт числовые выводы');
  });
});
