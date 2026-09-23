/**
 * Contract guard: the client still carries the PC-01 seam `B6`, `B7` and `B8` agreed on.
 *
 * The drift guard next door proves the client matches the document. This one proves the
 * document still says what `docs/program/P02_SEAMS.md` section 7 says it says — the
 * eighteen operations at their frozen methods and paths, the field sets a review screen depends on,
 * and the safety rules that must survive any future edit to the contract.
 *
 * A P02 change that breaks the seam fails here, before any UI task is blamed for it.
 */

import { describe, expect, it } from 'vitest';

import type { OperationId } from '@/shared/api';
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
  // R-5, 2026-09-18: the three listings that make published work reachable after a
  // page reload. DEBT_REGISTER.md D-16.
  ['listDocuments', 'GET', '/projects/{project_uid}/documents'],
  ['listVersions', 'GET', '/documents/{document_uid}/versions'],
  ['listRuns', 'GET', '/versions/{version_uid}/runs'],
  // W34-CONTRACT, 2026-09-22: the credential exchange. R-3 required a bearer credential on
  // every operation and described no way to obtain one, so this is the one operation whose
  // own `security` is the empty requirement. It says nothing about what the credential is.
  ['issueToken', 'POST', '/auth/token'],
  // W38-KB, 2026-09-22: `R-24`. The decision journal across findings, which the
  // knowledge base reads. `listDecisionHistory` answers for one finding and this
  // answers for all of them; it creates nothing and `ADR-0012` calls it a projection.
  ['listDecisions', 'GET', '/decisions'],
  // W39-REVOKE, 2026-09-23: `R-26`. The password change, and with it the only way this
  // surface can take a credential back -- the account's credential generation is raised by
  // the same write that stores the new digest, so every credential minted under the old
  // password stops being accepted. It answers `IssueTokenResponse`, because it revokes the
  // caller's own credential in the act of succeeding and has to hand back the replacement.
  ['changePassword', 'POST', '/auth/password'],
];

const document = JSON.parse(readText(CONTRACT_PATH)) as {
  components: { schemas: Record<string, { required?: string[]; properties?: Record<string, unknown> }> };
};

/** How many `components.schemas` keys the frozen document declares, read and not written. */
const SCHEMA_COUNT = Object.keys(document.components.schemas).length;

const schema = (name: string) => {
  const found = document.components.schemas[name];
  expect(found, `schema ${name} is missing from the contract`).toBeDefined();
  return found as { required?: string[]; properties?: Record<string, unknown> };
};

