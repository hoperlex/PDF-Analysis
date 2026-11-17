/**
 * «Подтвердить все предложения» (`UIP-S16-03`): one confirmation of the expert over a shown list, one command per pair.
 *
 * What is held here: the commands are one per pair in the order shown, each with its own key; a refusal of one pair does not stop
 * the others and is reported with its reason; a pair that failed keeps its key until it is confirmed, so a retry is the same command;
 * and the window says «Подтверждено N из M» and never claims a pair the server did not accept.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { StagePairSuggestion } from '@/shared/api';
import { HeldPairKeys, confirmSuggestions, pairSignature } from '@/entities/stage-pair';
import type { ConfirmedPairRequest } from '@/entities/stage-pair';
import { ConfirmAllSuggestionsView } from '@/widgets/stage-pair-catalog/ui/confirm-all-suggestions';
import type { ConfirmAllPhase } from '@/widgets/stage-pair-catalog/ui/confirm-all-suggestions';

import { render } from '../review/fixtures';
import { PROJECT_UID, uid } from '../version-compare/fixtures';
import { refusal } from '../version-compare/seed';

const suggestion = (index: number): StagePairSuggestion => ({
  left_document_uid: uid('doc', index), right_document_uid: uid('doc', 50 + index), reason: 'section_designation_exact', score: 1,
});
const LIST = [suggestion(1), suggestion(2), suggestion(3)];

function keys(): HeldPairKeys {
  let sequence = 0;
  return new HeldPairKeys(() => `key-${++sequence}`);
}

/** A `send` that records each command and refuses the pairs named by their left document, for as many times as asked. */
function sender(refuse: Readonly<Record<string, number>> = {}) {
  const sent: ConfirmedPairRequest[] = [];
  const refused = new Map(Object.entries(refuse));
  return {
    sent,
    send: async (request: ConfirmedPairRequest): Promise<void> => {
      sent.push(request);
      const left = refused.get(request.leftDocumentUid) ?? 0;
      if (left > 0) {
        refused.set(request.leftDocumentUid, left - 1);
        throw refusal('conflict');
      }
    },
  };
}

describe('one command per suggestion', () => {
  it('sends each pair in the order shown, each under its own key, and says how many the server accepted', async () => {
    const wire = sender();
    const progress: number[] = [];
    const result = await confirmSuggestions({ projectUid: PROJECT_UID, suggestions: LIST, send: wire.send, keys: keys(), onProgress: (done) => progress.push(done) });
    expect(wire.sent.map((request) => request.leftDocumentUid)).toEqual(LIST.map((one) => one.left_document_uid));
    expect(wire.sent.map((request) => request.rightDocumentUid)).toEqual(LIST.map((one) => one.right_document_uid));
    expect(wire.sent.map((request) => request.idempotencyKey)).toEqual(['key-1', 'key-2', 'key-3']);
    expect(result).toEqual({ total: 3, confirmed: 3, failures: [] });
    expect(progress).toEqual([1, 2, 3]);
  });

  it('does not stop at a refused pair: the others are confirmed and the refused one is reported as it came', async () => {
    const wire = sender({ [LIST[1]!.left_document_uid]: 1 });
    const result = await confirmSuggestions({ projectUid: PROJECT_UID, suggestions: LIST, send: wire.send, keys: keys() });
    expect(wire.sent).toHaveLength(3);
    expect(result.total).toBe(3);
    expect(result.confirmed).toBe(2);
    expect(result.failures.map((failure) => failure.suggestion)).toEqual([LIST[1]]);
    expect(result.failures[0]!.error).toMatchObject({ status: 409 });
  });

  it('keeps the key of a refused pair and sends the retry under it, while the confirmed pairs let theirs go', async () => {
    const held = keys();
    const wire = sender({ [LIST[1]!.left_document_uid]: 1 });
    const first = await confirmSuggestions({ projectUid: PROJECT_UID, suggestions: LIST, send: wire.send, keys: held });
    expect(held.holds(pairSignature(PROJECT_UID, LIST[1]!))).toBe(true);
    expect(held.holds(pairSignature(PROJECT_UID, LIST[0]!))).toBe(false);
    const retry = await confirmSuggestions({ projectUid: PROJECT_UID, suggestions: first.failures.map((failure) => failure.suggestion), send: wire.send, keys: held });
    expect(retry).toEqual({ total: 1, confirmed: 1, failures: [] });
    // The second pair was sent twice, and both times under the key it was first given.
    const second = wire.sent.filter((request) => request.leftDocumentUid === LIST[1]!.left_document_uid);
    expect(second.map((request) => request.idempotencyKey)).toEqual(['key-2', 'key-2']);
    expect(held.holds(pairSignature(PROJECT_UID, LIST[1]!))).toBe(false);
  });

  it('can fail: a pair confirmed once and asked again is a new command, with a new key', async () => {
    const held = keys();
    const wire = sender();
    await confirmSuggestions({ projectUid: PROJECT_UID, suggestions: [LIST[0]!], send: wire.send, keys: held });
    await confirmSuggestions({ projectUid: PROJECT_UID, suggestions: [LIST[0]!], send: wire.send, keys: held });
    expect(wire.sent.map((request) => request.idempotencyKey)).toEqual(['key-1', 'key-2']);
  });

  it('sends nothing for an empty list and says so as «0 из 0»', async () => {
    const wire = sender();
    expect(await confirmSuggestions({ projectUid: PROJECT_UID, suggestions: [], send: wire.send, keys: keys() })).toEqual({ total: 0, confirmed: 0, failures: [] });
    expect(wire.sent).toEqual([]);
  });
});

