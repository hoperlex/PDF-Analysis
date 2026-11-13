/** @jsxRuntime automatic */

import { unverifiedReason, verificationReasonLabel } from '../model/verification';
import type { VerificationSubject } from '../model/verification';

export function EvidenceLimitation({ finding }: { readonly finding: VerificationSubject }) {
  const reason = unverifiedReason(finding);
  if (reason === null) return null;
  return <span className="am-note" data-evidence-limitation="unverified" title={verificationReasonLabel(reason)}>Источник требует проверки</span>;
}
