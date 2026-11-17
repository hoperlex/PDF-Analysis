/**
 * «Предложения» rendered (`W60-OPT-PROPOSALS-01`): the set chooser, the passes with their
 * counts by decision, the proposals with their provenance, both exact prices and the saving
 * only where it is stated, the controls each role is given, and every refusal in Russian.
 */

import { QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  decideOptimisationProposal: vi.fn(),
}));

import { OPTIMISATION_MOVED_TO, OptimisationPage } from '@/_pages/optimisation';
import { CARRYOVER_REFUSAL_TEXT, carrySources } from '@/entities/optimisation-proposal';
import { CarryOverProposalDecisionsView } from '@/features/carry-over-proposal-decisions';
import {
  PROPOSAL_IMPORT_REFUSAL_LABELS,
  ImportProposalDecisionsView,
  importProposalFailure,
} from '@/features/import-proposal-decisions';
import {
  EXPORT_CSV_LABEL,
  EXPORT_XLSX_LABEL,
  ExportProposalsView,
  OptimisationProposals,
  PassList,
  ProposalCard,
  ProposalHistoryView,
  ProposalListView,
  classifiedDocumentSets,
} from '@/widgets/optimisation-proposals';
import { ApiError, decideOptimisationProposal, queryKeys } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import type { ProposalDecisionImportRefusal } from '@/shared/api';
import { ProposalDecisionForm, ProposalDecisionFormView } from '@/features/decide-optimisation-proposal';

import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import { newClient, renderScreen } from '../screens/harness';
import {
  AR_DOCUMENT_UID,
  DOOR_PROPOSAL,
  OLDER_PASS_ID,
  PASS_ID,
  PROPOSALS_PROJECT_UID,
  arVersion,
  carryOverShapes,
  decision,
  otherSectionVersion,
  pass,
  proposal,
  proposalPage,
  proposalShapes,
  seedLoadedProposals,
  seedOlderPassProposals,
  SHEET_URL,
  unclassifiedVersion,
} from './fixtures';

function rendered(name: string): string {
  const shape = [...proposalShapes(), ...carryOverShapes()].find((entry) => entry.name === name);
  if (shape === undefined) throw new Error(`no shape ${name}`);
  const client = newClient();
  shape.seedClient?.(client);
  return renderScreen(client, shape.make());
}

describe('the sets', () => {
  it('offers every set whose current version an expert confirmed, whatever the section', () => {
    expect(classifiedDocumentSets([arVersion(), otherSectionVersion(), unclassifiedVersion()])).toEqual([
      arVersion(),
      otherSectionVersion(),
    ]);
  });

  it('names the section of each set it offers', () => {
    const markup = rendered('proposals-set-chooser');
    expect(markup).toContain('Комплект АР — версия 2, раздел АР');
    expect(markup).toContain('Комплект АР, корпус 2 — версия 2, раздел АР');
    const loaded = rendered('proposals-loaded');
    expect(loaded).toContain('Комплект КЖ — версия 2, раздел КЖ');
  });

  it('says where a section is confirmed when there is none, and that the list is partial', () => {
    const markup = rendered('proposals-no-classified-sets');
    expect(markup).toContain('В объекте нет комплектов с подтверждённым разделом');
    expect(markup).toContain('Подтвердите раздел на экране версии');
    expect(markup).not.toContain('раздела АР');
    expect(rendered('proposals-set-chooser')).toContain('Предложены комплекты первой страницы');
    expect(rendered('proposals-set-chooser')).toContain('Комплект АР, корпус 2 — версия 2');
  });
});

