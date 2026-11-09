/**
 * `UI-B-27`, `UI-B-20`: seeds of «Принято» and of the address of «Оптимизация разделов», shared by their tests and the
 * contrast census. Every string is Cyrillic, a number, an identity or a contract enum.
 */

import { createElement } from 'react';
import type { ReactElement } from 'react';
import type { QueryClient } from '@tanstack/react-query';

import type { AcceptedOptimisationProposal, AcceptedOptimisationProposalPage, Project, ProjectUid } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { ACCEPTED_PAGE_LIMIT } from '@/entities/optimisation-proposal';
import { SECTION_ROW_LIMIT } from '@/entities/section-specification';
import { SectionAcceptedOptimisations } from '@/widgets/section-accepted-optimisations';

import { optimisationApiError } from '../optimisation/fixtures';
import { seedError } from '../screens/harness';

export const ACCEPTED_PROJECT_A = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8A';
export const ACCEPTED_PROJECT_B = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8G';
export const ACCEPTED_DOCUMENT = 'doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8H';
export const ACCEPTED_VERSION = 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8K';
export const ACCEPTED_PASS = 'opp_01J9ZQ8K7NHVXW3T2R5M6P4Q8N';
export const ACCEPTED_DOOR = 'opr_01J9ZQ8K7NHVXW3T2R5M6P4Q8Q';
export const ACCEPTED_TAPE = 'opr_01J9ZQ8K7NHVXW3T2R5M6P4Q8R';

export function acceptedRow(over: Partial<AcceptedOptimisationProposal> = {}): AcceptedOptimisationProposal {
  return {
    optimisation_proposal_id: ACCEPTED_DOOR,
    optimisation_pass_id: ACCEPTED_PASS,
    proposal_decision_id: 'opd_01J9ZQ8K7NHVXW3T2R5M6P4Q8S',
    proposal_type: 'cheaper_analog',
    project_uid: ACCEPTED_PROJECT_A,
    project_name: 'Школа на пятьсот мест',
    document_uid: ACCEPTED_DOCUMENT,
    document_name: 'Комплект АР',
    version_uid: ACCEPTED_VERSION,
    section: 'AR',
    page_number: 2,
    row_position: '1',
    row_text: 'Дверь противопожарная ДПМ-01/60 ООО «Промет»',
    matched_name: 'Дверь противопожарная ДПМ-01/60',
    proposed_name: 'Дверь противопожарная ДПМ-02/60',
    proposed_vendor: 'Кнауф Гипс',
    unit: 'шт',
    quantity: '4',
    current_unit_price: '25000',
    proposed_unit_price: '21000',
    currency: 'RUB',
    saving: '16000',
    // `D-346`: 25000 → 21000 is 16 % of the price.
    saving_percent: '16',
    comment: 'Подходит по огнестойкости.',
    actor_label: 'Петрова А.',
    decided_at: '2026-11-06T09:30:00Z',
    carried_from: null,
    ...over,
  };
}

/** The tape: a quantity that is not a number, so no saving and no comment. */
export function acceptedTape(): AcceptedOptimisationProposal {
  return acceptedRow({
    optimisation_proposal_id: ACCEPTED_TAPE,
    proposal_decision_id: 'opd_01J9ZQ8K7NHVXW3T2R5M6P4Q8T',
    row_position: null,
    row_text: 'Монтажная лента',
    matched_name: 'Монтажная лента',
    proposed_name: 'Монтажная лента армированная',
    unit: 'компл',
    quantity: null,
    current_unit_price: '450',
    proposed_unit_price: '300',
    saving: null,
    // 450 → 300 is a third; it stands where the amount cannot be computed.
    saving_percent: '33.33',
    comment: null,
    decided_at: '2026-11-06T09:40:00Z',
  });
}

export function acceptedPage(over: Partial<AcceptedOptimisationProposalPage> = {}): AcceptedOptimisationProposalPage {
  return { items: [acceptedTape(), acceptedRow()], page: { next_cursor: null }, total: 2, ...over };
}

export function projectRead(uid: string, name: string): Project {
  return { project_uid: uid, name, created_at: '2026-10-01T08:00:00Z', document_count: 3 } as Project;
}

export const acceptedKey = (
  filter: { sectionCode?: string; projectUid?: string; cursor?: string } = {},
) =>
  queryKeys.optimisation.accepted({
    ...(filter.projectUid === undefined ? {} : { project_uid: filter.projectUid as never }),
    ...(filter.sectionCode === undefined ? {} : { section_code: filter.sectionCode as never }),
    ...(filter.cursor === undefined ? {} : { cursor: filter.cursor }),
    limit: ACCEPTED_PAGE_LIMIT,
  });

export const specificationKey = (sectionCode: string, projectUid: string | null) =>
  queryKeys.optimisation.sectionSpecification(sectionCode as never, {
    projectUid: projectUid as never, q: null, offset: 0, limit: SECTION_ROW_LIMIT,
  });

export interface AcceptedShape {
  readonly name: string;
  readonly make: () => ReactElement;
  readonly seedClient?: (client: QueryClient) => void;
}

const accepted = (): ReactElement =>
  createElement(SectionAcceptedOptimisations, { sectionCode: 'AR', projectUid: null as ProjectUid | null });

/** «Принято» in every branch the container has: its read pending, refused, empty and answered. */
export function acceptedShapes(): readonly AcceptedShape[] {
  return [
    { name: 'accepted-loading', make: accepted },
    {
      name: 'accepted-refused',
      make: accepted,
      seedClient: (client) => seedError(client, acceptedKey({ sectionCode: 'AR' }), optimisationApiError(503, 'dependency_unavailable')),
    },
    {
      name: 'accepted-empty',
      make: accepted,
      seedClient: (client) => client.setQueryData(acceptedKey({ sectionCode: 'AR' }), acceptedPage({ items: [], total: 0 })),
    },
    {
      name: 'accepted-ready',
      make: accepted,
      seedClient: (client) => client.setQueryData(acceptedKey({ sectionCode: 'AR' }), acceptedPage()),
    },
  ];
}
