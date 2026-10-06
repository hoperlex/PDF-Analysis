/**
 * `/403` — a screen the session may not open, and the role that would open it.
 *
 * `W50-PLAN.md` §3.2, decision four: a session lacking every role a screen's registry row
 * lists is sent here with the address it asked for in `from`. The route validates `from`
 * with the screen registry's one validator and resolves the roles that row requires; this
 * screen names them in Russian (`entities/account`'s labels) and says who assigns roles.
 *
 * `from` itself is never shown: it is an address the browser controls, and a screen that
 * echoed it would be a place to put words in front of a reviewer. A missing or invalid
 * `from`, or one naming a screen that requires no role, renders the same screen without a
 * role name.
 *
 * A role value the labels do not know is not reachable here — the roles come from the
 * registry, which is typed by the contract's set — and if one were, `roleLabels` throws
 * rather than inventing a label.
 */

import Link from 'next/link';

import { roleLabels } from '@/entities/account';
import type { Role } from '@/shared/api';
import { PageShell, UnsupportedState } from '@/shared/ui';

export interface ForbiddenPageProps {
  /** The roles the asked-for screen requires, any one of which opens it; `null` when unknown. */
  readonly requiredRoles: readonly Role[] | null;
}

function requirement(requiredRoles: readonly Role[] | null): string {
  if (requiredRoles === null || requiredRoles.length === 0) {
    return 'У вашей учётной записи нет роли, которая открывает этот экран.';
  }
  const labels = roleLabels(requiredRoles).map((label) => `«${label}»`);
  return labels.length === 1
    ? `Этот экран открывается только с ролью ${labels[0]}, а у вашей учётной записи её нет.`
    : `Этот экран открывается с одной из ролей: ${labels.join(', ')}, а у вашей учётной записи нет ни одной из них.`;
}

export function ForbiddenPage({ requiredRoles }: ForbiddenPageProps) {
  return (
    <PageShell title="Доступ закрыт" actions={<Link href="/">На главную</Link>}>
      <UnsupportedState
        title={requirement(requiredRoles)}
        detail="Роли учётным записям назначает администратор. Повторная попытка ничего не изменит, пока роль не назначена."
      />
    </PageShell>
  );
}
