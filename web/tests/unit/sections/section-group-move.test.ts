/**
 * `UIP-S02-07` (owner rulings Г11, Г12-B): moving a document into a group — by dragging its card onto a group, and by «Группа…» in the
 * card's menu «⋯».
 *
 * The harness renders one pass and fires no event (`D-97`, `harness.ts`), so the three layers are held apart. What is decided is pure and stated
 * directly: what a drop asks for, what a choice in the window comes to, what is said of the result, and how the page's state goes from a
 * card picked up to a card moved or refused (`editingReducer`). What is drawn is rendered: the menu and the drag on the cards, the window,
 * the line under the cards, the groups as places to drop. And the handlers the browser calls are read off the elements the components
 * return and called with a stand-in for the event, so the wiring from the browser's event to the page's callback is run, not assumed.
 * The command itself is the hook of `UIP-G-10` (`useSetDocumentGroup`), which this task only calls; a source reading holds that.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { Children, createElement } from 'react';
import type { ReactElement } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { queryKeys } from '@/shared/api';
import type { DocumentVersion } from '@/shared/api';
import { DOCUMENT_PAGE_LIMIT, DocumentCardGrid } from '@/entities/document-version';
import type { DocumentCardGridProps } from '@/entities/document-version';
import {
  EDITING_IDLE, GROUP_DIALOG_CANCEL_LABEL, GROUP_DIALOG_SAVE_LABEL, GROUP_DIALOG_TITLE, GROUP_MENU_ITEM_LABEL, GroupDialog,
  GroupEditingLayer, NEW_GROUP_LABEL, NO_GROUP_LABEL, SectionDetailPage, SectionGroups, dragSourceOf, dropRequest, editingReducer,
  groupDocuments, movedSentence, movingSentence, newGroupProblem, refusedSentence, resolveGroupChoice,
} from '@/_pages/section-detail';
import type { EditingAction, EditingState, GroupDrop } from '@/_pages/section-detail';

import { WEB_ROOT } from '../../guards/lib/repo';
import { newClient, renderWith } from '../screens/harness';
import { PROJECT_UID, classification, otherVersion, page } from './fixtures';

const doc = (suffix: string, group?: string): DocumentVersion =>
  otherVersion(suffix, {
    display_title: `Документ ${suffix}`,
    classification: classification({ section_code: 'AR' }),
    ...(group === undefined ? {} : { group }),
  });

const key = (cursor: string | undefined) =>
  queryKeys.projects.documents(PROJECT_UID, cursor, DOCUMENT_PAGE_LIMIT, 'AR', false, undefined, undefined, 'audit');

const seeded = (items: DocumentVersion[], roles?: string[]) => {
  const client = newClient();
  client.setQueryData(key(undefined), page(items, null));
  if (roles !== undefined) client.setQueryData(queryKeys.account.me(), { roles });
  return client;
};

const renderPage = (client: ReturnType<typeof newClient>) =>
  renderWith(client, createElement(SectionDetailPage, { projectUid: PROJECT_UID, sectionCode: 'AR' }));

const GROUPED = [doc('A', 'Корпус А'), doc('B', 'Корпус Б'), doc('C', 'Корпус А'), doc('D')];

// ------------------------------------------------------------------ what a drop and a choice come to

describe('what dropping a card on a group asks for', () => {
  const source = dragSourceOf(doc('A', 'Корпус А'), 'Документ A');

  it('is the group dropped on, or «Без группы» (null), and nothing when the card is there already', () => {
    expect(dropRequest(source, 'Корпус Б')).toEqual({ group: 'Корпус Б' });
    expect(dropRequest(source, null)).toEqual({ group: null });
    expect(dropRequest(source, 'Корпус А')).toBeNull();
    expect(dropRequest(dragSourceOf(doc('D'), 'Документ D'), null)).toBeNull();
    expect(dropRequest(dragSourceOf(doc('D'), 'Документ D'), 'Корпус А')).toEqual({ group: 'Корпус А' });
  });

  it('takes the document by its identity and its group as the server holds it', () => {
    expect(source).toEqual({ documentUid: doc('A').document_uid, title: 'Документ A', group: 'Корпус А' });
    expect(dragSourceOf(doc('A', '  '), 'Документ A').group).toBeNull();
  });
});

describe('what the window «Группа…» comes to', () => {
  it('sends the group picked, or null for «Без группы», and sends nothing when the document is in it already', () => {
    expect(resolveGroupChoice({ kind: 'group', name: 'Корпус Б' }, '', 'Корпус А')).toEqual({ ok: true, group: 'Корпус Б', unchanged: false });
    expect(resolveGroupChoice({ kind: 'group', name: 'Корпус А' }, '', 'Корпус А')).toEqual({ ok: true, group: 'Корпус А', unchanged: true });
    expect(resolveGroupChoice({ kind: 'none' }, '', 'Корпус А')).toEqual({ ok: true, group: null, unchanged: false });
    expect(resolveGroupChoice({ kind: 'none' }, '', null)).toEqual({ ok: true, group: null, unchanged: true });
  });

  it('sends a new name trimmed, and says why one that cannot be stored is refused', () => {
    expect(resolveGroupChoice({ kind: 'new' }, '  Территория  ', null)).toEqual({ ok: true, group: 'Территория', unchanged: false });
    expect(resolveGroupChoice({ kind: 'new' }, 'Корпус А', 'Корпус А')).toEqual({ ok: true, group: 'Корпус А', unchanged: true });
    expect(resolveGroupChoice({ kind: 'new' }, '   ', null)).toEqual({ ok: false, problem: 'Назовите новую группу.' });
    expect(newGroupProblem('Я'.repeat(40))).toBeNull();
    expect(newGroupProblem('Я'.repeat(41))).toBe('Название группы длиннее 40 символов.');
    // «Без группы» is the absence of a group, so it is not a name a group can have, in any case
    expect(newGroupProblem(NO_GROUP_LABEL)).toMatch(/отсутствие группы/);
    expect(newGroupProblem('без ГРУППЫ')).toMatch(/отсутствие группы/);
    expect(resolveGroupChoice({ kind: 'new' }, NO_GROUP_LABEL, null).ok).toBe(false);
  });
});

describe('what is said of a move', () => {
  it('names the document and the place, in flight and done', () => {
    expect(movingSentence('Комплект АР', 'Корпус А')).toBe('Переношу документ «Комплект АР» в группу «Корпус А»…');
    expect(movingSentence('Комплект АР', null)).toBe('Переношу документ «Комплект АР» в «Без группы»…');
    expect(movedSentence('Комплект АР', 'Корпус А')).toBe('Документ «Комплект АР» перенесён в группу «Корпус А».');
    expect(movedSentence('Комплект АР', null)).toBe('Документ «Комплект АР» перенесён в «Без группы».');
  });

  it('says what did not work, why, and that the card did not move', () => {
    const text = refusedSentence('Комплект АР', 'Корпус А', 'Сервер недоступен.');
    expect(text).toContain('Не удалось перенести документ «Комплект АР» в группу «Корпус А».');
    expect(text).toContain('Сервер недоступен.');
    expect(text).toContain('Карточка осталась на месте.');
  });
});

// ------------------------------------------------------------------ the page's state

describe('the page\'s state from a card picked up to a card moved or refused', () => {
  const source = dragSourceOf(doc('A', 'Корпус А'), 'Документ A');
  const run = (...actions: EditingAction[]): EditingState => actions.reduce(editingReducer, EDITING_IDLE);

  it('follows the card: picked up, over a group, off it, and ended', () => {
    const up = run({ type: 'drag-start', source });
    expect(up.drag).toEqual(source);
    expect(up.over).toBeUndefined();
    expect(editingReducer(up, { type: 'over', target: 'Корпус Б' }).over).toBe('Корпус Б');
    // leaving a group that is not the one it is over changes nothing; leaving the one it is over clears it
    const over = run({ type: 'drag-start', source }, { type: 'over', target: 'Корпус Б' });
    expect(editingReducer(over, { type: 'leave', target: 'Корпус В' })).toBe(over);
    expect(editingReducer(over, { type: 'leave', target: 'Корпус Б' }).over).toBeUndefined();
    expect(editingReducer(over, { type: 'drag-end' })).toMatchObject({ drag: null, over: undefined });
    // «Без группы» is a place too: null is a target, not the absence of one
    expect(run({ type: 'drag-start', source }, { type: 'over', target: null }).over).toBeNull();
  });

  it('sends ONE command for a drop on another group and says it is on its way; the card is not moved by it', () => {
    const state = run({ type: 'drag-start', source }, { type: 'over', target: 'Корпус Б' }, { type: 'drop', target: 'Корпус Б' });
    expect(state.move).toEqual({ id: 1, source, group: 'Корпус Б' });
    expect(state.notice).toEqual({ kind: 'moving', text: movingSentence('Документ A', 'Корпус Б') });
    expect(state).toMatchObject({ drag: null, over: undefined, dialogFor: null });
  });

  it('sends null for a drop on «Без группы»', () => {
    expect(run({ type: 'drag-start', source }, { type: 'drop', target: null }).move?.group).toBeNull();
  });

  it('sends nothing for a drop on the card\'s own group, or for a drop of nothing', () => {
    const own = run({ type: 'drag-start', source }, { type: 'drop', target: 'Корпус А' });
    expect(own.move).toBeNull();
    expect(own.notice).toBeNull();
    expect(own.drag).toBeNull();
    expect(run({ type: 'drop', target: 'Корпус Б' }).move).toBeNull();
  });

  it('says the card is in its new group once the command is answered', () => {
    const state = run({ type: 'drag-start', source }, { type: 'drop', target: 'Корпус Б' }, { type: 'settled', reason: null });
    expect(state.move).toBeNull();
    expect(state.notice).toEqual({ kind: 'moved', text: movedSentence('Документ A', 'Корпус Б') });
  });

  it('says that it did not work and why when the server refused, and leaves nothing on its way', () => {
    const state = run(
      { type: 'drag-start', source }, { type: 'drop', target: 'Корпус Б' }, { type: 'settled', reason: 'Документ в архиве.' },
    );
    expect(state.move).toBeNull();
    expect(state.notice?.kind).toBe('refused');
    expect(state.notice?.text).toContain('Документ в архиве.');
    expect(state.notice?.text).toContain('Карточка осталась на месте.');
    // an answer with no command on its way is no news
    expect(editingReducer(EDITING_IDLE, { type: 'settled', reason: null })).toBe(EDITING_IDLE);
  });

  it('picks nothing up while a command is on its way, and numbers each command', () => {
    const sent = run({ type: 'drag-start', source }, { type: 'drop', target: 'Корпус Б' });
    expect(editingReducer(sent, { type: 'drag-start', source })).toBe(sent);
    const second = run(
      { type: 'drag-start', source }, { type: 'drop', target: 'Корпус Б' }, { type: 'settled', reason: null },
      { type: 'drag-start', source }, { type: 'drop', target: null },
    );
    expect(second.move?.id).toBe(2);
  });

  it('opens the window with the old line gone, and says the result when the window\'s command is done', () => {
    const noted = run({ type: 'drag-start', source }, { type: 'drop', target: 'Корпус Б' }, { type: 'settled', reason: null });
    const opened = editingReducer(noted, { type: 'dialog-open', version: doc('A', 'Корпус А') });
    expect(opened.dialogFor?.document_uid).toBe(doc('A').document_uid);
    expect(opened.notice).toBeNull();
    expect(editingReducer(opened, { type: 'dialog-close' }).dialogFor).toBeNull();
    const done = editingReducer(opened, { type: 'dialog-done', title: 'Документ A', group: null });
    expect(done.dialogFor).toBeNull();
    expect(done.notice).toEqual({ kind: 'moved', text: movedSentence('Документ A', null) });
  });
});

// ------------------------------------------------------------------ what the page draws

describe('the section page for a session that may act as an expert', () => {
  it('draws a menu «⋯» with «Группа…» on every card, named by its document', () => {
    const markup = renderPage(seeded(GROUPED));
    expect((markup.match(/data-card-menu=""/g) ?? [])).toHaveLength(4);
    expect(markup).toContain('aria-label="Действия с документом «Документ A»"');
    expect((markup.match(new RegExp(`>${GROUP_MENU_ITEM_LABEL}<`, 'g')) ?? [])).toHaveLength(4);
    expect(markup).toContain('aria-haspopup="menu"');
    expect(markup).toContain('>⋯<');
  });

  it('draws the menu on the cards of a section with no group too, where it is the way to the first group', () => {
    const markup = renderPage(seeded([doc('A'), doc('B')]));
    expect((markup.match(/data-card-menu=""/g) ?? [])).toHaveLength(2);
    expect(markup).toContain(`>${GROUP_MENU_ITEM_LABEL}<`);
  });

  it('lets the cards be dragged where there are groups to drop them on', () => {
    const markup = renderPage(seeded(GROUPED));
    expect((markup.match(/<li[^>]*draggable="true"/g) ?? [])).toHaveLength(4);
    // each group is a place to drop, apart from the one a card is in: nothing is dragged yet, so none is lit
    expect(markup).not.toContain('data-group-drop');
  });

  it('lets no card be dragged while no group is there to take it', () => {
    const markup = renderPage(seeded([doc('A'), doc('B')]));
    expect(markup).not.toContain('draggable=');
  });

  it('keeps a live region under the cards, empty until something is said', () => {
    const markup = renderPage(seeded(GROUPED));
    expect(markup).toMatch(/<div role="status" data-group-notice-region=""><\/div>/);
    expect(markup).not.toContain('data-group-notice=');
  });
});

describe('the section page for a session that may not act as an expert', () => {
  const markup = renderPage(seeded(GROUPED, ['admin']));

  it('draws the groups and the cards, and no menu, no drag, no window and no line to say what moved', () => {
    expect(markup).toContain('data-section-groups="3"');
    expect(markup).not.toContain('data-card-menu');
    expect(markup).not.toContain(GROUP_MENU_ITEM_LABEL);
    expect(markup).not.toContain('Действия с документом');
    expect(markup).not.toContain('draggable=');
    expect(markup).not.toContain('data-group-notice-region');
    expect(markup).not.toContain('data-group-dialog');
  });
});

describe('the window «Группа…»', () => {
  const groups = [{ name: 'Корпус А', count: 2 }, { name: 'Корпус Б', count: 1 }];
  const dialog = (version: DocumentVersion) => renderWith(newClient(), createElement(GroupDialog, {
    projectUid: PROJECT_UID, version, groups, onClose: () => undefined, onDone: () => undefined, staticOpen: true,
  }));

  it('is the shared window with the document, the groups there are, «Без группы» and a new group with its field', () => {
    const markup = dialog(doc('A', 'Корпус А'));
    expect(markup).toContain(`>${GROUP_DIALOG_TITLE}<`);
    expect(markup).toContain(`data-group-dialog="${doc('A').document_uid}"`);
    expect(markup).toContain('Документ «Документ A»');
    expect(markup).toMatch(/<fieldset[^>]*><legend[^>]*>Группа<\/legend>/);
    // the groups with their numbers, then «Без группы», then the new one
    expect([...markup.matchAll(/data-group-choice="(\w+)"/g)].map((match) => match[1])).toEqual(['group', 'group', 'none', 'new']);
    expect(markup).toMatch(/<span[^>]*>Корпус А<\/span><span[^>]*>\(2\)<\/span>/);
    expect(markup).toContain(`>${NO_GROUP_LABEL}<`);
    expect(markup).toContain(`>${NEW_GROUP_LABEL}<`);
    expect(markup).toMatch(/<input[^>]*type="text"[^>]*aria-label="Название новой группы"[^>]*maxLength="40"|<input[^>]*maxLength="40"[^>]*type="text"/);
  });

  it('has the document\'s own group chosen, and «Без группы» for a document with none', () => {
    const checked = (markup: string) => [...markup.matchAll(/<label[^>]*data-group-choice="(\w+)"[^>]*><input[^>]*checked=""/g)].map((match) => match[1]);
    expect(checked(dialog(doc('A', 'Корпус А')))).toEqual(['group']);
    expect(dialog(doc('A', 'Корпус А'))).toMatch(/<input[^>]*checked=""[^>]*\/><span[^>]*>Корпус А</);
    expect(checked(dialog(doc('D')))).toEqual(['none']);
  });

  it('has the buttons «Отмена» and «Сохранить», the second the form\'s own', () => {
    const markup = dialog(doc('A', 'Корпус А'));
    expect(markup).toContain(`>${GROUP_DIALOG_CANCEL_LABEL}<`);
    const form = markup.match(/<form id="([^"]+)"/)?.[1];
    expect(form).toBeDefined();
    expect(markup).toMatch(new RegExp(`<button[^>]*type="submit"[^>]*form="${form}"[^>]*>${GROUP_DIALOG_SAVE_LABEL}<`));
  });

  it('says nothing of a problem before there is one', () => {
    expect(dialog(doc('A', 'Корпус А'))).not.toContain('data-group-problem');
  });
});

describe('the line under the cards', () => {
  const layer = (notice: { kind: 'moving' | 'moved' | 'refused'; text: string } | null) => renderWith(newClient(), createElement(GroupEditingLayer, {
    layer: {
      projectUid: PROJECT_UID, notice, move: null, dialog: null,
      onMoveSettled: () => undefined, onDialogClose: () => undefined, onDialogDone: () => undefined,
    },
  }));

  it('is a live region, so a screen reader hears what was done', () => {
    const markup = layer({ kind: 'moved', text: movedSentence('Документ A', 'Корпус Б') });
    expect(markup).toMatch(/<div role="status"[^>]*><p[^>]*data-group-notice="moved"[^>]*>Документ «Документ A» перенесён в группу «Корпус Б»\.<\/p><\/div>/);
  });

  it('says in the same region that a move did not work, and why', () => {
    const markup = layer({ kind: 'refused', text: refusedSentence('Документ A', 'Корпус Б', 'Сервер недоступен.') });
    expect(markup).toMatch(/<div role="status"[^>]*><p[^>]*data-group-notice="refused"[^>]*>Не удалось перенести[^<]*Сервер недоступен\.[^<]*<\/p><\/div>/);
    expect(markup).toContain('am-form__problem');
  });

  it('says a move is on its way', () => {
    expect(layer({ kind: 'moving', text: movingSentence('Документ A', null) })).toContain('data-group-notice="moving"');
  });

  it('is nothing for a session that may not act', () => {
    expect(renderWith(newClient(), createElement(GroupEditingLayer, { layer: null }))).toBe('');
  });
});

// ------------------------------------------------------------------ the browser's events, run

describe('the groups as places to drop', () => {
  const GROUPS = groupDocuments(GROUPED) ?? [];
  const GRID = {
    addresses: () => ({ href: '/x', documentHref: '/y' }),
  };
  const dragging = dragSourceOf(doc('A', 'Корпус А'), 'Документ A');
  const drop = (over: GroupDrop['over'], overrides: Partial<GroupDrop> = {}): GroupDrop => ({
    source: dragging, over, onOver: vi.fn(), onLeave: vi.fn(), onDrop: vi.fn(), ...overrides,
  });
  const render = (given: GroupDrop | undefined) =>
    renderWith(newClient(), createElement(SectionGroups, { groups: GROUPS, grid: GRID, ...(given === undefined ? {} : { drop: given }) }));
  const dropStates = (markup: string) => [...markup.matchAll(/<section[^>]*data-group-kind="(\w+)"[^>]*?(?:data-group-name="([^"]*)")?[^>]*>/g)]
    .map((match) => [match[1], match[2], /data-group-drop="(\w+)"/.exec(match[0])?.[1]] as const);

  it('are lit as places to drop for a card that is in another group, and not for its own', () => {
    // Корпус А (the card's), Корпус Б, «Без группы»
    expect(dropStates(render(drop(undefined))).map((row) => row[2])).toEqual([undefined, 'ready', 'ready']);
    expect(dropStates(render(drop('Корпус Б'))).map((row) => row[2])).toEqual([undefined, 'over', 'ready']);
    expect(dropStates(render(drop(null))).map((row) => row[2])).toEqual([undefined, 'ready', 'over']);
  });

  it('are not places to drop while nothing is dragged, or for a session with no drop at all', () => {
    expect(render(drop(undefined, { source: null }))).not.toContain('data-group-drop');
    expect(render(undefined)).not.toContain('data-group-drop');
  });

  it('keep «Без группы» there while a card is dragged out of the last group that has one, and not at any other time', () => {
    const named = groupDocuments([doc('A', 'Корпус А'), doc('B', 'Корпус Б')]) ?? [];
    const markup = renderWith(newClient(), createElement(SectionGroups, { groups: named, grid: GRID, drop: drop(undefined) }));
    expect(markup).toContain('data-group-kind="none"');
    expect(markup).toContain('data-group-drop-hint');
    expect(markup).toContain('data-group-count="0"');
    const idle = renderWith(newClient(), createElement(SectionGroups, { groups: named, grid: GRID, drop: drop(undefined, { source: null }) }));
    expect(idle).not.toContain('data-group-kind="none"');
    expect(idle).not.toContain('data-group-drop-hint');
    expect(render(undefined)).not.toContain('data-group-drop-hint');
  });

  /** The elements the groups return, with their handlers: the groups' own function components are called, the rest is read as it stands. */
  function sections(given: GroupDrop): readonly ReactElement<Record<string, unknown>>[] {
    const root = SectionGroups({ groups: GROUPS, grid: GRID, drop: given }) as ReactElement<{ children: ReactElement[] }>;
    return Children.toArray(root.props.children).map((child) => {
      const element = child as ReactElement<Parameters<typeof SectionGroups>[0]>;
      return (element.type as (props: unknown) => ReactElement<Record<string, unknown>>)(element.props);
    });
  }
  const event = (related: unknown = null) => ({
    preventDefault: vi.fn(), dataTransfer: { dropEffect: '' }, relatedTarget: related, currentTarget: { contains: () => false },
  });

  it('take a card dragged over them: the browser is told it may drop, and the page is told which group it is over', () => {
    const given = drop(undefined);
    const [own, other, none] = sections(given);
    // the card's own group takes nothing: no handler at all, so the browser shows it cannot be dropped there
    expect(own?.props.onDragOver).toBeUndefined();
    expect(own?.props.onDrop).toBeUndefined();
    const over = event();
    (other?.props.onDragOver as (e: unknown) => void)(over);
    expect(over.preventDefault).toHaveBeenCalledTimes(1);
    expect(over.dataTransfer.dropEffect).toBe('move');
    expect(given.onOver).toHaveBeenCalledWith('Корпус Б');
    (none?.props.onDragOver as (e: unknown) => void)(event());
    expect(given.onOver).toHaveBeenLastCalledWith(null);
  });

  it('tell the page once, not at every move over the group it is already over', () => {
    const given = drop('Корпус Б');
    const [, other] = sections(given);
    (other?.props.onDragOver as (e: unknown) => void)(event());
    expect(given.onOver).not.toHaveBeenCalled();
  });

  it('are left only when the card leaves the group, not when it moves over a card inside it', () => {
    const given = drop('Корпус Б');
    const [, other] = sections(given);
    const leave = other?.props.onDragLeave as (e: unknown) => void;
    // a Node inside the group: the browser's `Node` is not in this environment, so a stand-in class is put there for the check
    class Inner {}
    vi.stubGlobal('Node', Inner);
    try {
      leave({ ...event(new Inner()), currentTarget: { contains: () => true } });
      expect(given.onLeave).not.toHaveBeenCalled();
      leave(event(new Inner()));
      expect(given.onLeave).toHaveBeenCalledWith('Корпус Б');
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('hand the drop to the page with the group dropped on, after telling the browser it was taken', () => {
    const given = drop('Корпус Б');
    const [, other, none] = sections(given);
    const taken = event();
    (other?.props.onDrop as (e: unknown) => void)(taken);
    expect(taken.preventDefault).toHaveBeenCalledTimes(1);
    expect(given.onDrop).toHaveBeenCalledWith('Корпус Б');
    (none?.props.onDrop as (e: unknown) => void)(event());
    expect(given.onDrop).toHaveBeenLastCalledWith(null);
  });
});

describe('the cards as things to drag', () => {
  const drag: NonNullable<DocumentCardGridProps['drag']> = { onStart: vi.fn(), onEnd: vi.fn() };
  const cards = (props: { drag?: NonNullable<DocumentCardGridProps['drag']>; dragging?: string | null }) => {
    const root = DocumentCardGrid({ documents: [doc('A', 'Корпус А'), doc('B')], addresses: () => ({ href: '/x', documentHref: '/y' }), ...props }) as
      ReactElement<{ children: unknown }>;
    return Children.toArray(root.props.children as never) as ReactElement<Record<string, unknown>>[];
  };

  it('are draggable only with the callbacks; the picked-up one is marked', () => {
    expect(cards({}).map((card) => card.props.draggable)).toEqual([undefined, undefined]);
    expect(cards({ drag }).map((card) => card.props.draggable)).toEqual([true, true]);
    const classes = (list: ReactElement<Record<string, unknown>>[]) => list.map((card) => String(card.props.className ?? ''));
    expect(classes(cards({ drag, dragging: doc('A').document_uid })).map((name) => name.split(' ').length)).toEqual([3, 2]);
  });

  it('tell the page which card was picked up, with the browser told it is a move, and when the drag ends', () => {
    const [first] = cards({ drag });
    const card = { getBoundingClientRect: () => ({ left: 100, top: 50 }) };
    const start = {
      clientX: 130, clientY: 70, currentTarget: card,
      dataTransfer: { effectAllowed: '', setData: vi.fn(), clearData: vi.fn(), setDragImage: vi.fn() },
    };
    (first?.props.onDragStart as (e: unknown) => void)(start);
    expect(start.dataTransfer.effectAllowed).toBe('move');
    // a drag that began on a link carries the link's address: it is cleared, so a drop outside the groups opens nothing; Firefox starts no drag without data
    expect(start.dataTransfer.clearData).toHaveBeenCalledTimes(1);
    expect(start.dataTransfer.clearData.mock.invocationCallOrder[0]).toBeLessThan(start.dataTransfer.setData.mock.invocationCallOrder[0] ?? 0);
    expect(start.dataTransfer.setData).toHaveBeenCalledWith('text/plain', 'Документ A');
    // the picture of the drag is the card, held where the pointer took it
    expect(start.dataTransfer.setDragImage).toHaveBeenCalledWith(card, 30, 20);
    expect(drag.onStart).toHaveBeenCalledWith(expect.objectContaining({ document_uid: doc('A').document_uid }));
    (first?.props.onDragEnd as () => void)();
    expect(drag.onEnd).toHaveBeenCalledTimes(1);
  });
});

// ------------------------------------------------------------------ the command is the hook's

describe('the command and the drag are what the task says they are', () => {
  const read = (path: string) => readFileSync(join(WEB_ROOT, path), 'utf8').replace(/\/\*[^]*?\*\//g, '').replace(/\/\/.*$/gm, '');
  const files = ['src/_pages/section-detail/ui/group-editing.tsx', 'src/_pages/section-detail/ui/group-dialog.tsx'];
  const callsTheApiDirectly = (source: string) => /\bsetDocumentGroup\b/.test(source.replace(/\buseSetDocumentGroup\b/g, ''));

  it('calls useSetDocumentGroup of UIP-G-10 and not the operation itself', () => {
    for (const file of files) {
      expect(read(file), file).toContain('useSetDocumentGroup');
      expect(callsTheApiDirectly(read(file)), file).toBe(false);
    }
  });

  it('can fail: a file that sends the operation itself is read as one', () => {
    expect(callsTheApiDirectly("import { setDocumentGroup } from '@/shared/api'; setDocumentGroup({});")).toBe(true);
    expect(callsTheApiDirectly("const set = useSetDocumentGroup({});")).toBe(false);
  });

  it('uses the browser\'s drag and drop: no drag library is a dependency', () => {
    const manifest = JSON.parse(readFileSync(join(WEB_ROOT, 'package.json'), 'utf8')) as { dependencies?: Record<string, string>; devDependencies?: Record<string, string> };
    const names = Object.keys({ ...manifest.dependencies, ...manifest.devDependencies });
    expect(names.filter((name) => /dnd|drag|sortable/i.test(name))).toEqual([]);
  });
});
