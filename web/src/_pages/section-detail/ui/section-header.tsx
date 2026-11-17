'use client';

/**
 * The one line over a section's cards (`UIP-S02-01`, the original's section header in our words and on our controls):
 *
 *   «←» to the object's «Главная» · the section's dot, code and name · «(N)» with the box that chooses every document ·
 *   the plaques of the audit states (the one that says «ждут решения N» chooses those documents) · «Выделить необработанные»
 *   and «Снять выделение» · and, at the right end, «+ Добавить» and «Обновить».
 *
 * There is no plaque «N документов»: the number is the «(N)» beside the name. There is no second line of crumbs over the cards:
 * where the reader is stands in the heading and the way up is the arrow. The dot beside the code is the section's colour (`R-151`:
 * «свой цвет у каждого раздела везде», `UIP-G-17`); it is not a filled plaque, so the colour is one more mark of the section and
 * not the only one.
 *
 * **What the controls choose is the listing, whole** (`UI-A-35`, {@link sectionChoices}): the box, «Выделить необработанные» and
 * «ждут решения N» choose across every page of the listing in view, read to its end by the server's cursor, and wait — disabled —
 * while pages are being read or when one failed; none of them ever chooses part of the section as if it were the whole. They are
 * drawn only for a session that may start an audit (`BatchSelection.selection`), and not at all when no document of the listing
 * can be started. The state of the reading, and the retry, are said by {@link SectionBatchBar}; the chosen ones are started from the
 * bottom bar (`SectionSelectionBar`, `UIP-S02-03`).
 *
 * Presentational over what the page already holds: the figures, the page's documents, the walk and the selection come in as props.
 */

import { useEffect, useRef } from 'react';
import Link from 'next/link';

import type { DocumentVersion, ProjectUid } from '@/shared/api';
import { withProjectParam } from '@/shared/lib';
import { AuditTallyLine } from '@/entities/document-version';
import type { AuditTally } from '@/entities/document-version';
import { SectionDot } from '@/entities/project';
import type { ProjectSection } from '@/entities/project';
import type { BatchSelection } from '@/widgets/project-sections';

import { sectionChoices } from '../model/section-choices';
import type { ListingWalk } from '../model/use-listing-walk';
import styles from './section-header.module.css';

export interface SectionHeaderProps {
  readonly projectUid: ProjectUid;
  readonly section: ProjectSection;
  /** The object's name for the arrow's name, when it is known (the page reads it by identity, `getProject`). */
  readonly objectName?: string | undefined;
  /** The documents of the page in view, or `undefined` while the listing has not answered: no figures, no choice. */
  readonly documents: readonly DocumentVersion[] | undefined;
  /** The listing read to its end, or `idle` when the page is all of it. */
  readonly walk: ListingWalk;
  /** The figures behind «(N)» and the plaques: the server's own count of the section, or the page's. */
  readonly tally: AuditTally | null;
  /** The figures cover a page of a longer listing, and the line says so. */
  readonly partial: boolean;
  /** Where the plaque «не запускались N» leads: the section narrowed to those documents; `undefined`, it is plain. */
  readonly notRunHref?: string | undefined;
  readonly selection: BatchSelection;
  /** `UI-A-56`: where «+ Добавить» leads — the project's upload. */
  readonly addHref: string;
  readonly refreshing: boolean;
  readonly onRefresh: () => void;
}

/** The address of the object's «Главная»: `/` with the object it follows (`UIP-G-06`, `UIP-S01`). */
export function objectHomeHref(projectUid: string): string {
  return withProjectParam('/', projectUid);
}

