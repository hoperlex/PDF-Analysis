import type { Role } from '@/shared/api';

/** The API remains authoritative; these checks prevent a known-invalid UI command. */
export function approvedRoles(roles: readonly Role[]): Role[] | null {
  return roles.length > 0 ? [...roles] : null;
}

export function approvalIntentSignature(requestId: string, roles: readonly Role[]): string {
  return `approve:${requestId}:${roles.join(',')}`;
}

export function rejectionReason(value: string): string | null {
  const reason = value.trim();
  return reason.length >= 1 && reason.length <= 256 ? reason : null;
}
