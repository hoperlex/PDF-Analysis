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
 * `W60-OPT-PROPOSALS-01` adds «Предложения» to that tab (`widgets/optimisation-proposals`):
 * the deterministic cheaper-analog proposals of an АР set, with the experts' decisions.
 * The optimisation tab reads nothing until it is opened, so a cold load of the project still
 * makes exactly the calls the documents need. The session's roles, as the route's guard read
 * them, decide which controls that tab draws; the API still checks every write.
 *
 * The route parameter is checked for shape only. A string that is not a `prj_<ULID>` is a
 * malformed URL, which is a different thing from a project the server says does not exist,
 * and saying so costs no request. The identity is never parsed for meaning beyond that.
 */

import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import type { DocumentVersion, Role } from '@/shared/api';
import { PageShell, UnsupportedState } from '@/shared/ui';
import { routes } from '@/shared/lib';
import { AuditTallyLine, tallyOfCounts } from '@/entities/document-version';
import { looksLikeProjectUid, useProject } from '@/entities/project';
import { OptimisationByDocument } from '@/widgets/optimisation-proposals';
import { ProjectOptimisation } from '@/widgets/project-optimisation';
import { ProjectSections } from '@/widgets/project-sections';
import { UploadPanel } from '@/widgets/upload-panel';
import styles from './project-detail-page.module.css';

export interface ProjectDetailPageProps {
  readonly projectUid: string;
  /** The session's roles, as the route's guard read them. */
  readonly roles?: readonly Role[] | undefined;
}

type ProjectTab = 'documents' | 'optimisation';

const NO_PARAMS = new URLSearchParams();

const TABS: readonly { readonly tab: ProjectTab; readonly label: string }[] = [
  { tab: 'documents', label: 'Документы' },
  { tab: 'optimisation', label: 'Оптимизация' },
];

/**
 * `UI-A-22`: the tab lives in the address (`?tab=`), so a link, a reload and «Назад» return to the same
 * tab. An absent or unknown value is the first tab, said plainly by the address once a tab is chosen.
 */
export function tabOf(value: string | null): ProjectTab {
  return TABS.some((entry) => entry.tab === value) ? (value as ProjectTab) : 'documents';
}

export function ProjectDetailPage({ projectUid, roles = [] }: ProjectDetailPageProps) {
  const router = useRouter();
  // Outside the app router (a static render, a test without its contexts) both hooks answer `null`:
  // the first tab, and a change of tab written onto the project's own address.
  const pathname = usePathname() ?? routes.project(projectUid);
  const searchParams = useSearchParams() ?? NO_PARAMS;
  const tab = tabOf(searchParams.get('tab'));
  // `UI-PARITY-P0N`: the page is titled with the project's name, as the original's, read by its identity.
  const project = useProject(looksLikeProjectUid(projectUid) ? projectUid : null);
  const setTab = (next: ProjectTab) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('tab', next);
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  };

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
      title={project.data?.name ?? 'Проект'}
      surface="canvas"
      subtitle={<code>{projectUid}</code>}
      actions={<Link href={routes.projects()}>Все проекты</Link>}
    >
      {/* `UI-A-35`: the original's row of numbers for the whole project, from the counters `getProject` carries. */}
      {project.data?.audit_counts === undefined ? null : (
        <div className={styles.summary}>
          <AuditTallyLine tally={tallyOfCounts(project.data.audit_counts)} label={project.data.name} />
        </div>
      )}
      <nav className={styles.tabs} aria-label="Разделы проекта" data-project-tabs={tab}>
        {TABS.map((entry) => (
          <button
            key={entry.tab}
            type="button"
            className={styles.tab}
            aria-pressed={entry.tab === tab}
            onClick={() => setTab(entry.tab)}
          >
            {entry.label}
          </button>
        ))}
      </nav>

      {tab === 'documents' ? (
        <div className={styles.documentGrid}>
          <section className={styles.panel} aria-label="Документы по разделам">
            <ProjectSections projectUid={projectUid} />
          </section>
          <section className={styles.panel} id="upload" aria-label="Добавить документ">
            <UploadPanel projectUid={projectUid} onUploaded={goToVersion} />
          </section>
        </div>
      ) : (
        <div className={styles.stack}>
          <section className={styles.panel} aria-label="Прайс-листы и вендор-листы">
            <ProjectOptimisation projectUid={projectUid} roles={roles} />
          </section>
          {/* `R-151r`: passes and proposals live on each document's own tab; the project keeps the summary. */}
          <section className={styles.panel} aria-label="Предложения по документам">
            <OptimisationByDocument projectUid={projectUid} />
          </section>
        </div>
      )}
    </PageShell>
  );
}
