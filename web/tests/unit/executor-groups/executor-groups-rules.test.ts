/**
 * `EXEC2-WEB-GROUPS-01` — «Правила»: the table of exactly six rules, the routing mode, the note that
 * rules are stored and unused under the legacy mode, and the cut-over panel with its explicit
 * confirmation of the mapping and its way back (ADR-0026 decisions 11 and 17). Written under `R-149d`
 * and not run in EXEC-2; none of it needs PostgreSQL.
 *
 * The cut-over is served by `EXEC2-CUTOVER-01`. Until then the server refuses `previewExecutorRouting`
 * and `setExecutorRoutingMode`, and the panel has to show that refusal and offer nothing in its place;
 * the live cases below send the refusals the contract names.
 */

import { QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => ({
  ...await importOriginal<Record<string, unknown>>(),
  previewExecutorRouting: vi.fn(),
  setExecutorRoutingMode: vi.fn(),
}));

import type { ErrorCode, ErrorEnvelope, ExecutorRoutingPreview, Role } from '@/shared/api';
import {
  ApiError, EXECUTOR_WORK_KIND_VALUES, previewExecutorRouting, setExecutorRoutingMode,
} from '@/shared/api';
import { WORK_KIND_LABELS } from '@/entities/executor-connection';
import {
  CUT_OVER_CONFIRM_LABEL, CUT_OVER_LABEL, MAPPING_CONFIRMATION_LABEL, ROLLBACK_CONFIRM_LABEL, ROLLBACK_LABEL,
  cutOverCanBeConfirmed, cutOverMapping, previewItems, ruleRows, ruleTargets,
} from '@/entities/executor-group';
import { CutOverPanel } from '@/features/manage-executor-group';
import { ExecutorRules } from '@/widgets/executor-rules';

import { newClient, renderWith } from '../screens/harness';
import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import {
  ARCHIVED_GROUP, CONNECTION_CASES, MAIN_GROUP, PREVIEW, ROUTED_GROUP, groupOf, ruleOf, seedGroups, seedRules,
} from './executor-groups-fixtures';

function apiError(
  status: number, code: ErrorCode, details: Record<string, string | number | boolean | null> = {},
): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.41.0', error_code: code, message: 'A caller-safe sentence.',
    correlation_id: 'cid-cut', retryable: false, details,
  };
  return new ApiError(status, envelope, 'cid-cut');
}

describe('the rows of the table', () => {
  it('are exactly one per kind of model work, in the contract’s order, whatever the server returned', () => {
    expect(EXECUTOR_WORK_KIND_VALUES).toHaveLength(6);
    const none = ruleRows([], [MAIN_GROUP]);
    expect(none.map((row) => row.workKind)).toEqual([...EXECUTOR_WORK_KIND_VALUES]);
    expect(none.every((row) => row.rule === null && row.group === null && !row.onCurrentRevision)).toBe(true);

    const some = ruleRows([ruleOf('comparison_spec', MAIN_GROUP, 1), ruleOf('text_analysis', ROUTED_GROUP, 2)], [MAIN_GROUP, ROUTED_GROUP]);
    expect(some).toHaveLength(6);
    expect(some.find((row) => row.workKind === 'text_analysis')?.group?.display_name).toBe(ROUTED_GROUP.display_name);
    expect(some.find((row) => row.workKind === 'comparison_spec')?.group?.display_name).toBe(MAIN_GROUP.display_name);
    expect(some.filter((row) => row.rule !== null)).toHaveLength(2);
  });

  it('draws no row for a kind this client does not know, and does not lose the six', () => {
    const foreign = { ...ruleOf('text_analysis', MAIN_GROUP, 1), work_kind: 'future_kind' as never };
    const rows = ruleRows([foreign], [MAIN_GROUP]);
    expect(rows).toHaveLength(6);
    expect(rows.every((row) => row.rule === null)).toBe(true);
  });

  it('says when a rule names an earlier revision of its group, or a group the list does not hold', () => {
    const revised = groupOf(1, MAIN_GROUP.display_name, {}, { group_revision_id: 'exgr_01J9ZQ8K7NHVXW3T2R5M6P4Q9Z', revision_no: 2 });
    const old = ruleOf('text_analysis', MAIN_GROUP, 1);
    expect(ruleRows([old], [revised]).find((row) => row.workKind === 'text_analysis')?.onCurrentRevision).toBe(false);
    expect(ruleRows([old], [MAIN_GROUP]).find((row) => row.workKind === 'text_analysis')?.onCurrentRevision).toBe(true);
    expect(ruleRows([old], []).find((row) => row.workKind === 'text_analysis')?.group).toBeNull();
  });

  it('offers a rule only the groups that are not archived', () => {
    expect(ruleTargets([MAIN_GROUP, ARCHIVED_GROUP, ROUTED_GROUP]).map((group) => group.display_name))
      .toEqual([MAIN_GROUP.display_name, ROUTED_GROUP.display_name]);
  });
});

