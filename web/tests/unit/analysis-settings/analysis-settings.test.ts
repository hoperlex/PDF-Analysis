/**
 * «Настройки анализа» (`W59-ANALYSIS-SETTINGS-01`): the fifteen sections and their analysis
 * profiles, read-only.
 *
 * Rendered, not read from source (`D-53`): every assertion is on markup a reviewer would see.
 * The fixture is the shape `listAnalysisProfiles` answers — AR builtin with no source, a draft,
 * a reviewed profile, and ПБ with none.
 */

import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { AnalysisProfileListItem } from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import {
  ANALYSIS_PROFILE_STATUS_LABELS,
  NO_PROFILE_LABEL,
  UNKNOWN_STATUS_LABEL,
  analysisProfileStatusLabel,
  analysisProfilesQueryOptions,
  shortDigest,
} from '@/entities/analysis-profile';
import { PROJECT_STRUCTURE_ORDER, projectSectionOf } from '@/entities/project';
import { AnalysisProfileTable } from '@/widgets/analysis-profile-table';
import { ArV3BetaStatus } from '@/widgets/ar-v3-beta-status';
import { AnalysisSettingsPage } from '@/_pages/analysis-settings';

import { newClient, renderScreen, seedError } from '../screens/harness';

const LEGACY_COMMIT = '16ba8e5d23e4782550e79355002fde1365f682b7';
const ROLE_FILE_SHA = '9999c2e3398db818d1b85941473db785b8b132558c95661c016ad845a437b7fa';

function item(code: (typeof PROJECT_STRUCTURE_ORDER)[number], index: number): AnalysisProfileListItem {
  const section = projectSectionOf(code);
  if (code === 'PB') return { section_code: code, section_name: section.name, profile: null };
  const digit = (index % 10).toString();
  return {
    section_code: code,
    section_name: section.name,
    profile: {
      analysis_profile_id: `ap_01M5AXG1K22R027A33VTKZ468${digit}`,
      prompt_bundle_id: `pb_01M5AXG1K2JQQH7R4ACTBW897${digit}`,
      profile_version: code === 'TX' ? '1.2.0' : '1.0.0',
      status: code === 'AR' ? 'builtin' : code === 'POS' ? 'reviewed' : 'draft',
      prompt_bundle_sha256: digit.repeat(64),
      content_sha256: 'e'.repeat(63) + digit,
      source: code === 'AR' ? null : {
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

describe('what each row says', () => {
  it('marks a draft as needing an expert review, in words', () => {
    const ps = row(table(), 'PS');
    expect(ps).toContain('черновик, требует экспертной проверки');
    expect(ps).toContain('data-profile="draft"');
    expect(ps).toContain('версия 1.0.0');
  });

  it('says ПБ has no profile, and what follows from it, without inventing one', () => {
    const pb = row(table(), 'PB');
    expect(pb).toContain(NO_PROFILE_LABEL);
    expect(pb).toContain('Прогон версии этого раздела будет отклонён.');
    expect(pb).toContain('data-profile="none"');
    expect(pb).not.toContain('версия');
    expect(pb).not.toContain('<details');
  });

  it('shows the builtin AR profile as written here, with no legacy source', () => {
    const ar = row(table(), 'AR');
    expect(ar).toContain('встроенный');
    expect(ar).toContain('data-profile-source="builtin"');
    expect(ar).not.toContain('PDF-proverka');
  });

  it('labels a reviewed profile and shows its own version', () => {
    expect(row(table(), 'POS')).toContain('проверен экспертом');
    expect(row(table(), 'TX')).toContain('версия 1.2.0');
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
    expect(Object.keys(ANALYSIS_PROFILE_STATUS_LABELS).sort()).toEqual(['builtin', 'draft', 'reviewed']);
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
      contract_version: '1.4.0', error_code: 'permission_denied',
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
