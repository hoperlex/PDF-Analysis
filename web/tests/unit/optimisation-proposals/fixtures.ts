/**
 * The «Предложения» seeds (`W60-OPT-PROPOSALS-01`), shared by their unit tests, the rendered-
 * language guard and the contrast census.
 *
 * Every string a seed carries is Cyrillic, a number, an identity or a contract enum, so anything
 * Latin a render shows is chrome the application authored. The shapes reach every branch the
 * widget has: the set chooser and its empty state, no pass yet, a pass with proposals in every
 * decision state (one with a saving, one without), a pass with no proposals, a filter that
 * admits nothing, each refused read, each refusal of a start, the decision form in its states
 * and the history.
 */

import { createElement } from 'react';
import type { ReactElement } from 'react';
import type { QueryClient } from '@tanstack/react-query';

import type {
  DocumentVersion,
  OptimisationPass,
  OptimisationProposal,
  OptimisationProposalPage,
  ProposalDecision,
  ProposalDecisionState,
} from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { PASS_REFUSAL_TEXT, PROPOSAL_PAGE_LIMIT } from '@/entities/optimisation-proposal';
import { ProposalDecisionFormView } from '@/features/decide-optimisation-proposal';
import { StartOptimisationPassView } from '@/features/start-optimisation-pass';
import {
  ExportProposalsView,
  OptimisationProposals,
  PassList,
  ProposalCard,
  ProposalHistoryPanelView,
  ProposalHistoryView,
  ProposalListView,
  ProposalSetChooser,
} from '@/widgets/optimisation-proposals';

import { seedError } from '../screens/harness';
import { OPT_PROJECT_UID, optimisationApiError } from '../optimisation/fixtures';

export const PROPOSALS_PROJECT_UID = OPT_PROJECT_UID;
export const AR_DOCUMENT_UID = 'doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8H';
export const OTHER_DOCUMENT_UID = 'doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8J';
export const VERSION_UID = 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8K';
export const RUN_ID = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8M';
export const PASS_ID = 'opp_01J9ZQ8K7NHVXW3T2R5M6P4Q8N';
export const OLDER_PASS_ID = 'opp_01J9ZQ8K7NHVXW3T2R5M6P4Q8P';
export const DOOR_PROPOSAL = 'opr_01J9ZQ8K7NHVXW3T2R5M6P4Q8Q';
export const TAPE_PROPOSAL = 'opr_01J9ZQ8K7NHVXW3T2R5M6P4Q8R';
const EXPERT_UID = 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8E';
const CORRELATION = '0f0e9d8c-7b6a-4948-b726-150413021100';

export function arVersion(overrides: Partial<DocumentVersion> = {}): DocumentVersion {
  return {
    version_uid: VERSION_UID,
    document_uid: AR_DOCUMENT_UID,
    project_uid: PROPOSALS_PROJECT_UID,
    version_ordinal: 2,
    media_type: 'application/pdf',
    byte_size: 58978,
    sha256: '6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f',
    page_count: 8,
    published_at: '2026-10-20T06:55:52.642022Z',
    input_manifest: [],
    display_title: 'Комплект АР',
    classification: {
      version_uid: VERSION_UID,
      project_stage: 'R',
      section_code: 'AR',
      confirmed_at: '2026-10-20T08:00:00Z',
      confirmed_by_user_uid: EXPERT_UID,
      revision: 1,
    },
    ...overrides,
  };
}

export function otherSectionVersion(): DocumentVersion {
  return arVersion({
    document_uid: OTHER_DOCUMENT_UID,
    version_uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8S',
    display_title: 'Комплект КЖ',
    classification: {
      version_uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8S',
      project_stage: 'R',
      section_code: 'KJ',
      confirmed_at: '2026-10-20T08:00:00Z',
      confirmed_by_user_uid: EXPERT_UID,
      revision: 1,
    },
  });
}

