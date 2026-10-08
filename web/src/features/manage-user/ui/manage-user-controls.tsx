'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import type { FormEvent } from 'react';

import type { Account } from '@/shared/api';
import { ROLE_VALUES } from '@/shared/api';
import { roleLabels } from '@/entities/account';
import { userFailure } from '@/entities/user';
import { ErrorState } from '@/shared/ui';

import type { UserCommand } from '../model/use-manage-user';
import { useManageUser } from '../model/use-manage-user';
import { confirmedTemporaryPassword } from '../model/confirmation';

export function ManageUserControls({ account }: { readonly account: Account }) {
  const router = useRouter();
  const manage = useManageUser(account.user_uid);
  const [confirmPurge, setConfirmPurge] = useState(false);
  const [passwordMismatch, setPasswordMismatch] = useState(false);

  async function execute(command: UserCommand): Promise<boolean> {
    try {
      const result = await manage.mutateAsync(command);
      if (result.kind === 'purged') router.push('/admin/users');
      return true;
    } catch {
      // The typed failure is shown below. No second write or optimistic state follows.
      return false;
    }
  }

  function saveNames(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const middle = String(form.get('middle_name') ?? '').trim();
    void execute({ kind: 'names', names: {
      last_name: String(form.get('last_name') ?? '').trim(),
      first_name: String(form.get('first_name') ?? '').trim(),
      ...(middle ? { middle_name: middle } : {}),
    } });
  }

  function saveRoles(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const selected = new FormData(event.currentTarget).getAll('role');
    const roles = ROLE_VALUES.filter((role) => selected.includes(role));
    void execute({ kind: 'roles', roles });
  }

  function resetPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fields = new FormData(event.currentTarget);
    const password = confirmedTemporaryPassword(
      String(fields.get('temporary_password') ?? ''),
      String(fields.get('confirm_password') ?? ''),
    );
    if (password === null) { setPasswordMismatch(true); return; }
    setPasswordMismatch(false);
    const form = event.currentTarget;
    void execute({ kind: 'reset-password', temporaryPassword: password }).then((succeeded) => {
      if (succeeded) form.reset();
    });
  }

  const failure = manage.isError ? userFailure(manage.error) : null;
  return (
    <div>
      <form className="am-form" key={`names-${account.last_name}-${account.first_name}-${account.middle_name}`} onSubmit={saveNames}>
        <h2>Имя пользователя</h2>
        <div className="am-form__field"><label htmlFor="user-last"><strong>Фамилия</strong></label><input id="user-last" name="last_name" type="text" defaultValue={account.last_name ?? ''} required maxLength={60} /></div>
        <div className="am-form__field"><label htmlFor="user-first"><strong>Имя</strong></label><input id="user-first" name="first_name" type="text" defaultValue={account.first_name ?? ''} required maxLength={60} /></div>
        <div className="am-form__field"><label htmlFor="user-middle"><strong>Отчество (необязательно)</strong></label><input id="user-middle" name="middle_name" type="text" defaultValue={account.middle_name ?? ''} maxLength={60} /></div>
        <button className="am-button" type="submit" disabled={manage.isPending}>Сохранить имя</button>
      </form>

      <form className="am-form" key={`roles-${account.roles.join('-')}`} onSubmit={saveRoles}>
        <h2>Роли</h2>
        {ROLE_VALUES.map((role) => <label key={role} className="am-form__field"><input type="checkbox" name="role" value={role} defaultChecked={account.roles.includes(role)} /> {roleLabels([role])[0]}</label>)}
        <p className="am-form__hint">При изменении ролей все прежние пропуска этой учётной записи отзываются. Пользователю потребуется войти снова.</p>
        <button className="am-button" type="submit" disabled={manage.isPending}>Сохранить роли</button>
      </form>

      {account.archived_at === null ? (
        <div>
          <button className="am-button am-button--quiet" type="button" disabled={manage.isPending} onClick={() => void execute({ kind: 'archive' })}>Архивировать учётную запись</button>
          <form className="am-form" onSubmit={resetPassword}>
            <h2>Временный пароль</h2>
            <p className="am-form__hint">После сброса все прежние пропуска отзываются, а новый пароль нужно будет сменить при следующем входе. Значение не показывается после отправки.</p>
            <div className="am-form__field"><label htmlFor="user-password"><strong>Временный пароль</strong></label><input id="user-password" name="temporary_password" type="password" autoComplete="new-password" required minLength={8} maxLength={1024} /></div>
            <div className="am-form__field"><label htmlFor="user-password-confirm"><strong>Повторите временный пароль</strong></label><input id="user-password-confirm" name="confirm_password" type="password" autoComplete="new-password" required minLength={8} maxLength={1024} /></div>
            {passwordMismatch ? <div data-user-failure="password_mismatch"><ErrorState title="Пароль не сброшен" detail="Пароль и его повтор не совпадают. Запрос не отправлен." /></div> : null}
            <button className="am-button" type="submit" disabled={manage.isPending}>Сбросить пароль</button>
          </form>
        </div>
      ) : (
        <div>
          <button className="am-button am-button--quiet" type="button" disabled={manage.isPending} onClick={() => void execute({ kind: 'restore' })}>Восстановить учётную запись</button>
          {confirmPurge ? (
            <div role="group" aria-label="Подтверждение удаления">
              <p className="am-note">Безвозвратно удалить учётную запись {account.login}? Это действие нельзя отменить.</p>
              <button className="am-button" type="button" disabled={manage.isPending} onClick={() => void execute({ kind: 'purge' })}>Подтвердить удаление</button>
              <button className="am-button am-button--quiet" type="button" onClick={() => setConfirmPurge(false)}>Отмена</button>
            </div>
          ) : <button className="am-button am-button--quiet" type="button" onClick={() => setConfirmPurge(true)}>Удалить навсегда</button>}
        </div>
      )}
      {manage.isSuccess ? <p className="am-note" role="status">Действие выполнено.</p> : null}
      {failure ? <div data-user-failure={failure.kind}><ErrorState title="Изменение не выполнено" detail={failure.detail} correlationId={failure.correlationId} /></div> : null}
    </div>
  );
}