describe('the loaded section for an expert', () => {
  const markup = rendered('proposals-loaded');

  it('offers the passes and opens the newest, with the proposals’ own counts (`UIP-S09-04`: in the panel of «Проход от … ▾»)', () => {
    expect(markup).toContain('data-pass-count="2"');
    expect(markup).toContain('data-optimisation-pass="opp_01J9ZQ8K7NHVXW3T2R5M6P4Q8N"');
    expect(markup).toContain('data-decision-count="pending"');
    expect(markup).toContain('не решено: <strong>1</strong>');
    expect(markup).toContain('на доработку: <strong>1</strong>');
    expect(markup).toContain('не смешиваются со счётчиками замечаний');
  });

  it('opens on the table, with the link to the cards (`UIP-S09-01`)', () => {
    expect(markup).toContain('data-proposal-table');
    expect(markup).not.toContain('<article');
    expect(markup).toContain('data-proposal-layout="table"');
    expect(markup).toContain('Показать карточками');
    // The rows stand by verdict, and each says its own number and state: the first pass of the seed holds one waiting and one for revision.
    const rows = [...markup.matchAll(/<tr data-proposal="[^"]+" data-proposal-ordinal="(\d+)" data-decision="([^"]+)">/g)].map(
      (row) => `${row[1]}:${row[2]}`,
    );
    expect(rows).toEqual(['2:pending', '1:revise']);
  });

  it('shows the provenance, both exact prices and the saving where it is stated', () => {
    expect(markup).toContain('страница 2, лист 10, строки 3–4, позиция 1');
    expect(markup).toContain('25 000 руб.');
    expect(markup).toContain('21 000,5 руб.');
    expect(markup).toContain('Экономия: 17 998 руб.');
    expect(markup).toContain('Поставщик: Кнауф Гипс');
  });

  it('says a saving that cannot be computed is not computed, and shows no zero for it', () => {
    expect(markup).toContain('Экономия не рассчитана: в спецификации количество не записано числом.');
    expect(markup).toContain('«-» (не число)');
    expect(markup).toContain('Поставщик: не указан');
    expect(markup).not.toContain('Экономия: 0');
  });

  it('gives an expert the start, the decision field of each row and the CSV, and the current decision', () => {
    expect(markup).toContain('Запустить проход');
    // `UIP-S09-03`: ✓ and ✕ and the one-line «Причина» of the entity's field, «На доработку» in the menu «⋯».
    expect(markup.match(/data-intent="accept"/g)).toHaveLength(2);
    expect(markup.match(/data-intent="reject"/g)).toHaveLength(2);
    expect(markup.match(/data-decision-reason=""/g)).toHaveLength(2);
    expect(markup).toContain('role="menuitem" tabindex="-1">На доработку</button>');
    expect(markup).toContain('data-proposal-decision=');
    expect(markup).toContain('Выгрузить CSV предложений');
    expect(markup).toContain('Решение: <strong>на доработку</strong>, Петрова А.');
    expect(markup).toContain('Уточнить марку двери у поставщика.');
  });

  it('reads the history only when it is opened', () => {
    expect(markup).toContain('История решений');
    expect(markup).not.toContain('data-proposal-history');
  });
});

describe('the same section for an administrator', () => {
  const markup = rendered('proposals-loaded-admin');

  it('reads everything and decides nothing', () => {
    expect(markup).toContain('data-proposal="opr_01J9ZQ8K7NHVXW3T2R5M6P4Q8Q"');
    expect(markup).toContain('Выгрузить CSV предложений');
    expect(markup).toContain('Запустить проход может эксперт');
    expect(markup).not.toContain('Запустить проход</button>');
    expect(markup).not.toContain('data-proposal-decision=');
    expect(markup).not.toContain('data-decision-control');
    expect(markup).not.toContain('На доработку</button>');
    expect(markup).not.toContain('aria-label="Принять"');
  });
});

describe('the other states', () => {
  it('says nothing yet, an empty pass and a filter that admits nothing', () => {
    expect(rendered('proposals-no-passes')).toContain('Проходов по этому комплекту ещё не было');
    const empty = rendered('proposals-empty-pass');
    expect(empty).toContain('В этом проходе нет предложений');
    expect(empty).toContain('не нашлось более дешёвой позиции');
    expect(rendered('proposals-filter-admits-nothing')).toContain('Нет предложений в выбранном состоянии');
  });

  it('says every refused read in Russian with its correlation id', () => {
    for (const [name, sentence] of [
      ['proposals-documents-refused', 'Документы объекта не прочитаны'],
      ['proposals-passes-refused', 'Проходы не прочитаны'],
      ['proposals-pass-refused', 'Предложения не прочитаны'],
      ['proposals-history-refused', 'История решений не прочитана'],
      ['proposals-export-refused', 'Файл не выгружен'],
    ] as const) {
      const markup = rendered(name);
      expect(markup, name).toContain(sentence);
    }
    expect(rendered('proposals-pass-refused')).toContain('0f0e9d8c-7b6a-4948-b726-150413021100');
  });

  it('marks the state of every proposal by its current decision', () => {
    for (const state of ['pending', 'accept', 'reject', 'revise'] as const) {
      expect(rendered(`proposal-state-${state}`)).toContain(`data-decision="${state}"`);
    }
  });

  it('pages with Назад and Далее, and disables what is not there', () => {
    const second = rendered('proposals-second-page');
    expect(second).toContain('Показано 21–21 из 22.');
    expect(second).toContain('data-proposal-paging="20-end"');
  });
});

const noop = (): void => undefined;

describe('the decision field (`UIP-S09-03`)', () => {
  /** The opening tag of the button of this intent, as the markup draws it. */
  function buttonOf(markup: string, intent: 'accept' | 'reject'): string {
    const found = markup.match(new RegExp(`<button[^>]*data-intent="${intent}"[^>]*>`));
    if (found === null) throw new Error(`no ${intent} button in ${markup}`);
    return found[0];
  }
  const items = (markup: string): string[] => [...markup.matchAll(/<button[^>]*role="menuitem"[^>]*>([^<]*)<\/button>/g)].map((item) => item[1] ?? '');

  it('is the entity’s field: ✓ green, ✕ red and a one-line «Причина», with «⋯» after them, and no second field of comment', () => {
    const markup = rendered('decision-form-idle');
    expect(markup).toContain('data-decision-control=""');
    expect(buttonOf(markup, 'accept')).toContain('aria-label="Принять"');
    expect(buttonOf(markup, 'reject')).toContain('aria-label="Отклонить"');
    expect(markup).toMatch(/<input[^>]*aria-label="Причина"[^>]*placeholder="Причина"/);
    expect(markup).toMatch(/<button[^>]*aria-haspopup="menu"[^>]*aria-label="Другие решения"[^>]*><span aria-hidden="true">⋯<\/span><\/button>/);
    expect(markup.indexOf('data-intent="reject"')).toBeLessThan(markup.indexOf('aria-haspopup="menu"'));
    expect(markup).not.toContain('<textarea');
    expect(markup).not.toContain('Комментарий к решению');
    expect(markup).not.toContain('data-revise-hint');
    expect(markup).toContain(`data-proposal-decision="${DOOR_PROPOSAL}"`);
  });

  it('puts «На доработку» in the menu, and «Снять решение» there only while a decision is in force', () => {
    expect(items(rendered('decision-form-idle'))).toEqual(['На доработку']);
    expect(items(rendered('decision-form-withdrawn'))).toEqual(['На доработку']);
    expect(items(rendered('decision-form-repeat-blocked'))).toEqual(['На доработку', 'Снять решение']);
    expect(items(rendered('decision-form-rejected'))).toEqual(['На доработку', 'Снять решение']);
  });

  it('does not offer a revision that would repeat the one in force, and offers the withdrawal instead', () => {
    expect(items(rendered('decision-form-revise-repeat'))).toEqual(['Снять решение']);
    // Another reason is another decision.
    const other = renderScreen(newClient(), createElement(ProposalDecisionFormView, {
      proposalId: DOOR_PROPOSAL, current: decision(), reason: 'Другая причина', sending: null, note: null, onReason: noop, onDecide: noop,
    }));
    expect(items(other)).toEqual(['На доработку', 'Снять решение']);
  });

  it('holds the verdict in force and a press on its way, and never the verdicts that are no decision', () => {
    const accepted = rendered('decision-form-repeat-blocked');
    expect(buttonOf(accepted, 'accept')).toContain('disabled');
    expect(buttonOf(accepted, 'accept')).toContain('aria-pressed="true"');
    expect(buttonOf(accepted, 'reject')).not.toContain('disabled');
    const rejected = rendered('decision-form-rejected');
    expect(buttonOf(rejected, 'reject')).toContain('disabled');
    expect(buttonOf(rejected, 'accept')).not.toContain('disabled');
    for (const name of ['decision-form-idle', 'decision-form-withdrawn']) {
      expect(buttonOf(rendered(name), 'accept'), name).not.toContain('disabled');
      expect(buttonOf(rendered(name), 'reject'), name).not.toContain('disabled');
    }
    // Sent back for revision holds neither ✓ nor ✕: the proposal is decided again from there.
    const revise = renderScreen(newClient(), createElement(ProposalDecisionFormView, {
      proposalId: DOOR_PROPOSAL, current: decision(), reason: '', sending: null, note: null, onReason: noop, onDecide: noop,
    }));
    expect(buttonOf(revise, 'accept')).not.toContain('disabled');
    expect(buttonOf(revise, 'reject')).not.toContain('disabled');
    const sending = rendered('decision-form-sending-accept');
    expect(buttonOf(sending, 'accept')).toContain('disabled');
    expect(buttonOf(sending, 'reject')).toContain('disabled');
    expect(sending).toContain('aria-busy="true"');
    expect(sending).not.toContain('inert');
  });

  it('holds the whole control while a revision or a withdrawal is on its way', () => {
    expect(rendered('decision-form-sending-revise')).toMatch(/<div[^>]*data-proposal-decision="[^"]+"[^>]*inert=""|<div[^>]*inert=""[^>]*data-proposal-decision=/);
    expect(rendered('decision-form-idle')).not.toContain('inert');
  });

  it('says in the row what the last press did: a refusal before sending, the server’s reason and «Записано»', () => {
    const refused = rendered('decision-form-refused');
    expect(refused).toMatch(/role="alert"[^>]*>Для «На доработку» нужна причина</);
    // The journey reads the refusal as a state of the row (`data-revise-hint`), present for this refusal and for no other line.
    expect(refused).toMatch(/<div[^>]*data-proposal-decision="[^"]+"[^>]*data-revise-hint=""/);
    for (const name of ['decision-form-idle', 'decision-form-refused-nothing-to-revoke', 'decision-form-recorded']) {
      expect(rendered(name), name).not.toContain('data-revise-hint');
    }
    expect(rendered('decision-form-refused-nothing-to-revoke')).toContain('Снимать нечего');
    expect(rendered('decision-form-recorded')).toMatch(/role="status"[^>]*>Записано</);
    expect(rendered('decision-form-idle')).not.toMatch(/role="(alert|status)"/);
  });

  it('keeps the text the expert is about to send in the field the entity owns', () => {
    expect(rendered('decision-form-revise-ready')).not.toContain('Для «На доработку» нужна причина');
  });
});

/**
 * `UIP-S09-03`: the field mounted and pressed the way an expert presses it -- the real container over the real hook and React Query,
 * the entity's real field and shared menu, typed into and pressed; only the transport, `decideOptimisationProposal`, is a stub, so
 * each case reads the request a browser would put on the wire. The harness has no event propagation: typing is the field's own
 * `onChange` and then the wrapper's, which in a browser receives the same event by bubbling.
 */
describe('a press in the field of a row (`UIP-S09-03`)', () => {
  interface DomNode {
    readonly nodeName: string;
    readonly childNodes: readonly DomNode[];
  }
  type Props = { value?: string; onChange?: (event: unknown) => void };

  let live: LiveRender | null = null;
  let host: DomNode | null = null;
  let written = 0;

  const descendants = (node: DomNode): DomNode[] => node.childNodes.flatMap((child) => [child, ...descendants(child)]);
  const propsOf = (node: DomNode): Props => {
    const key = Object.keys(node).find((name) => name.startsWith('__reactProps$'));
    return (node as unknown as Record<string, Props>)[key as string] as Props;
  };
  const field = (): Props => {
    const inputs = descendants(host as DomNode).filter((node) => node.nodeName === 'input');
    expect(inputs).toHaveLength(1);
    return propsOf(inputs[0] as DomNode);
  };
  /** The wrapper that listens for the field's change events: the `div` that carries the proposal's marker. */
  const wrapper = (): Props => {
    const found = descendants(host as DomNode).filter((node) => {
      const key = Object.keys(node).find((name) => name.startsWith('__reactProps$'));
      return key !== undefined && (node as unknown as Record<string, Record<string, unknown>>)[key]?.['data-proposal-decision'] !== undefined;
    });
    expect(found).toHaveLength(1);
    return propsOf(found[0] as DomNode);
  };
  async function type(text: string): Promise<void> {
    await (live as LiveRender).settle(() => {
      const event = { type: 'change', target: { value: text }, currentTarget: { value: text } };
      (field().onChange as (event: unknown) => void)(event);
      (wrapper().onChange as (event: unknown) => void)(event);
    });
  }
  const shown = (): string => field().value ?? '';
  const sent = () =>
    vi.mocked(decideOptimisationProposal).mock.calls.map(([call]) => {
      const { path, body, idempotencyKey } = call as unknown as {
        path: { optimisation_proposal_id: string }; body: { verdict: string; comment?: string }; idempotencyKey: string;
      };
      return { id: path.optimisation_proposal_id, body, idempotencyKey };
    });

  async function mount(subject = proposal({ current_verdict: 'pending', current_decision: null })): Promise<LiveRender> {
    live = await mountLive(
      createElement(
        QueryClientProvider,
        { client: newClient() },
        createElement(
          'div',
          { ref: (node: unknown) => { host = node as DomNode | null; } },
          createElement(ProposalDecisionForm, { passId: PASS_ID, proposal: subject }),
        ),
      ),
    );
    return live;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    written = 0;
    vi.mocked(decideOptimisationProposal).mockImplementation((async (call: { body: { verdict: string; comment?: string } }) => {
      written += 1;
      return {
        data: {
          decision: decision({ proposal_decision_id: `opd_01J9ZQ8K7NHVXW3T2R5M6P4Q${String(written).padStart(2, '0')}`, verdict: call.body.verdict as never }),
          proposal: proposal(),
        },
      };
    }) as never);
  });

  afterEach(async () => {
    await live?.unmount();
    live = null;
    host = null;
  });

  it('sends ✓ with no reason as the verdict alone, and with a reason as the same event’s comment, trimmed', async () => {
    await mount();
    expect(await (live as LiveRender).press('✓')).toBe(true);
    expect(sent()).toHaveLength(1);
    expect(sent()[0]?.body).toEqual({ verdict: 'accept' });
    expect(Object.keys(sent()[0]?.body ?? {})).toEqual(['verdict']);
    await live?.unmount();
    await mount();
    await type('  Марка подходит  ');
    expect(await (live as LiveRender).press('✓')).toBe(true);
    expect(sent()[1]?.body).toEqual({ verdict: 'accept', comment: 'Марка подходит' });
    expect(sent()).toHaveLength(2);
  });

  it('sends ✕ the same way: no reason is allowed, and a reason goes in the same event', async () => {
    await mount();
    expect(await (live as LiveRender).press('✕')).toBe(true);
    expect(sent()[0]?.body).toEqual({ verdict: 'reject' });
    await type('Не наш поставщик');
    expect(await (live as LiveRender).press('✕')).toBe(true);
    expect(sent()[1]?.body).toEqual({ verdict: 'reject', comment: 'Не наш поставщик' });
  });

  it('refuses «На доработку» with no reason, in the row, and sends nothing; a blank reason is none', async () => {
    await mount();
    expect(await (live as LiveRender).press('На доработку')).toBe(true);
    expect(sent()).toEqual([]);
    expect((live as LiveRender).markup()).toContain('Для «На доработку» нужна причина');
    await type('   ');
    expect(await (live as LiveRender).press('На доработку')).toBe(true);
    expect(sent()).toEqual([]);
    expect((live as LiveRender).markup()).toContain('Для «На доработку» нужна причина');
  });

  it('takes the refusal away when the expert writes the reason, and then sends «На доработку» with it', async () => {
    await mount();
    await (live as LiveRender).press('На доработку');
    expect((live as LiveRender).markup()).toContain('Для «На доработку» нужна причина');
    expect((live as LiveRender).markup()).toContain('data-revise-hint=""');
    await type('Заменить марку.');
    expect((live as LiveRender).markup()).not.toContain('Для «На доработку» нужна причина');
    expect((live as LiveRender).markup()).not.toContain('data-revise-hint');
    expect(await (live as LiveRender).press('На доработку')).toBe(true);
    expect(sent()).toHaveLength(1);
    expect(sent()[0]?.body).toEqual({ verdict: 'revise', comment: 'Заменить марку.' });
  });

  it('empties the field and says «Записано» once the press is written, and not before', async () => {
    await mount();
    await type('Марка подходит');
    expect(shown()).toBe('Марка подходит');
    await (live as LiveRender).press('✓');
    expect(shown()).toBe('');
    expect((live as LiveRender).markup()).toContain('Записано');
    // The next thing typed is the end of what the last press said.
    await type('Ещё одно');
    expect(shown()).toBe('Ещё одно');
    expect((live as LiveRender).markup()).not.toContain('Записано');
  });

  it('leaves the text where it is when the press fails, says why in the row, and a repeat of it carries the same key', async () => {
    vi.mocked(decideOptimisationProposal).mockRejectedValueOnce(new Error('lost answer'));
    await mount();
    await type('Марка подходит');
    await (live as LiveRender).press('✓');
    expect(shown()).toBe('Марка подходит');
    expect((live as LiveRender).markup()).toContain('Решение не записано.');
    await (live as LiveRender).press('✓');
    expect(sent()).toHaveLength(2);
    expect(sent()[1]?.idempotencyKey).toBe(sent()[0]?.idempotencyKey);
    expect(shown()).toBe('');
  });

  it('withdraws a decision in force with «Снять решение», with the reason when there is one, and offers it only then', async () => {
    await mount(proposal({ current_verdict: 'accept', current_decision: decision({ verdict: 'accept', comment: null }) }));
    expect((live as LiveRender).count('Снять решение')).toBe(1);
    expect(await (live as LiveRender).press('Снять решение')).toBe(true);
    expect(sent()[0]?.body).toEqual({ verdict: 'revoke' });
    await type('Ошибся');
    await (live as LiveRender).press('Снять решение');
    expect(sent()[1]?.body).toEqual({ verdict: 'revoke', comment: 'Ошибся' });
    await live?.unmount();
    await mount();
    expect((live as LiveRender).count('Снять решение')).toBe(0);
    await live?.unmount();
    await mount(proposal({ current_verdict: 'pending', current_decision: decision({ verdict: 'revoke', comment: null }) }));
    expect((live as LiveRender).count('Снять решение')).toBe(0);
  });

  it('does not offer «На доработку» again with the reason it already carries, and offers it with another', async () => {
    await mount(proposal({ current_verdict: 'revise', current_decision: decision({ verdict: 'revise', comment: 'Заменить марку.' }) }));
    expect((live as LiveRender).count('На доработку')).toBe(1);
    await type('Заменить марку.');
    expect((live as LiveRender).count('На доработку')).toBe(0);
    await type('Заменить производителя.');
    expect((live as LiveRender).count('На доработку')).toBe(1);
  });

  it('holds ✓ while the verdict is in force, so a double press cannot append a second identical event', async () => {
    await mount(proposal({ current_verdict: 'accept', current_decision: decision({ verdict: 'accept', comment: null }) }));
    expect(await (live as LiveRender).press('✓')).toBe(false);
    expect(sent()).toEqual([]);
  });
});