/** A set no expert has classified: the `classification` key is absent, not `undefined`. */
export function unclassifiedVersion(): DocumentVersion {
  const version: Record<string, unknown> = { ...arVersion() };
  delete version['classification'];
  return version as unknown as DocumentVersion;
}

export function pass(overrides: Partial<OptimisationPass> = {}): OptimisationPass {
  return {
    optimisation_pass_id: PASS_ID,
    project_uid: PROPOSALS_PROJECT_UID,
    document_uid: AR_DOCUMENT_UID,
    version_uid: VERSION_UID,
    run_id: RUN_ID,
    text_layer_sha256: 'e'.repeat(64),
    price_list_id: 'prl_01J9ZQ8K7NHVXW3T2R5M6P4Q8C',
    vendor_list_id: 'vnl_01J9ZQ8K7NHVXW3T2R5M6P4Q8T',
    vendor_list_source: 'global',
    extraction_algorithm: 'specification-text-v1',
    match_algorithm: 'price-match-v1',
    generator_version: 'cheaper-analog-v1',
    specification_row_count: 6,
    matched_row_count: 4,
    proposed_row_count: 2,
    proposal_count: 2,
    decision_counts: { pending: 1, accept: 0, reject: 0, revise: 1 },
    started_by_user_uid: EXPERT_UID,
    started_by_label: 'Петрова А.',
    started_at: '2026-10-20T09:00:00Z',
    ...overrides,
  };
}

export function decision(overrides: Partial<ProposalDecision> = {}): ProposalDecision {
  return {
    proposal_decision_id: 'opd_01J9ZQ8K7NHVXW3T2R5M6P4Q8V',
    optimisation_proposal_id: DOOR_PROPOSAL,
    verdict: 'revise',
    comment: 'Уточнить марку двери у поставщика.',
    actor_user_uid: EXPERT_UID,
    actor_label: 'Петрова А.',
    decided_at: '2026-10-20T09:30:00Z',
    ...overrides,
  };
}

export function proposal(overrides: Partial<OptimisationProposal> = {}): OptimisationProposal {
  return {
    optimisation_proposal_id: DOOR_PROPOSAL,
    optimisation_pass_id: PASS_ID,
    ordinal: 1,
    proposal_type: 'cheaper_analog',
    spec_row_key: `sr-${'a'.repeat(32)}`,
    page_number: 2,
    sheet_label: '10',
    line_start: 3,
    line_end: 4,
    table_ordinal: 1,
    row_position: '1',
    row_text: 'Дверь противопожарная ДПМ-01/60 ООО «Промет»',
    matched_position: {
      price_list_position_id: 'prp_01J9ZQ8K7NHVXW3T2R5M6P4Q8W',
      row_number: 2,
      code: null,
      name: 'Дверь противопожарная',
      mark: 'ДПМ-01/60',
      vendor: 'Промет',
    },
    matched_basis: 'mark',
    proposed_position: {
      price_list_position_id: 'prp_01J9ZQ8K7NHVXW3T2R5M6P4Q8X',
      row_number: 3,
      code: null,
      name: 'Дверь противопожарная',
      mark: 'ДПМ-02/60',
      vendor: 'Кнауф Гипс',
    },
    analog_basis: 'code_family',
    name_similarity: '1',
    proposed_vendor: 'Кнауф Гипс',
    unit: 'шт',
    quantity: '4',
    quantity_text: '4',
    current_unit_price: '25000',
    proposed_unit_price: '21000.5',
    currency: 'RUB',
    saving: '17998',
    rationale:
      'Более дешёвый аналог: «Дверь противопожарная» (ДПМ-02/60), поставщик Кнауф Гипс, вместо «Дверь противопожарная» (ДПМ-01/60); основание: одно семейство кода «дпм».',
    current_verdict: 'revise',
    current_decision: decision(),
    ...overrides,
  };
}

