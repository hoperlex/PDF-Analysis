/**
 * Moving a document into a group (`UIP-S02-07`, owner rulings Г11, Г12-B): by dragging its card onto a group, and by «Группа…» in the card's
 * menu. Either way the document gets its new group in ONE command with a key (`useSetDocumentGroup`, `UIP-G-10`); this file is what is
 * decided before and after the command, apart from the screen: what a drop asks for, what a choice in the window comes to, and the
 * sentences the result is said in (for the eye and, in a live region, for a screen reader).
 *
 * A group is a value of the document and not an entity (Г11): «a new group» is a name no document has yet, a group is gone when its last
 * document leaves, and «Без группы» is no name at all (the command takes `null` for it).
 *
 * Pure: the same inputs give the same answers, so a test can state each of them.
 */

import type { DocumentUid, DocumentVersion } from '@/shared/api';

import { GROUP_NAME_MAX_LENGTH, NO_GROUP_LABEL, groupOf } from './group-documents';

/** The card being dragged: which document, what it is called, and the group it is in now. */
export interface DragSource {
  readonly documentUid: DocumentUid;
  readonly title: string;
  readonly group: string | null;
}

export function dragSourceOf(version: DocumentVersion, title: string): DragSource {
  return { documentUid: version.document_uid, title, group: groupOf(version) };
}

/** What the command takes: the group's name, or `null` to take the document out of its group. */
export interface GroupRequest {
  readonly group: string | null;
}

/**
 * What dropping the dragged card on `target` asks for — the group's name, or `null` for «Без группы» — or `null` when the card is
 * already there (nothing is sent, and the group does not light as a place to drop).
 */
export function dropRequest(source: DragSource, target: string | null): GroupRequest | null {
  return source.group === target ? null : { group: target };
}

/** What the reader picked in the window «Группа…»: one of the groups there are, «Без группы», or a new name from the field. */
export type GroupChoice =
  | { readonly kind: 'group'; readonly name: string }
  | { readonly kind: 'none' }
  | { readonly kind: 'new' };

/** The name of a new group as it will be stored: trimmed, 1 to 40 characters, and not the words that mean «no group». */
export function newGroupProblem(text: string): string | null {
  const name = text.trim();
  if (name === '') return 'Назовите новую группу.';
  if (name.length > GROUP_NAME_MAX_LENGTH) return `Название группы длиннее ${GROUP_NAME_MAX_LENGTH} символов.`;
  if (name.toLocaleLowerCase('ru') === NO_GROUP_LABEL.toLocaleLowerCase('ru')) {
    return `«${NO_GROUP_LABEL}» — это отсутствие группы, так группу не назвать.`;
  }
  return null;
}

export type GroupAnswer =
  /** `group` is what to send; `unchanged` is that the document is in it already, so nothing is sent. */
  | { readonly ok: true; readonly group: string | null; readonly unchanged: boolean }
  | { readonly ok: false; readonly problem: string };

/** What the window's choice comes to, for a document now in `current`. */
export function resolveGroupChoice(choice: GroupChoice, draft: string, current: string | null): GroupAnswer {
  if (choice.kind === 'none') return { ok: true, group: null, unchanged: current === null };
  if (choice.kind === 'group') return { ok: true, group: choice.name, unchanged: current === choice.name };
  const problem = newGroupProblem(draft);
  if (problem !== null) return { ok: false, problem };
  const name = draft.trim();
  return { ok: true, group: name, unchanged: current === name };
}

/** The place a document goes to, in a sentence: «в группу «Корпус А»» or «в «Без группы»». */
function into(group: string | null): string {
  return group === null ? `в «${NO_GROUP_LABEL}»` : `в группу «${group}»`;
}

/** Said while the command is on its way. */
export function movingSentence(title: string, group: string | null): string {
  return `Переношу документ «${title}» ${into(group)}…`;
}

/** Said when the document is in its new group. */
export function movedSentence(title: string, group: string | null): string {
  return `Документ «${title}» перенесён ${into(group)}.`;
}