export function SectionHeader({
  projectUid, section, objectName, documents, walk, tally, partial, notRunHref, selection, addHref, refreshing, onRefresh,
}: SectionHeaderProps) {
  // `UI-A-35`: the controls choose from the whole listing; `null` while it is being read or a page failed.
  const choices = documents === undefined ? null : sectionChoices(documents, walk);
  // Drawn for a session that may start an audit, once there is a listing, unless the whole of it holds nothing startable.
  const chooses = selection.selection !== undefined && documents !== undefined && (choices === null || choices.all.length > 0);
  const selected = selection.selection?.selected;
  const allChosen = choices !== null && choices.all.length > 0 && choices.all.every((version) => selected?.has(version.version_uid) === true);
  const someChosen = selection.chosenCount > 0;
  const awaiting = choices?.awaitingDecision ?? [];
  const awaitingChosen = awaiting.length > 0 && awaiting.every((version) => selected?.has(version.version_uid) === true);

  // A box that is neither on nor off is a property of the element, not of its markup.
  const box = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (box.current !== null) box.current.indeterminate = someChosen && !allChosen;
  }, [someChosen, allChosen]);

  const homeName = objectName === undefined ? 'На главную объекта' : `На главную объекта «${objectName}»`;
  return (
    <header className={styles.header} data-section-header="">
      <Link className={styles.back} href={objectHomeHref(projectUid)} title={homeName} aria-label={homeName} data-section-back="">
        ←
      </Link>
      <h1 className={styles.title}>
        <SectionDot code={section.code} />
        <span className={styles.code} data-section-code-mark={section.code}>{section.abbr}</span>
        <span className={styles.name}>{section.name}</span>
      </h1>
      {tally === null ? null : (
        <span className={styles.count} data-section-count={tally.documents} title="Документов раздела с текущей версией">
          ({tally.documents})
        </span>
      )}
      {!chooses ? null : (
        <label className={styles.check} data-select-all={choices === null ? 'waiting' : choices.all.length}>
          <input
            ref={box}
            type="checkbox"
            aria-label={choices === null ? 'Выбрать все документы раздела' : `Выбрать все документы раздела: ${choices.all.length}`}
            checked={allChosen}
            disabled={choices === null}
            onChange={() => (allChosen ? selection.clear() : choices !== null && selection.choose(choices.all))}
          />
        </label>
      )}
      {tally === null ? null : (
        <AuditTallyLine
          tally={tally}
          total={false}
          partial={partial}
          label={`${section.abbr} ${section.name}`}
          notRunHref={notRunHref}
          awaiting={
            !chooses
              ? undefined
              : {
                  onPress: choices === null || awaiting.length === 0
                    ? undefined
                    : () => (awaitingChosen ? selection.clear() : selection.choose(awaiting)),
                  pressed: awaitingChosen,
                  title: choices === null
                    ? 'Выбрать документы, которые ждут решения: раздел ещё читается'
                    : `Выбрать документы, которые ждут решения: ${awaiting.length}`,
                }
          }
        />
      )}
      {/* Only where there is something never run to choose, as the original's; while the listing is read it waits, disabled. */}
      {!chooses || (choices !== null && choices.notRun.length === 0) ? null : (
        <button
          type="button"
          className="am-button am-button--quiet am-button--small"
          disabled={choices === null}
          title={choices === null ? 'Раздел ещё читается' : `Документов, которые не запускались: ${choices.notRun.length}`}
          onClick={() => choices !== null && selection.choose(choices.notRun)}
          data-select-not-run=""
        >
          Выделить необработанные
        </button>
      )}
      {!chooses || !someChosen ? null : (
        <button type="button" className="am-button am-button--quiet am-button--small" onClick={selection.clear} data-clear-selection="">
          Снять выделение
        </button>
      )}
      <div className={styles.end}>
        {/* `UI-A-56`: the original's «+ Добавить»; the upload form is the project's page. */}
        <Link className="am-button am-button--small" href={addHref} data-section-add="">
          + Добавить
        </Link>
        <button type="button" className="am-button am-button--quiet am-button--small" disabled={refreshing} onClick={onRefresh}>
          {refreshing ? 'Обновляется…' : 'Обновить'}
        </button>
      </div>
    </header>
  );
}
