'use client';

/**
 * `/dispatcher` — «Диспетчер» (`W61-DISPATCHER-01`, roadmap Q-2).
 *
 * An administrator assigns a project, or one document of it, to an expert and sees every
 * assignment with its status and history, and may reassign or cancel it. An expert sees the
 * work currently given to them and moves it: takes it, completes it or returns it with a
 * reason. The same screen for both, because the API decides what each reads and may do; the
 * roles the route's guard read only decide which controls are drawn.
 *
 * Two more reads: `getMe`, for the viewer's own account identity (which rows are theirs, so
 * the assignee's moves are offered only there), and, for an administrator, `listUsers`, for
 * the active experts a creation or a reassignment may name.
 */

import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';

import type { Account, Role } from '@/shared/api';
import { readProjectContext, switchProject } from '@/shared/lib';
import { useMe } from '@/entities/account';
import { useProjectList } from '@/entities/project';
import { USER_PAGE_LIMIT, useUsers } from '@/entities/user';
import { canAssignWork } from '@/entities/assignment';
import { CreateAssignmentForm } from '@/features/create-assignment';
import type { ExpertOption } from '@/features/transition-assignment';
import { AssignmentBoard } from '@/widgets/assignment-board';
import styles from './dispatcher-page.module.css';

export interface DispatcherPageProps {
  /** The session's roles, as the route's guard read them. */
  readonly roles: readonly Role[];
}

/** Active accounts holding `expert`, as the choices a creation or reassignment may name. */
export function expertOptions(accounts: readonly Account[]): readonly ExpertOption[] {
  return accounts
    .filter((account) => account.archived_at === null && account.roles.includes('expert'))
    .map((account) => ({ userUid: account.user_uid, label: account.display_label }));
}

/** This screen's registry address, the one `readProjectContext` classifies (`R-151m`: it follows the header). */
const DISPATCHER_ADDRESS = '/dispatcher';
const NO_PARAMS = new URLSearchParams();

/** «Все проекты» or the project's name, and the way back to all of them, as the dashboard says its scope. */
function ProjectScope({ projectUid, allProjectsHref }: { readonly projectUid: string | null; readonly allProjectsHref: string }) {
  const projects = useProjectList(undefined, { enabled: projectUid !== null });
  if (projectUid === null) return <p className="am-note" data-dispatcher-scope="all">Все проекты</p>;
  const name = projects.data?.items.find((item) => item.project_uid === projectUid)?.name ?? 'Проект';
  return (
    <p className="am-note" data-dispatcher-scope="project">
      Проект: {name} · <Link href={allProjectsHref}>Все проекты</Link>
    </p>
  );
}

function AdministratorTools({ roles, viewerUid, projectUid }: { readonly roles: readonly Role[]; readonly viewerUid: string | null; readonly projectUid: string | null }) {
  const users = useUsers({ includeArchived: false, limit: USER_PAGE_LIMIT });
  const experts = users.isSuccess ? expertOptions(users.data.items) : [];
  return (
    <div className={styles.layout}>
      <section className={`am-section ${styles.panel}`} data-dispatcher-create="">
        <h2>Назначить работу</h2>
        {users.isError ? (
          <p className="am-note" data-dispatcher-experts-failure="">
            Список экспертов не загружен — назначить работу сейчас нельзя.
          </p>
        ) : null}
        <CreateAssignmentForm key={projectUid ?? 'all'} experts={experts} defaultProjectUid={projectUid} />
      </section>
      <section className={`am-section ${styles.panel}`} data-dispatcher-list="">
        <h2>Назначения</h2>
        <AssignmentBoard key={projectUid ?? 'all'} roles={roles} viewerUid={viewerUid} experts={experts} projectUid={projectUid} />
      </section>
    </div>
  );
}

export function DispatcherPage({ roles }: DispatcherPageProps) {
  // `R-151m`: the project comes from the address only; a reload or a pasted link restores it.
  const pathname = usePathname();
  const searchParams = useSearchParams() ?? NO_PARAMS;
  const { projectUid } = readProjectContext(pathname ?? '', searchParams);
  const withoutProject = switchProject(searchParams, null).toString();
  const allProjectsHref = withoutProject === '' ? DISPATCHER_ADDRESS : `${DISPATCHER_ADDRESS}?${withoutProject}`;
  const me = useMe();
  const viewerUid = me.isSuccess ? me.data.user_uid : null;
  const admin = canAssignWork(roles);
  return (
    <section className="am-page" data-screen="dispatcher">
      <header className={`am-page__header ${styles.hero}`}>
        <h1 className="am-page__title">Диспетчер</h1>
        <p className="am-page__subtitle">
          {admin
            ? 'Назначение проектов и документов экспертам, их состояние и история.'
            : 'Работа, назначенная вам: возьмите её в работу, отметьте выполненной или верните с причиной.'}
        </p>
      </header>
      <div className="am-page__body am-page__body--canvas">
        <ProjectScope projectUid={projectUid} allProjectsHref={allProjectsHref} />
        {admin ? (
          <AdministratorTools roles={roles} viewerUid={viewerUid} projectUid={projectUid} />
        ) : (
          <section className={`am-section ${styles.panel}`} data-dispatcher-list="">
            <h2>Мои назначения</h2>
            <AssignmentBoard key={projectUid ?? 'all'} roles={roles} viewerUid={viewerUid} experts={[]} projectUid={projectUid} />
          </section>
        )}
      </div>
    </section>
  );
}
