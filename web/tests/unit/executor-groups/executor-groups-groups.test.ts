/**
 * `EXEC2-WEB-GROUPS-01` — «Группы»: the list with its capacity and the eligibility of each member, the
 * form that creates and revises a homogeneous group, the picker that flags a mismatched model, name on
 * the gateway or billing **before the server refuses**, the archive that a rule can forbid, and the
 * rule editor (ADR-0026 decisions 10, 11, 14 and 19). Written under `R-149d` and not run in EXEC-2;
 * none of it needs PostgreSQL.
 */

import { QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import type { ReactElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => ({
  ...await importOriginal<Record<string, unknown>>(),
  archiveExecutorGroup: vi.fn(),
  createExecutorGroup: vi.fn(),
  reviseExecutorGroup: vi.fn(),
  setExecutorRoutingRule: vi.fn(),
}));

import type { ErrorCode, ErrorEnvelope, ExecutorConnectionDetail, Role } from '@/shared/api';
import {
  ApiError, archiveExecutorGroup, createExecutorGroup, reviseExecutorGroup, setExecutorRoutingRule,
} from '@/shared/api';
import { CLIENT_DOCUMENTS_NOTICE } from '@/entities/executor-connection';
import type { GroupDraft, GroupSettings } from '@/entities/executor-group';
import {
  GROUP_MEMBERS_MAX, MEMBER_ISSUE_SENTENCES, createGroupBody, groupCapacitySentence, groupDraftProblem,
  memberCandidates, memberProblem, memberRevisionIsStale, memberStatusSentence, reviseGroupBody,
} from '@/entities/executor-group';
import { ArchiveGroupControl, GroupForm, RuleEditor } from '@/features/manage-executor-group';
import { ExecutorGroups } from '@/widgets/executor-groups';

import { newClient, renderWith } from '../screens/harness';
import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import { PINNED, executorCase } from '../workers/executor-fixtures';
import {
  ARCHIVED, ARCHIVED_GROUP, CONNECTION_CASES, MAIN_GROUP, OTHER_MODEL, OTHER_NAME, READY, ROUTED_GROUP, SPARE, TWIN,
  capacityOf, groupId, groupOf, member, seedGroups,
} from './executor-groups-fixtures';

function apiError(
  status: number, code: ErrorCode, details: Record<string, string | number | boolean | null>,
): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.51.0', error_code: code, message: 'A caller-safe sentence.',
    correlation_id: 'cid-grp', retryable: false, details,
  };
  return new ApiError(status, envelope, 'cid-grp');
}

function candidates(cases = CONNECTION_CASES) {
  const details = new Map<string, ExecutorConnectionDetail>(
    cases.map((one) => [one.connection.connection_id, one.detail] as const),
  );
  return memberCandidates(cases.map((one) => one.connection), details);
}

const candidateOf = (name: string) => candidates().find((one) => one.name === name)!;
const READY_ID = READY.connection.connection_id;
const TWIN_ID = TWIN.connection.connection_id;

const SETTINGS: GroupSettings = { pinId: 'модель-основная', gatewayModel: 'шлюзовая-основная', billing: 'metered' };
const draft = (over: Partial<GroupDraft> = {}): GroupDraft => ({
  name: 'Новая группа', settings: SETTINGS, memberIds: [READY_ID, TWIN_ID], ...over,
});

