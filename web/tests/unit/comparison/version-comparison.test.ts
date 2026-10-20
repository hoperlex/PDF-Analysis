/**
 * The version comparison on the comparison screen (`W59-VERSION-COMPARE-01`).
 *
 * Rendered through the screen harness with seeded caches: the version, its set's versions
 * and the comparison answer. Each test reads what a reviewer sees and the `data-` attributes
 * an instrument reads, never the component's internals.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { DocumentVersion, VersionClassification, VersionComparison } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { COMPARISON_DIFF_LIMIT, VERSION_PAGE_LIMIT, orderedPair, refusalText, stageModeOffered } from '@/entities/document-version';
import { StageComparisonPage } from '@/_pages/stage-comparison';

import { newClient, renderScreen } from '../screens/harness';

const ULID = '01M2545JSD15ETSNNV904X991J';
const PROJECT_UID = `prj_${ULID}`;
const DOCUMENT_UID = `doc_${ULID}`;
const OLDER = `ver_${ULID}`;
const NEWER = 'ver_01M2545JSD15ETSNNV904X991K';
const SHA = 'a'.repeat(64);

function classification(versionUid: string, stage: 'P' | 'R', section = 'AR'): VersionClassification {
  return {
    version_uid: versionUid,
    project_stage: stage,
    section_code: section as VersionClassification['section_code'],
    confirmed_by_user_uid: `usr_${ULID}`,
    confirmed_at: '2026-10-20T08:00:00Z',
  };
}

function version(over: Partial<DocumentVersion>): DocumentVersion {
  return {
    version_uid: OLDER,
    document_uid: DOCUMENT_UID,
    project_uid: PROJECT_UID,
    version_ordinal: 1,
    media_type: 'application/pdf',
    byte_size: 1,
    sha256: SHA,
    page_count: 3,
    published_at: '2026-10-20T08:00:00Z',
    input_manifest: [],
    ...over,
  };
}

const OLDER_VERSION = version({ classification: classification(OLDER, 'P') });
const NEWER_VERSION = version({
  version_uid: NEWER, version_ordinal: 2, classification: classification(NEWER, 'P'),
});

function compared(over: Partial<VersionComparison> = {}): VersionComparison {
  return {
    project_uid: PROJECT_UID, document_uid: DOCUMENT_UID,
    source_version_uid: OLDER, target_version_uid: NEWER,
    mode: 'version', outcome: 'compared', refusal: null,
    source: { version_uid: OLDER, version_ordinal: 1, page_count: 3, sha256: SHA, project_stage: 'P',
      section_code: 'AR', run_id: `run_${ULID}`, text_layer_sha256: SHA },
    target: { version_uid: NEWER, version_ordinal: 2, page_count: 3, sha256: SHA, project_stage: 'P',
      section_code: 'AR', run_id: 'run_01M2545JSD15ETSNNV904X991K', text_layer_sha256: SHA },
    comparison_sha256: SHA,
    sheets: [
      { status: 'unchanged', source_page_number: 1, target_page_number: 1, pairing_basis: 'exact_text',
        similarity_permille: 1000, shared_line_count: null, suggestion_sha256: SHA, textless: false },
      { status: 'changed', source_page_number: 2, target_page_number: 3, pairing_basis: 'similar_text',
        similarity_permille: 833, shared_line_count: 5, suggestion_sha256: SHA, textless: false },
      { status: 'added', source_page_number: null, target_page_number: 2, pairing_basis: null,
        similarity_permille: null, shared_line_count: null, suggestion_sha256: null, textless: true },
    ],
    sheet_diffs: {
      offset: 0, limit: COMPARISON_DIFF_LIMIT, total: 1, next_offset: null,
      items: [{
        status: 'changed', source_page_number: 2, target_page_number: 3, outcome: 'computed',
        too_large_reason: null, source_line_count: 3, target_line_count: 3, added_line_count: 1,
        removed_line_count: 1, evidence_sha256: SHA,
        hunks: [
          { tag: 'equal', source_start: 0, source_end: 2, target_start: 0, target_end: 2,
            source_lines: [], target_lines: [] },
          { tag: 'replace', source_start: 2, source_end: 3, target_start: 2, target_end: 3,
            source_lines: ['Стена 200\n'], target_lines: ['Стена 250\n'] },
        ],
      }],
    },
    findings: {
      status: 'compared', unavailable_reason: null, source_finding_count: 1, target_finding_count: 1,
      proposals: [
        { kind: 'probably_fixed', basis: 'quotes_absent_from_paired_sheets', proposal_sha256: null,
          source_finding: { finding_uid: `fnd_${ULID}`, category: 'dimensions',
            finding_text: 'Толщина стены не совпадает', page_numbers: [2] },
          target_finding: null },
        { kind: 'new', basis: 'no_exact_source_match', proposal_sha256: null, source_finding: null,
          target_finding: { finding_uid: 'fnd_01M2545JSD15ETSNNV904X991K', category: 'layout',
            finding_text: 'Нет дверного проёма', page_numbers: [3] } },
      ],
      carryover_candidates: [],
    },
    ...over,
  };
}

function screen(
  versionUid: string,
  versions: readonly DocumentVersion[],
  answer: VersionComparison | null,
  current: DocumentVersion = OLDER_VERSION,
): string {
  const client = newClient();
  client.setQueryData(queryKeys.versions.detail(versionUid), current);
  client.setQueryData(queryKeys.versions.list(DOCUMENT_UID, undefined, VERSION_PAGE_LIMIT), {
    items: versions, page: { next_cursor: null },
  });
  if (answer !== null) {
    client.setQueryData(
      queryKeys.versions.comparison(OLDER, NEWER, answer.mode, 0, COMPARISON_DIFF_LIMIT), answer,
    );
  }
  return renderScreen(client, createElement(StageComparisonPage, { projectUid: PROJECT_UID, versionUid }));
}

function visible(markup: string): string {
  return markup.replace(/<[^>]*>/g, ' ').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ');
}

describe('a set with one version has nothing to compare', () => {
  it('says so instead of asking the server', () => {
    const markup = screen(OLDER, [OLDER_VERSION], null);
    expect(visible(markup)).toContain('В комплекте пока одна версия.');
    expect(markup).not.toContain('data-version-comparison');
  });
});

describe('a compared pair', () => {
  const markup = screen(OLDER, [NEWER_VERSION, OLDER_VERSION], compared());
  const text = visible(markup);

  it('labels the pairing and the finding matches as proposals', () => {
    expect(text).toContain('Сопоставление листов (предложение)');
    expect(text).toContain('Соответствие замечаний (предложение)');
    expect(text).toContain('предложения системы, а не решения эксперта');
  });

  it('shows every sheet with its status and the evidence of its pair', () => {
    expect(markup).toContain('data-sheet-status="unchanged"');
    expect(markup).toContain('data-sheet-status="changed"');
    expect(text).toContain('похожий текст: сходство 83 %, общих строк 5');
    expect(text).toContain('нет текстового слоя');
    expect(text).toContain('Без изменений: 1 · изменено: 1 · удалено: 0 · добавлено: 1.');
  });

  it('shows the raw changed lines with their page and line anchors, equal lines as a count', () => {
    expect(text).toContain('Лист 2 → лист 3');
    expect(markup).toContain('<del');
    expect(markup).toContain('<ins');
    expect(text).toContain('Стена 200');
    expect(text).toContain('Стена 250');
    expect(text).toContain('строк без изменений: 2');
  });

  it('labels each finding proposal in Russian and keeps the kind in an attribute', () => {
    expect(markup).toContain('data-proposal-kind="probably_fixed"');
    expect(text).toContain('Вероятно, устранено');
    expect(text).toContain('Новое');
    expect(text).toContain('цитируемого текста на сопоставленном листе больше нет');
  });

  it('keeps the run comparison below it', () => {
    expect(text).toContain('Сравнение прогонов');
  });
});

describe('a refused pair', () => {
  it('names the reason and never shows a comparison', () => {
    const refused = compared({
      outcome: 'refused', refusal: { reason: 'confirmed_section_mismatch', side: null },
      comparison_sha256: null, sheets: [], sheet_diffs: null, findings: null,
    });
    const markup = screen(OLDER, [NEWER_VERSION, OLDER_VERSION], refused);
    expect(markup).toContain('data-comparison-refusal="confirmed_section_mismatch"');
    expect(visible(markup)).toContain('У версий подтверждены разные разделы.');
    expect(markup).not.toContain('data-sheet-status');
  });

  it('names the side a reason belongs to', () => {
    expect(refusalText({ reason: 'stage_unclassified', side: 'target' })).toBe(
      'У более поздней версии не указана стадия (П или Р).',
    );
  });
});

describe('the pair is ordered and the stage switch offered only where it means something', () => {
  it('asks older → newer even from the newer version', () => {
    const markup = screen(NEWER, [NEWER_VERSION, OLDER_VERSION], compared(), NEWER_VERSION);
    expect(markup).toContain('data-comparison-outcome="compared"');
  });

  it('offers «Стадии П → Р» for a confirmed П source and Р target of one section', () => {
    const working = version({
      version_uid: NEWER, version_ordinal: 2, classification: classification(NEWER, 'R'),
    });
    const { source, target } = orderedPair(working, OLDER_VERSION);
    expect(source.version_uid).toBe(OLDER);
    expect(stageModeOffered(source, target)).toBe(true);
    expect(stageModeOffered(OLDER_VERSION, NEWER_VERSION)).toBe(false);
    expect(
      stageModeOffered(OLDER_VERSION, version({
        version_uid: NEWER, version_ordinal: 2, classification: classification(NEWER, 'R', 'KJ'),
      })),
    ).toBe(false);
    const markup = screen(OLDER, [working, OLDER_VERSION], null);
    expect(visible(markup)).toContain('Стадии П → Р');
  });
});
