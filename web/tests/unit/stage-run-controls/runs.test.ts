import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { StageBatchControls, StageRunControls } from '@/widgets/stage-run-controls';
import { IntentKey, latestFullRun, STAGE_RUN_KEYS } from '@/widgets/stage-run-controls/model/runs';
import { StageEstimateConsent } from '@/widgets/stage-run-controls/ui/estimate-consent';

import { newClient, renderScreen } from '../screens/harness';
import { render } from '../review/fixtures';
import { estimate, MODEL } from '../version-compare/ai-fixtures';
import { uid } from '../version-compare/fixtures';
import { run } from '../stage-changes/fixtures';

describe('stage launch intent', () => {
  it('retains a key after uncertainty and changes it only for a changed request or success', () => {
    let sequence = 0;
    const intent = new IntentKey(() => `key-${++sequence}`);
    expect(intent.for(['start', { link_revision_id: 'a' }])).toBe('key-1');
    expect(intent.for(['start', { link_revision_id: 'a' }])).toBe('key-1');
    expect(intent.for(['start', { link_revision_id: 'b' }])).toBe('key-2');
    intent.clear();
    expect(intent.for(['start', { link_revision_id: 'b' }])).toBe('key-3');
  });
  it('does not reuse the consented launch identity for another comparison engine', () => {
    let sequence = 0;
    const intent = new IntentKey(() => `key-${++sequence}`);
    expect(intent.for(['start', { engine: 'classic', link_revision_id: 'a' }])).toBe('key-1');
    expect(intent.for(['start', { engine: 'v3_native_text_experimental', link_revision_id: 'a' }])).toBe('key-2');
    expect(intent.for(['start', { engine: 'v3_native_text_experimental', link_revision_id: 'a' }])).toBe('key-2');
  });
  it('selects the latest full run and excludes a newer deterministic recomputation', () => {
    expect(latestFullRun([run({ run_id: uid('crn', 2), kind: 'deterministic', created_at: '2026-10-30T12:00:00Z' }),
      run({ run_id: uid('crn', 3), created_at: '2026-10-30T10:00:00Z' }), run()])?.run_id).toBe(uid('crn', 3));
  });
  it('offers consent for a cached full chain and displays the routed model', () => {
    const value = estimate({ calls: 0, units: 4, reused: 4 });
    const html = render(createElement(StageEstimateConsent, { estimate: value, agreedDigest: null, disabled: false, onAgree: () => {} }));
    expect(html).toContain(MODEL);
    expect(html).toContain('Сохранённые ответы будут использованы повторно');
    expect(html).not.toContain('disabled');
    const blocked = render(createElement(StageEstimateConsent, { estimate: estimate({ blocked_by: 'day' }), agreedDigest: null, disabled: false, onAgree: () => {} }));
    expect(blocked).toContain('disabled');
  });
});