/** Said when the server refused or could not be reached: what did not happen, why, and that nothing moved. */
export function refusedSentence(title: string, group: string | null, reason: string): string {
  return `Не удалось перенести документ «${title}» ${into(group)}. ${reason} Карточка осталась на месте.`;
}

/** What is said under the cards about the last move: in flight, done, or refused. */
export interface MoveNotice {
  readonly kind: 'moving' | 'moved' | 'refused';
  readonly text: string;
}

/** A command sent for a dropped card: which document, which group, and a number that tells this drop from the one before. */
export interface PendingMove {
  readonly id: number;
  readonly source: DragSource;
  readonly group: string | null;
}

/** Everything the section page holds about moving documents between groups. */
export interface EditingState {
  /** The card being dragged, or `null`. */
  readonly drag: DragSource | null;
  /** The group the card is over: its name, `null` for «Без группы», `undefined` for none. */
  readonly over: string | null | undefined;
  /** The command of a dropped card that has not been answered. */
  readonly move: PendingMove | null;
  /** What was said of the last move, under the cards. */
  readonly notice: MoveNotice | null;
  /** The window «Группа…» is open for this document. */
  readonly dialogFor: DocumentVersion | null;
  /** How many drops have sent a command, for {@link PendingMove.id}. */
  readonly moves: number;
}

export const EDITING_IDLE: EditingState = { drag: null, over: undefined, move: null, notice: null, dialogFor: null, moves: 0 };

export type EditingAction =
  | { readonly type: 'drag-start'; readonly source: DragSource }
  | { readonly type: 'drag-end' }
  | { readonly type: 'over'; readonly target: string | null }
  | { readonly type: 'leave'; readonly target: string | null }
  | { readonly type: 'drop'; readonly target: string | null }
  /** The command of the dropped card was answered: `null` for done, else the reason it was refused. */
  | { readonly type: 'settled'; readonly reason: string | null }
  | { readonly type: 'dialog-open'; readonly version: DocumentVersion }
  | { readonly type: 'dialog-close' }
  /** The window's command was answered: the document is in `group` (`null`: out of its group). */
  | { readonly type: 'dialog-done'; readonly title: string; readonly group: string | null };

/**
 * The page's side of moving a document, as a function of what happened: a card picked up, over a group, dropped, the command answered, the
 * window opened and closed. Drop on the group the card is in sends nothing; a drop elsewhere sends one command and says it is on its way;
 * the answer says it is done or — on a refusal — that it did not work and why, and the card, which only the server's lists move, stays.
 */
export function editingReducer(state: EditingState, action: EditingAction): EditingState {
  switch (action.type) {
    case 'drag-start':
      // One command at a time: nothing else is picked up while one is on its way.
      return state.move === null ? { ...state, drag: action.source, over: undefined } : state;
    case 'drag-end':
      return { ...state, drag: null, over: undefined };
    case 'over':
      return state.over === action.target ? state : { ...state, over: action.target };
    case 'leave':
      return state.over === action.target ? { ...state, over: undefined } : state;
    case 'drop': {
      const source = state.drag;
      const idle = { ...state, drag: null, over: undefined };
      if (source === null) return idle;
      const request = dropRequest(source, action.target);
      if (request === null) return idle;
      return {
        ...idle,
        moves: state.moves + 1,
        move: { id: state.moves + 1, source, group: request.group },
        notice: { kind: 'moving', text: movingSentence(source.title, request.group) },
      };
    }
    case 'settled': {
      const { move } = state;
      if (move === null) return state;
      return {
        ...state,
        move: null,
        notice: action.reason === null
          ? { kind: 'moved', text: movedSentence(move.source.title, move.group) }
          : { kind: 'refused', text: refusedSentence(move.source.title, move.group, action.reason) },
      };
    }
    case 'dialog-open':
      return { ...state, dialogFor: action.version, notice: null };
    case 'dialog-close':
      return { ...state, dialogFor: null };
    case 'dialog-done':
      return { ...state, dialogFor: null, notice: { kind: 'moved', text: movedSentence(action.title, action.group) } };
  }
}