/** A proposal whose quantity is a dash in the specification: both prices, no saving. */
export function tapeProposal(overrides: Partial<OptimisationProposal> = {}): OptimisationProposal {
  return proposal({
    optimisation_proposal_id: TAPE_PROPOSAL,
    ordinal: 2,
    row_text: 'Монтажная лента компл. - по месту',
    matched_position: {
      price_list_position_id: 'prp_01J9ZQ8K7NHVXW3T2R5M6P4Q8Y',
      row_number: 9,
      code: 'ЛМ-100',
      name: 'Монтажная лента',
      mark: null,
      vendor: null,
    },
    matched_basis: 'name',
    proposed_position: {
      price_list_position_id: 'prp_01J9ZQ8K7NHVXW3T2R5M6P4Q8Z',
      row_number: 10,
      code: null,
      name: 'Монтажная лента армированная',
      mark: null,
      vendor: 'Кнауф Гипс',
    },
    analog_basis: 'name_similarity',
    name_similarity: '0.6666',
    unit: 'компл',
    quantity: null,
    quantity_text: '-',
    current_unit_price: '450',
    proposed_unit_price: '300',
    saving: null,
    current_verdict: 'pending',
    current_decision: null,
    ...overrides,
  });
}

export function proposalPage(overrides: Partial<OptimisationProposalPage> = {}): OptimisationProposalPage {
  return {
    optimisation_pass: pass(),
    decision: null,
    items: [proposal(), tapeProposal()],
    offset: 0,
    limit: PROPOSAL_PAGE_LIMIT,
    total: 2,
    next_offset: null,
    ...overrides,
  };
}

const KEYS = {
  documents: queryKeys.projects.documents(PROPOSALS_PROJECT_UID, undefined, 50),
  passes: queryKeys.optimisation.passes(PROPOSALS_PROJECT_UID, AR_DOCUMENT_UID),
  proposals: queryKeys.optimisation.proposals(PASS_ID, null, 0, PROPOSAL_PAGE_LIMIT),
};

const noMore = { next_cursor: null } as never;

/** Seed a client with a loaded «Предложения» section. */
export function seedLoadedProposals(client: QueryClient): void {
  client.setQueryData(KEYS.documents, { items: [arVersion(), otherSectionVersion()], page: noMore });
  client.setQueryData(KEYS.passes, {
    items: [
      pass(),
      pass({
        optimisation_pass_id: OLDER_PASS_ID,
        started_at: '2026-10-19T09:00:00Z',
        proposal_count: 1,
        decision_counts: { pending: 0, accept: 1, reject: 0, revise: 0 },
      }),
    ],
  });
  client.setQueryData(KEYS.proposals, proposalPage());
}

const noop = (): void => undefined;

/** One render of a shape: a name, an element and how to seed the client it renders under. */
export interface ProposalShape {
  readonly name: string;
  readonly make: () => ReactElement;
  readonly seedClient?: (client: QueryClient) => void;
}

function failure(detail: string) {
  return {
    kind: 'conflict' as const,
    detail,
    correlationId: CORRELATION,
    errorCode: 'conflict' as const,
    retryable: false,
  };
}

