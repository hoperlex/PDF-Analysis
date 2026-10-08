import { createElement } from 'react';
import { describe, expect, it, vi } from 'vitest';

import type { ErrorEnvelope, RegistrationRequest } from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import { UnknownRegistrationStatusError, registrationFailure } from '@/entities/registration-request';
import { RegistrationDecisionControls, approvalIntentSignature, approvedRoles, refreshDecisionCache, rejectionReason } from '@/features/decide-registration';
import { RegistrationQueue } from '@/widgets/registration-queue';
import { resolveIntentKey } from '@/shared/lib';

import { newClient, renderScreen } from '../screens/harness';

const REQUEST: RegistrationRequest = {
  created_user_uid: null,
  decided_at: null,
  decided_by: null,
  display_label: 'Заявкина М. П.',
  first_name: 'Мария',
  last_name: 'Заявкина',
  login: 'zayavkina@example.org',
  middle_name: 'Петровна',
  rejection_reason: null,
  request_id: 'reg_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
  status: 'pending',
  submitted_at: '2026-10-08T00:00:00Z',
};

function queueMarkup(request: RegistrationRequest): string {
  const client = newClient();
  client.setQueryData(queryKeys.registrations.list({ status: 'pending', limit: 50 }), {
    items: [request], page: { next_cursor: null }, pending_total: request.status === 'pending' ? 1 : 0,
  });
  return renderScreen(client, createElement(RegistrationQueue));
}

function refusal(code: ErrorEnvelope['error_code']): ApiError {
  return new ApiError(409, {
    contract_version: '1.0.0-draft.1', error_code: code,
    message: 'Refused', correlation_id: 'cid-request-1', retryable: false,
  }, 'cid-request-1');
}

describe('administrator registration queue', () => {
  it('shows the global pending count and actions only for a pending request', () => {
    const markup = queueMarkup(REQUEST);
    expect(markup).toContain('data-pending-total="1"');
    expect(markup).toContain('Одобрить заявку');
    expect(markup).toContain('Отклонить заявку');
    expect(markup).not.toContain('type="password"');
  });

  it('shows a decided request and its reason without decision controls', () => {
    const rejected: RegistrationRequest = { ...REQUEST, status: 'rejected', decided_at: '2026-10-08T01:00:00Z', rejection_reason: 'Не прошла проверку.' };
    const markup = queueMarkup(rejected);
    expect(markup).toContain('Отклонена');
    expect(markup).toContain('Причина отказа: Не прошла проверку.');
    expect(markup).not.toContain('Одобрить заявку');
    expect(renderScreen(newClient(), createElement(RegistrationDecisionControls, { request: rejected }))).toBe('');
  });

  it('refuses zero roles and a 257-character reason before a command', () => {
    expect(approvedRoles([])).toBeNull();
    expect(approvedRoles(['expert'])).toEqual(['expert']);
    expect(rejectionReason(' '.repeat(5))).toBeNull();
    expect(rejectionReason('а'.repeat(257))).toBeNull();
    expect(rejectionReason('  Причина.  ')).toBe('Причина.');
  });

  it('reuses the approval key on retry and changes it when the role payload changes', () => {
    const mint = vi.fn().mockReturnValueOnce('key-one').mockReturnValueOnce('key-two');
    const first = resolveIntentKey(null, approvalIntentSignature(REQUEST.request_id, ['expert']), mint);
    const retry = resolveIntentKey(first, approvalIntentSignature(REQUEST.request_id, ['expert']), mint);
    const changed = resolveIntentKey(retry, approvalIntentSignature(REQUEST.request_id, ['expert', 'admin']), mint);
    expect(retry.idempotencyKey).toBe('key-one');
    expect(changed.idempotencyKey).toBe('key-two');
    expect(mint).toHaveBeenCalledTimes(2);
  });

  it('keeps unknown status and server refusals typed', () => {
    expect(registrationFailure(new UnknownRegistrationStatusError('later')).kind).toBe('unknown_status');
    expect(registrationFailure(refusal('state_transition_not_allowed')).kind).toBe('state_transition_not_allowed');
    expect(registrationFailure(refusal('idempotency_key_reuse')).kind).toBe('idempotency_key_reuse');
  });

  it('invalidates queue and home count on either decision, users only on approval', () => {
    const client = newClient();
    const invalidate = vi.spyOn(client, 'invalidateQueries');
    refreshDecisionCache(client, 'approve');
    expect(invalidate).toHaveBeenCalledWith({ queryKey: queryKeys.registrations.all() });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: queryKeys.users.all() });
    invalidate.mockClear();
    refreshDecisionCache(client, 'reject');
    expect(invalidate).toHaveBeenCalledWith({ queryKey: queryKeys.registrations.all() });
    expect(invalidate).not.toHaveBeenCalledWith({ queryKey: queryKeys.users.all() });
  });
});
