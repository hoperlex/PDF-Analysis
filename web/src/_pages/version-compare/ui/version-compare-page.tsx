'use client';

/**
 * `/version-comparison` — «Сравнение версий» (plan §1.1, wave C1; `UIP-S17-01`).
 *
 * **The object** (`R-150c`, `UIP-G-06`; the registry class is `optional`) is the one of the top strip: the address says it first
 * (`?project=<uid>`), and an address that says nothing opens on the object the account chose last. There is no card that chooses
 * it on this screen and no subtitle. Without an object («Все объекты», or none remembered) the screen says in one line where to
 * choose it; it does not pick the only object of the list for the reader. `initial.projectUid` still seeds a static render, which
 * has no address.
 *
 * Then two tabs. «Документы и этапы» is the table of the object's document sets and the steps of their comparison; a row opens
 * «Сравнение листов» for that set: the transitions between adjacent versions, the matrix of sheets and the viewer of one pair.
 * «Сравнение стадий» is a quiet link at the right of the row of the tabs. The button «Загрузить документ со всеми версиями» opens
 * the upload dialogs.
 *
 * **Composition only.** The tables and the matrix are `widgets/version-series`, the dialogs `widgets/comparison-upload`, the
 * viewer `widgets/comparison-viewer` (with its side panel «Изменения в листе»), the window «Сформировать PDF-отчёт…»
 * `widgets/comparison-report`; the viewer and the dialogs are sibling widgets, so this page is where they meet. What
 * is read and sent is `entities/version-series`.
 *
 * **The module.** `ProductVersion.comparison_modules` says whether «Сравнение версий» is served. A module that is off is
 * said so above the tabs and its controls that change anything are not drawn; an operation that is not wired yet answers
 * `503 dependency_unavailable`, and each widget shows that as the module's state — «Модуль ещё недоступен» — never as a crash.
 * A reader who is not an expert sees the state and no button that sends anything (`R-60`).
 */

import { useState } from 'react';

import type { DocumentUid, ProjectUid } from '@/shared/api';
import { EmptyState, ErrorState, LoadingState, PageShell } from '@/shared/ui';
import { classifyListingFailure, routes, withProjectParam } from '@/shared/lib';
import { useMe } from '@/entities/account';
import { useCurrentProject, useProjectList } from '@/entities/project';
import { useProductVersion } from '@/entities/release';
import { codeOf, useComparisonOverview, versionsModuleOn } from '@/entities/version-series';
import { ComparisonViewer } from '@/widgets/comparison-viewer';
import { ReportWindow } from '@/widgets/comparison-report';
import { UploadDialog } from '@/widgets/comparison-upload';
import type { UploadMode } from '@/widgets/comparison-upload';
import { AiQueueNotice, ModuleOffState, ProjectsAndStages, SheetsTab } from '@/widgets/version-series';

import type { CompareTab } from '../model/tabs';
import { useCompareAddress } from '../model/use-compare-address';

import { CompareTabs } from './compare-tabs';

export interface VersionComparePageProps {
  /** Where the screen starts; a reload starts from nothing. The static render starts here too. */
  readonly initial?: {
    readonly projectUid?: ProjectUid;
    readonly tab?: CompareTab;
    readonly documentUid?: DocumentUid;
    readonly upload?: UploadMode;
  };
}

/** What the screen says, in one line, when there is no object: where to choose it. */
export const CHOOSE_PROJECT_TITLE = 'Выберите объект в верхней строке';
export const UPLOAD_BUTTON = 'Загрузить документ со всеми версиями';

