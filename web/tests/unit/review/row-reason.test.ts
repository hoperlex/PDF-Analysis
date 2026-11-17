/**
 * The reason beside ✓ and ✕ in a finding's row goes with the verdict in ONE event (`UIP-S06-02`, decision `Г9-B`).
 *
 * Mounted live and driven the way an expert drives it: the real `ReviewRowActions`, the real `useRecordVerdict` over React Query,
 * the entity's real field, typed into and pressed; only the transport, `appendDecision`, is a stub, so each case reads the request a
 * browser would put on the wire. What is claimed is a sequence, and every claim has a negative that can fail:
 *
 *   - the text goes as `comment` of the SAME `accept` or `reject` event (one request per press, never a second `comment` event),
 *     trimmed; a field that is empty or blank adds no `comment` key at all, so the press is byte-for-byte what it always was;
 *   - once the server has written the press the field is empty and the line says «Записано»;
 *   - a press the browser refuses before sending (✓ on a finding with a proposed severity the expert has not chosen) and a press
 *     the server fails leave the text where it is, and pressing again with that text reuses the idempotency key of the first
 *     press -- while other text, or the other verdict, is another command with another key;
 *   - the choice «Критичность» beside ✓ (`UIP-S06-08`): the severity the expert chose goes with the reason in the same accept, a ✓
 *     without a choice says so in the row and opens nothing, and a finding the model proposed no severity for has no select.
 */

import { QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import type { ReactElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  appendDecision: vi.fn(),
}));

import { ReviewRowActions } from '@/_pages/review';
import type { AppendDecisionRequest, AppendDecisionResponse, Finding, RunId } from '@/shared/api';
import { appendDecision } from '@/shared/api';

import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import { newClient } from '../screens/harness';
import { FINDING_UID, OBSERVATION_ID, RUN_ID, decisionEvent, decisionId, finding, observation } from './fixtures';

/** The part of the test document's node this file reads: React keeps its props on it, and `childNodes` lead to the field. */
interface DomNode {
  readonly nodeName: string;
  readonly childNodes: readonly DomNode[];
}

type FieldProps = { value?: string; onChange?: (event: unknown) => void };

const RUN = RUN_ID as RunId;
const REASON = 'Пункт подтверждён по листу 3';

let live: LiveRender | null = null;
let host: DomNode | null = null;
let written = 0;

const MARKER = 'Записано';

function row(subject: Finding): ReactElement {
  return createElement(
    QueryClientProvider,
    { client: newClient() },
    createElement(
      'div',
      { ref: (node: unknown) => { host = node as DomNode | null; } },
      createElement(ReviewRowActions, { finding: subject, runId: RUN }),
    ),
  );
}

function descendants(node: DomNode): DomNode[] {
  return node.childNodes.flatMap((child) => [child, ...descendants(child)]);
}

/** The props React stored on the field's node: where its `value` and its `onChange` live. */
function fieldProps(): FieldProps {
  const input = descendants(host as DomNode).filter((node) => node.nodeName === 'input');
  expect(input).toHaveLength(1);
  const key = Object.keys(input[0] as object).find((name) => name.startsWith('__reactProps$'));
  return (input[0] as unknown as Record<string, FieldProps>)[key as string] as FieldProps;
}

/** What the field shows now. */
const shown = (): string => fieldProps().value ?? '';

async function type(text: string): Promise<void> {
  await (live as LiveRender).settle(() => {
    (fieldProps().onChange as (event: unknown) => void)({ type: 'change', target: { value: text }, currentTarget: { value: text } });
  });
}

async function mount(subject: Finding): Promise<LiveRender> {
  live = await mountLive(row(subject));
  return live;
}

type SelectProps = { value?: string; onChange?: (event: unknown) => void };

/** The props React stored on the severity select's node, or `null` when the row draws none. */
function selectProps(): SelectProps | null {
  const found = descendants(host as DomNode).filter((node) => node.nodeName === 'select');
  expect(found.length).toBeLessThanOrEqual(1);
  if (found[0] === undefined) return null;
  const key = Object.keys(found[0] as object).find((name) => name.startsWith('__reactProps$'));
  return (found[0] as unknown as Record<string, SelectProps>)[key as string] as SelectProps;
}