describe('the members a group can be made of', () => {
  it('are the connections with their current revision: model, name on the gateway, billing, capacity', () => {
    const ready = candidateOf('Основной шлюз');
    expect(ready).toMatchObject({
      connectionId: READY_ID, kind: 'http_api', archived: false, revisionNo: 1,
      pinId: 'модель-основная', gatewayModel: 'шлюзовая-основная', billing: 'metered', capacity: 1, readiness: null,
    });
    expect(ready.revisionId).toBe(READY.detail.revisions[0]!.revision_id);
    expect(candidateOf('Шлюз в архиве').archived).toBe(true);
  });

  it('say what a connection still lacks without blocking it, and when its settings were not read', () => {
    const unprobed = executorCase({ n: 84, name: 'Шлюз без проверки', secrets: [{}], probe: null });
    const [one] = candidates([unprobed]);
    expect(one?.readiness).toBe('текущие настройки ещё не проверены');
    expect(memberProblem(one!, SETTINGS)).toBeNull();
    const unread = memberCandidates([READY.connection], new Map());
    expect(unread[0]?.revisionId).toBeNull();
    expect(unread[0]?.readiness).toBe('настройки подключения не прочитаны');
  });

  it('are flagged for a model, a name on the gateway and a billing that disagree with the group', () => {
    expect(memberProblem(candidateOf('Основной шлюз'), SETTINGS)).toBeNull();
    expect(memberProblem(candidateOf('Парный шлюз'), SETTINGS)).toBeNull();
    expect(memberProblem(candidateOf(OTHER_MODEL.connection.display_name), SETTINGS)).toBe('pin_mismatch');
    expect(memberProblem(candidateOf(OTHER_NAME.connection.display_name), SETTINGS)).toBe('model_mismatch');
    expect(memberProblem(candidateOf(SPARE.connection.display_name), SETTINGS)).toBe('billing_mismatch');
    expect(memberProblem(candidateOf(ARCHIVED.connection.display_name), SETTINGS)).toBe('archived');
  });

  it('judge nothing against a setting that has not been filled in', () => {
    const empty: GroupSettings = { pinId: '', gatewayModel: '  ', billing: '' };
    for (const one of candidates().filter((item) => !item.archived)) expect(memberProblem(one, empty)).toBeNull();
  });
});

describe('a draft is blocked in the form before the server refuses it', () => {
  const all = candidates();

  it('passes a valid draft, with or without a name when a revision is made', () => {
    expect(groupDraftProblem(draft(), all, true)).toBeNull();
    expect(groupDraftProblem(draft({ name: '' }), all, false)).toBeNull();
  });

  it('asks for what is missing, in the order of the form', () => {
    expect(groupDraftProblem(draft({ name: '  ' }), all, true)).toBe('Укажите название группы.');
    expect(groupDraftProblem(draft({ name: 'х'.repeat(121) }), all, true)).toBe('Название группы не длиннее 120 знаков.');
    expect(groupDraftProblem(draft({ settings: { ...SETTINGS, pinId: '' } }), all, true)).toBe('Выберите модель группы.');
    expect(groupDraftProblem(draft({ settings: { ...SETTINGS, gatewayModel: ' ' } }), all, true)).toBe('Укажите имя модели на шлюзе.');
    expect(groupDraftProblem(draft({ settings: { ...SETTINGS, billing: '' } }), all, true)).toBe('Выберите тарификацию группы.');
  });

  it('refuses a group with no member and one of more than sixteen', () => {
    const size = 'В группе должно быть от 1 до 16 подключений.';
    expect(groupDraftProblem(draft({ memberIds: [] }), all, true)).toBe(size);
    expect(GROUP_MEMBERS_MAX).toBe(16);
    expect(groupDraftProblem(draft({ memberIds: Array.from({ length: 17 }, () => READY_ID) }), all, true)).toBe(size);
  });

  it('names the member that disagrees and what it disagrees about', () => {
    const with_ = (one: { connection: { connection_id: string } }) => draft({ memberIds: [READY_ID, one.connection.connection_id] });
    expect(groupDraftProblem(with_(OTHER_MODEL), all, true))
      .toBe('Подключение «Шлюз другой модели»: у подключения закреплена другая модель, чем у группы.');
    expect(groupDraftProblem(with_(OTHER_NAME), all, true))
      .toBe('Подключение «Шлюз с другим именем модели»: у подключения другое имя модели на шлюзе, чем у группы.');
    expect(groupDraftProblem(with_(SPARE), all, true))
      .toBe('Подключение «Запасной шлюз»: у подключения другая тарификация, чем у группы.');
    expect(groupDraftProblem(with_(ARCHIVED), all, true)).toBe('Подключение «Шлюз в архиве»: подключение в архиве.');
  });

  it('refuses a member the list does not hold', () => {
    expect(groupDraftProblem(draft({ memberIds: ['exc_01J9ZQ8K7NHVXW3T2R5M6P4QZZ'] }), all, true))
      .toBe('Выбранного подключения нет в списке. Обновите страницу.');
  });
});

