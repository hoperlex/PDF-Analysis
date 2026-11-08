import type { Role } from '@/shared/api';

import type { UserCommand } from './use-manage-user';

/** The second entry is UI confirmation only; it is never sent to the API. */
export function confirmedTemporaryPassword(password: string, repeat: string): string | null {
  return password.length > 0 && password === repeat ? password : null;
}

/**
 * What a change of roles has to be confirmed for, if anything (`UI-A-93`). The original asks before it makes an account an
 * administrator («Администратор может всё, включая управление пользователями»); this also asks before an administrator takes
 * the role from their own account, which is the one change that locks the person out of this screen. Anything else is sent
 * as it stands.
 */
export type RoleChangeConfirmation = 'grant-admin' | 'drop-own-admin';

export function roleChangeConfirmation(
  current: readonly Role[],
  next: readonly Role[],
  isSelf: boolean,
): RoleChangeConfirmation | null {
  if (next.includes('admin') && !current.includes('admin')) return 'grant-admin';
  if (isSelf && current.includes('admin') && !next.includes('admin')) return 'drop-own-admin';
  return null;
}

/**
 * The sentence that says a command went through, in the words of what it did. Every command but a purge (which leaves the
 * screen) is answered, so a press is never followed by silence and an administrator who changed roles is told, as the original
 * tells them, that the person's earlier sessions are over.
 */
export function userCommandDone(kind: UserCommand['kind']): string {
  switch (kind) {
    case 'names': return 'Имя сохранено.';
    case 'roles': return 'Роли сохранены. Прежние пропуска отозваны: пользователю потребуется войти снова.';
    case 'archive': return 'Учётная запись в архиве: её пропуска больше не принимаются.';
    case 'end-sessions': return 'Сеансы завершены. Пользователю потребуется войти снова.';
    case 'restore': return 'Учётная запись восстановлена.';
    case 'reset-password': return 'Временный пароль задан. Прежние пропуска отозваны; при следующем входе пользователь задаст свой.';
    case 'purge': return 'Учётная запись удалена.';
  }
}