describe('the window of the confirmation', () => {
  const NAMES = new Map([
    [uid('doc', 1), { title: 'Пояснительная записка', section: 'AR', stage: 'P' as const }],
    [uid('doc', 51), { title: 'Пояснительная записка, редакция 2', section: 'AR', stage: 'R' as const }],
  ]);

  function view(phase: ConfirmAllPhase, suggestions: readonly StagePairSuggestion[] = LIST, total = LIST.length): string {
    return render(createElement(ConfirmAllSuggestionsView, {
      suggestions, total, names: NAMES, phase, onConfirm: () => undefined, onRetry: () => undefined, onClose: () => undefined, staticOpen: true,
    })).replace(/<!-- -->/g, '');
  }

  it('shows the list the expert is asked about, each pair by its documents and its reason, and asks for one confirmation', () => {
    const html = view({ kind: 'review' });
    expect(html).toContain('Подтвердить все предложения');
    expect(html).toContain('П: Пояснительная записка · AR · Р: Пояснительная записка, редакция 2 · AR');
    expect(html).toContain('Совпадают раздел и подтверждённый шифр');
    expect((html.match(/<li>/g) ?? []).length).toBe(3);
    expect(html).toContain('Каждая пара подтверждается отдельным решением эксперта. Предложение само ничего не связывает.');
    expect(html).toContain('Подтвердить все (3)');
    expect(html).toContain('>Отмена<');
  });

  it('says how far the commands have gone, and does not let the window be left or asked twice while they run', () => {
    const html = view({ kind: 'running', done: 2 });
    expect(html).toContain('Подтверждаем: 2 из 3…');
    expect(html).toMatch(/<button[^>]*disabled[^>]*>Отмена</);
    expect(html).toMatch(/data-confirm-all-submit=""[^>]*disabled/);
  });

  it('ends with «Подтверждено N из M» and nothing else when every pair was accepted', () => {
    const html = view({ kind: 'finished', result: { total: 3, confirmed: 3, failures: [] } });
    expect(html).toContain('Подтверждено 3 из 3');
    expect(html).not.toContain('Не подтверждены');
    expect(html).not.toContain('Повторить для оставшихся');
    expect(html).toContain('>Закрыть<');
  });

  it('names a refused pair with the reason as the server gave it, and offers to send only the refused ones again', () => {
    const html = view({ kind: 'finished', result: { total: 3, confirmed: 2, failures: [{ suggestion: LIST[0]!, error: refusal('conflict') }] } });
    expect(html).toContain('Подтверждено 2 из 3');
    expect(html).toContain('Не подтверждены:');
    expect(html).toContain('П: Пояснительная записка · AR · Р: Пояснительная записка, редакция 2 · AR —');
    expect(html).toContain('Повторить для оставшихся (1)');
    // The reason is the application's Russian sentence for the code, and not the server's English one.
    expect(html).not.toContain('A caller-safe sentence in English.');
  });
});
