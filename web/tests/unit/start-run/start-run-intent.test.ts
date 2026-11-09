/**
 * `EXEC-PAR-WEB-01`: the executor the person chooses is part of the request and of the intent.
 *
 * Three claims, each with a way to fail:
 *   - the choice is SENT, as `executor_connection_id`, and only when a connection is chosen (the
 *     default is the absence of the field, never `null`, which the contract refuses);
 *   - the choice changes the idempotency KEY: the same version on another executor is another
 *     request, and sending it under the first one's key is `idempotency_key_reuse`;
 *   - the control takes both from one value, so they cannot disagree (a wiring test over its source).
 *
 * The control's `useState` cannot be driven by a static render, so the pure functions it calls are
 * tested here and the control's use of them is read from its source.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

const calls = vi.hoisted(() => ({ invalidations: [] as unknown[], writes: [] as unknown[] }));

vi.mock('@tanstack/react-query', () => ({
  useMutation: (configuration: unknown) => configuration,
  useQueryClient: () => ({
    setQueryData: (...args: unknown[]) => calls.writes.push(args),
    invalidateQueries: (...args: unknown[]) => { calls.invalidations.push(args); return Promise.resolve(); },
  }),
}));

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, startRun: vi.fn() };
});

import { join } from 'node:path';

import { startRun } from '@/shared/api';
import { resolveIntentKey } from '@/shared/lib';
import { startRunBody, startRunIntent, useStartRun } from '@/features/start-run';

import { WEB_ROOT, readText } from '../../guards/lib/repo';

const VERSION = 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const OTHER_VERSION = 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8G';
const GATEWAY = 'exc_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const SPARE = 'exc_01J9ZQ8K7NHVXW3T2R5M6P4Q8G';
const KEY = 'ik-one-intent';
const RUN = { run_id: 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', project_uid: 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8F' };

type Captured = { mutationFn: (input: unknown) => Promise<unknown> };

beforeEach(() => {
  calls.invalidations.length = 0;
  calls.writes.length = 0;
  vi.clearAllMocks();
});

describe('the choice is sent, and only when a connection is chosen', () => {
  it('sends executor_connection_id for a chosen connection', async () => {
    vi.mocked(startRun).mockResolvedValue({ data: RUN } as never);
    const command = useStartRun() as unknown as Captured;
    await command.mutationFn(startRunIntent(VERSION, GATEWAY).command(KEY));
    expect(startRun).toHaveBeenCalledWith({
      body: { version_uid: VERSION, executor_connection_id: GATEWAY },
      idempotencyKey: KEY,
    });
  });

  it('omits the field for the default: the request is the one it always was', async () => {
    vi.mocked(startRun).mockResolvedValue({ data: RUN } as never);
    const command = useStartRun() as unknown as Captured;
    await command.mutationFn(startRunIntent(VERSION, null).command(KEY));
    expect(startRun).toHaveBeenCalledWith({ body: { version_uid: VERSION }, idempotencyKey: KEY });
    const sent = vi.mocked(startRun).mock.calls[0]?.[0] as { body: Record<string, unknown> };
    expect('executor_connection_id' in sent.body).toBe(false);
    expect(JSON.stringify(sent.body)).not.toContain('null');
  });

  it('builds the body from the command alone', () => {
    expect(startRunBody({ versionUid: VERSION, idempotencyKey: KEY })).toEqual({ version_uid: VERSION });
    expect(startRunBody({ versionUid: VERSION, idempotencyKey: KEY, executorConnectionId: GATEWAY })).toEqual({
      version_uid: VERSION, executor_connection_id: GATEWAY,
    });
  });

  it('sends the raised-limit flag only after an explicit choice, with either a preset or an executor', async () => {
    vi.mocked(startRun).mockResolvedValue({ data: RUN } as never);
    const command = useStartRun() as unknown as Captured;
    await command.mutationFn(startRunIntent(VERSION, null, null, true).command(KEY));
    expect(startRun).toHaveBeenCalledWith({
      body: { version_uid: VERSION, relaxed_limits: true }, idempotencyKey: KEY,
    });
    expect(startRunBody(startRunIntent(VERSION, GATEWAY, null, true).command(KEY))).toEqual({
      version_uid: VERSION, executor_connection_id: GATEWAY, relaxed_limits: true,
    });
    expect(startRunBody(startRunIntent(VERSION, GATEWAY, 'preset-1', true).command(KEY))).toEqual({
      version_uid: VERSION, preset_id: 'preset-1', relaxed_limits: true,
    });
    expect(startRunBody(startRunIntent(VERSION, null, null, false).command(KEY))).toEqual({
      version_uid: VERSION,
    });
  });

  it('puts the choice in the command only when there is one', () => {
    const none = startRunIntent(VERSION, null).command(KEY);
    expect('executorConnectionId' in none).toBe(false);
    expect(startRunIntent(VERSION, SPARE).command(KEY).executorConnectionId).toBe(SPARE);
  });
});

describe('the choice is part of the intent, so it changes the idempotency key', () => {
  let minted = 0;
  const mint = () => `key-${++minted}`;
  const keyFor = (previous: ReturnType<typeof resolveIntentKey> | null, version: string, choice: string | null) =>
    resolveIntentKey(previous, startRunIntent(version, choice).signature, mint);

  it('keeps the signature a start without a choice always had', () => {
    expect(startRunIntent(VERSION, null).signature).toBe(`start-run:${VERSION}`);
  });

  it('gives the same version on another executor another signature, and so another key', () => {
    const first = keyFor(null, VERSION, GATEWAY);
    expect(keyFor(first, VERSION, GATEWAY).idempotencyKey).toBe(first.idempotencyKey);
    expect(keyFor(first, VERSION, SPARE).idempotencyKey).not.toBe(first.idempotencyKey);
    expect(startRunIntent(VERSION, GATEWAY).signature).not.toBe(startRunIntent(VERSION, SPARE).signature);
  });

  it('gives the default and a chosen executor different keys, in both directions', () => {
    const byDefault = keyFor(null, VERSION, null);
    const chosen = keyFor(byDefault, VERSION, GATEWAY);
    expect(chosen.idempotencyKey).not.toBe(byDefault.idempotencyKey);
    expect(keyFor(chosen, VERSION, null).idempotencyKey).not.toBe(chosen.idempotencyKey);
  });

  it('still gives another version another key', () => {
    const first = keyFor(null, VERSION, GATEWAY);
    expect(keyFor(first, OTHER_VERSION, GATEWAY).idempotencyKey).not.toBe(first.idempotencyKey);
  });

  it('keeps a retry of one intent under one key', () => {
    const first = keyFor(null, VERSION, GATEWAY);
    expect(keyFor(first, VERSION, GATEWAY)).toBe(first);
  });

  it('mints another key when the raised-limit choice changes, while standard signatures stay stable', () => {
    for (const [executor, preset] of [[null, null], [GATEWAY, null], [null, 'preset-1']] as const) {
      const standard = startRunIntent(VERSION, executor, preset, false);
      const raised = startRunIntent(VERSION, executor, preset, true);
      expect(raised.signature).not.toBe(standard.signature);
      const first = resolveIntentKey(null, standard.signature, mint);
      const second = resolveIntentKey(first, raised.signature, mint);
      expect(second.idempotencyKey).not.toBe(first.idempotencyKey);
      expect(resolveIntentKey(second, raised.signature, mint)).toBe(second);
      expect('relaxedLimits' in standard.command(KEY)).toBe(false);
      expect(raised.command(KEY).relaxedLimits).toBe(true);
    }
    expect(startRunIntent(VERSION, null, null, false).signature).toBe(`start-run:${VERSION}`);
  });
});

describe('the control takes its key and its request from the same intent, and names no selector', () => {
  // `RUN-START-ONE-01a`: the one-button sequence lives in the hook; the control only draws it.
  const strip = (text: string) => text.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
  const hook = strip(readText(join(WEB_ROOT, 'src', 'features', 'start-run', 'model', 'use-run-cost-approval.ts')));
  const control = strip(readText(join(WEB_ROOT, 'src', 'features', 'start-run', 'ui', 'start-run-control.tsx')));

  it('derives the one intent from the version, the limit choice and the consent, with no selector', () => {
    expect(hook.match(/startRunIntent\(/g)).toHaveLength(1);
    expect(hook).toContain('startRunIntent(versionUid, null, null, relaxed, consent)');
    expect(hook).not.toMatch(/startRunIntent\([^)]*\b(executor|group|preset)/i);
  });

  it('mints the key for that intent with the same rule every write feature uses, and sends that intent’s command', () => {
    expect(hook).toContain('held.current = resolveIntentKey(held.current, intent.signature, newIdempotencyKey);');
    expect(hook).toContain('intent.command(held.current.idempotencyKey)');
  });

  it('builds the estimate request from the version and the limit choice alone', () => {
    expect(hook).toContain('estimateRunCost({ body: estimateRequest(versionUid, relaxed) })');
    const model = strip(readText(join(WEB_ROOT, 'src', 'features', 'start-run', 'model', 'one-click-start.ts')));
    expect(model).toContain("{ version_uid: versionUid, ...(relaxed ? { relaxed_limits: true } : {}) }");
  });

  it('writes no intent signature or request body of its own, and holds no executor, group or preset', () => {
    for (const code of [hook, control]) {
      expect(code).not.toMatch(/useIntentKey\(\s*[`'"]/);
      expect(code).not.toContain('executor_connection_id');
      expect(code).not.toContain('executor_group_id');
      expect(code).not.toContain('preset_id');
      expect(code).not.toMatch(/executorConnectionId|executorGroupId|presetId/);
    }
    expect(control).not.toContain('version_uid');
    expect(control).not.toMatch(/<select|type="radio"|type="checkbox"/);
  });

  it('answers a changed estimate with an estimate, and never with a different executor or route', () => {
    expect(hook).toContain('if (estimateChanged(error)) {');
    expect(hook).toContain('estimate(relaxed, true);');
    // `READINESS-WEB-01`: the line under the button is read again at the same moment, since the access it states may be what changed.
    expect(hook).toContain('invalidateQueries({ queryKey: runStartReadinessKey(versionUid) })');
  });
});
