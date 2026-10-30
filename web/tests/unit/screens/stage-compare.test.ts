import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { StageComparePage } from '@/_pages/stage-compare';
import { STAGE_PAIR_KEYS } from '@/entities/stage-pair';

import { newClient, renderScreen } from './harness';
import { DOCUMENT_UID, PROJECT_UID, uid } from '../version-compare/fixtures';
import { READER, seedComparison } from '../version-compare/seed';

const RIGHT = uid('doc', 18);
const PAIR = uid('stp', 19);

function loaded(expert = true): string {
  const client = newClient();
  seedComparison(client, { modules: 'versions,stages', ...(expert ? {} : { account: READER }) });
  client.setQueryData(STAGE_PAIR_KEYS.pairs(PROJECT_UID), {
    items: [{ pair_id: PAIR, project_uid: PROJECT_UID, left_document_uid: DOCUMENT_UID, right_document_uid: RIGHT, completeness: 'unknown', state: 'confirmed', created_at: '2026-10-29T00:00:00Z' }],
    page: { next_cursor: null },
  });
  client.setQueryData(STAGE_PAIR_KEYS.suggestions(PROJECT_UID), {
    items: [{ left_document_uid: uid('doc', 20), right_document_uid: uid('doc', 21), reason: 'section_designation_exact', score: 1 }],
    page: { next_cursor: null },
  });
  const fileId = uid('suf', 22);
  client.setQueryData(['comparison', 'stage-uploads', PROJECT_UID, ''], {
    items: [{
      upload_id: uid('stu', 23), project_uid: PROJECT_UID, state: 'completed',
      created_at: '2026-10-29T00:00:00Z', updated_at: '2026-10-29T00:00:00Z',
      files: [{
        file_id: fileId, upload_id: uid('stu', 23), state: 'ready',
        declaration: { display_name: 'АР-01.pdf', media_kind: 'pdf', size_bytes: 12, sha256: 'a'.repeat(64) },
        received_parts: 1, received_bytes: 12, created_at: '2026-10-29T00:00:00Z',
      }],
      candidates: [{
        candidate_id: uid('suc', 24), file_id: fileId, member_number: 1,
        display_name: 'АР-01.pdf', state: 'proposed',
      }],
    }],
    page: { next_cursor: null },
  });
  return renderScreen(client, createElement(StageComparePage));
}

describe('stage comparison catalog', () => {
  it('shows confirmed pairs separately from nonbinding suggestions and offers expert acts', () => {
    const html = loaded();
    expect(html).toContain('Пары стадий');
    expect(html).toContain('Наборы PDF и ZIP');
    expect(html).toContain('Загрузить новый набор');
    expect(html).toContain('АР-01.pdf');
    expect(html).toContain('Подтвердить документ');
    expect(html).toContain('Возможные пары');
    expect(html).toContain('Полнота не указана');
    expect(html).toContain('Совпадают раздел и подтверждённый шифр');
    expect(html).toContain('Проверить связь');
    expect(html).toContain('Полный');
    expect(html).toContain(`href="/projects/${PROJECT_UID}/documents/${DOCUMENT_UID}"`);
  });

  it('keeps the catalog readable for a nonexpert but withholds decisions', () => {
    const html = loaded(false);
    expect(html).toContain('Пары стадий');
    expect(html).toContain('Наборы PDF и ZIP');
    expect(html).not.toContain('Загрузить новый набор');
    expect(html).toContain('АР-01.pdf');
    expect(html).not.toContain('Подтвердить документ');
    expect(html).toContain('Возможные пары');
    expect(html).not.toContain('Проверить связь');
    expect(html).not.toContain('>Неполный</button>');
  });

  it('does not mount the catalog when the stages module is off', () => {
    const client = newClient();
    seedComparison(client, { modules: 'versions' });
    const html = renderScreen(client, createElement(StageComparePage));
    expect(html).toContain('Модуль «Сравнение стадий» выключен');
    expect(html).not.toContain('Пары стадий');
    expect(html).not.toContain('Наборы PDF и ZIP');
    expect(html).not.toContain('Возможные пары');
  });
});
