'use client';

/**
 * «Вендор-листы по разделам» (`W60-PRICE-LIST-01`): for each of the fifteen sections, the list
 * of allowed vendors that applies to this project — the project's own list when an expert set
 * one, otherwise the administrator's general list, otherwise none.
 *
 * Who may change what is the API's rule and the roles only decide which controls are drawn:
 * an expert edits the project's list or returns the section to the general list; an
 * administrator edits the general list. Every change is a new revision with its author and
 * time, sent with the revision the screen showed, so a concurrent change is refused rather
 * than overwritten.
 */

import { useState } from 'react';

import type {
  ProjectSection,
  ProjectUid,
  Role,
  SectionVendorList,
  VendorListEntry,
  VendorListRevision,
} from '@/shared/api';
import { ErrorState, LoadingState } from '@/shared/ui';
import { formatInstant } from '@/shared/lib';
import type { FailureMessage } from '@/shared/api/failure-message';
import { failureMessage } from '@/shared/api/failure-message';
import { findProjectSection, projectSectionTitle } from '@/entities/project';
import {
  VENDOR_SOURCE_LABELS,
  useEffectiveVendorLists,
  vendorListFailureMessage,
} from '@/entities/price-list';
import {
  VendorListEditor,
  useSetGlobalVendorList,
  useSetProjectVendorList,
} from '@/features/set-vendor-list';

import styles from './project-optimisation.module.css';

/** Which list is open for editing: a section's project list or its general list. */
export interface VendorListEditing {
  readonly sectionCode: ProjectSection;
  readonly scope: 'project' | 'global';
}

function entryText(entry: VendorListEntry): string {
  const head = entry.material === null || entry.material === undefined
    ? entry.vendor
    : `${entry.material} — ${entry.vendor}`;
  return entry.note === null || entry.note === undefined ? head : `${head} (${entry.note})`;
}

function EntriesView({ revision }: { readonly revision: VendorListRevision | null }) {
  if (revision === null) return <>не задан</>;
  if (revision.entries.length === 0) return <>без ограничений</>;
  return (
    <ul className={styles.entries}>
      {revision.entries.map((entry, index) => (
        <li key={index}>{entryText(entry)}</li>
      ))}
    </ul>
  );
}

function sectionTitle(code: string): string {
  const section = findProjectSection(code);
  return section === null ? code : projectSectionTitle(section);
}

function revisionNote(revision: VendorListRevision | null): string {
  if (revision === null) return '';
  return `редакция ${revision.revision_number} от ${formatInstant(revision.set_at)}`;
}

export interface VendorListsViewProps {
  readonly items: readonly SectionVendorList[];
  readonly canEditProject: boolean;
  readonly canEditGlobal: boolean;
  readonly editing: VendorListEditing | null;
  readonly pending: boolean;
  readonly failure: FailureMessage | null;
  readonly onEdit: (editing: VendorListEditing) => void;
  readonly onInherit: (item: SectionVendorList) => void;
  readonly onSave: (item: SectionVendorList, entries: VendorListEntry[]) => void;
  readonly onCancel: () => void;
}