describe('the eighteen seam operations', () => {
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

  it('mints no idempotency key for the credential exchange, which creates nothing', () => {
    // A repeat of the same exchange is a second exchange, not a replay of the first, so
    // the key would be a promise this operation cannot keep.
    expect(OPERATIONS.issueToken.requiresIdempotencyKey).toBe(false);
  });

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

  it('lets a reviewer filter findings by category and by verdict', () => {
    // Paging and filtering is the first thing a reviewer reaches for, and the two
    // filters were the half of the query surface no guard mentioned: `cursor` and
    // `limit` were checked above from the day this file was written, `category` and
    // `verdict` were not checked anywhere on this side.
    expect(OPERATIONS.listRunFindings.queryParams).toContain('category');
    expect(OPERATIONS.listRunFindings.queryParams).toContain('verdict');
  });

  it('sends every query parameter the contract declares, and no other', () => {
    // The generator is what keeps these in step, so this asserts the *result* of that
    // rather than trusting it: a parameter the document declares and the descriptor
    // omits cannot be sent at all, and `buildQuery` iterates the descriptor, so a
    // caller that passes it has it dropped before the request is built.
    const paths = (
      JSON.parse(readText(CONTRACT_PATH)) as {
        paths: Record<string, Record<string, unknown>>;
        components: { parameters: Record<string, { name: string; in: string }> };
      }
    );
    const resolve = (node: { $ref?: string; name?: string; in?: string }) => {
      if (!node.$ref) return node as { name: string; in: string };
      const key = node.$ref.split('/').pop() as string;
      const found = paths.components.parameters[key];
      expect(found, `#/components/parameters/${key} does not resolve`).toBeDefined();
      return found as { name: string; in: string };
    };

    for (const [path, operations] of Object.entries(paths.paths)) {
      for (const operation of Object.values(operations)) {
        const typed = operation as {
          operationId?: string;
          parameters?: Array<{ $ref?: string; name?: string; in?: string }>;
        };
        if (!typed.operationId) continue;
        const declared = (typed.parameters ?? [])
          .map(resolve)
          .filter((parameter) => parameter.in === 'query')
          .map((parameter) => parameter.name)
          .sort();
        const exposed = [...(OPERATIONS[typed.operationId as OperationId].queryParams ?? [])].sort();
        expect(exposed, `${typed.operationId} (${path})`).toEqual(declared);
      }
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
  it('is the closed twenty-two-code set', () => {
    // Twenty-two since round 7: owner ruling `R-8`, reinstated by `R-13`, added
    // `staged_upload_lost` so one 409 stopped meaning two opposite things (`D-18`).
    // Twenty-one before it, since the wave-13 reseal, where `R-3` added
    // `dependency_credential_refused` so one 403 stopped meaning two things (`D-7`).
    expect(ERROR_CODE_VALUES).toHaveLength(22);
    expect(ERROR_CODE_VALUES).toContain('idempotency_key_in_progress');
    expect(ERROR_CODE_VALUES).toContain('state_transition_not_allowed');
    expect(ERROR_CODE_VALUES).toContain('dependency_credential_refused');
    expect(ERROR_CODE_VALUES).toContain('staged_upload_lost');
    expect(ERROR_CODE_VALUES).toContain('permission_denied');
  });

  it('narrows to the codes a PC-01 screen must render, all of them in the catalog', () => {
    // No length literal since `D-40`: the subset is derived from the document by
    // `pc01-error-codes.contract.test.ts`, and a count written here is the hand-kept
    // figure that row is about. What belongs here is that it is a strict narrowing.
    expect(PC01_ERROR_CODES.length).toBeGreaterThan(0);
    expect(PC01_ERROR_CODES.length).toBeLessThan(ERROR_CODE_VALUES.length);
    for (const code of PC01_ERROR_CODES) {
      expect(ERROR_CODE_VALUES as readonly string[]).toContain(code);
    }
  });

  it('includes both authorization codes, because the document declares 401 and 403 on every operation', () => {
    expect(PC01_ERROR_CODES).toContain('authentication_required');
    expect(PC01_ERROR_CODES).toContain('permission_denied');
    // Read off the frozen document rather than asserted from memory: if a later reseal
    // dropped the security scheme, this would stop agreeing with the list above. The
    // document is re-read here in the same style the parameter check below uses, because
    // an operation is identified by carrying an `operationId`, not by its HTTP verb.
    const contract = JSON.parse(readText(CONTRACT_PATH)) as {
      paths: Record<string, Record<string, unknown>>;
    };
    const withResponses: Array<[string, string[]]> = [];
    for (const operations of Object.values(contract.paths)) {
      for (const operation of Object.values(operations)) {
        const typed = operation as {
          operationId?: string;
          responses?: Record<string, unknown>;
        };
        if (!typed.operationId) continue;
        withResponses.push([typed.operationId, Object.keys(typed.responses ?? {})]);
      }
    }
    expect(withResponses).toHaveLength(SEAM_OPERATIONS.length);
    for (const [operationId, statuses] of withResponses) {
      expect(statuses, `${operationId} declares no 401`).toContain('401');
      // `W34-CONTRACT`: 403 is `permission_denied`, which needs an authenticated subject.
      // `issueToken` is the operation that produces one and presents none itself, so it
      // declares the 401 and not the 403. That exception is pinned by name here and
      // derived from the document's `security` in `pc01-error-codes.contract.test.ts`.
      if (operationId === 'issueToken') {
        expect(statuses, 'issueToken has no authenticated subject to deny').not.toContain('403');
      } else {
        expect(statuses, `${operationId} declares no 403`).toContain('403');
      }
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

  it('names every component schema the document declares, so a truncated one cannot pass', () => {
    // Read off the frozen document rather than written down: a client generated from a
    // truncated contract carries fewer names than the contract has, which is the defect
    // this asserts, and a literal here would only ever be the last reseal's figure.
    expect(SCHEMA_NAMES).toHaveLength(SCHEMA_COUNT);
    expect(SCHEMA_COUNT).toBeGreaterThan(40);
  });
});
