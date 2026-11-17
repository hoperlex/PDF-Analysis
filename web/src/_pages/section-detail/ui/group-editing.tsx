'use client';

/**
 * Moving documents between the section's groups (`UIP-S02-07`, owner rulings Г11, Г12-B): the card's menu «⋯» with «Группа…», the
 * dragging of a card onto a group, the window, the command and the sentence about the result. One hook ({@link useGroupEditing}) holds
 * all of it for the page and hands out the pieces: a slot for the cards' menu, the cards' drag callbacks, the groups' drop callbacks,
 * and the {@link GroupEditingLayer} that stands under the cards (the live region, the window, the command on its way).
 *
 * ## Who sees it
 *
 * Only a session that may act as an expert (`enabled`, `useMayActAsExpert`): for any other the hook hands out nothing — no menu, no
 * dragging, no window — and there is nothing under the cards either. The server is the authority and refuses anyone else's command in any case.
 *
 * ## The drag
 *
 * The browser's own drag and drop (HTML5, no library): a card is dragged by anywhere that is not a control; a group that is not the
 * card's own accepts it and lights while the card is over it; dropping sends ONE command with a key (`useSetDocumentGroup`, `UIP-G-10`)
 * for the dragged document. The card moves only when the server has answered and the lists are read again — on a refusal it stays where
 * it was, and under the cards the page says that it did not work and why (`refusedSentence`). While a command is on its way nothing else
 * can be dragged. A touch screen does not drag; «Группа…» works everywhere, with the keyboard too.
 *
 * ## Why the command is a component
 *
 * `useSetDocumentGroup` is bound to one document, and the dragged one is known only when the card is dropped, so each drop mounts a
 * {@link GroupMoveRunner} for that document, which sends its command once and says how it ended, then goes. The window «Группа…» is for one
 * document from the start and holds the hook itself.
 *
 * Every result is said in a live region (`role="status"`), so a screen reader hears it.
 */

import { useEffect, useReducer, useRef } from 'react';
import type { ReactNode } from 'react';

import type { DocumentVersion, ProjectUid } from '@/shared/api';
import { failureMessage } from '@/shared/api';
import { Menu } from '@/shared/ui';
import { documentCardTitle } from '@/entities/document-version';
import type { DocumentCardGridProps } from '@/entities/document-version';
import { useSetDocumentGroup } from '@/features/manage-document';

import { groupDocuments } from '../model/group-documents';
import { EDITING_IDLE, dragSourceOf, editingReducer } from '../model/group-move';
import type { MoveNotice, PendingMove } from '../model/group-move';
import { GroupDialog } from './group-dialog';
import type { KnownGroup } from './group-dialog';
import type { GroupDrop } from './section-groups';

export const GROUP_MENU_ITEM_LABEL = 'Группа…';

export interface GroupEditingInput {
  readonly projectUid: ProjectUid;
  /** May this session act as an expert? Without it nothing here is offered. */
  readonly enabled: boolean;
  /** The documents the page knows: the whole listing, or the page in view while the listing is not read whole. */
  readonly known: readonly DocumentVersion[];
}

export interface GroupEditingLayerProps {
  readonly projectUid: ProjectUid;
  readonly notice: MoveNotice | null;
  readonly move: PendingMove | null;
  /** The window «Группа…» is open for this document. */
  readonly dialog: { readonly version: DocumentVersion; readonly groups: readonly KnownGroup[] } | null;
  readonly onMoveSettled: (reason: string | null) => void;
  readonly onDialogClose: () => void;
  readonly onDialogDone: (version: DocumentVersion, group: string | null) => void;
}

export interface GroupEditing {
  /** The slot of the cards' menu «⋯»; `undefined` for a session that may not act. */
  readonly menu: ((version: DocumentVersion) => ReactNode) | undefined;
  /** The cards' drag callbacks; `undefined` while nothing may be dragged. */
  readonly drag: DocumentCardGridProps['drag'];
  /** The `document_uid` of the card being dragged, for its look. */
  readonly dragging: string | null;
  /** What the groups need to take a drop; `undefined` for a session that may not act. */
  readonly drop: GroupDrop | undefined;
  /** What stands under the cards; `null` for a session that may not act: it has nothing to say there. */
  readonly layer: GroupEditingLayerProps | null;
}

/** What a session that may not act is handed: nothing to drag, nothing to open, nothing to say. */
function inert(): GroupEditing {
  return {
    menu: undefined,
    drag: undefined,
    dragging: null,
    drop: undefined,
    layer: null,
  };
}