describe('the request a valid draft becomes', () => {
  const all = candidates();

  it('makes a group of the trimmed name, the shared fields and each member’s current revision', () => {
    expect(createGroupBody(draft({ name: '  Новая группа ' }), all)).toEqual({
      display_name: 'Новая группа',
      pin_id: 'модель-основная',
      gateway_model: 'шлюзовая-основная',
      billing: 'metered',
      members: [member(READY), member(TWIN)],
    });
  });

  it('adds a revision with the full settings and no name, keeping the order of a member it already had', () => {
    const body = reviseGroupBody(draft(), all, [{ ...member(READY), tie_break_order: 2 }]);
    expect(body).toEqual({
      pin_id: 'модель-основная',
      gateway_model: 'шлюзовая-основная',
      billing: 'metered',
      members: [{ ...member(READY), tie_break_order: 2 }, member(TWIN)],
    });
    expect(body).not.toHaveProperty('display_name');
  });

  it('guesses no billing: an unchosen one is no request at all', () => {
    const unbilled = draft({ settings: { ...SETTINGS, billing: '' } });
    expect(createGroupBody(unbilled, all)).toBeNull();
    expect(reviseGroupBody(unbilled, all, [])).toBeNull();
  });

  it('knows a member whose connection was revised after the group snapshotted it', () => {
    const old = { connection_id: READY_ID, connection_revision_id: 'excr_01J9ZQ8K7NHVXW3T2R5M6P4Q9Y' };
    expect(memberRevisionIsStale(old, all)).toBe(true);
    expect(memberRevisionIsStale(member(READY), all)).toBe(false);
  });
});

describe('the words of capacity and eligibility', () => {
  it('say what is in use and what waits, and never that a place is free', () => {
    expect(groupCapacitySentence({ capacity: 4, used: 1, waiting: 2 })).toBe('Занято 1 из 4, ждут отправки в работу: 2.');
    expect(groupCapacitySentence({ capacity: 4, used: 0, waiting: 0 })).toBe('Занято 0 из 4.');
    for (const reading of [{ capacity: 4, used: 4, waiting: 9 }, { capacity: 1, used: 0, waiting: 0 }]) {
      expect(groupCapacitySentence(reading)).not.toMatch(/свободн/i);
    }
  });

  it('draw nothing for a reading that is not whole numbers', () => {
    for (const reading of [
      { capacity: -1, used: 0, waiting: 0 }, { capacity: 4, used: 1.5, waiting: 0 }, { capacity: 4, used: 0, waiting: Number.NaN },
    ]) expect(groupCapacitySentence(reading)).toBeNull();
  });

  it('say why dispatch would not choose a member, with the first reason the server gave and none it did not', () => {
    const base = capacityOf(MAIN_GROUP).members[1]!;
    for (const [reason, sentence] of Object.entries(MEMBER_ISSUE_SENTENCES)) {
      expect(memberStatusSentence({ ...base, ineligible_reason: reason as keyof typeof MEMBER_ISSUE_SENTENCES }))
        .toBe(`Сейчас не будет выбрано: ${sentence}`);
      expect(sentence).not.toMatch(/[A-Za-z]/);
    }
    const withoutReason = {
      connection_id: base.connection_id, snapshot_revision_id: base.snapshot_revision_id, eligible: false,
    };
    expect(memberStatusSentence(withoutReason)).toBe('Сейчас не будет выбрано');
    expect(memberStatusSentence({ ...base, eligible: true })).toBe('Подходит для выбора');
  });
});

