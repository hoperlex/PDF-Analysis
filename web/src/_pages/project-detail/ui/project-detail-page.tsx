'use client';

/**
 * `/projects/{project_uid}` — upload a PDF, then start a run over the published version.
 *
 * The route parameter is checked for shape only. A string that is not a `prj_<ULID>` is
 * a malformed URL, which is a different thing from a project the server says does not
 * exist, and saying so costs no request. The identity is never parsed for meaning
 * beyond that.
 */

import { useRouter } from 'next/navigation';

import type { RunStatus } from '@/shared/api';
import { PageShell, UnsupportedState } from '@/shared/ui';
import { looksLikeProjectUid } from '@/entities/project';
import { UploadPanel } from '@/widgets/upload-panel';

export interface ProjectDetailPageProps {
  readonly projectUid: string;
}

export function ProjectDetailPage({ projectUid }: ProjectDetailPageProps) {
  const router = useRouter();

  if (!looksLikeProjectUid(projectUid)) {
    return (
      <PageShell title="Project">
        <UnsupportedState
          title="That is not a project address."
          detail="A project is addressed by an opaque identifier. Nothing was requested."
        />
      </PageShell>
    );
  }

  const goToRun = (run: RunStatus) => {
    router.push(`/projects/${projectUid}/runs/${run.run_id}`);
  };

  return (
    <PageShell
      title="Project"
      subtitle={
        <>
          <code>{projectUid}</code>
        </>
      }
    >
      <UploadPanel projectUid={projectUid} onRunStarted={goToRun} />
    </PageShell>
  );
}