/** The fifteen sections from an answer already in hand. Rendered by the static harness. */
export function VendorListsView({
  items,
  canEditProject,
  canEditGlobal,
  editing,
  pending,
  failure,
  onEdit,
  onInherit,
  onSave,
  onCancel,
}: VendorListsViewProps) {
  return (
    <div className={styles.frame}>
      {failure !== null && editing === null ? (
        <ErrorState
          title="Список не изменён."
          detail={failure.detail}
          correlationId={failure.correlationId}
        />
      ) : null}
      <table className={styles.table} data-vendor-lists="">
        <thead>
          <tr>
            <th className={styles.cell}>Раздел</th>
            <th className={styles.cell}>Действует</th>
            <th className={styles.cell}>Поставщики</th>
            <th className={styles.cell} />
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const open = editing !== null && editing.sectionCode === item.section_code;
            const projectOverride =
              item.project_revision !== null && item.project_revision.mode === 'list';
            return (
              <tr key={item.section_code} data-vendor-section={item.section_code} data-vendor-source={item.source}>
                <td className={styles.cell}>{sectionTitle(item.section_code)}</td>
                <td className={styles.cell}>
                  {VENDOR_SOURCE_LABELS[item.source]}
                  {item.effective === null ? null : (
                    <>
                      <br />
                      <span className="am-note">{revisionNote(item.effective)}</span>
                    </>
                  )}
                </td>
                <td className={styles.cell}>
                  <EntriesView revision={item.effective} />
                  {item.source === 'project' ? (
                    <p className="am-note">
                      Общий список: <EntriesView revision={item.global_revision} />
                    </p>
                  ) : null}
                </td>
                <td className={styles.cell}>
                  {open && editing !== null ? (
                    <VendorListEditor
                      title={
                        editing.scope === 'project'
                          ? 'Список проекта для раздела'
                          : 'Общий список для раздела'
                      }
                      initial={
                        (editing.scope === 'project'
                          ? (projectOverride ? item.project_revision : item.global_revision)
                          : item.global_revision
                        )?.entries ?? []
                      }
                      pending={pending}
                      failure={failure}
                      onSave={(entries) => onSave(item, entries)}
                      onCancel={onCancel}
                    />
                  ) : (
                    <>
                      {canEditProject ? (
                        <button
                          type="button"
                          className="am-button am-button--quiet am-button--small"
                          onClick={() => onEdit({ sectionCode: item.section_code, scope: 'project' })}
                        >
                          Изменить список проекта
                        </button>
                      ) : null}
                      {canEditProject && projectOverride ? (
                        <button
                          type="button"
                          className="am-button am-button--quiet am-button--small"
                          disabled={pending}
                          onClick={() => onInherit(item)}
                        >
                          Вернуться к общему списку
                        </button>
                      ) : null}
                      {canEditGlobal ? (
                        <button
                          type="button"
                          className="am-button am-button--quiet am-button--small"
                          onClick={() => onEdit({ sectionCode: item.section_code, scope: 'global' })}
                        >
                          Изменить общий список
                        </button>
                      ) : null}
                    </>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export interface VendorListsPanelProps {
  readonly projectUid: ProjectUid;
  readonly roles: readonly Role[];
}

export function VendorListsPanel({ projectUid, roles }: VendorListsPanelProps) {
  const lists = useEffectiveVendorLists(projectUid);
  const [editing, setEditing] = useState<VendorListEditing | null>(null);
  const setProject = useSetProjectVendorList();
  const setGlobal = useSetGlobalVendorList();
  const failed = setProject.error ?? setGlobal.error ?? null;

  const close = () => {
    setEditing(null);
    setProject.reset();
    setGlobal.reset();
  };

  if (lists.isPending) return <LoadingState what="вендор-листы" />;
  if (lists.isError) {
    const failure = failureMessage(lists.error);
    return (
      <ErrorState
        title="Вендор-листы не удалось прочитать."
        detail={failure.detail}
        correlationId={failure.correlationId}
        onRetry={() => void lists.refetch()}
      />
    );
  }

  return (
    <VendorListsView
      items={lists.data.items}
      canEditProject={roles.includes('expert')}
      canEditGlobal={roles.includes('admin')}
      editing={editing}
      pending={setProject.isPending || setGlobal.isPending}
      failure={failed === null ? null : vendorListFailureMessage(failed)}
      onEdit={(next) => {
        setProject.reset();
        setGlobal.reset();
        setEditing(next);
      }}
      onInherit={(item) =>
        setProject.mutate({
          projectUid,
          sectionCode: item.section_code,
          mode: 'inherit',
          entries: [],
          expectedVendorListId: item.project_revision?.vendor_list_id ?? null,
        })
      }
      onSave={(item, entries) => {
        if (editing === null) return;
        if (editing.scope === 'project') {
          setProject.mutate(
            {
              projectUid,
              sectionCode: item.section_code,
              mode: 'list',
              entries,
              expectedVendorListId: item.project_revision?.vendor_list_id ?? null,
            },
            { onSuccess: () => setEditing(null) },
          );
        } else {
          setGlobal.mutate(
            {
              sectionCode: item.section_code,
              entries,
              expectedVendorListId: item.global_revision?.vendor_list_id ?? null,
            },
            { onSuccess: () => setEditing(null) },
          );
        }
      }}
      onCancel={close}
    />
  );
}