async function choose(severity: string): Promise<void> {
  await (live as LiveRender).settle(() => {
    ((selectProps() as SelectProps).onChange as (event: unknown) => void)({ type: 'change', target: { value: severity }, currentTarget: { value: severity } });
  });
}

interface Sent {
  readonly findingUid: string;
  readonly body: AppendDecisionRequest;
  readonly idempotencyKey: string;
}

function sent(): Sent[] {
  return vi.mocked(appendDecision).mock.calls.map(([call]) => {
    const { path, body, idempotencyKey } = call as unknown as { path: { finding_uid: string }; body: AppendDecisionRequest; idempotencyKey: string };
    return { findingUid: path.finding_uid, body, idempotencyKey };
  });
}

beforeEach(() => {
  vi.resetAllMocks();
  written = 0;
  // The server answers with the verdict of the event it was asked to append, under a fresh id each time.
  vi.mocked(appendDecision).mockImplementation((input) => {
    const { body } = input as unknown as { body: AppendDecisionRequest };
    written += 1;
    const verdict = body.event_type === 'accept' ? 'accepted' : 'rejected';
    const answer: AppendDecisionResponse = {
      current_verdict: verdict,
      event: decisionEvent({
        decision_id: decisionId(String.fromCharCode(64 + written)),
        event_type: body.event_type,
        verdict,
        comment: body.comment ?? null,
      }),
    };
    return Promise.resolve({ data: answer } as never);
  });
});

afterEach(async () => {
  await live?.unmount();
  live = null;
  host = null;
});

describe('the reason is the comment of the same event', () => {
  it('sends ✓ with the typed text, trimmed, as one accept carrying it', async () => {
    const view = await mount(finding());
    await type(`  ${REASON}  `);
    expect(shown()).toBe(`  ${REASON}  `);

    expect(await view.press('✓')).toBe(true);

    expect(sent()).toEqual([
      { findingUid: FINDING_UID, body: { event_type: 'accept', finding_observation_id: OBSERVATION_ID, comment: REASON }, idempotencyKey: expect.any(String) },
    ]);
  });

  it('sends ✕ with the typed text, trimmed, as one reject carrying it', async () => {
    const view = await mount(finding());
    await type(' Не относится к разделу ');

    await view.press('✕');

    expect(sent().map((call) => call.body)).toEqual([
      { event_type: 'reject', finding_observation_id: OBSERVATION_ID, comment: 'Не относится к разделу' },
    ]);
  });

  it('sends no comment key at all when the field is empty or blank, on either button', async () => {
    const view = await mount(finding());
    await view.press('✓');
    await type('   ');
    await view.press('✕');

    const bodies = sent().map((call) => call.body);
    expect(bodies).toEqual([
      { event_type: 'accept', finding_observation_id: OBSERVATION_ID },
      { event_type: 'reject', finding_observation_id: OBSERVATION_ID },
    ]);
    // `toEqual` treats an undefined property as absent; the wire does not, and the ledger refuses an empty comment.
    for (const body of bodies) expect(Object.keys(body).sort()).toEqual(['event_type', 'finding_observation_id']);
  });

  it('is one request per press: the reason is never a second event', async () => {
    const view = await mount(finding());
    await type(REASON);
    await view.press('✓');

    expect(vi.mocked(appendDecision)).toHaveBeenCalledTimes(1);
    expect(sent().some((call) => call.body.event_type === 'comment')).toBe(false);
  });
});