describe('«Правила», rendered once', () => {
  function rules(mode: 'legacy' | 'rules', roles: Role[] = ['admin'], slot = true): string {
    const client = newClient();
    seedGroups(client, [MAIN_GROUP, ROUTED_GROUP, ARCHIVED_GROUP]);
    seedRules(client, mode, [ruleOf('text_analysis', ROUTED_GROUP, 1), ruleOf('comparison_spec', MAIN_GROUP, 2)]);
    return renderWith(client, createElement(ExecutorRules, {
      roles,
      ...(slot ? { legacyRoutes: createElement('p', null, 'прежние назначения слота') } : {}),
    }));
  }

  it('has exactly six rows, one per kind of work, named in words', () => {
    const markup = rules('legacy');
    expect(markup).toContain('data-rules-table="6"');
    expect(markup.match(/<tr data-rule-row="/g)).toHaveLength(6);
    for (const kind of EXECUTOR_WORK_KIND_VALUES) {
      expect(markup).toContain(`data-rule-row="${kind}"`);
      expect(markup).toContain(WORK_KIND_LABELS[kind]);
    }
    expect(markup).toContain(`«${ROUTED_GROUP.display_name}»`);
    expect(markup.match(/data-rule-state="none"/g)).toHaveLength(4);
  });

  it('says plainly that a kind without a rule is refused under rules, and only then', () => {
    expect(rules('rules')).toContain('работа этого вида не запустится');
    expect(rules('legacy')).not.toContain('работа этого вида не запустится');
  });

  it('shows the mode in words and as its machine value', () => {
    const legacy = rules('legacy');
    expect(legacy).toContain('data-routing-mode="legacy"');
    expect(legacy).toContain('основное и резервное подключения');
    const ruled = rules('rules');
    expect(ruled).toContain('data-routing-mode="rules"');
    expect(ruled).toContain('правила по видам работы');
  });

  it('says under the legacy mode that the rules are stored and not used yet, and shows the routes as history', () => {
    const markup = rules('legacy');
    expect(markup).toContain('data-rules-legacy-note');
    expect(markup).toContain('Правила сохранены, но пока не используются');
    expect(markup).toContain('data-rules-legacy-routes');
    expect(markup).toContain('прежние назначения слота');
    expect(markup).not.toContain('data-rules-active-note');
  });

  it('says under rules that they are in force, and does not repeat the routes', () => {
    const markup = rules('rules');
    expect(markup).toContain('data-rules-active-note');
    expect(markup).not.toContain('data-rules-legacy-note');
    expect(markup).not.toContain('data-rules-legacy-routes');
    expect(markup).not.toContain('прежние назначения слота');
  });

  it('offers the cut-over under the legacy mode and the way back under rules, not the other way round', () => {
    const legacy = rules('legacy');
    expect(legacy).toContain(CUT_OVER_LABEL);
    expect(legacy).not.toContain(ROLLBACK_LABEL);
    const ruled = rules('rules');
    expect(ruled).toContain(ROLLBACK_LABEL);
    expect(ruled).not.toContain(`>${CUT_OVER_LABEL}<`);
  });

  it('offers the rule editor the groups that are not archived, each with its model and revision', () => {
    const markup = rules('legacy');
    expect(markup).toContain('data-rule-editor');
    expect(markup).toContain(`${MAIN_GROUP.display_name} · модель «модель-основная» · версия 1`);
    expect(markup).toContain(`${ROUTED_GROUP.display_name} · модель «модель-основная» · версия 3`);
    expect(markup).not.toContain(`${ARCHIVED_GROUP.display_name} · модель`);
  });

  it('shows the table to every role and the editor and the cut-over to an administrator only', () => {
    const reader = rules('legacy', ['expert']);
    expect(reader).toContain('data-rules-table="6"');
    expect(reader).not.toContain('data-rule-editor');
    expect(reader).not.toContain(CUT_OVER_LABEL);
    expect(reader.match(/data-rules-readonly/g)).toHaveLength(2);
  });
});

describe('the cut-over panel, live', () => {
  let live: LiveRender | null = null;

  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(previewExecutorRouting).mockResolvedValue({ data: PREVIEW } as never);
    vi.mocked(setExecutorRoutingMode).mockResolvedValue({
      data: { groups: [MAIN_GROUP], routing_mode: { mode: 'rules' }, rules: [] },
    } as never);
  });

  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  async function mount(mode: 'legacy' | 'rules'): Promise<LiveRender> {
    live = await mountLive(createElement(QueryClientProvider, { client: newClient() },
      createElement(CutOverPanel, { mode, connections: CONNECTION_CASES.map((one) => one.connection) })));
    return live;
  }

  async function open(view: LiveRender): Promise<void> {
    await view.press(CUT_OVER_LABEL);
    await view.settle(() => undefined);
  }

  it('writes nothing until it is asked, and shows the proposal when it is', async () => {
    const view = await mount('legacy');
    expect(previewExecutorRouting).not.toHaveBeenCalled();
    expect(view.markup()).not.toContain('data-cut-over-preview');
    await open(view);
    expect(previewExecutorRouting).toHaveBeenCalled();
    expect(setExecutorRoutingMode).not.toHaveBeenCalled();
    const markup = view.markup();
    expect(markup).toContain('data-cut-over-preview="6"');
    for (const kind of EXECUTOR_WORK_KIND_VALUES) expect(markup).toContain(`data-cut-over-item="${kind}"`);
  });

  it('shows the six kinds, flags a standby, an incompatible route and a kind with no route', async () => {
    const view = await mount('legacy');
    await open(view);
    const markup = view.markup();
    expect(markup).toContain('data-cut-over-status="ready"');
    expect(markup).toContain('data-cut-over-status="incompatible"');
    expect(markup.match(/data-cut-over-status="no_route"/g)).toHaveLength(4);
    expect(markup).toContain('в группу не переходит');
    expect(markup).toContain('data-cut-over-flag="standby"');
    expect(markup).toContain('data-cut-over-flag="incompatible"');
    expect(markup).toContain('data-cut-over-flag="no_route"');
    expect(markup).toContain('основное подключение в архиве');
    expect(markup).toContain('группа «Анализ текста: Основной шлюз»');
  });

  it('keeps the confirmation disabled until the mapping is explicitly confirmed', async () => {
    const view = await mount('legacy');
    await open(view);
    expect(await view.press(CUT_OVER_CONFIRM_LABEL)).toBe(false);
    expect(setExecutorRoutingMode).not.toHaveBeenCalled();
    expect(await view.check(MAPPING_CONFIRMATION_LABEL, true)).toBe(true);
    // Unchecking takes the permission away again.
    expect(await view.check(MAPPING_CONFIRMATION_LABEL, false)).toBe(true);
    expect(await view.press(CUT_OVER_CONFIRM_LABEL)).toBe(false);
    expect(setExecutorRoutingMode).not.toHaveBeenCalled();
  });

  it('sends rules with the digest that was shown and the mapping of the ready kinds only', async () => {
    const view = await mount('legacy');
    await open(view);
    await view.check(MAPPING_CONFIRMATION_LABEL, true);
    expect(await view.press(CUT_OVER_CONFIRM_LABEL)).toBe(true);
    expect(setExecutorRoutingMode).toHaveBeenCalledTimes(1);
    const call = vi.mocked(setExecutorRoutingMode).mock.calls[0]![0] as { body: unknown; idempotencyKey: string };
    expect(call.body).toEqual({
      mode: 'rules',
      preview_digest: PREVIEW.preview_digest,
      mapping: [{ work_kind: 'text_analysis', group_display_name: 'Анализ текста: Основной шлюз' }],
    });
    expect(call.idempotencyKey).toMatch(/\S/);
    expect(view.markup()).toContain('Включены правила. Создано групп: 1.');
  });

  it('shows the server’s refusal of the proposal, with its correlation id, and offers nothing in its place', async () => {
    vi.mocked(previewExecutorRouting).mockRejectedValue(apiError(404, 'not_found', { aggregate_type: 'executor_routing' }));
    const view = await mount('legacy');
    await open(view);
    const markup = view.markup();
    expect(markup).toContain('Предложение перехода не прочитано');
    expect(markup).toContain('cid-cut');
    expect(markup).not.toContain('data-cut-over-preview');
    expect(markup).not.toContain(MAPPING_CONFIRMATION_LABEL);
    expect(view.count(CUT_OVER_CONFIRM_LABEL)).toBe(0);
    expect(setExecutorRoutingMode).not.toHaveBeenCalled();
  });

  it('shows the server’s refusal of the confirmation, and a stale proposal says to read it again', async () => {
    vi.mocked(setExecutorRoutingMode).mockRejectedValue(apiError(409, 'conflict', { conflict_reason: 'preview_stale' }));
    const view = await mount('legacy');
    await open(view);
    await view.check(MAPPING_CONFIRMATION_LABEL, true);
    await view.press(CUT_OVER_CONFIRM_LABEL);
    const markup = view.markup();
    expect(markup).toContain('data-group-failure="conflict"');
    expect(markup).toContain('Предложение устарело');
    expect(markup).toContain('cid-cut');
    expect(view.count('Прочитать предложение заново')).toBe(1);
  });

  it('asks before going back, says that admitted work stays on its group, and sends legacy alone', async () => {
    vi.mocked(setExecutorRoutingMode).mockResolvedValue({
      data: { groups: [], routing_mode: { mode: 'legacy' }, rules: [] },
    } as never);
    const view = await mount('rules');
    expect(view.markup()).toContain(ROLLBACK_LABEL);
    expect(await view.press(ROLLBACK_LABEL)).toBe(true);
    const asking = view.markup();
    expect(asking).toContain('data-cut-over-rollback="asking"');
    expect(asking).toContain('остаётся на своей группе и дойдёт до конца там');
    expect(setExecutorRoutingMode).not.toHaveBeenCalled();
    expect(await view.press(ROLLBACK_CONFIRM_LABEL)).toBe(true);
    expect(setExecutorRoutingMode).toHaveBeenCalledTimes(1);
    const call = vi.mocked(setExecutorRoutingMode).mock.calls[0]![0] as { body: Record<string, unknown> };
    expect(call.body).toEqual({ mode: 'legacy' });
    expect(call.body).not.toHaveProperty('preview_digest');
    expect(call.body).not.toHaveProperty('mapping');
    expect(view.markup()).toContain('Работа, принятая по правилам, дойдёт до конца на своей группе.');
  });

  it('sends nothing when the way back is cancelled', async () => {
    const view = await mount('rules');
    await view.press(ROLLBACK_LABEL);
    await view.press('Отмена');
    expect(setExecutorRoutingMode).not.toHaveBeenCalled();
    expect(view.markup()).toContain(ROLLBACK_LABEL);
    expect(view.markup()).not.toContain('data-cut-over-rollback');
  });
});