export function useGroupEditing({ projectUid, enabled, known }: GroupEditingInput): GroupEditing {
  // What happens is `editingReducer`'s (pure, and stated in `section-group-move.test.ts`); this is its connection to the page.
  const [state, dispatch] = useReducer(editingReducer, EDITING_IDLE);
  // A drag that began and ended before the page caught up must not leave it in a drag: each start and each end is a new number.
  const dragToken = useRef(0);

  if (!enabled) return inert();

  const knownGroups: readonly KnownGroup[] = (groupDocuments(known) ?? []).flatMap((group) =>
    group.name === null ? [] : [{ name: group.name, count: group.documents.length }]);

  return {
    menu: (version) => (
      <Menu
        label={`Действия с документом «${documentCardTitle(version)}»`}
        trigger={<span aria-hidden="true">⋯</span>}
        items={[{ kind: 'action', label: GROUP_MENU_ITEM_LABEL, onChoose: () => dispatch({ type: 'dialog-open', version }) }]}
      />
    ),
    // One command at a time: nothing is dragged while one is on its way.
    drag: state.move !== null ? undefined : {
      onStart: (version) => {
        dragToken.current += 1;
        const token = dragToken.current;
        const source = dragSourceOf(version, documentCardTitle(version));
        // After the browser has taken the picture of the card: changing the page inside the event can cancel the drag.
        setTimeout(() => {
          if (dragToken.current === token) dispatch({ type: 'drag-start', source });
        }, 0);
      },
      onEnd: () => {
        dragToken.current += 1;
        dispatch({ type: 'drag-end' });
      },
    },
    dragging: state.drag?.documentUid ?? null,
    drop: {
      source: state.drag,
      over: state.over,
      onOver: (target) => dispatch({ type: 'over', target }),
      onLeave: (target) => dispatch({ type: 'leave', target }),
      onDrop: (target) => {
        dragToken.current += 1;
        dispatch({ type: 'drop', target });
      },
    },
    layer: {
      projectUid,
      notice: state.notice,
      move: state.move,
      dialog: state.dialogFor === null ? null : { version: state.dialogFor, groups: knownGroups },
      onMoveSettled: (reason) => dispatch({ type: 'settled', reason }),
      onDialogClose: () => dispatch({ type: 'dialog-close' }),
      onDialogDone: (version, group) => dispatch({ type: 'dialog-done', title: documentCardTitle(version), group }),
    },
  };
}

/**
 * Sends the command of one dropped card, once, and says how it ended (`null`: done; else the reason the server's refusal is told in).
 * It draws nothing.
 */
function GroupMoveRunner({ projectUid, move, onSettled }: {
  readonly projectUid: ProjectUid;
  readonly move: PendingMove;
  readonly onSettled: (reason: string | null) => void;
}) {
  const set = useSetDocumentGroup({ projectUid, documentUid: move.source.documentUid });
  // A render that runs the effect twice (a strict one) still sends the one command.
  const started = useRef(false);
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    set.mutate({ group: move.group }, {
      onSuccess: () => onSettled(null),
      onError: (error) => onSettled(failureMessage(error).detail),
    });
  }, [set, move.group, onSettled]);
  return null;
}

export interface GroupEditingLayerViewProps {
  readonly layer: GroupEditingLayerProps | null;
}

/**
 * What stands under the cards: the line about the last move (a live region, so it is read out — and kept in the page even when empty,
 * so the first words in it are heard), the command of a dropped card on its way, and the window «Группа…» when it is open.
 */
export function GroupEditingLayer({ layer }: GroupEditingLayerViewProps) {
  if (layer === null) return null;
  const { notice, move, dialog } = layer;
  return (
    <>
      <div role="status" data-group-notice-region="">
        {notice === null ? null : notice.kind === 'refused' ? (
          <p className="am-form__problem" data-group-notice="refused">{notice.text}</p>
        ) : (
          <p className="am-note" data-group-notice={notice.kind}>{notice.text}</p>
        )}
      </div>
      {move === null ? null : <GroupMoveRunner key={move.id} projectUid={layer.projectUid} move={move} onSettled={layer.onMoveSettled} />}
      {dialog === null ? null : (
        <GroupDialog
          key={dialog.version.document_uid}
          projectUid={layer.projectUid}
          version={dialog.version}
          groups={dialog.groups}
          onClose={layer.onDialogClose}
          onDone={(group) => layer.onDialogDone(dialog.version, group)}
        />
      )}
    </>
  );
}