describe('after the server has written the press', () => {
  it('empties the field and says «Записано»', async () => {
    const view = await mount(finding());
    expect(view.markup()).not.toContain(MARKER);
    await type(REASON);
    expect(shown()).toBe(REASON);

    await view.press('✓');

    expect(shown()).toBe('');
    expect(view.markup()).toContain(`role="status">${MARKER}<`);
  });

  it('empties it again after the next write, and the next press carries only the new text', async () => {
    const view = await mount(finding());
    await type(REASON);
    await view.press('✓');
    await type('Передумал: пункт не подтверждён');
    await view.press('✕');

    expect(shown()).toBe('');
    expect(sent().map((call) => call.body.comment)).toEqual([REASON, 'Передумал: пункт не подтверждён']);
  });

  it('does not empty the field while the next press is still out, only once it is written', async () => {
    let answer: (value: unknown) => void = () => {};
    vi.mocked(appendDecision).mockReturnValueOnce(new Promise((resolve) => { answer = resolve; }) as never);
    const view = await mount(finding());
    await type(REASON);

    await view.press('✓');
    expect(shown()).toBe(REASON);
    // Both buttons are held while the press is on its way (one click is one event), and the held one reads as sending.
    expect(view.count('…')).toBe(1);
    expect(view.count('✕')).toBe(1);

    await view.settle(() => {
      answer({ data: { current_verdict: 'accepted', event: decisionEvent({ decision_id: decisionId('Z'), comment: REASON }) } });
    });
    expect(shown()).toBe('');
  });
});

describe('after a failure', () => {
  it('keeps the text, shows the failure, and the same press with the same text reuses the first press’s key', async () => {
    vi.mocked(appendDecision).mockRejectedValueOnce(new Error('connection closed'));
    const view = await mount(finding());
    await type(REASON);

    await view.press('✓');

    expect(shown()).toBe(REASON);
    expect(view.markup()).toContain('role="alert"');
    expect(view.markup()).not.toContain(MARKER);

    await view.press('✓');

    const [first, retry] = sent();
    expect(sent()).toHaveLength(2);
    expect(retry?.body).toEqual(first?.body);
    expect(retry?.body.comment).toBe(REASON);
    expect(retry?.idempotencyKey).toBe(first?.idempotencyKey);
    // The retry went through: now the field is empty.
    expect(shown()).toBe('');
    expect(view.markup()).toContain(`role="status">${MARKER}<`);
  });

  it('keeps the text of a press that fails after an earlier press was written, while it is out and after it failed', async () => {
    const view = await mount(finding());
    await type(REASON);
    await view.press('✓');
    expect(shown()).toBe('');

    let fail: (error: unknown) => void = () => {};
    vi.mocked(appendDecision).mockReturnValueOnce(new Promise((_resolve, reject) => { fail = reject; }) as never);
    await type('Передумал: пункт не подтверждён');
    await view.press('✕');
    // The earlier write's answer has gone back to nothing while this press is out; the text must not go with it.
    expect(shown()).toBe('Передумал: пункт не подтверждён');

    await view.settle(() => {
      fail(new Error('connection closed'));
    });
    expect(shown()).toBe('Передумал: пункт не подтверждён');
    expect(view.markup()).toContain('role="alert"');
  });

  it('mints another key for other text, and for the other verdict, after the same failure', async () => {
    vi.mocked(appendDecision).mockRejectedValueOnce(new Error('connection closed'));
    vi.mocked(appendDecision).mockRejectedValueOnce(new Error('connection closed'));
    const view = await mount(finding());
    await type(REASON);
    await view.press('✓');
    await type(`${REASON}, лист 4`);
    await view.press('✓');
    await view.press('✕');

    const calls = sent();
    expect(calls.map((call) => call.body.comment)).toEqual([REASON, `${REASON}, лист 4`, `${REASON}, лист 4`]);
    expect(calls.map((call) => call.body.event_type)).toEqual(['accept', 'accept', 'reject']);
    expect(new Set(calls.map((call) => call.idempotencyKey)).size).toBe(3);
  });

  it('a press with no text after a failed press with text is another command too', async () => {
    vi.mocked(appendDecision).mockRejectedValueOnce(new Error('connection closed'));
    const view = await mount(finding());
    await type(REASON);
    await view.press('✓');
    await type('');
    await view.press('✓');

    const [first, second] = sent();
    expect(second?.body).toEqual({ event_type: 'accept', finding_observation_id: OBSERVATION_ID });
    expect(second?.idempotencyKey).not.toBe(first?.idempotencyKey);
  });
});

