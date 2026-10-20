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

import type { Account, Role } from '@/shared/api';
import { useMe } from '@/entities/account';
import { USER_PAGE_LIMIT, useUsers } from '@/entities/user';
import { canAssignWork } from '@/entities/assignment';
import { CreateAssignmentForm } from '@/features/create-assignment';
import type { ExpertOption } from '@/features/transition-assignment';
import { AssignmentBoard } from '@/widgets/assignment-board';

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

function AdministratorTools({ roles, viewerUid }: { readonly roles: readonly Role[]; readonly viewerUid: string | null }) {
  const users = useUsers({ includeArchived: false, limit: USER_PAGE_LIMIT });
  const experts = users.isSuccess ? expertOptions(users.data.items) : [];
  return (
    <>
      <section className="am-section" data-dispatcher-create="">
        <h2>Назначить работу</h2>
        {users.isError ? (
          <p className="am-note" data-dispatcher-experts-failure="">
            Список экспертов не загружен — назначить работу сейчас нельзя.
          </p>
        ) : null}
        <CreateAssignmentForm experts={experts} />
      </section>
      <section className="am-section" data-dispatcher-list="">
        <h2>Назначения</h2>
        <AssignmentBoard roles={roles} viewerUid={viewerUid} experts={experts} />
      </section>
    </>
  );
}

export function DispatcherPage({ roles }: DispatcherPageProps) {
  const me = useMe();
  const viewerUid = me.isSuccess ? me.data.user_uid : null;
  const admin = canAssignWork(roles);
  return (
    <section className="am-page" data-screen="dispatcher">
      <header className="am-page__header">
        <h1 className="am-page__title">Диспетчер</h1>
        <p className="am-page__subtitle">
          {admin
            ? 'Назначение проектов и документов экспертам, их состояние и история.'
            : 'Работа, назначенная вам: возьмите её в работу, отметьте выполненной или верните с причиной.'}
        </p>
      </header>
      <div className="am-page__body">
        {admin ? (
          <AdministratorTools roles={roles} viewerUid={viewerUid} />
        ) : (
          <section className="am-section" data-dispatcher-list="">
            <h2>Мои назначения</h2>
            <AssignmentBoard roles={roles} viewerUid={viewerUid} experts={[]} />
          </section>
        )}
      </div>
    </section>
  );
}
