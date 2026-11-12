import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ConsolidatedObservations } from '@/widgets/extended-review/ui/consolidated-observations';
import { extendedCandidateCounts } from '@/widgets/extended-review/ui/extended-review-summary';
import { InputPassport } from '@/widgets/extended-review/ui/input-passport';
import { MachineAdvice } from '@/widgets/extended-review/ui/machine-advice';
import { mountLive } from '../analysis-settings/live-render';

beforeEach(() => vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', 'https://api.example.test/api/v1'));
afterEach(() => vi.unstubAllEnvs());

const observations = [
  { observation_id: 'left', title: 'Нагрузка ВРУ-2', description: 'Схема: 294 кВт', source_ids: ['s1'] },
  { observation_id: 'right', title: 'Мощность ВРУ-2', description: 'Спецификация: 336 кВт', source_ids: ['s2'] },
];
const group = { group_id: 'g1', title: observations[1]?.title, description: observations[1]?.description,
  grouping_status: 'ensemble_relationship', origin_count: 2, source_count: 2, source_ids: ['s1', 's2'],
  origin_records: observations.map((item, index) => ({ raw_index: index, observation_id: item.observation_id,
    title: item.title, description: item.description })) };
const consolidation = { version: 'ensemble-linked-v1', complete: true, raw_count: 2,
  group_count: 1, merged_group_count: 1, coalesced_count: 1 };

describe('v2 quality hotfix in the existing panel', () => {
  it('shows hashes and unresolved register rows without declaring a sheet absent', () => {
    const markup = renderToStaticMarkup(createElement(InputPassport, { value: {
      pdf_sha256: 'a'.repeat(64), crop_manifest_sha256: 'b'.repeat(64), page_count: 2, crop_count: 1,
      source_coverage_complete: true, crop_verification: 'verified', pages: [],
      sheet_register: { entries: [{ sheet_label: '2', title: 'Схема ВРУ-2', status: 'unresolved', register_page: 1,
        quote: '2 Схема ВРУ-2', page_numbers: [] }] },
    } }));
    expect(markup).toContain('a'.repeat(64));
    expect(markup).toContain('b'.repeat(64));
    expect(markup).toContain('хеши совпали');
    expect(markup).toContain('Соответствие не установлено');
    expect(markup).toContain('Неустановленное соответствие не доказывает отсутствие листа');
    expect(markup).not.toContain('— Отсутствует');
  });

  it('shows one linked card and lets the user open every unchanged original', async () => {
    const live = await mountLive(createElement(ConsolidatedObservations, { groups: [group], consolidation,
      observations, rawRecords: observations, sources: [], fallbackVersion: 'ver_x' }));
    try {
      expect(live.markup()).toContain('Свод вопросов');
      expect(live.markup().match(/data-consolidated-group=/g)).toHaveLength(1);
      expect(live.markup()).toContain('Исходные записи и отдельные рекомендации · 2');
      await live.change('Поиск группы, исходного текста или источника', '294');
      expect(live.markup().match(/data-consolidated-group=/g)).toHaveLength(1);
      await live.press('Все исходные · 2');
      expect(live.markup()).toContain('Нагрузка ВРУ-2');
      expect(live.markup()).toContain('Мощность ВРУ-2');
      expect(live.markup()).toContain('Схема: 294 кВт');
      expect(live.markup()).toContain('Спецификация: 336 кВт');
    } finally { await live.unmount(); }
  });

  it('counts linked questions while preserving raw recommendation counts and legacy counts', () => {
    const result = { observations, consolidation, consolidated_observations: [group] };
    expect(extendedCandidateCounts(result).candidates).toBe(1);
    expect(extendedCandidateCounts({ ...result, consolidation: { ...consolidation, complete: false } }).candidates).toBe(2);
    expect(extendedCandidateCounts({ observations }).candidates).toBe(2);
  });

  it('shows all substantive checks and does not label a model critic as a deterministic correction', () => {
    const markup = renderToStaticMarkup(createElement(MachineAdvice, { review: {
      mode: 'substantive', model_called: true, llm_decision: 'needs_human', evidence_checked: true,
      substantive_checks: { evidence: { checked: true, explanation: 'Показан объект ВРУ-2' },
        alternatives: { checked: false, explanation: 'Режим нагрузки не установлен' },
        materiality: { checked: true, explanation: 'Влияет на выбор защиты' } },
      validator_downgrade_reason: 'substantive_checks_or_evidence_missing',
    }, correction: { mode: 'deterministic', action: 'retain' } }));
    expect(markup).toContain('Доказательства: рассмотрены');
    expect(markup).toContain('Альтернативные трактовки: проверка не подтверждена');
    expect(markup).toContain('Существенность: рассмотрены');
    expect(markup).toContain('Рекомендация модели');
    expect(markup).not.toContain('data-machine-mode="deterministic"');
  });
});