describe('a ✓ the browser refuses before sending', () => {
  const proposed = () => finding({ observation: observation({ proposed_severity: 'critical' }) });

  it('sends nothing, says why in the row, and leaves the text in the field', async () => {
    const view = await mount(proposed());
    await type(REASON);

    await view.press('✓');

    expect(vi.mocked(appendDecision)).not.toHaveBeenCalled();
    expect(shown()).toBe(REASON);
    expect(view.markup()).toContain('Перед принятием выберите критичность. Ничего не отправлено.');
    expect(view.markup()).toContain('role="alert"');
  });

  it('still sends ✕ with the same text: a reject needs no severity', async () => {
    const view = await mount(proposed());
    await type(REASON);
    await view.press('✓');

    await view.press('✕');

    expect(sent().map((call) => call.body)).toEqual([{ event_type: 'reject', finding_observation_id: OBSERVATION_ID, comment: REASON }]);
    expect(shown()).toBe('');
  });

  it('sends the chosen severity together with the reason when the expert has chosen one', async () => {
    const view = await mount(finding({ observation: observation({ proposed_severity: 'critical' }), decided_severity: 'economic' }));
    await type(REASON);

    await view.press('✓');

    expect(sent().map((call) => call.body)).toEqual([
      { event_type: 'accept', finding_observation_id: OBSERVATION_ID, comment: REASON, severity: 'economic' },
    ]);
  });
});

describe('the choice «Критичность» beside ✓', () => {
  const proposed = (over: Partial<Finding> = {}) => finding({ observation: observation({ proposed_severity: 'critical' }), ...over });

  it('is in the row of a finding the model proposed a severity for, empty, and not in the row of one it did not', async () => {
    await mount(finding());
    expect(selectProps()).toBeNull();
    await (live as LiveRender).unmount();
    live = null;

    await mount(proposed());
    expect(selectProps()?.value).toBe('');
  });

  it('sends one accept with the chosen severity and the reason, never the proposal', async () => {
    const view = await mount(proposed());
    await type(REASON);
    await choose('economic');
    expect(selectProps()?.value).toBe('economic');

    await view.press('✓');

    expect(sent().map((call) => call.body)).toEqual([
      { event_type: 'accept', finding_observation_id: OBSERVATION_ID, comment: REASON, severity: 'economic' },
    ]);
    expect(shown()).toBe('');
    expect(view.markup()).toContain(`role="status">${MARKER}<`);
  });

  it('refuses ✓ without a choice in the row, opens nothing, keeps the reason, and sends the accept once a choice is made', async () => {
    const view = await mount(proposed());
    await type(REASON);

    await view.press('✓');
    expect(vi.mocked(appendDecision)).not.toHaveBeenCalled();
    expect(view.markup()).toContain('Перед принятием выберите критичность. Ничего не отправлено.');
    expect(view.markup()).toContain('aria-invalid="true"');
    expect(shown()).toBe(REASON);

    await choose('operational');
    // The sentence asked for the choice, and goes when it is made.
    expect(view.markup()).not.toContain('Перед принятием выберите критичность.');
    expect(view.markup()).not.toContain('aria-invalid');

    await view.press('✓');
    expect(sent().map((call) => call.body)).toEqual([
      { event_type: 'accept', finding_observation_id: OBSERVATION_ID, comment: REASON, severity: 'operational' },
    ]);
  });

  it('is held while the press is out, and once the finding is accepted, with the severity that was chosen', async () => {
    let answer: (value: unknown) => void = () => {};
    vi.mocked(appendDecision).mockReturnValueOnce(new Promise((resolve) => { answer = resolve; }) as never);
    const view = await mount(proposed());
    await choose('economic');

    await view.press('✓');
    expect(view.markup()).toMatch(/<select[^>]*disabled/);

    await view.settle(() => {
      answer({ data: { current_verdict: 'accepted', event: decisionEvent({ decision_id: decisionId('Y') }) } });
    });
    // Accepted: ✓ is not offered, and the choice is held with the severity that was chosen.
    expect(view.markup()).toMatch(/<select[^>]*disabled/);
    expect(selectProps()?.value).toBe('economic');
  });
});
