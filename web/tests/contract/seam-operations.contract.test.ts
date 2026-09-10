/**
 * Contract guard: the client still carries the PC-01 seam `B6`, `B7` and `B8` agreed on.
 *
 * The drift guard next door proves the client matches the document. This one proves the
 * document still says what `docs/program/P02_SEAMS.md` section 7 says it says — the twelve
 * operations at their frozen methods and paths, the field sets a review screen depends on,
 * and the safety rules that must survive any future edit to the contract.
 *
 * A P02 change that breaks the seam fails here, before any UI task is blamed for it.
 */

import { describe, expect, it } from 'vitest';

import {
  DECISION_EVENT_TYPE_VALUES,
  ERROR_CODE_VALUES,
  OPERATIONS,
  OPERATION_IDS,
  PROVIDER_MODE_VALUES,
  RUN_STATE_VALUES,
  SCHEMA_NAMES,
  STAGE_STATUS_VALUES,
  VERDICT_VALUES,
} from '@/shared/api';
import { PC01_ERROR_CODES } from '@/shared/api';
import {
  EXPORTABLE_RUN_STATES,
  NON_TERMINAL_RUN_STATES,
  TERMINAL_RUN_STATES,
} from '@/shared/api';
import { CONTRACT_PATH, readText } from '../guards/lib/repo';

/** The frozen register of P02_SEAMS.md section 7, restated so a change has to be deliberate. */
const SEAM_OPERATIONS: ReadonlyArray<readonly [string, string, string]> = [
  ['createProject', 'POST', '/projects'],
  ['listProjects', 'GET', '/projects'],
  ['uploadDocument', 'POST', '/projects/{project_uid}/documents'],
  ['getDocumentVersion', 'GET', '/versions/{version_uid}'],
  ['streamDocumentVersionContent', 'GET', '/versions/{version_uid}/content'],
  ['startRun', 'POST', '/runs'],
  ['getRunStatus', 'GET', '/runs/{run_id}'],
  ['listRunFindings', 'GET', '/runs/{run_id}/findings'],
  ['getFinding', 'GET', '/findings/{finding_uid}'],
  ['appendDecision', 'POST', '/findings/{finding_uid}/decisions'],
  ['listDecisionHistory', 'GET', '/findings/{finding_uid}/decisions'],
  ['exportRunCsv', 'GET', '/runs/{run_id}/export.csv'],
];

const document = JSON.parse(readText(CONTRACT_PATH)) as {
  components: { schemas: Record<string, { required?: string[]; properties?: Record<string, unknown> }> };
};

const schema = (name: string) => {
  const found = document.components.schemas[name];
  expect(found, `schema ${name} is missing from the contract`).toBeDefined();
  return found as { required?: string[]; properties?: Record<string, unknown> };
};

describe('the twelve seam operations', () => {
  it('are exactly the operations the client exposes', () => {
    expect([...OPERATION_IDS].sort()).toEqual(SEAM_OPERATIONS.map(([id]) => id).sort());
  });

  for (const [operationId, method, path] of SEAM_OPERATIONS) {
    it(`${operationId} is ${method} ${path}`, () => {
      const descriptor = OPERATIONS[operationId as keyof typeof OPERATIONS];
      expect(descriptor, `${operationId} is not in the generated descriptor table`).toBeDefined();
      expect(descriptor.method).toBe(method);
      expect(descriptor.path).toBe(path);
    });
  }

  it('requires an idempotency key on exactly the four writes', () => {
    const writes = Object.values(OPERATIONS)
      .filter((op) => op.requiresIdempotencyKey)
      .map((op) => op.operationId)
      .sort();
    expect(writes).toEqual(['appendDecision', 'createProject', 'startRun', 'uploadDocument']);
  });

  it('returns bytes, not JSON, from the viewer and the export', () => {
    expect(OPERATIONS.streamDocumentVersionContent.responseMediaType).toBe('application/pdf');
    expect(OPERATIONS.exportRunCsv.responseMediaType).toBe('text/csv');
  });

  it('cursor-paginates every growing list', () => {
    for (const id of ['listProjects', 'listRunFindings', 'listDecisionHistory'] as const) {
      expect(OPERATIONS[id].queryParams).toContain('cursor');
      expect(OPERATIONS[id].queryParams).toContain('limit');
    }
  });
});

