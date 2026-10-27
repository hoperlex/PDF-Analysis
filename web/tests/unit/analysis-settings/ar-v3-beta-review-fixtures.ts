/**
 * The AR v3 beta group review as the server answers it: six scopes, one of each state the panel
 * draws (available with provisional evidence, failed, verification refused, and three pending).
 *
 * One fixture, two readers: the panel's own test, and the contrast census (`tests/unit/styles/
 * screens.ts`), which must render the panel's loaded state to measure the rules that state alone
 * carries (`._member details`, `._quote`).
 */

import type { Account, ArV3BetaGroupReview, Finding, FindingPage } from '@/shared/api';

import { finding, observation } from '../review/fixtures';

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

/** The run of the first scope: the one member the fixture above gives an available review. */
export const AVAILABLE_RUN_ID = groupReviewFixture().members[0]!.run_id;
export const NORM_QUOTE = 'Минимальная ширина эвакуационных путей составляет 1,4 м.';
export const PDF_QUOTE = 'Ширина эвакуационных путей принята не менее 1,2 м';

/**
 * `AR-V3-DECISIONS-01`: one published finding of that run, as the server serves an AR v3 beta finding
 * (`R-146as`): the PDF anchor, one certified norm citation, the model's sentences and a proposed
 * severity; no `required_value` and no `stated_value` (the profile serves none). Cyrillic on purpose
 * (the language guard reads it as application chrome otherwise).
 */
export function v3FindingFixture(overrides: Partial<Finding> = {}): Finding {
  const base = observation({
    category: 'evacuation',
    finding_text: 'Проверить ширину прохода.',
    recommendation_text: 'Сверить проект и норму.',
    proposed_severity: 'operational',
    evidence: [{
      evidence_ordinal: 0, page_number: 7, quote: PDF_QUOTE, char_start: 10, char_end: 10 + PDF_QUOTE.length,
    }],
    norm_citations: [{
      norms_snapshot_id: 'ns_01M59N8QNBVN91ACA2HCE6VE74', norm_document_id: 'ndoc_01M59N8QNBVN91ACA2HCE6VE74',
      norm_paragraph_id: 'npar_01M59N8QNBVN91ACA2HCE6VE74', designation: 'СП 1.13130', title: 'Эвакуационные пути',
      clause_number: '4.2.5', page_label: 3, quote: NORM_QUOTE, state: 'verified', source_attribution: 'unattributed',
    }],
  });
  return finding({ category: 'evacuation', run_id: AVAILABLE_RUN_ID, observation: base, ...overrides });
}

export function runFindingsPage(items: Finding[]): FindingPage {
  return { items, page: { next_cursor: null } } as FindingPage;
}

export function accountFixture(roles: Account['roles']): Account {
  return {
    archived_at: null, display_label: 'Сьютова Е.', first_name: 'Е', is_default_credential: false,
    last_name: 'Сьютова', login: 'e@suite.invalid', middle_name: null, profile_complete: true, roles,
    user_uid: 'usr_01M59N8QNBVN91ACA2HCE6VE74',
  } as Account;
}
