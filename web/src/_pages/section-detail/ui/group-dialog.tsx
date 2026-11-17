'use client';

/**
 * The window «Группа…» that a card's menu «⋯» opens (`UIP-S02-07`, owner rulings Г11, Г12-B): the shared window (`Dialog`, `UIP-G-04`)
 * with one choice for one document — a group there already is, «Без группы», or a new name — and the buttons «Отмена» and «Сохранить».
 *
 * ## What it is made of
 *
 * One set of radio buttons, so the choice is one thing a reader sees whole and a keyboard walks with the arrow keys: the groups of the
 * section (each with its number), «Без группы», and «Новая группа» with its field. Typing in the field chooses it. The Enter key in
 * the field and the button «Сохранить» are one submit (the button is the form's by its `form` attribute, as in the window «Новый объект»).
 *
 * The command is `useSetDocumentGroup` (`UIP-G-04`'s sibling, `UIP-G-10`): one command with a key, for this document. The window does
 * not repeat the group's rules; what the server holds a name to (1 to 40 characters) is checked here only so that the reader is told
 * before sending, and a refusal of the server stands in the window as it came, with the field as it was.
 *
 * ## What it promises
 *
 * - **What was typed is not lost.** The window is closed by «Отмена», «Закрыть» and Esc (`Dialog`), and by a saved choice; a press on the
 *   dimmed page does nothing, and a refusal leaves the choice and the field as they were.
 * - **A choice that changes nothing sends nothing.** The document is in the group already: the window closes.
 * - **The result is said** (`onDone`): the page puts it in a live region, so a screen reader hears it; the window itself is gone by then.
 *
 * `staticOpen` is for the census and the unit suite (`Dialog` draws open without `showModal`).
 */

import { useId, useState } from 'react';

import type { DocumentVersion, ProjectUid } from '@/shared/api';
import { failureMessage } from '@/shared/api';
import { Dialog } from '@/shared/ui';
import { documentCardTitle } from '@/entities/document-version';
import { useSetDocumentGroup } from '@/features/manage-document';

import { GROUP_NAME_MAX_LENGTH, NO_GROUP_LABEL, groupOf } from '../model/group-documents';
import { newGroupProblem, resolveGroupChoice } from '../model/group-move';
import type { GroupChoice } from '../model/group-move';
import styles from './group-dialog.module.css';

export const GROUP_DIALOG_TITLE = 'Группа документа';
export const GROUP_DIALOG_CANCEL_LABEL = 'Отмена';
export const GROUP_DIALOG_SAVE_LABEL = 'Сохранить';
export const NEW_GROUP_LABEL = 'Новая группа';

/** A group that exists and how many documents of the section are in it. */
export interface KnownGroup {
  readonly name: string;
  readonly count: number;
}

export interface GroupDialogProps {
  readonly projectUid: ProjectUid;
  /** The document the window is for. */
  readonly version: DocumentVersion;
  /** The groups the reader may pick, in the order they stand on the page; the document's own group is among them. */
  readonly groups: readonly KnownGroup[];
  /** Esc, «Закрыть» and «Отмена»: the owner unmounts the window. */
  readonly onClose: () => void;
  /** The document is in its new group (`null`: out of its group); the owner says so and unmounts the window. */
  readonly onDone: (group: string | null) => void;
  /** The census and the unit suite: drawn open without `showModal`. */
  readonly staticOpen?: boolean | undefined;
}

export function GroupDialog({ projectUid, version, groups, onClose, onDone, staticOpen }: GroupDialogProps) {
  const formId = useId();
  const radioName = useId();
  const current = groupOf(version);
  const title = documentCardTitle(version);
  const save = useSetDocumentGroup({ projectUid, documentUid: version.document_uid });
  const [choice, setChoice] = useState<GroupChoice>(current === null ? { kind: 'none' } : { kind: 'group', name: current });
  const [draft, setDraft] = useState('');

  const answer = resolveGroupChoice(choice, draft, current);
  // A name that does not hold is said as soon as there is one to judge; an empty field is not yet a problem.
  const typed = choice.kind === 'new' && draft.trim() !== '' ? newGroupProblem(draft) : null;
  const refusal = save.isError ? failureMessage(save.error).detail : null;

  const submit = () => {
    if (save.isPending || !answer.ok) return;
    if (answer.unchanged) {
      onClose();
      return;
    }
    save.mutate({ group: answer.group }, { onSuccess: () => onDone(answer.group) });
  };

  const choose = (next: GroupChoice) => {
    save.reset();
    setChoice(next);
  };

  return (
    <Dialog
      title={GROUP_DIALOG_TITLE}
      size="sm"
      onClose={onClose}
      staticOpen={staticOpen}
      markers={{ 'data-group-dialog': version.document_uid }}
      actions={
        <>
          <button type="button" className="am-button am-button--quiet" onClick={onClose}>
            {GROUP_DIALOG_CANCEL_LABEL}
          </button>
          <button type="submit" className="am-button" form={formId} disabled={save.isPending || !answer.ok}>
            {GROUP_DIALOG_SAVE_LABEL}
          </button>
        </>
      }
    >
      <form
        id={formId}
        className={styles.form}
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <p className={styles.document} data-group-dialog-document="">Документ «{title}»</p>
        <fieldset className={styles.choices} disabled={save.isPending}>
          <legend className={styles.legend}>Группа</legend>
          {groups.map((group) => (
            <label key={group.name} className={styles.choice} data-group-choice="group">
              <input
                type="radio"
                name={radioName}
                checked={choice.kind === 'group' && choice.name === group.name}
                onChange={() => choose({ kind: 'group', name: group.name })}
              />
              <span className={styles.choiceName}>{group.name}</span>
              <span className={styles.choiceCount}>({group.count})</span>
            </label>
          ))}
          <label className={styles.choice} data-group-choice="none">
            <input type="radio" name={radioName} checked={choice.kind === 'none'} onChange={() => choose({ kind: 'none' })} />
            <span className={styles.choiceName}>{NO_GROUP_LABEL}</span>
          </label>
          <label className={styles.choice} data-group-choice="new">
            <input type="radio" name={radioName} checked={choice.kind === 'new'} onChange={() => choose({ kind: 'new' })} />
            <span className={styles.choiceName}>{NEW_GROUP_LABEL}</span>
          </label>
          <input
            type="text"
            className={styles.field}
            aria-label="Название новой группы"
            placeholder="Название новой группы"
            value={draft}
            maxLength={GROUP_NAME_MAX_LENGTH}
            onChange={(event) => {
              setDraft(event.target.value);
              choose({ kind: 'new' });
            }}
          />
        </fieldset>
        {typed === null ? null : <p className="am-form__problem" role="alert" data-group-problem="name">{typed}</p>}
        {refusal === null ? null : <p className="am-form__problem" role="alert" data-group-problem="refused">{refusal}</p>}
      </form>
    </Dialog>
  );
}