describe('«Группы», rendered once', () => {
  function groups(roles: Role[] = ['admin'], items = [MAIN_GROUP, ROUTED_GROUP, ARCHIVED_GROUP]): string {
    const client = newClient();
    seedGroups(client, items);
    return renderWith(client, createElement(ExecutorGroups, { roles }));
  }

  it('shows the R-149a notice to every role, with the list or without it', () => {
    expect(groups(['admin'])).toContain(CLIENT_DOCUMENTS_NOTICE);
    expect(groups(['expert'])).toContain(CLIENT_DOCUMENTS_NOTICE);
    const empty = groups(['admin'], []);
    expect(empty).toContain(CLIENT_DOCUMENTS_NOTICE);
    expect(empty).toContain('Групп нет');
  });

  it('shows the capacity of each group and the verdict of dispatch on each member', () => {
    const markup = groups();
    expect(markup).toContain('Занято 1 из 4, ждут отправки в работу: 2.');
    expect(markup).toContain('Подходит для выбора. Занято 1 из 2.');
    expect(markup).toContain('Сейчас не будет выбрано: клиент подключения не на связи');
    expect(markup).toContain('Основной шлюз');
    expect(markup).toContain('Парный шлюз');
    expect(markup).not.toMatch(/свободн/i);
  });

  it('says which kinds of work a rule sends to a group, and lists an archived group apart', () => {
    const markup = groups();
    expect(markup).toContain('Правила направляют на группу: «Анализ текста».');
    expect(markup).toContain('Архив групп (1)');
    expect(markup).toContain('data-group-state="archived"');
    expect(markup.match(/data-group-state="active"/g)).toHaveLength(2);
  });

  it('offers the controls to an administrator only, and none for an archived group', () => {
    const admin = groups(['admin']);
    expect(admin.match(/data-group-revise/g)).toHaveLength(2);
    expect(admin).toContain('data-executor-group-create');
    const reader = groups(['expert']);
    expect(reader).not.toContain('data-group-revise');
    expect(reader).not.toContain('data-executor-group-create');
    expect(reader).not.toContain('В архив');
  });

  it('forbids archiving a group a rule names, and says so before anything is sent', () => {
    const markup = groups();
    expect(markup).toContain('data-group-archive="routed"');
    expect(markup).toContain('В архив группу убрать нельзя: правило направляет на неё работу («Анализ текста»)');
    // The group no rule names keeps its button; the routed one has none.
    expect(markup.match(/>В архив</g)).toHaveLength(1);
  });
});

describe('the form of a group, rendered once', () => {
  const render = (props: { group?: typeof MAIN_GROUP }): string =>
    renderWith(newClient(), createElement(GroupForm, { ...props, candidates: candidates(), pinnedModels: PINNED }));

  it('starts a new group empty, with the button disabled and what is missing said', () => {
    const markup = render({});
    expect(markup).toContain('data-group-form="create"');
    expect(markup).toContain('data-group-incomplete');
    expect(markup).toContain('Укажите название группы.');
    expect(markup).toMatch(/<button[^>]*type="submit"[^>]*disabled=""[^>]*>Создать группу<\/button>|<button[^>]*disabled=""[^>]*type="submit"[^>]*>Создать группу<\/button>/);
    expect(markup.match(/checked=""/g)).toBeNull();
  });

  it('flags in the picker a model, a name on the gateway and a billing that disagree with the group', () => {
    const markup = render({ group: MAIN_GROUP });
    expect(markup).toContain('data-group-form="revise"');
    expect(markup).toContain('data-group-member-flag="pin_mismatch"');
    expect(markup).toContain('data-group-member-flag="model_mismatch"');
    expect(markup).toContain('data-group-member-flag="billing_mismatch"');
    expect(markup).toContain('Не подходит группе: у подключения закреплена другая модель, чем у группы.');
    expect(markup).toContain('Не подходит группе: у подключения другое имя модели на шлюзе, чем у группы.');
    expect(markup).toContain('Не подходит группе: у подключения другая тарификация, чем у группы.');
  });

  it('offers the live connections, checks the members, and disables the three that disagree', () => {
    const markup = render({ group: MAIN_GROUP });
    expect(markup.match(/type="checkbox"/g)).toHaveLength(5);
    expect(markup).not.toContain('Шлюз в архиве');
    expect(markup.match(/checked=""/g)).toHaveLength(2);
    expect(markup.match(/disabled=""/g)).toHaveLength(3);
    expect(markup).not.toContain('data-group-problem');
  });

  it('shows the model, the name on the gateway and the billing the members share, and the models to pick from', () => {
    const markup = render({ group: MAIN_GROUP });
    for (const model of PINNED) expect(markup).toContain(`>${model.pin_id}</option>`);
    expect(markup).toContain('Оно должно совпадать у всех подключений группы буква в букву.');
    expect(markup).toContain('Смешанные группы не принимаются');
  });

  it('says when a member holds an earlier revision of its connection, and that the new revision takes the current one', () => {
    const stale = groupOf(4, 'Группа со старой версией', {}, {
      members: [{ connection_id: READY_ID, connection_revision_id: 'excr_01J9ZQ8K7NHVXW3T2R5M6P4Q9Y' }, member(TWIN)],
    });
    const markup = render({ group: stale });
    expect(markup.match(/data-group-member-stale/g)).toHaveLength(1);
    expect(markup).toContain('новая версия группы возьмёт текущую');
  });

  it('does not rename a group when a revision is made', () => {
    const markup = render({ group: MAIN_GROUP });
    expect(markup).toContain(`Название группы «${MAIN_GROUP.display_name}» не меняется.`);
    expect(markup).not.toContain('>Название группы</label>');
  });
});

