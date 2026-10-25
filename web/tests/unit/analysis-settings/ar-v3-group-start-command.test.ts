/**
 * `AR-V3-BETA-PACK-STATUS-WEB-01`: the command behind «Запустить шесть проверок АР v3».
 *
 * `useMutation` is replaced by the identity so the hook's configuration can be called: what the
 * request carries, and what an accepted start invalidates. The control's settled states are in
 * `ar-v3-group-start-failure.test.ts` and the instrument below.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

const calls = vi.hoisted(() => ({ invalidations: [] as unknown[], writes: [] as unknown[] }));
const settled = vi.hoisted(() => ({
  mutation: { isPending: false, isSuccess: false, error: null as unknown, data: undefined as unknown },
  mutate: [] as unknown[][],
  identity: false,
}));

vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useMutation: (configuration: unknown) =>
      settled.identity
        ? configuration
        : { ...settled.mutation, mutate: (...args: unknown[]) => settled.mutate.push(args) },
    useQueryClient: () => ({
      setQueryData: (...args: unknown[]) => calls.writes.push(args),
      invalidateQueries: (...args: unknown[]) => {
        calls.invalidations.push(args);
        return Promise.resolve();
      },
    }),
  };
});

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, startArV3BetaGroup: vi.fn() };
});

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

import { queryKeys, startArV3BetaGroup } from '@/shared/api';
import type { ArV3BetaGroup } from '@/shared/api';
import { StartArV3GroupControl, useStartArV3Group } from '@/features/start-ar-v3-group';

import { GROUP_ID } from './ar-v3-beta-review-fixtures';

const PROJECT_UID = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const VERSION_UID = 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const KEY = 'ik-one-intent';
const GROUP = { group_id: GROUP_ID, project_uid: PROJECT_UID, version_uid: VERSION_UID } as ArV3BetaGroup;

type Captured = {
  mutationFn: (input: { versionUid: string; idempotencyKey: string }) => Promise<ArV3BetaGroup>;
  onSuccess: (result: ArV3BetaGroup) => void;
};

beforeEach(() => {
  calls.invalidations.length = 0;
  calls.writes.length = 0;
  settled.mutate.length = 0;
  settled.identity = false;
  settled.mutation = { isPending: false, isSuccess: false, error: null, data: undefined };
  vi.clearAllMocks();
});

describe('the start command', () => {
  it('sends the version and the caller key — no provider mode, no pack, no scope', async () => {
    settled.identity = true;
    vi.mocked(startArV3BetaGroup).mockResolvedValue({ data: GROUP } as never);
    const command = useStartArV3Group() as unknown as Captured;
    const answer = await command.mutationFn({ versionUid: VERSION_UID, idempotencyKey: KEY });
    await command.mutationFn({ versionUid: VERSION_UID, idempotencyKey: KEY });
    expect(answer).toBe(GROUP);
    expect(vi.mocked(startArV3BetaGroup).mock.calls).toEqual([
      [{ body: { version_uid: VERSION_UID }, idempotencyKey: KEY }],
      [{ body: { version_uid: VERSION_UID }, idempotencyKey: KEY }],
    ]);
  });

  it('an accepted start invalidates the run lists, the dashboard and every execution read', () => {
    settled.identity = true;
    const command = useStartArV3Group() as unknown as Captured;
    command.onSuccess(GROUP);
    expect(calls.invalidations).toEqual([
      [{ queryKey: queryKeys.runs.all() }],
      [{ queryKey: queryKeys.dashboard.summary() }],
      [{ queryKey: queryKeys.execution.all() }],
    ]);
    // Six queued Runs are read back through the group review, not seeded as single runs.
    expect(calls.writes).toEqual([]);
  });
});

describe('the control hands over only a group the settings screen can open', () => {
  const render = (onStarted: (group: ArV3BetaGroup) => void): string =>
    renderToStaticMarkup(
      createElement(StartArV3GroupControl, { projectUid: PROJECT_UID, versionUid: VERSION_UID, onStarted }),
    );

  it('calls onStarted with a 202 group that carries a valid address, and with no other', () => {
    const started: ArV3BetaGroup[] = [];
    // A static render cannot press the button, but the control is an ordinary function of its
    // hooks: calling it inside a component's render gives it a dispatcher and hands back the view
    // element, whose `onSend` is the very handler the button carries.
    let onSend: (() => void) | undefined;
    function Probe() {
      const element = StartArV3GroupControl({
        projectUid: PROJECT_UID,
        versionUid: VERSION_UID,
        onStarted: (group) => started.push(group),
      });
      onSend = (element.props as { onSend: () => void }).onSend;
      return element;
    }
    renderToStaticMarkup(createElement(Probe));
    expect(onSend, 'the control did not hand its view a send handler').toBeDefined();
    onSend!();
    const [variables, options] = settled.mutate[0] as [
      { versionUid: string; idempotencyKey: string },
      { onSuccess: (group: ArV3BetaGroup) => void },
    ];
    expect(variables.versionUid).toBe(VERSION_UID);
    expect(variables.idempotencyKey.length).toBeGreaterThan(8);

    options.onSuccess(GROUP);
    expect(started).toEqual([GROUP]);
    options.onSuccess({ ...GROUP, group_id: 'arg_bad' as never });
    options.onSuccess({} as ArV3BetaGroup);
    options.onSuccess(null as never);
    expect(started, 'a malformed group address must not be handed on').toEqual([GROUP]);
  });

  it('draws the fault, not a success, when the settled answer has no usable address', () => {
    settled.mutation = { isPending: false, isSuccess: true, error: null, data: { ...GROUP, group_id: 'arg_bad' } };
    const markup = render(() => undefined);
    expect(markup).toContain('data-ar-v3-group-failure="malformed_answer"');
    expect(markup).toContain('Ответ сервера не соответствует контракту.');
    settled.mutation = { isPending: false, isSuccess: true, error: null, data: GROUP };
    expect(render(() => undefined)).not.toContain('data-ar-v3-group-failure');
  });
});