describe('stage run controls', () => {
  it('waits for an expert-saved sheet map and unlocks the same pair after it is saved', () => {
    const cache = newClient();
    const pairId = uid('stp', 40);
    cache.setQueryData(STAGE_RUN_KEYS.list(pairId), []);
    cache.setQueryData(STAGE_RUN_KEYS.map(pairId), null);
    const screen = () => renderScreen(cache, createElement(StageRunControls, { pairId, mayAct: true }));
    expect(STAGE_RUN_KEYS.map(pairId)).toEqual(['stage-sheet-map', pairId, 'current']);
    expect(screen()).toContain('Сначала откройте «2. Сопоставление листов»');
    expect(screen()).toMatch(/disabled=""[^>]*>Запустить полное сравнение/);
    cache.setQueryData(STAGE_RUN_KEYS.map(pairId), { revision_id: uid('slr', 41) });
    const saved = screen();
    expect(saved).not.toContain('Сначала откройте «2. Сопоставление листов»');
    expect(saved).toMatch(/class="am-button"[^>]*>Запустить полное сравнение/);
  });
  it('keeps classic as default and names the native-text V3 bounds before a new launch', () => {
    const cache = newClient();
    const value = run();
    cache.setQueryData(STAGE_RUN_KEYS.list(value.pair_id), [value]);
    cache.setQueryData(STAGE_RUN_KEYS.run(value.run_id), value);
    const html = renderScreen(cache, createElement(StageRunControls, { pairId: value.pair_id, linkRevisionId: value.link_revision_id, mayAct: true }));
    expect(html).toMatch(/value="classic" selected=""/);
    expect(html).toContain('V3 · эксперимент, только текст PDF');
    expect(html).toContain('07 Карточки');
  });
  it('shows the actual six procedure states and no classic seven-step strip for experimental runs', () => {
    const cache = newClient();
    const value = run({ state: 'paused', engine: 'v3_native_text_experimental', experimental_progress: {
      engine: 'v3_native_text_experimental', source_version: '3c994817', procedure: 'Miner', status: 'running',
      procedures: [{ name: 'Mapper', state: 'completed' }, { name: 'Miner', state: 'running' },
        { name: 'Разбор непарных страниц', state: 'queued' }, { name: 'Dedupe', state: 'queued' },
        { name: 'Проверка параметров', state: 'queued' }, { name: 'Карточки V3', state: 'queued' }],
      limitations: ['Только текст PDF'],
    } });
    cache.setQueryData(STAGE_RUN_KEYS.list(value.pair_id), [value]);
    cache.setQueryData(STAGE_RUN_KEYS.run(value.run_id), value);
    const html = renderScreen(cache, createElement(StageRunControls, { pairId: value.pair_id, linkRevisionId: value.link_revision_id, mayAct: false }));
    expect(html).toContain('data-stage-v3-progress');
    expect(html).toContain('Подтверждено завершение процедур: 1 из 6');
    expect(html).toContain('data-v3-procedure="Miner" data-v3-procedure-state="running"');
    expect(html).toContain('Для следующего обращения откройте');
    expect(html).not.toContain('07 Карточки');
    expect(html).not.toContain('<p>Шаги:');
  });
  it('never fabricates procedure completion when the backend progress is absent', () => {
    const cache = newClient();
    const value = run({ engine: 'v3_native_text_experimental' });
    cache.setQueryData(STAGE_RUN_KEYS.list(value.pair_id), [value]);
    cache.setQueryData(STAGE_RUN_KEYS.run(value.run_id), value);
    const html = renderScreen(cache, createElement(StageRunControls, { pairId: value.pair_id, linkRevisionId: value.link_revision_id, mayAct: false }));
    expect(html).toContain('Состояние процедур ещё не передано. Завершение не подтверждено.');
    expect(html).not.toContain('07 Карточки');
  });
  it('shows the saved run and step strip without expert launch controls', () => {
    const cache = newClient();
    const value = run({ stale: true });
    cache.setQueryData(STAGE_RUN_KEYS.list(value.pair_id), [value]);
    cache.setQueryData(STAGE_RUN_KEYS.run(value.run_id), value);
    const html = renderScreen(cache, createElement(StageRunControls, { pairId: value.pair_id, linkRevisionId: value.link_revision_id, mayAct: false }));
    expect(html).toContain('Завершено');
    expect(html).toContain('07 Карточки');
    expect(html).toContain('Результат устарел');
    expect(html).not.toContain('Запустить полное сравнение');
  });
  it('recovers a persisted queue by its server id without inventing success', () => {
    const cache = newClient();
    const batchId = uid('scb', 1);
    cache.setQueryData(['stage-batch', batchId], { batch_id: batchId, project_uid: uid('prj', 1), state: 'paused',
      created_at: run().created_at, updated_at: run().updated_at, counts: { queued: 1 }, items: [
        { item_id: uid('scbi', 1), pair_id: run().pair_id, link_revision_id: run().link_revision_id, position: 1, state: 'queued' },
      ] });
    const html = renderScreen(cache, createElement(StageBatchControls, { projectUid: uid('prj', 1), selectedPairs: [], mayAct: true, batchId }));
    expect(html).toContain('Приостановлено');
    expect(html).toContain('Продолжить очередь');
    expect(html).toContain('Отменить очередь');
    expect(html).not.toContain('Завершено');
  });
});