describe('the commands, live', () => {
  let live: LiveRender | null = null;

  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(createExecutorGroup).mockResolvedValue({ data: MAIN_GROUP } as never);
    vi.mocked(reviseExecutorGroup).mockResolvedValue({ data: MAIN_GROUP } as never);
    vi.mocked(archiveExecutorGroup).mockResolvedValue({ data: { ...MAIN_GROUP, archived_at: '2026-11-03T10:00:00.000Z' } } as never);
    vi.mocked(setExecutorRoutingRule).mockResolvedValue({ data: {} } as never);
  });

  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  async function mount(element: ReactElement): Promise<LiveRender> {
    live = await mountLive(createElement(QueryClientProvider, { client: newClient() }, element));
    return live;
  }

  const form = (group?: typeof MAIN_GROUP) =>
    createElement(GroupForm, { ...(group === undefined ? {} : { group }), candidates: candidates(), pinnedModels: PINNED });

  const sent = <T,>(mock: unknown): T => (vi.mocked(mock as (input: unknown) => unknown).mock.calls.at(-1)![0]) as T;

  it('creates a group: the first member fills the shared fields, a member that disagrees cannot be added', async () => {
    const view = await mount(form());
    await view.change('Название группы', 'Новая группа');
    expect(await view.check('Основной шлюз', true)).toBe(true);
    expect(await view.check('Парный шлюз', true)).toBe(true);
    // The three that disagree with what the first member filled in cannot be added.
    expect(await view.check(OTHER_MODEL.connection.display_name, true)).toBe(false);
    expect(await view.check(OTHER_NAME.connection.display_name, true)).toBe(false);
    expect(await view.check(SPARE.connection.display_name, true)).toBe(false);
    expect(await view.press('Создать группу')).toBe(true);
    expect(createExecutorGroup).toHaveBeenCalledTimes(1);
    const call = sent<{ body: unknown; idempotencyKey: string }>(createExecutorGroup);
    expect(call.body).toEqual({
      display_name: 'Новая группа',
      pin_id: 'модель-основная',
      gateway_model: 'шлюзовая-основная',
      billing: 'metered',
      members: [member(READY), member(TWIN)],
    });
    expect(call.idempotencyKey).toMatch(/\S/);
    expect(view.markup()).toContain('Группа «Новая группа» создана.');
  });

  it('blocks a combination the server would refuse: the button stays disabled and nothing is sent', async () => {
    const view = await mount(form());
    await view.change('Название группы', 'Новая группа');
    await view.check('Основной шлюз', true);
    await view.check('Парный шлюз', true);
    await view.change('Тарификация группы', 'not_metered');
    const markup = view.markup();
    expect(markup).toContain('data-group-problem');
    expect(markup).toContain('Подключение «Основной шлюз»: у подключения другая тарификация, чем у группы.');
    expect(await view.press('Создать группу')).toBe(false);
    expect(createExecutorGroup).not.toHaveBeenCalled();
    // Putting the billing back lifts the block.
    await view.change('Тарификация группы', 'metered');
    expect(view.markup()).not.toContain('data-group-problem');
    expect(await view.press('Создать группу')).toBe(true);
  });

  it('repeats an unknown outcome under the same key, and says the refusal of the server in Russian', async () => {
    vi.mocked(createExecutorGroup)
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockRejectedValueOnce(apiError(422, 'validation_failed', { field: 'pin_id', constraint: 'member_pin_mismatch' }));
    const view = await mount(form());
    await view.change('Название группы', 'Новая группа');
    await view.check('Основной шлюз', true);
    await view.press('Создать группу');
    expect(view.markup()).toContain('data-group-failure="unknown_outcome"');
    expect(view.markup()).toContain('Исход команды неизвестен');
    await view.press('Создать группу');
    const keys = vi.mocked(createExecutorGroup).mock.calls.map((call) => (call[0] as { idempotencyKey: string }).idempotencyKey);
    expect(keys).toHaveLength(2);
    expect(keys[0]).toBe(keys[1]);
    expect(view.markup()).toContain('Модель: у одного из подключений закреплена другая модель');
    expect(view.markup()).toContain('cid-grp');
  });

  it('revises a group with the full settings and no name, and says the rules stay on the earlier revision', async () => {
    const view = await mount(form(MAIN_GROUP));
    expect(await view.press('Сохранить новую версию')).toBe(true);
    expect(reviseExecutorGroup).toHaveBeenCalledTimes(1);
    const call = sent<{ path: unknown; body: Record<string, unknown> }>(reviseExecutorGroup);
    expect(call.path).toEqual({ group_id: MAIN_GROUP.group_id });
    expect(call.body).toEqual({
      pin_id: 'модель-основная', gateway_model: 'шлюзовая-основная', billing: 'metered', members: [member(READY), member(TWIN)],
    });
    expect(view.markup()).toContain('Правила остаются на прежней версии, пока вы не назначите новую на вкладке «Правила».');
  });

  it('archives a group after asking, and says the refusal when a rule named it meanwhile', async () => {
    vi.mocked(archiveExecutorGroup).mockRejectedValue(apiError(409, 'conflict', { conflict_reason: 'group_routed' }));
    const view = await mount(createElement(ArchiveGroupControl, { group: MAIN_GROUP }));
    expect(await view.press('В архив')).toBe(true);
    expect(view.markup()).toContain(`Убрать группу «${MAIN_GROUP.display_name}» в архив насовсем?`);
    expect(archiveExecutorGroup).not.toHaveBeenCalled();
    await view.press('Подтвердить архивирование');
    expect(sent<{ path: unknown }>(archiveExecutorGroup).path).toEqual({ group_id: MAIN_GROUP.group_id });
    expect(view.markup()).toContain('Группу нельзя убрать в архив, пока правило направляет на неё работу');
    expect(view.markup()).toContain('cid-grp');
  });

  it('sends nothing when the archive is cancelled', async () => {
    const view = await mount(createElement(ArchiveGroupControl, { group: MAIN_GROUP }));
    await view.press('В архив');
    await view.press('Отмена');
    expect(archiveExecutorGroup).not.toHaveBeenCalled();
    expect(view.count('В архив')).toBe(1);
  });

  it('points the rule of a work kind at the current revision of a group that is not archived', async () => {
    const view = await mount(createElement(RuleEditor, { groups: [MAIN_GROUP, ROUTED_GROUP, ARCHIVED_GROUP], mode: 'legacy' }));
    expect(view.markup()).not.toContain(`value="${ARCHIVED_GROUP.group_id}"`);
    expect(await view.press('Назначить группу')).toBe(false);
    await view.change('Вид работы', 'comparison_spec');
    await view.change('Группа для правила', MAIN_GROUP.group_id);
    expect(await view.press('Назначить группу')).toBe(true);
    const call = sent<{ path: unknown; body: unknown; idempotencyKey: string }>(setExecutorRoutingRule);
    expect(call.path).toEqual({ work_kind: 'comparison_spec' });
    expect(call.body).toEqual({ group_revision_id: MAIN_GROUP.current_revision.group_revision_id });
    expect(call.idempotencyKey).toMatch(/\S/);
    expect(view.markup()).toContain('Правило «Сравнение версий: спецификации» сохранено: группа «Основная группа», версия 1.');
    expect(view.markup()).toContain('Пока включены основное и резервное подключения, правило хранится и не используется.');
  });

  it('says a stored rule is in force once rules are the mode', async () => {
    const view = await mount(createElement(RuleEditor, { groups: [MAIN_GROUP], mode: 'rules' }));
    await view.change('Вид работы', 'text_analysis');
    await view.change('Группа для правила', groupId(1));
    await view.press('Назначить группу');
    expect(view.markup()).toContain('Оно действует для работы, которую примут после этого.');
    expect(view.markup()).not.toContain('хранится и не используется');
  });

  it('says the refusal of an archived group’s revision', async () => {
    vi.mocked(setExecutorRoutingRule).mockRejectedValue(apiError(409, 'conflict', { conflict_reason: 'group_archived' }));
    const view = await mount(createElement(RuleEditor, { groups: [MAIN_GROUP], mode: 'legacy' }));
    await view.change('Вид работы', 'text_analysis');
    await view.change('Группа для правила', MAIN_GROUP.group_id);
    await view.press('Назначить группу');
    expect(view.markup()).toContain('Группа в архиве');
    expect(view.markup()).toContain('data-group-failure="conflict"');
  });
});
