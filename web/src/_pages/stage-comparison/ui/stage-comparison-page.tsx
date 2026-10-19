'use client';

/**
 * `/projects/{project_uid}/versions/{version_uid}/comparison` — this version against another
 * version of the same set, and two runs of this version side by side.
 *
 * **`W59-VERSION-COMPARE-01` put the version comparison first.** «Сравнение версий» asks
 * `compareDocumentVersions` for this version and another version of its set that the reviewer
 * chooses (`widgets/version-comparison`): refusals with their reasons, proposed sheet pairs,
 * raw line differences and proposed finding matches. The run comparison below it is the
 * `W43-COMPARE` widget, unchanged and still lazy.
 *
 * `R-23` sorted ten legacy screens and this is one of the two whose answer was still
 * unbuilt: *«Сравнение стадий — очень важно; хотя бы скелет с заглушками сейчас,
 * реализация по ходу альфы.»*
 *
 * **Why it hangs off the version and not off a run.** A comparison is only meaningful
 * between two runs of the *same* published version: the version is immutable, so a
 * difference between two runs of it is a difference in the analysis rather than in the
 * document. Mounting it under one run would make the other run a parameter of the first,
 * which is a claim about their relationship that nothing supports — the same reasoning
 * that puts `review` under the run that produced the findings.
 *
 * **Composition only.** The shell from `shared/ui`, the query inside the widget, the back
 * links from `shared/lib`'s route module. Nothing is computed here.
 *
 * **Reached from the version screen.** `routes.comparison()` exists and the version screen
 * links here twice: beside its runs («Сравнить два прогона») and beside its stage-and-section
 * panel («Сравнить с другой версией комплекта», `W59-VERSION-COMPARE-01`).
 */

import Link from 'next/link';

import { PageShell, UnsupportedState } from '@/shared/ui';
import { routes } from '@/shared/lib';
import { looksLikeProjectUid } from '@/entities/project';
import { looksLikeVersionUid } from '@/entities/document-version';

import { VersionComparison } from '@/widgets/version-comparison';

import { LazyStageComparison } from './lazy-stage-comparison';

export interface StageComparisonPageProps {
  readonly projectUid: string;
  readonly versionUid: string;
}

export function StageComparisonPage({ projectUid, versionUid }: StageComparisonPageProps) {
  const wellFormed = looksLikeProjectUid(projectUid) && looksLikeVersionUid(versionUid);

  if (!wellFormed) {
    return (
      <PageShell
        title="Сравнение версий"
        actions={<Link href={routes.projects()}>Все проекты</Link>}
      >
        <UnsupportedState
          title="Это не адрес версии."
          detail="Проект и версия адресуются непрозрачными идентификаторами. Запроса не было."
        />
      </PageShell>
    );
  }

  return (
    <PageShell
      title="Сравнение версий"
      subtitle={<code>{versionUid}</code>}
      actions={
        <>
          <Link href={routes.version(projectUid, versionUid)}>К версии</Link>{' '}
          <Link href={routes.project(projectUid)}>К проекту</Link>
        </>
      }
    >
      <p>
        Эта версия сравнивается с другой версией того же комплекта: одной стадии и одного
        подтверждённого раздела, или стадии П с более поздней стадией Р.
      </p>
      <VersionComparison projectUid={projectUid} versionUid={versionUid} />
      <h2>Сравнение прогонов</h2>
      <p>
        Версия документа неизменяема, поэтому два её прогона отличаются только тем, как
        прошёл анализ. Ниже — то, что о каждом прогоне записала система.
      </p>
      <LazyStageComparison versionUid={versionUid} />
    </PageShell>
  );
}