describe('the proposal, as the words and the request see it', () => {
  const none: ExecutorRoutingPreview = {
    ...PREVIEW,
    items: PREVIEW.items.map((item) => ({ work_kind: item.work_kind, status: 'no_route' as const })),
  };

  it('maps each ready kind to the group name the server proposed, and nothing else', () => {
    expect(cutOverMapping(PREVIEW)).toEqual([
      { work_kind: 'text_analysis', group_display_name: 'Анализ текста: Основной шлюз' },
    ]);
    expect(cutOverCanBeConfirmed(PREVIEW)).toBe(true);
  });

  it('cannot be confirmed when nothing can be converted, or when a ready kind has no proposed name', () => {
    expect(cutOverMapping(none)).toEqual([]);
    expect(cutOverCanBeConfirmed(none)).toBe(false);
    const nameless: ExecutorRoutingPreview = {
      ...PREVIEW,
      items: PREVIEW.items.map((item) => ({ work_kind: item.work_kind, status: item.status })),
    };
    expect(cutOverCanBeConfirmed(nameless)).toBe(false);
  });

  it('lists the kinds in the contract’s order and ignores one it does not know', () => {
    const shuffled: ExecutorRoutingPreview = {
      ...PREVIEW,
      items: [...PREVIEW.items].reverse().concat([{ work_kind: 'future_kind' as never, status: 'no_route' }]),
    };
    expect(previewItems(shuffled).map((item) => item.work_kind)).toEqual([...EXECUTOR_WORK_KIND_VALUES]);
  });
});