describe('a withdrawn decision (`UI-B-12`)', () => {
  it('is said as withdrawn, by whom and when, and the proposal is «не решено» again', () => {
    const withdrawn = decision({ verdict: 'revoke', comment: 'Ошибся, пересмотрю.' });
    const markup = renderScreen(newClient(), createElement(ProposalCard, {
      proposal: proposal({ current_verdict: 'pending', current_decision: withdrawn }), controls: null, history: null,
    }));
    expect(markup).toContain('data-decision="pending"');
    expect(markup).toContain('решение снято');
    expect(markup).toContain('Петрова А.');
    expect(markup).toContain('Ошибся, пересмотрю.');
  });

  it('keeps the withdrawal in the history as an event, after the decision it withdrew', () => {
    const markup = renderScreen(newClient(), createElement(ProposalHistoryView, {
      items: [decision({ verdict: 'accept', comment: null }), decision({ proposal_decision_id: 'opd_01J9ZQ8K7NHVXW3T2R5M6P4Q8W', verdict: 'revoke', comment: null })],
    }));
    expect(markup).toContain('data-proposal-history="2"');
    expect(markup.indexOf('Принять')).toBeLessThan(markup.indexOf('Снять решение'));
  });
});

describe('the retired /optimisation address', () => {
  it('points to the projects list and to the project’s tab, with no number and no promise of more', () => {
    expect(OPTIMISATION_MOVED_TO).toBe('/projects');
    const markup = renderScreen(newClient(), createElement(OptimisationPage));
    expect(markup).toContain('href="/projects"');
    expect(markup).toContain('вкладке объекта');
    expect(markup).not.toMatch(/пока недоступен|ещё не готов/);
  });
});