describe('the run vocabulary', () => {
  it('has `published` as the success terminal and no `succeeded`', () => {
    expect(RUN_STATE_VALUES).toContain('published');
    expect(RUN_STATE_VALUES as readonly string[]).not.toContain('succeeded');
  });

  it('keeps `succeeded` as a stage status, where it is correct', () => {
    expect(STAGE_STATUS_VALUES).toEqual(['succeeded', 'partial', 'failed', 'skipped']);
  });

  it('partitions run states into terminal and non-terminal with nothing left over', () => {
    expect([...NON_TERMINAL_RUN_STATES, ...TERMINAL_RUN_STATES].sort()).toEqual(
      [...RUN_STATE_VALUES].sort(),
    );
    const overlap = NON_TERMINAL_RUN_STATES.filter((s) =>
      (TERMINAL_RUN_STATES as readonly string[]).includes(s),
    );
    expect(overlap).toEqual([]);
  });

  it('exports exactly the terminals whose OD-11 semantics publish a result', () => {
    expect([...EXPORTABLE_RUN_STATES].sort()).toEqual(['partial', 'published']);
  });

  it('carries the closed verdict and provider-mode unions', () => {
    expect(VERDICT_VALUES).toEqual(['pending', 'accepted', 'rejected', 'needs_manual_review']);
    expect(PROVIDER_MODE_VALUES).toEqual(['live', 'recorded']);
    expect(DECISION_EVENT_TYPE_VALUES).toEqual(['accept', 'reject', 'comment', 'revoke']);
  });
});

describe('the error catalog', () => {
  it('is the closed twenty-code set', () => {
    expect(ERROR_CODE_VALUES).toHaveLength(20);
    expect(ERROR_CODE_VALUES).toContain('idempotency_key_in_progress');
    expect(ERROR_CODE_VALUES).toContain('state_transition_not_allowed');
  });

  it('narrows to the ten codes a PC-01 screen must render, all of them in the catalog', () => {
    expect(PC01_ERROR_CODES).toHaveLength(10);
    for (const code of PC01_ERROR_CODES) {
      expect(ERROR_CODE_VALUES as readonly string[]).toContain(code);
    }
  });

  it('carries no partial-specific refusal, because OD-11 exports a partial run', () => {
    expect(PC01_ERROR_CODES as readonly string[]).not.toContain('partial_result_not_publishable');
    expect(PC01_ERROR_CODES).toContain('state_transition_not_allowed');
  });
});

describe('the field sets a review screen depends on', () => {
  it('keeps every required Finding field', () => {
    expect(schema('Finding').required?.sort()).toEqual(
      [
        'category',
        'current_verdict',
        'finding_uid',
        'observation',
        'project_uid',
        'run_id',
        'version_uid',
      ].sort(),
    );
  });

  it('keeps every required FindingObservation field, evidence included', () => {
    expect(schema('FindingObservation').required?.sort()).toEqual(
      [
        'category',
        'evidence',
        'finding_observation_id',
        'finding_text',
        'provenance',
        'recommendation_text',
        'run_id',
      ].sort(),
    );
  });

  it('keeps the evidence anchors the grounding gate resolves against', () => {
    expect(schema('Evidence').required?.sort()).toEqual(
      ['char_end', 'char_start', 'evidence_ordinal', 'page_number', 'quote'].sort(),
    );
  });

  it('keeps the append-only decision-ledger field set', () => {
    expect(schema('DecisionEvent').required?.sort()).toEqual(
      [
        'author_label',
        'decision_id',
        'event_type',
        'finding_observation_id',
        'finding_uid',
        'recorded_at',
      ].sort(),
    );
  });

  it('records a decision against the observation the reviewer actually saw', () => {
    expect(schema('AppendDecisionRequest').required).toContain('finding_observation_id');
  });
});

describe('the surface leaks no internal address', () => {
  const FORBIDDEN = /^(?:.*_)?(?:bucket|object_key|s3_key|storage_url|presigned_url|prompt|model_payload)$/;

  it('has no schema property naming a bucket, an object key or a prompt', () => {
    const offenders: string[] = [];
    for (const name of SCHEMA_NAMES) {
      const properties = document.components.schemas[name]?.properties ?? {};
      for (const property of Object.keys(properties)) {
        if (FORBIDDEN.test(property)) offenders.push(`${name}.${property}`);
      }
    }
    expect(offenders).toEqual([]);
  });

  it('would catch one if it appeared — the detector is not vacuous', () => {
    expect(FORBIDDEN.test('object_key')).toBe(true);
    expect(FORBIDDEN.test('source_bucket')).toBe(true);
    expect(FORBIDDEN.test('finding_uid')).toBe(false);
  });

  it('names 43 component schemas, so a truncated document cannot pass', () => {
    expect(SCHEMA_NAMES).toHaveLength(43);
  });
});
