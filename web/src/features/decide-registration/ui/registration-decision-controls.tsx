'use client';

import { useState } from 'react';
import type { FormEvent } from 'react';

import type { RegistrationRequest, Role } from '@/shared/api';
import { ROLE_VALUES } from '@/shared/api';
import { roleLabels } from '@/entities/account';
import { registrationFailure } from '@/entities/registration-request';
import { useIntentKey } from '@/shared/lib';
import { ErrorState } from '@/shared/ui';

import { approvalIntentSignature, approvedRoles, rejectionReason } from '../model/validation';
import { useDecideRegistration } from '../model/use-decide-registration';

export function RegistrationDecisionControls({ request }: { readonly request: RegistrationRequest }) {
  const [selectedRoles, setSelectedRoles] = useState<Role[]>([]);
  const [reason, setReason] = useState('');
  const [localFailure, setLocalFailure] = useState<'roles' | 'reason' | null>(null);
  const decision = useDecideRegistration();
  const roles = ROLE_VALUES.filter((role) => selectedRoles.includes(role));
  const idempotencyKey = useIntentKey(approvalIntentSignature(request.request_id, roles));

  if (request.status !== 'pending') return null;

  function toggleRole(role: Role, checked: boolean) {
    setSelectedRoles((current) => checked ? [...current, role] : current.filter((value) => value !== role));
    setLocalFailure(null);
    decision.reset();
  }

  function approve(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const valid = approvedRoles(roles);
    if (valid === null) { setLocalFailure('roles'); return; }
    setLocalFailure(null);
    decision.mutate({ kind: 'approve', requestId: request.request_id, roles: valid, idempotencyKey });
  }

  function reject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const valid = rejectionReason(reason);
    if (valid === null) { setLocalFailure('reason'); return; }
    setLocalFailure(null);
    decision.mutate({ kind: 'reject', requestId: request.request_id, reason: valid });
  }

  const failure = decision.isError ? registrationFailure(decision.error) : null;
  return (
    <div>
      <form className="am-form" onSubmit={approve}>
        <fieldset>
          <legend>Роли новой учётной записи</legend>
          {ROLE_VALUES.map((role) => <label key={role} className="am-form__field"><input type="checkbox" checked={selectedRoles.includes(role)} onChange={(event) => toggleRole(role, event.target.checked)} /> {roleLabels([role])[0]}</label>)}
        </fieldset>
        <button className="am-button" type="submit" disabled={decision.isPending}>Одобрить заявку</button>
      </form>
      <form className="am-form" onSubmit={reject}>
        <div className="am-form__field"><label htmlFor={`reject-${request.request_id}`}><strong>Причина отказа для администратора</strong></label><textarea id={`reject-${request.request_id}`} value={reason} onChange={(event) => { setReason(event.target.value); setLocalFailure(null); decision.reset(); }} required minLength={1} maxLength={256} /></div>
        <p className="am-form__hint">Причина остаётся доступна администраторам и не показывается заявителю.</p>
        <button className="am-button am-button--quiet" type="submit" disabled={decision.isPending}>Отклонить заявку</button>
      </form>
      {localFailure === 'roles' ? <div data-registration-decision-failure="roles"><ErrorState title="Заявка не одобрена" detail="Выберите хотя бы одну роль. Запрос не отправлен." /></div> : null}
      {localFailure === 'reason' ? <div data-registration-decision-failure="reason"><ErrorState title="Заявка не отклонена" detail="Причина должна содержать от 1 до 256 символов. Запрос не отправлен." /></div> : null}
      {failure ? <div data-registration-decision-failure={failure.kind}><ErrorState title="Решение не сохранено" detail={failure.detail} correlationId={failure.correlationId} /></div> : null}
      {decision.isSuccess ? <p className="am-note" role="status">Решение сохранено. Список обновляется.</p> : null}
    </div>
  );
}
