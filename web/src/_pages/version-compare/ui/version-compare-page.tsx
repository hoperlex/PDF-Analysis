'use client';

/**
 * `/version-comparison` — «Сравнение версий» (plan §1.1, wave C1).
 *
 * A project is chosen on the screen (there is no global object, unlike the original); then two tabs. «Проекты и этапы» is
 * the table of the project's document sets and the steps of their comparison; a row opens «Сравнение листов» for that set:
 * the transitions between adjacent versions, the matrix of sheets and the viewer of one pair. The button «Загрузить проект
 * со всеми версиями» opens the upload dialogs.
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
import { useAddressProject, useProjectList } from '@/entities/project';
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
import styles from './version-compare-page.module.css';

export interface VersionComparePageProps {
  /** Where the screen starts; a reload starts from nothing. The static render starts here too. */
  readonly initial?: {
    readonly projectUid?: ProjectUid;
    readonly tab?: CompareTab;
    readonly documentUid?: DocumentUid;
    readonly upload?: UploadMode;
  };
}

export const CHOOSE_PROJECT_TITLE = 'Выберите проект';
export const CHOOSE_PROJECT_DETAIL =
  'Сравнение версий ведётся внутри проекта: выберите проект, и экран покажет его комплекты и версии.';
export const UPLOAD_BUTTON = 'Загрузить проект со всеми версиями';

export function VersionComparePage({ initial }: VersionComparePageProps) {
  const projects = useProjectList();
  const me = useMe();
  const product = useProductVersion(true);
  // `R-150c`: the project follows the header, so it lives in the address; `initial` still seeds a static render.
  const [addressProject, chooseProject] = useAddressProject(routes.versionComparison());
  const chosen = (addressProject ?? initial?.projectUid ?? null) as ProjectUid | null;
  const setChosen = (next: ProjectUid | null) => chooseProject(next);
  // `UI-B-102`: the open set and the tab are in the address too (`?set=&tab=`), so Back, reload and a pasted link return to them.
  const [address, goTo] = useCompareAddress({
    ...(initial?.documentUid === undefined ? {} : { documentUid: initial.documentUid }),
    ...(initial?.tab === undefined ? {} : { tab: initial.tab }),
  });
  const addressDocument = address.documentUid as DocumentUid | null;
  const [upload, setUpload] = useState<UploadMode | null>(initial?.upload ?? null);

  const items = projects.data?.items ?? [];
  const projectUid: ProjectUid | null = chosen ?? (items.length === 1 ? ((items[0]?.project_uid ?? null) as ProjectUid | null) : null);
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

  const chooser = (
    <label className={styles.chooser}>
      Проект
      <select
        value={projectUid ?? ''}
        onChange={(event) => {
          // The address drops `set` and `tab` with the old project (`switchProject`).
          setChosen(event.target.value === '' ? null : (event.target.value as ProjectUid));
          setUpload(null);
        }}
      >
        <option value="">— выберите —</option>
        {items.map((project) => (
          <option key={project.project_uid} value={project.project_uid}>
            {project.name}
          </option>
        ))}
      </select>
    </label>
  );

  return (
    <PageShell
      title="Сравнение версий"
      subtitle="Версии комплектов проекта: загрузка, разбор, сопоставление листов и сравнение соседних версий."
      actions={
        <>
        {product.data?.comparison_modules === 'versions,stages' ? <a className="am-button" href={withProjectParam(routes.stageComparison(), projectUid)}>Сравнение стадий</a> : null}
        <button
          type="button"
          className="am-button"
          disabled={!mayAct || projectUid === null}
          title={
            projectUid === null
              ? 'Сначала выберите проект.'
              : !mayAct
                ? 'Загружать версии для сравнения может эксперт, когда модуль включён.'
                : 'Загрузить PDF: один проект со всеми версиями или несколько проектов пакетом.'
          }
          onClick={() => setUpload('single')}
        >
          {UPLOAD_BUTTON}
        </button>
        </>
      }
    >
      {projects.isPending ? <LoadingState what="проекты" /> : null}
      {projects.isError ? (
        <ErrorState
          title="Проекты не открылись"
          detail={classifyListingFailure(projects.error, { collection: 'проекты', parent: 'project' }).detail}
          onRetry={() => void projects.refetch()}
        />
      ) : null}
      {projects.isSuccess ? <div className={styles.toolbar}>{chooser}</div> : null}
      {moduleOff ? <ModuleOffState /> : null}

      {projectUid === null ? (
        projects.isSuccess ? (
          items.length === 0 ? (
            <EmptyState title="Проектов пока нет." detail="Создайте проект на странице «Проекты», затем загрузите в него версии." />
          ) : (
            <EmptyState title={CHOOSE_PROJECT_TITLE} detail={CHOOSE_PROJECT_DETAIL} />
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
              Комплект из адреса не найден в этом проекте. Выберите комплект в таблице.
            </p>
          ) : null}
          <AiQueueNotice sets={overview.data?.sets ?? []} />
          <CompareTabs
            active={tab}
            onSelect={(next) => goTo({ documentUid, tab: next })}
            disabled={documentUid === null ? { sheets: 'Сначала выберите комплект на вкладке «Проекты и этапы».' } : {}}
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
                renderViewer={({ pair, rasterSize, navigation }) => (
                  <ComparisonViewer pair={pair} navigation={navigation} changes={{ mayAct }} {...(rasterSize === undefined ? {} : { rasterSize })} />
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
