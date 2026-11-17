'use client';

/**
 * «+ Добавить документы» (`UIP-S13-03`): the panel the button opens on the queue's page. The original's «Добавить проекты» lets the
 * reader put work into the queue from the queue's own page; here the work is a document's audit, and the panel is:
 *
 *   - **the object** — the one the header has chosen (`useCurrentProject`, `UIP-G-06`), and with «Все объекты» chosen here, in a list;
 *   - **its documents with no run in flight**, each with a box and its section (`addableDocuments`), read to the end of the listing;
 *   - **«Выбрано: N» and «Запустить аудит (N)»** — the batch panel the section page opens (`BatchStartPanel`): every estimate, ONE
 *     agreement for the batch, each run's own outcome. It is the same panel, so the two ways in say the same words.
 *
 * It offers no choice of an action (audit, optimisation, both): the optimisation is a pass inside a request and no job of the queue.
 */

import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { queryKeys } from '@/shared/api';
import type { ProjectUid } from '@/shared/api';
import { documentCardTitle } from '@/entities/document-version';
import { useCurrentProject, useProjectList } from '@/entities/project';
import { BatchStartPanel } from '@/features/start-run';
import type { BatchEntry } from '@/features/start-run';
import { ErrorState, LoadingState } from '@/shared/ui';

import { addableDocuments, addableSection, chosenEntries } from '../model/add-documents';
import { useObjectDocuments } from '../model/use-object-documents';
import styles from './queue-page.module.css';

/** This screen's registry address: outside the app router there is no address of its own, and this stands in for it. */
const QUEUE_ADDRESS = '/queue';

export function AddDocumentsPanel() {
  const { projectUid: current } = useCurrentProject(QUEUE_ADDRESS);
  const [picked, setPicked] = useState<string | null>(null);
  const projectUid = picked ?? current;
  const objects = useProjectList(undefined, { order: 'name' });
  const root = useRef<HTMLElement>(null);
  // The panel opens under the list and the reader may be reading its top: the focus goes to the panel, and the page follows it.
  useEffect(() => { root.current?.focus(); }, []);
  const listed = objects.data?.items ?? [];
  const known = projectUid !== null && listed.some((project) => project.project_uid === projectUid);
  return (
    <section ref={root} tabIndex={-1} className={`${styles.panel} ${styles.add}`} aria-label="Добавить документы в очередь" data-queue-add-panel="">
      <label className={styles.addObject}>
        Объект
        <select name="queue-add-object" data-queue-add-object value={projectUid ?? ''} onChange={(event) => setPicked(event.currentTarget.value === '' ? null : event.currentTarget.value)}>
          {projectUid === null ? <option value="">Выберите объект</option> : null}
          {projectUid !== null && !known ? <option value={projectUid}>Выбранный объект</option> : null}
          {listed.map((project) => <option key={project.project_uid} value={project.project_uid}>{project.name}</option>)}
        </select>
      </label>
      {objects.data !== undefined && objects.data.page.next_cursor !== null ? (
        <p className="am-note" data-queue-add-more="">Показаны первые {listed.length} объектов; остальные выбираются в верхней строке.</p>
      ) : null}
      {objects.isError ? <p role="status" className="am-note">Список объектов не прочитан: выбрать другой объект здесь нельзя.</p> : null}
      {projectUid === null
        ? <p className="am-note" data-queue-add-pick="">Выберите объект, чтобы увидеть его документы.</p>
        : <AddableDocuments key={projectUid} projectUid={projectUid} />}
    </section>
  );
}

function AddableDocuments({ projectUid }: { readonly projectUid: string }) {
  const walk = useObjectDocuments(projectUid);
  const client = useQueryClient();
  const [chosen, setChosen] = useState<ReadonlySet<string>>(() => new Set());
  const [batch, setBatch] = useState<readonly BatchEntry[] | null>(null);
  if (walk.status === 'pending' || walk.status === 'idle') return <LoadingState what="документы объекта" />;
  if (walk.status === 'failed') {
    return <ErrorState title="Документы объекта не прочитаны" detail="Список документов прочитан не до конца, поэтому выбрать из него нельзя." onRetry={walk.retry} />;
  }
  const documents = addableDocuments(walk.items);
  if (documents.length === 0) {
    return <p className="am-note" data-queue-add-empty="">Все документы объекта уже в очереди или ещё не отнесены к разделу.</p>;
  }
  const all = documents.every((version) => chosen.has(version.version_uid));
  const toggle = (versionUid: string) => setChosen((current) => {
    const next = new Set(current);
    if (next.has(versionUid)) next.delete(versionUid);
    else next.add(versionUid);
    return next;
  });
  return (
    <>
      <ul className={styles.addList} data-queue-add-documents={documents.length}>
        {documents.map((version) => (
          <li key={version.version_uid}>
            <label className={styles.addRow}>
              <input type="checkbox" checked={chosen.has(version.version_uid)} disabled={batch !== null} onChange={() => toggle(version.version_uid)} />
              <span className={styles.addTitle}>{documentCardTitle(version)}</span>
              <span className={styles.addSection} data-queue-add-section="">{addableSection(version)}</span>
            </label>
          </li>
        ))}
      </ul>
      <p className={styles.addActions} data-queue-add-controls="">
        <span data-queue-add-chosen={chosen.size}>Выбрано: {chosen.size}</span>
        <button
          type="button"
          className="am-button am-button--quiet am-button--small"
          disabled={batch !== null}
          onClick={() => setChosen(all ? new Set() : new Set(documents.map((version) => version.version_uid)))}
        >
          {all ? 'Снять выделение' : 'Выбрать все'}
        </button>
        <button
          type="button"
          className="am-button"
          disabled={chosen.size === 0 || batch !== null}
          onClick={() => setBatch(chosenEntries(documents, chosen))}
        >
          Запустить аудит ({chosen.size})
        </button>
      </p>
      {batch === null ? null : (
        <BatchStartPanel
          projectUid={projectUid as ProjectUid}
          entries={batch}
          onClose={() => {
            setBatch(null);
            setChosen(new Set());
            // The documents just started have a run in flight now: they leave the offer.
            void client.invalidateQueries({ queryKey: queryKeys.projects.documents(projectUid as ProjectUid).slice(0, 3) });
          }}
        />
      )}
    </>
  );
}