describe('«Открыть лист» (`UI-B-09`)', () => {
  it('opens the version’s PDF on the proposal’s page in a new tab, once the PDF is fetched', () => {
    const markup = rendered('proposals-sheet-ready');
    expect(markup).toContain(`href="${SHEET_URL}#page=2"`);
    expect(markup).toContain('target="_blank"');
    expect(markup).toContain('rel="noopener noreferrer"');
    expect(markup).toContain('data-open-sheet="2"');
    expect(markup.match(/Открыть лист ↗/g)?.length).toBe(2);
    expect(markup).not.toContain('data-proposal-sheet');
  });

  it('offers nothing where no PDF is given, as before', () => {
    expect(rendered('proposals-loaded-admin')).not.toContain('data-open-sheet');
    expect(rendered('proposals-second-page')).not.toContain('Открыть лист');
  });

  it('says the PDF is on its way, and draws no link meanwhile', () => {
    const markup = rendered('proposals-sheet-loading');
    expect(markup).toContain('data-proposal-sheet="loading"');
    expect(markup).toContain('Загружается PDF версии');
    expect(markup).not.toContain('data-open-sheet');
  });

  it('says a refused PDF in Russian with its correlation id, and draws no link', () => {
    const markup = rendered('proposals-sheet-refused');
    expect(markup).toContain('PDF версии не получен: ссылок «Открыть лист» нет');
    expect(markup).toContain('PDF версии недоступен.');
    expect(markup).toContain('0f0e9d8c-7b6a-4948-b726-150413021100');
    expect(markup).not.toContain('data-open-sheet');
  });

  it('draws no link for a proposal that names no page a reader can open', () => {
    const named = renderScreen(newClient(), createElement(ProposalCard, {
      proposal: proposal(), controls: null, history: null, documentUrl: SHEET_URL,
    }));
    expect(named).toContain('data-open-sheet="2"');
    for (const page of [0, -1, 1.5]) {
      const markup = renderScreen(newClient(), createElement(ProposalCard, {
        proposal: proposal({ page_number: page }), controls: null, history: null, documentUrl: SHEET_URL,
      }));
      expect(markup, `page ${page}`).not.toContain('data-open-sheet');
    }
  });
});