/** Every shape the section can show, for the static renders. */
export function proposalShapes(): readonly ProposalShape[] {
  const section = (roles: readonly ('expert' | 'admin')[]) => () =>
    createElement(OptimisationProposals, { projectUid: PROPOSALS_PROJECT_UID, roles: [...roles] });
  const listView = (page: OptimisationProposalPage, canDecide: boolean) => () =>
    createElement(ProposalListView, { page, canDecide, onDecision: noop, onPage: noop });
  const states: readonly ProposalDecisionState[] = ['pending', 'accept', 'reject', 'revise'];
  return [
    { name: 'proposals-loaded', make: section(['expert', 'admin']), seedClient: seedLoadedProposals },
    { name: 'proposals-loaded-admin', make: section(['admin']), seedClient: seedLoadedProposals },
    // Nothing seeded: the documents are in flight.
    { name: 'proposals-pending', make: section(['expert']) },
    {
      name: 'proposals-passes-pending',
      make: section(['expert']),
      seedClient: (client) => {
        client.setQueryData(KEYS.documents, { items: [arVersion()], page: noMore });
      },
    },
    {
      name: 'proposals-no-classified-sets',
      make: section(['expert']),
      seedClient: (client) => {
        client.setQueryData(KEYS.documents, { items: [unclassifiedVersion()], page: { next_cursor: 'c2' } as never });
      },
    },
    {
      name: 'proposals-no-passes',
      make: section(['expert']),
      seedClient: (client) => {
        client.setQueryData(KEYS.documents, { items: [arVersion()], page: noMore });
        client.setQueryData(KEYS.passes, { items: [] });
      },
    },
    {
      name: 'proposals-documents-refused',
      make: section(['expert']),
      seedClient: (client) => {
        seedError(client, KEYS.documents, optimisationApiError(503, 'dependency_unavailable'));
      },
    },
    {
      name: 'proposals-passes-refused',
      make: section(['expert']),
      seedClient: (client) => {
        client.setQueryData(KEYS.documents, { items: [arVersion()], page: noMore });
        seedError(client, KEYS.passes, optimisationApiError(503, 'dependency_unavailable'));
      },
    },
    {
      name: 'proposals-pass-refused',
      make: section(['expert']),
      seedClient: (client) => {
        client.setQueryData(KEYS.documents, { items: [arVersion()], page: noMore });
        client.setQueryData(KEYS.passes, { items: [pass()] });
        seedError(client, KEYS.proposals, optimisationApiError(404, 'not_found'));
      },
    },
    {
      name: 'proposals-empty-pass',
      make: section(['expert']),
      seedClient: (client) => {
        const empty = pass({
          proposal_count: 0,
          proposed_row_count: 0,
          decision_counts: { pending: 0, accept: 0, reject: 0, revise: 0 },
        });
        client.setQueryData(KEYS.documents, { items: [arVersion()], page: noMore });
        client.setQueryData(KEYS.passes, { items: [empty] });
        client.setQueryData(KEYS.proposals, proposalPage({ optimisation_pass: empty, items: [], total: 0 }));
      },
    },
    {
      name: 'proposals-filter-admits-nothing',
      make: listView(
        proposalPage({ decision: 'accept', items: [], total: 0, optimisation_pass: pass() }),
        true,
      ),
    },
    {
      name: 'proposals-second-page',
      make: listView(proposalPage({ offset: 20, total: 22, next_offset: null, items: [tapeProposal()] }), false),
    },
    {
      name: 'proposals-set-chooser',
      make: () =>
        createElement(ProposalSetChooser, {
          sets: [arVersion(), arVersion({ document_uid: OTHER_DOCUMENT_UID, display_title: 'Комплект АР, корпус 2' })],
          selected: AR_DOCUMENT_UID,
          onSelect: noop,
          partial: true,
        }),
    },
    {
      name: 'proposals-pass-list',
      make: () => createElement(PassList, { passes: [pass()], active: PASS_ID, onOpen: noop }),
    },
    {
      name: 'proposals-history',
      make: () => createElement(ProposalCard, {
        proposal: proposal(),
        controls: null,
        history: createElement(ProposalHistoryPanelView, {
          open: true, pending: false, failure: null,
          items: [decision({ verdict: 'accept', comment: null }), decision()],
          onToggle: noop, onRetry: noop,
        }),
      }),
    },
    {
      name: 'proposals-history-empty',
      make: () => createElement(ProposalCard, {
        proposal: tapeProposal(),
        controls: null,
        history: createElement(ProposalHistoryPanelView, {
          open: true, pending: false, failure: null, items: [], onToggle: noop, onRetry: noop,
        }),
      }),
    },
    {
      name: 'proposals-history-pending',
      make: () => createElement(ProposalCard, {
        proposal: proposal(),
        controls: null,
        history: createElement(ProposalHistoryPanelView, {
          open: true, pending: true, failure: null, items: null, onToggle: noop, onRetry: noop,
        }),
      }),
    },
    {
      name: 'proposals-history-refused',
      make: () => createElement(ProposalCard, {
        proposal: proposal(),
        controls: null,
        history: createElement(ProposalHistoryPanelView, {
          open: true, pending: false, failure: failure('История решений недоступна.'), items: null,
          onToggle: noop, onRetry: noop,
        }),
      }),
    },
    {
      name: 'proposals-history-closed',
      make: () => createElement(ProposalCard, {
        proposal: proposal(),
        controls: null,
        history: createElement(ProposalHistoryPanelView, {
          open: false, pending: false, failure: null, items: null, onToggle: noop, onRetry: noop,
        }),
      }),
    },
    {
      name: 'proposals-history-list',
      make: () => createElement(ProposalHistoryView, { items: [decision()] }),
    },
    {
      name: 'proposals-export-refused',
      make: () => createElement(ExportProposalsView, {
        pending: false, failure: failure('Файл не удалось выгрузить.'), onDownload: noop,
      }),
    },
    {
      name: 'proposals-export-pending',
      make: () => createElement(ExportProposalsView, { pending: true, failure: null, onDownload: noop }),
    },
    ...states.map((state) => ({
      name: `proposal-state-${state}`,
      make: listView(
        proposalPage({
          items: [proposal({
            current_verdict: state,
            current_decision: state === 'pending' ? null : decision({ verdict: state }),
          })],
          total: 1,
        }),
        true,
      ),
    })),
    {
      name: 'start-pass-expert',
      make: () => createElement(StartOptimisationPassView, {
        canStart: true, chosen: true, pending: false, failure: null, onStart: noop,
      }),
    },
    {
      name: 'start-pass-pending',
      make: () => createElement(StartOptimisationPassView, {
        canStart: true, chosen: true, pending: true, failure: null, onStart: noop,
      }),
    },
    {
      name: 'start-pass-readonly',
      make: () => createElement(StartOptimisationPassView, {
        canStart: false, chosen: true, pending: false, failure: null, onStart: noop,
      }),
    },
    ...Object.entries(PASS_REFUSAL_TEXT).map(([reason, detail]) => ({
      name: `start-pass-refused-${reason}`,
      make: () => createElement(StartOptimisationPassView, {
        canStart: true, chosen: true, pending: false, failure: failure(detail), onStart: noop,
      }),
    })),
    {
      name: 'decision-form-idle',
      make: () => createElement(ProposalDecisionFormView, {
        proposalId: DOOR_PROPOSAL, current: null, comment: '', pending: false, failure: null,
        onComment: noop, onDecide: noop,
      }),
    },
    {
      name: 'decision-form-repeat-blocked',
      make: () => createElement(ProposalDecisionFormView, {
        proposalId: DOOR_PROPOSAL, current: decision({ verdict: 'accept', comment: null }), comment: '',
        pending: false, failure: null, onComment: noop, onDecide: noop,
      }),
    },
    {
      name: 'decision-form-revise-ready',
      make: () => createElement(ProposalDecisionFormView, {
        proposalId: DOOR_PROPOSAL, current: null, comment: 'Заменить марку.', pending: false, failure: null,
        onComment: noop, onDecide: noop,
      }),
    },
    {
      name: 'decision-form-refused',
      make: () => createElement(ProposalDecisionFormView, {
        proposalId: DOOR_PROPOSAL, current: null, comment: 'Заменить марку.', pending: false,
        failure: failure('Для решения «На доработку» нужен комментарий: напишите, что изменить.'),
        onComment: noop, onDecide: noop,
      }),
    },
  ];
}
