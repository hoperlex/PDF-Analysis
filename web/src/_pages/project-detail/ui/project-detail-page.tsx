'use client';

/**
 * `/projects/{project_uid}` — one project: what is already in it, and how to add to it.
 *
 * **It fetches its own data.** `listDocuments` runs on mount. Before `D-16` this screen
 * queried nothing at all: it rendered the version held in React state by the upload that
 * had just happened, so a fresh tab made **zero** API calls and reported *"No version
 * published in this session"* over a project whose documents, versions, runs and
 * decisions had all survived in PostgreSQL and the store. `W15-RUN` §6 measured exactly
 * that, in a real browser, and this screen is the answer to it.
 *
 * The documents come first and the upload second. What is already here is what a returning
 * user came back for; the upload is the thing they do next.
 *
 * `W59-SECTION-UI-01`: the documents are shown as the project's structure — the fifteen
 * sections in the owner's `S-5` order, each holding the documents whose current version an
 * expert confirmed for it, then «Не классифицировано» (`widgets/project-sections`). It is the
 * same `listDocuments` read, grouped; the static fourteen-tab stub it replaces made no claim
 * about membership because nothing could, and now the version's own classification can.
 *
 * `W60-PRICE-LIST-01`: two tabs. «Документы» (the default, everything above) and «Оптимизация»
 * — the project's price list and the vendor lists per section (`widgets/project-optimisation`).
 * The optimisation tab reads nothing until it is opened, so a cold load of the project still
 * makes exactly the calls the documents need. The session's roles, as the route's guard read
 * them, decide which controls that tab draws; the API still checks every write.
 *
 * The route parameter is checked for shape only. A string that is not a `prj_<ULID>` is a
 * malformed URL, which is a different thing from a project the server says does not exist,
 * and saying so costs no request. The identity is never parsed for meaning beyond that.
 */

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import type { DocumentVersion, Role } from '@/shared/api';
import { PageShell, UnsupportedState } from '@/shared/ui';
import { routes } from '@/shared/lib';
import { looksLikeProjectUid } from '@/entities/project';
import { ProjectOptimisation } from '@/widgets/project-optimisation';
import { ProjectSections } from '@/widgets/project-sections';
import { UploadPanel } from '@/widgets/upload-panel';

export interface ProjectDetailPageProps {
  readonly projectUid: string;
  /** The session's roles, as the route's guard read them. */
  readonly roles?: readonly Role[] | undefined;
}

type ProjectTab = 'documents' | 'optimisation';

const TABS: readonly { readonly tab: ProjectTab; readonly label: string }[] = [
  { tab: 'documents', label: 'Документы' },
  { tab: 'optimisation', label: 'Оптимизация' },
];

export function ProjectDetailPage({ projectUid, roles = [] }: ProjectDetailPageProps) {
  const router = useRouter();
  const [tab, setTab] = useState<ProjectTab>('documents');

  if (!looksLikeProjectUid(projectUid)) {
    return (
      <PageShell title="Проект" actions={<Link href={routes.projects()}>Все проекты</Link>}>
        <UnsupportedState
          title="Это не адрес проекта."
          detail="Проект адресуется непрозрачным идентификатором. Запроса не было."
        />
      </PageShell>
    );
  }

  const goToVersion = (version: DocumentVersion) => {
    router.push(routes.version(version.project_uid, version.version_uid));
  };

  return (
    <PageShell
      title="Проект"
      subtitle={<code>{projectUid}</code>}
      actions={<Link href={routes.projects()}>Все проекты</Link>}
    >
      <nav aria-label="Разделы проекта" data-project-tabs={tab}>
        {TABS.map((entry) => (
          <button
            key={entry.tab}
            type="button"
            className={entry.tab === tab ? 'am-button' : 'am-button am-button--quiet'}
            aria-pressed={entry.tab === tab}
            onClick={() => setTab(entry.tab)}
          >
            {entry.label}
          </button>
        ))}
      </nav>

      {tab === 'documents' ? (
        <>
          <ProjectSections projectUid={projectUid} />

          <UploadPanel projectUid={projectUid} onUploaded={goToVersion} />
        </>
      ) : (
        <ProjectOptimisation projectUid={projectUid} roles={roles} />
      )}
    </PageShell>
  );
}