/**
 * `UIP-S09-02`: the top row over the table. At the left the plates of the decisions with the pass's counts and «Всего: N»; at the
 * right «Файлы ▾» (the shared menu), «Загрузить решения» and «Перенести решения из V#», which are the features' own controls drawn
 * where they were drawn before but in one row. No paragraph of buttons and no caption stands over it, and what a file or a load
 * refuses stands under it in the words it always had.
 */
describe('the top row of the tab (`UIP-S09-02`)', () => {
  const noop = (): void => undefined;
  const loaded = rendered('proposals-loaded');
  const CORRELATION = '0f0e9d8c-7b6a-4948-b726-150413021100';

  /** The text of each button of the plates, without the separators the server render may put between text nodes. */
  const plates = (markup: string): string[] => {
    const nav = /<nav[^>]*data-decision-filter="[^"]*"[^>]*>([\s\S]*?)<\/nav>/.exec(markup)?.[1] ?? '';
    return [...nav.matchAll(/<button[^>]*>([\s\S]*?)<\/button>/g)].map((button) => (button[1] ?? '').replace(/<!-- -->/g, ''));
  };

  const earlier = [
    pass({ version_ordinal: 2 }),
    pass({ optimisation_pass_id: OLDER_PASS_ID, version_ordinal: 1, decision_counts: { pending: 2, accept: 3, reject: 1, revise: 2 } }),
  ];
  const carryOver = (failure: string | null = null) =>
    createElement(CarryOverProposalDecisionsView, {
      sources: carrySources(earlier, earlier[0] as never),
      confirming: null, pending: false, report: null, failure, onAsk: noop, onConfirm: noop, onCancel: noop,
    });
  const imported = (failure: string | null = null, report: Parameters<typeof ImportProposalDecisionsView>[0]['report'] = null) =>
    createElement(ImportProposalDecisionsView, { pending: false, report, failure, onChoose: noop });
  const row = (props: Record<string, unknown> = {}) =>
    renderScreen(newClient(), createElement(ExportProposalsView, { pending: false, failure: null, onDownload: noop, ...props }));

  it('shows the plates of the decisions with the pass’s counts, then «Всего: N», at the left of the row', () => {
    // The seed's pass holds two proposals: one waiting, one for revision.
    expect(plates(loaded)).toEqual(['Все (2)', 'не решено (1)', 'принято (0)', 'отклонено (0)', 'на доработку (1)']);
    expect(loaded).toMatch(/data-proposal-total="2"[^>]*>Всего: (<!-- -->)?2</);
    const at = (marker: string) => loaded.indexOf(marker);
    expect(at('data-decision-filter')).toBeGreaterThan(-1);
    expect(at('data-proposal-total')).toBeGreaterThan(at('data-decision-filter'));
    expect(at('data-proposal-layout=')).toBeGreaterThan(at('data-proposal-total'));
    expect(at('data-proposals-export')).toBeGreaterThan(at('data-proposal-layout='));
    expect(at('data-proposal-table')).toBeGreaterThan(at('data-proposals-export'));
  });

  it('counts the pass, not the filtered page: the plates and «Всего» are the pass’s under a filter', () => {
    const filtered = renderScreen(
      newClient(),
      createElement(ProposalListView, {
        page: proposalPage({ decision: 'accept', items: [], total: 0 }),
        canDecide: true,
        onDecision: noop,
        onPage: noop,
      }),
    );
    expect(filtered).toMatch(/data-proposal-total="2"/);
    expect(plates(filtered)).toEqual(['Все (2)', 'не решено (1)', 'принято (0)', 'отклонено (0)', 'на доработку (1)']);
    expect(filtered).toMatch(/data-decision-filter="accept"/);
  });

  it('offers «Файлы ▾» as the shared menu, and each file as an item of it, to an expert and to an administrator', () => {
    for (const markup of [loaded, rendered('proposals-loaded-admin')]) {
      expect(markup).toMatch(/<button[^>]*aria-haspopup="menu"[^>]*aria-label="Файлы"[^>]*>Файлы <span aria-hidden="true">▾<\/span><\/button>/);
      expect(markup).toContain(`role="menuitem" tabindex="-1">${EXPORT_CSV_LABEL}</button>`);
      expect(markup).toContain(`role="menuitem" tabindex="-1">${EXPORT_XLSX_LABEL}</button>`);
    }
  });

  it('draws no paragraph of buttons and no file or load over the plates', () => {
    expect(loaded).not.toMatch(/<p[^>]*>\s*<button[^>]*>Выгрузить/);
    const before = loaded.slice(0, loaded.indexOf('data-decision-filter'));
    expect(before).not.toContain('Выгрузить');
    expect(before).not.toContain('Загрузить решения');
  });

  it('stands the load and the carrying over after the files, in the one block of the row, for an expert', () => {
    const markup = row({ onDownloadXlsx: noop, importControl: imported(), carryOverControl: carryOver() });
    const at = (marker: string) => markup.indexOf(marker);
    expect(at('data-proposals-files')).toBeGreaterThan(-1);
    expect(at('data-proposal-decision-import')).toBeGreaterThan(at('data-proposals-files'));
    expect(at('data-proposal-decision-carryover')).toBeGreaterThan(at('data-proposal-decision-import'));
    expect(markup).toContain('Загрузить решения');
    expect(markup).toContain('Перенести решения из V1');
    const block = /<div class="[^"]*tools[^"]*" data-proposals-export="">([\s\S]*)<\/div>$/.exec(markup);
    expect(block?.[1], 'the row is one block').toContain('data-proposal-decision-carryover');
  });

  it('offers a reader who does not decide the files and no load', () => {
    const admin = rendered('proposals-loaded-admin');
    expect(admin).toContain(EXPORT_CSV_LABEL);
    expect(admin).not.toContain('Загрузить решения');
    expect(admin).not.toContain('Перенести решения');
  });

  it('says a refused file under the row, in the words it always had, with the server’s reason and its correlation id', () => {
    const markup = row({ failure: { detail: 'Файл не удалось выгрузить.', correlationId: CORRELATION } });
    expect(markup.indexOf('Файл не выгружен')).toBeGreaterThan(markup.indexOf('data-proposals-files'));
    expect(markup).toContain('Файл не удалось выгрузить.');
    expect(markup).toContain(CORRELATION);
    expect(markup).toContain('data-proposals-export-refusal');
    expect(row()).not.toContain('Файл не выгружен');
  });

  it('says every refused row of a load, each in its own words, inside the row’s block after the button', () => {
    const reasons = Object.keys(PROPOSAL_IMPORT_REFUSAL_LABELS) as ProposalDecisionImportRefusal[];
    const rows = reasons.map((reason, index) => ({ row: index + 2, outcome: 'refused' as const, reason }));
    const markup = row({
      importControl: imported(null, {
        optimisation_pass_id: 'opp_01J9ZQ8K7NHVXW3T2R5M6P4Q8N', recorded: 0, unchanged: 0, refused: rows.length, rows,
      }),
    });
    const upload = markup.slice(markup.indexOf('data-proposal-decision-import'));
    for (const [index, reason] of reasons.entries()) {
      const sentence = `Строка ${index + 2}: ${PROPOSAL_IMPORT_REFUSAL_LABELS[reason]}`;
      expect(upload, reason).toContain(sentence);
      expect(upload.indexOf(sentence), reason).toBeGreaterThan(upload.indexOf('Загрузить решения'));
    }
    expect(upload).toContain(`отклонено ${rows.length}`);
  });

  it('says each refusal of a whole file, and each refusal of the carrying over, in a line of the row', () => {
    const refuse = (constraint: string) =>
      new ApiError(422, {
        contract_version: '1.59.0', error_code: 'validation_failed', message: 'x',
        correlation_id: 'cid-1', retryable: false, details: { field: 'file', constraint },
      }, 'cid-1');
    for (const constraint of ['not_our_export', 'unreadable', 'too_large', 'too_many_rows']) {
      const sentence = importProposalFailure(refuse(constraint));
      const markup = row({ importControl: imported(sentence) });
      expect(markup, constraint).toContain(`role="alert">${sentence}</p>`);
    }
    for (const [reason, sentence] of Object.entries(CARRYOVER_REFUSAL_TEXT)) {
      expect(row({ carryOverControl: carryOver(sentence) }), reason).toContain(`role="alert">${sentence}</p>`);
    }
  });

  it('hands the press on a file to its handler, and ignores it while a file is being made, saying so', async () => {
    const csv = vi.fn();
    const xlsx = vi.fn();
    const live = await mountLive(createElement(ExportProposalsView, { pending: false, failure: null, onDownload: csv, onDownloadXlsx: xlsx }));
    expect(await live.press(EXPORT_CSV_LABEL)).toBe(true);
    expect(await live.press(EXPORT_XLSX_LABEL)).toBe(true);
    expect([csv.mock.calls.length, xlsx.mock.calls.length]).toEqual([1, 1]);
    expect(live.markup()).not.toContain('data-proposals-export-state');
    await live.update(createElement(ExportProposalsView, { pending: true, failure: null, onDownload: csv, onDownloadXlsx: xlsx }));
    await live.press(EXPORT_CSV_LABEL);
    await live.press(EXPORT_XLSX_LABEL);
    expect([csv.mock.calls.length, xlsx.mock.calls.length]).toEqual([1, 1]);
    expect(live.markup()).toContain('data-proposals-export-state="pending"');
    expect(live.markup()).toContain('Готовлю файл…');
    await live.unmount();
  });

  it('offers the workbook only where it is given', () => {
    const plain = row();
    expect(plain).toContain(EXPORT_CSV_LABEL);
    expect(plain).not.toContain(EXPORT_XLSX_LABEL);
  });
});

