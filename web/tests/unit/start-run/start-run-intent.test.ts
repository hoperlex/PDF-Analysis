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
import { chosenExecutor, startRunBody, startRunIntent, useStartRun } from '@/features/start-run';

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

  it('reads the empty option as the default and any other value as the connection', () => {
    expect(chosenExecutor('')).toBeNull();
    expect(chosenExecutor(GATEWAY)).toBe(GATEWAY);
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

describe('the control takes its key and its request from the same choice', () => {
  const source = readText(join(WEB_ROOT, 'src', 'features', 'start-run', 'ui', 'start-run-control.tsx'));
  const code = source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');

  it('derives one intent from the version, executor, preset and limit choice', () => {
    expect(code).toContain('startRunIntent(versionUid, chosen, chosenPreset, relaxedLimits)');
  });

  it('mints the key for that intent and sends that intent’s command', () => {
    expect(code).toContain('useIntentKey(intent.signature)');
    expect(code).toContain('intent.command(idempotencyKey)');
  });

  it('clears a refusal when the choice changes, because it was about the old choice', () => {
    expect(code).toMatch(/setChosen\(next\);\s*mutation\.reset\(\);/);
    expect(code).toMatch(/setRelaxedLimits\(event\.currentTarget\.checked\);\s*mutation\.reset\(\);/);
    expect(code).toContain('disabled={mutation.isPending}');
  });

  it('never changes the choice itself: only the person’s change does, and a refusal changes nothing', () => {
    // After a refusal the control keeps the choice and offers the retry; it must not move to the
    // default or to another connection on its own, and it must not learn of a refusal except to show it.
    //
    // `ANALYSIS-PRESETS-01`: choosing a preset fills the executor, so the preset select's own change
    // handler clears the hand-chosen connection (`setChosen(null)` straight after `setChosenPreset`).
    // That is still the person's change; no other place may call it, and nothing reacts to an error.
    expect(code.match(/setChosen\(/g)).toHaveLength(2);
    expect(code).toContain('setChosen(next)');
    expect(code.match(/setChosen\(null\)/g)).toHaveLength(1);
    expect(code).toMatch(/setChosenPreset\(next\);[\s\S]{0,200}?setChosen\(null\);\s*mutation\.reset\(\);/);
    expect(code.match(/setChosenPreset\(/g)).toHaveLength(1);
    expect(code).not.toMatch(/onError/);
  });

  it('writes no intent signature or request body of its own', () => {
    expect(code).not.toMatch(/useIntentKey\(\s*[`'"]/);
    expect(code).not.toContain('version_uid');
    expect(code).not.toContain('executor_connection_id');
  });

  it('holds the choice as an id or null, never as a mode', () => {
    expect(code).toMatch(/useState<ExecutorConnectionId \| null>\(null\)/);
  });
});
