'use client';

/**
 * `/projects/{project_uid}/versions/{version_uid}/comparison` — two runs of one version,
 * side by side.
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
 * **NOTHING LINKS HERE YET, and that is reported rather than papered over.**
 * `W43-COMPARE`'s `allowed_paths` do not include `web/src/shared/lib/**` or the version
 * screen, so this stream may add neither `routes.comparison()` nor the link that would use
 * it. The address is served — paste it into a fresh tab and it renders — and it is reached
 * from no other screen. Writing the string into a `Link` here instead would be the defect
 * `shared/lib/routes.ts`'s own header names: an address that exists in several places can
 * be wrong in all but one of them. `docs/program/W43-COMPARE.md` §7 carries the one-line
 * addition and the caller for whoever owns those files next.
 */

import Link from 'next/link';

import { PageShell, UnsupportedState } from '@/shared/ui';
import { routes } from '@/shared/lib';
import { looksLikeProjectUid } from '@/entities/project';
import { looksLikeVersionUid } from '@/entities/document-version';
import { StageComparison } from '@/widgets/stage-comparison';

export interface StageComparisonPageProps {
  readonly projectUid: string;
  readonly versionUid: string;
}

export function StageComparisonPage({ projectUid, versionUid }: StageComparisonPageProps) {
  const wellFormed = looksLikeProjectUid(projectUid) && looksLikeVersionUid(versionUid);

  if (!wellFormed) {
    return (
      <PageShell
        title="Сравнение прогонов"
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
      title="Сравнение прогонов"
      subtitle={<code>{versionUid}</code>}
      actions={
        <>
          <Link href={routes.version(projectUid, versionUid)}>К версии</Link>{' '}
          <Link href={routes.project(projectUid)}>К проекту</Link>
        </>
      }
    >
      <p>
        Версия документа неизменяема, поэтому два её прогона отличаются только тем, как
        прошёл анализ. Ниже — то, что о каждом прогоне записала система.
      </p>
      <StageComparison versionUid={versionUid} />
    </PageShell>
  );
}