/**
 * `UIP-S09-04`: «Проход от ДД.ММ.ГГГГ ЧЧ:ММ ▾» -- one element at the right of the top row in place of the list «Проходы комплекта» and
 * the disclosure «Сведения о проходе». It chooses the pass (with the number of proposals and the counts of decisions of each) and opens
 * the facts of the open one; a set with one pass shows that pass and its facts; the address `?pass=` works as it did, and a pass it
 * names that the set does not have is said.
 */
describe('«Проход от … ▾» (`UIP-S09-04`)', () => {
  const noop = (): void => undefined;
  const NEWEST = formatInstant(pass().started_at);
  const OLDER = formatInstant('2026-10-19T09:00:00Z');
  const section = (props: Record<string, unknown> = {}, seed: (client: ReturnType<typeof newClient>) => void = seedLoadedProposals) => {
    const client = newClient();
    seed(client);
    return renderScreen(client, createElement(OptimisationProposals, { projectUid: PROPOSALS_PROJECT_UID, roles: ['expert'], ...props }));
  };
  /** The pass element's own markup. */
  const element = (markup: string): string => /<details[^>]*data-pass-menu=""[\s\S]*?<\/details>/.exec(markup)?.[0] ?? '';

  it('is one button in the top row, after the files, and says the open pass', () => {
    const markup = rendered('proposals-loaded');
    expect(markup).toContain(`Проход от ${NEWEST}`);
    expect(markup.match(/data-pass-menu=""/g)).toHaveLength(1);
    const at = (marker: string) => markup.indexOf(marker);
    expect(at('data-pass-menu')).toBeGreaterThan(at('data-proposals-files'));
    expect(at('data-pass-menu')).toBeLessThan(at('data-proposal-table'));
    // Inside the one block of the row, which the browser journey waits for.
    const row = /<div class="[^"]*tools[^"]*" data-proposals-export="">([\s\S]*)/.exec(markup)?.[1] ?? '';
    expect(row).toContain('data-pass-menu');
    expect(markup).toMatch(/<summary[^>]*>Проход от [^<]*<span aria-hidden="true">▾<\/span><\/summary>/);
  });

  it('is closed, and the list «Проходы комплекта» and the disclosure «Сведения о проходе» are gone', () => {
    const markup = rendered('proposals-loaded');
    expect(/<details[^>]*data-pass-menu=""[^>]*>/.exec(markup)?.[0]).not.toContain('open');
    expect(markup).not.toContain('Сведения о проходе');
    // The only list of passes is inside the element's panel.
    expect(markup.match(/aria-label="Проходы комплекта"/g)).toHaveLength(1);
    expect(element(markup)).toContain('aria-label="Проходы комплекта"');
  });

  it('lists each pass in the panel with the number of its proposals and the counts of its decisions, the open one pressed', () => {
    const panel = element(rendered('proposals-loaded'));
    expect(panel).toContain('data-pass-count="2"');
    const items = [...panel.matchAll(/<li class="[^"]*"><button[^>]*aria-pressed="(true|false)"[^>]*>Проход от ([^<]*)<\/button><span>([^<]*)<\/span>/g)].map(
      (item) => [item[1], item[2], (item[3] ?? '').replace(/<!-- -->/g, '')],
    );
    expect(items).toEqual([
      ['true', NEWEST, 'предложений — 2; не решено — 1, принято — 0, отклонено — 0, на доработку — 1'],
      ['false', OLDER, 'предложений — 1; не решено — 0, принято — 1, отклонено — 0, на доработку — 0'],
    ]);
  });

  it('opens the facts of the open pass in the same panel: the version, the run, the price list and the vendor list', () => {
    const panel = element(rendered('proposals-loaded'));
    expect(panel).toContain('data-optimisation-pass="opp_01J9ZQ8K7NHVXW3T2R5M6P4Q8N"');
    for (const label of ['Версия комплекта', 'Прогон', 'Прайс-лист', 'Вендор-лист раздела', 'Строки спецификации']) expect(panel, label).toContain(`<dt>${label}</dt>`);
    for (const id of [pass().version_uid, pass().run_id, pass().price_list_id, pass().vendor_list_id]) expect(panel, id).toContain(`<code>${id}</code>`);
    expect(panel).toContain('не решено: <strong>1</strong>');
  });

  it('shows a set’s only pass and its facts, and offers no choice', () => {
    const markup = section({}, (client) => {
      seedLoadedProposals(client);
      client.setQueryData(queryKeys.optimisation.passes(PROPOSALS_PROJECT_UID, AR_DOCUMENT_UID), { items: [pass()] });
    });
    const panel = element(markup);
    expect(panel).toContain('data-pass-count="1"');
    expect(panel).toContain(`Проход от ${NEWEST}`);
    expect(panel).not.toContain('aria-label="Проходы комплекта"');
    expect(panel).not.toContain('aria-pressed');
    expect(panel).toContain(`<code>${pass().run_id}</code>`);
  });

  it('opens the pass the address names, with its own facts and proposals', () => {
    const markup = section({ passId: OLDER_PASS_ID, onPassChange: noop }, (client) => {
      seedLoadedProposals(client);
      seedOlderPassProposals(client);
    });
    expect(markup).not.toContain('data-pass-not-found');
    expect(markup).toMatch(new RegExp(`<summary[^>]*>Проход от ${OLDER.replace('.', '\\.')}`));
    expect(element(markup)).toMatch(new RegExp(`aria-pressed="true"[^>]*>Проход от ${OLDER.replace('.', '\\.')}<`));
    expect(markup).toContain(`data-optimisation-pass="${OLDER_PASS_ID}"`);
    expect(markup).toContain('data-proposal-total="1"');
  });

  it('says a pass of the address that the set does not have, and opens the newest', () => {
    const markup = section({ passId: 'opp_01J9ZQ8K7NHVXW3T2R5M6P4Q9X', onPassChange: noop });
    expect(markup).toContain('data-pass-not-found="opp_01J9ZQ8K7NHVXW3T2R5M6P4Q9X"');
    expect(markup).toMatch(/role="status"[^>]*>Проход из адреса не найден среди проходов этого комплекта: открыт последний\./);
    expect(markup).toContain(`<summary`);
    expect(markup).toContain(`Проход от ${NEWEST}`);
    expect(markup).toContain(`data-optimisation-pass="${PASS_ID}"`);
    // A pass that exists is not reported.
    expect(section({ passId: PASS_ID, onPassChange: noop })).not.toContain('data-pass-not-found');
  });

  it('hands the choice of another pass to the page when its button is pressed', async () => {
    const chosen: string[] = [];
    const live = await mountLive(createElement(PassList, {
      passes: [pass(), pass({ optimisation_pass_id: OLDER_PASS_ID, started_at: '2026-10-19T09:00:00Z', proposal_count: 1 })],
      active: PASS_ID,
      onOpen: (id: string) => chosen.push(id),
    }));
    expect(live.count(`Проход от ${NEWEST}`)).toBe(1);
    expect(await live.press(`Проход от ${OLDER}`)).toBe(true);
    expect(chosen).toEqual([OLDER_PASS_ID]);
    await live.unmount();
  });

  it('stays at the right while the proposals are on their way or refused, so another pass can be chosen, and says nothing for a set with no pass', () => {
    const refused = rendered('proposals-pass-refused');
    expect(refused).toContain('data-pass-menu');
    expect(refused).toContain('Предложения не прочитаны');
    expect(refused.indexOf('data-pass-menu')).toBeLessThan(refused.indexOf('Предложения не прочитаны'));
    expect(refused).not.toContain('data-proposals-export');
    const none = rendered('proposals-no-passes');
    expect(none).toContain('Проходов по этому комплекту ещё не было');
    expect(none).not.toContain('data-pass-menu');
  });
});
