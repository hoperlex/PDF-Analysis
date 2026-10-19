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
 * The route parameter is checked for shape only. A string that is not a `prj_<ULID>` is a
 * malformed URL, which is a different thing from a project the server says does not exist,
 * and saying so costs no request. The identity is never parsed for meaning beyond that.
 */

import Link from 'next/link';
import { useRouter } from 'next/navigation';

import type { DocumentVersion } from '@/shared/api';
import { PageShell, UnsupportedState } from '@/shared/ui';
import { routes } from '@/shared/lib';
import { looksLikeProjectUid } from '@/entities/project';
import { ProjectSections } from '@/widgets/project-sections';
import { UploadPanel } from '@/widgets/upload-panel';

export interface ProjectDetailPageProps {
  readonly projectUid: string;
}

export function ProjectDetailPage({ projectUid }: ProjectDetailPageProps) {
  const router = useRouter();

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
      <ProjectSections projectUid={projectUid} />

      <UploadPanel projectUid={projectUid} onUploaded={goToVersion} />
    </PageShell>
  );
}