export function VersionComparePage({ initial }: VersionComparePageProps) {
  const projects = useProjectList();
  const me = useMe();
  const product = useProductVersion(true);
  // `R-150c`, `UIP-G-06`, `UIP-S17-01`: the object is the top strip's: the address, and where that is silent the account's last
  // object; `initial` still seeds a static render. The screen chooses nothing, so it keeps nothing for next time.
  const current = useCurrentProject(routes.versionComparison());
  // `UI-B-102`: the open set and the tab are in the address too (`?set=&tab=`), so Back, reload and a pasted link return to them.
  const [address, goTo] = useCompareAddress({
    ...(initial?.documentUid === undefined ? {} : { documentUid: initial.documentUid }),
    ...(initial?.tab === undefined ? {} : { tab: initial.tab }),
  });
  const addressDocument = address.documentUid as DocumentUid | null;
  const [upload, setUpload] = useState<UploadMode | null>(initial?.upload ?? null);

  const items = projects.data?.items ?? [];
  const projectUid = (current.projectUid ?? initial?.projectUid ?? null) as ProjectUid | null;
  // The account's answer is on its way: the last object may still arrive, so «выберите объект» is not said yet.
  const objectPending = projectUid === null && current.pending;
  const overview = useComparisonOverview(projectUid);

  const expert = me.data?.roles.includes('expert') === true;
  // Known and off: nothing that changes anything is drawn. Not yet known (or failed): the operations answer for themselves.
  const moduleOff = product.data !== undefined && !versionsModuleOn(product.data.comparison_modules);
  const mayAct = expert && !moduleOff;

  const selectedSet = addressDocument === null ? undefined : overview.data?.sets.find((set) => set.document_uid === addressDocument);
  // A set in the address that the project does not have is said, never replaced by another one (no silent fallback).
  const unknownSet = addressDocument !== null && overview.data !== undefined && selectedSet === undefined;
  const documentUid = unknownSet ? null : addressDocument;
  const tab: CompareTab = documentUid === null ? 'projects' : address.tab;
  const heading = selectedSet === undefined ? 'Комплект' : codeOf(selectedSet) === '' ? 'Комплект без шифра' : codeOf(selectedSet);

  return (
    <PageShell
      title="Сравнение версий"
      actions={
        <button
          type="button"
          className="am-button"
          disabled={!mayAct || projectUid === null}
          title={
            projectUid === null
              ? 'Сначала выберите объект в верхней строке.'
              : !mayAct
                ? 'Загружать версии для сравнения может эксперт, когда модуль включён.'
                : 'Загрузить PDF: один документ со всеми версиями или несколько документов пакетом.'
          }
          onClick={() => setUpload('single')}
        >
          {UPLOAD_BUTTON}
        </button>
      }
    >
      {projects.isPending ? <LoadingState what="объекты" /> : null}
      {projects.isError ? (
        <ErrorState
          title="Объекты не открылись"
          detail={classifyListingFailure(projects.error, { collection: 'объекты', parent: 'project' }).detail}
          onRetry={() => void projects.refetch()}
        />
      ) : null}
      {moduleOff ? <ModuleOffState /> : null}
      {objectPending ? <LoadingState what="объект" /> : null}

      {projectUid === null ? (
        projects.isSuccess && !objectPending ? (
          items.length === 0 ? (
            <EmptyState title="Объектов пока нет." detail="Создайте объект на странице «Объекты», затем загрузите в него версии." />
          ) : (
            <EmptyState title={CHOOSE_PROJECT_TITLE} />
          )
        ) : null
      ) : (
        <>
          {upload === null ? null : (
            <UploadDialog
              projectUid={projectUid}
              mode={upload}
              mayAct={mayAct}
              onSwitch={() => setUpload('batch')}
              onClose={() => setUpload(null)}
            />
          )}
          {unknownSet ? (
            <p role="status" data-compare-unknown-set="">
              Комплект из адреса не найден в этом объекте. Выберите комплект в таблице.
            </p>
          ) : null}
          <AiQueueNotice sets={overview.data?.sets ?? []} />
          <CompareTabs
            active={tab}
            onSelect={(next) => goTo({ documentUid, tab: next })}
            disabled={documentUid === null ? { sheets: 'Сначала выберите комплект на вкладке «Документы и этапы».' } : {}}
            aside={
              product.data?.comparison_modules === 'versions,stages' ? (
                <a className="am-button am-button--quiet am-button--small" href={withProjectParam(routes.stageComparison(), projectUid)}>
                  Сравнение стадий
                </a>
              ) : null
            }
            suffix={{
              ...(overview.data === undefined ? {} : { projects: String(overview.data.sets.length) }),
              ...(documentUid === null ? {} : { sheets: heading }),
            }}
          >
            {tab === 'projects' || documentUid === null ? (
              <ProjectsAndStages
                projectUid={projectUid}
                mayAct={mayAct}
                queueOnPage
                onOpen={(uid) => goTo({ documentUid: uid, tab: 'sheets' })}
              />
            ) : (
              <SheetsTab
                projectUid={projectUid}
                documentUid={documentUid}
                heading={heading}
                mayEdit={mayAct}
                renderViewer={({ pair, rasterSize, navigation, versionLabels }) => (
                  <ComparisonViewer
                    pair={pair}
                    navigation={navigation}
                    versionLabels={versionLabels}
                    changes={{ mayAct }}
                    {...(rasterSize === undefined ? {} : { rasterSize })}
                  />
                )}
                renderReport={({ series, names, mayAct: allowed, onClose }) => (
                  <ReportWindow series={series} names={names} mayAct={allowed} onClose={onClose} />
                )}
              />
            )}
          </CompareTabs>
        </>
      )}
    </PageShell>
  );
}
