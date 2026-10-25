/**
 * The AR v3 beta group review as the server answers it: six scopes, one of each state the panel
 * draws (available with provisional evidence, failed, verification refused, and three pending).
 *
 * One fixture, two readers: the panel's own test, and the contrast census (`tests/unit/styles/
 * screens.ts`), which must render the panel's loaded state to measure the rules that state alone
 * carries (`._member details`, `._quote`).
 */

import type { ArV3BetaGroupReview } from '@/shared/api';

export const GROUP_ID = 'arg_01M2545JSD15ETSNNV904X991K';
export const SCOPES = ['F1', 'F2', 'A1', 'A2', 'S1', 'S2'] as const;

export function groupReviewFixture(): ArV3BetaGroupReview {
  return {
    group_id: GROUP_ID,
    version_uid: 'ver_01M2545JSD15ETSNNV904X991J',
    members: SCOPES.map((scope, index): ArV3BetaGroupReview['members'][number] => ({
      scope_id: scope,
      run_id: `run_01M2545JSD15ETSNNV904X991${'KMNPQR'[index]}`,
      run_state: index === 0 ? 'published' : index === 1 ? 'failed' : index === 2 ? 'partial' : 'queued',
      review_state: index === 0 ? 'available' : index === 1 ? 'failed' : index === 2 ? 'verification_refused' : 'pending',
      terminal_reason: index === 1 ? 'dependency_unavailable' : null,
      refusal_code: index === 2 ? 'storage_integrity_error' : null,
      review: index === 0 ? {
        topics: [{
          item_id: 'C01', mode: 'provisional_citation', reason: 'edition check',
          source_ids: ['D1_LOCAL'], review_status: 'requires_expert_review',
          provisional_citation_count: 1,
        }],
        provisional_citations: [{
          proposal_ordinal: 0,
          evidence: [{ page_number: 3, quote: 'ширина двери' }],
          citations: [{
            item_id: 'C01', label: 'N1', document_id: 'ndoc_example',
            paragraph_id: 'npar_example', raw_quote: '<script>цитата</script>', state: 'grounded',
          }],
        }],
        withheld_proposal_count: 1,
        rejected_proposal_count: 0,
      } : null,
    })),
  };
}
