/**
 * The queue's state filter offers exactly the states the contract declares (`UI-PARITY-QUEUE-A`), and each of them has the
 * label the row prints for that state. Read from the frozen document, so a state the server adds reddens this file before it
 * can be a state the screen cannot filter by or cannot name.
 */

import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

import { QUEUE_STATE_GROUPS, QUEUE_STATE_OPTIONS, jobStateLabel } from '@/entities/execution';
import { REPO_ROOT, readJson } from '../guards/lib/repo';

interface Parameter {
  readonly name?: string;
  readonly in?: string;
  readonly required?: boolean;
  readonly schema?: { readonly enum?: readonly string[]; readonly format?: string };
}
interface Contract {
  readonly paths: Record<string, Record<string, { readonly operationId?: string; readonly parameters?: readonly Parameter[] }>>;
  readonly components: { readonly schemas: Record<string, { readonly required?: readonly string[]; readonly properties: Record<string, unknown> }> };
}

const contract = readJson<Contract>(join(REPO_ROOT, 'contracts', 'api', 'v1', 'openapi.json'));
const queryOf = (name: string): Parameter | undefined =>
  contract.paths['/execution/queue']?.get?.parameters?.find((p) => p.in === 'query' && p.name === name);

describe('listExecutionQueue declares its filters', () => {
  it('has the state and the period as optional query parameters', () => {
    for (const name of ['state', 'created_from', 'created_to']) {
      expect(queryOf(name), name).toBeDefined();
      expect(queryOf(name)?.required ?? false, name).toBe(false);
    }
    expect(queryOf('created_from')?.schema?.format).toBe('date-time');
    expect(queryOf('created_to')?.schema?.format).toBe('date-time');
  });

  it('offers in the select the states of the declared enum, no more and no fewer', () => {
    const declared = [...(queryOf('state')?.schema?.enum ?? [])].sort();
    expect(declared).toHaveLength(8);
    expect(QUEUE_STATE_OPTIONS.map((option) => option.value).sort()).toEqual(declared);
  });

  it('labels each declared state', () => {
    for (const state of queryOf('state')?.schema?.enum ?? []) {
      expect(jobStateLabel(state), state).not.toBeNull();
    }
  });

  it('D-370: declares `state_group`, optional, and the strip\'s three groups are its values', () => {
    expect(queryOf('state_group')).toBeDefined();
    expect(queryOf('state_group')?.required ?? false).toBe(false);
    expect(queryOf('state_group')?.schema?.enum).toEqual(QUEUE_STATE_GROUPS.map((group) => group.key));
    // The groups hold every declared state once: a group\'s press and the eight single states cannot disagree.
    expect(QUEUE_STATE_GROUPS.flatMap((group) => [...group.states]).sort()).toEqual([...(queryOf('state')?.schema?.enum ?? [])].sort());
  });
});

describe('ExecutionQueuePage carries the counts the menu and the strip read', () => {
  const page = contract.components.schemas.ExecutionQueuePage;

  it('D-395: has `live_failure_count`, an optional count', () => {
    expect(page?.properties).toHaveProperty('live_failure_count');
    expect(page?.required).not.toContain('live_failure_count');
    expect(page?.properties).toHaveProperty('overview');
  });
});

describe('ExecutionQueueItem names its work', () => {
  const schema = contract.components.schemas.ExecutionQueueItem;

  it('requires the six members that identify and name the work and leaves the four times and reasons optional', () => {
    for (const name of ['project_uid', 'project_name', 'document_uid', 'document_name', 'version_uid', 'version_ordinal']) {
      expect(schema?.required, name).toContain(name);
    }
    for (const name of ['started_at', 'finished_at', 'error_code', 'interrupted_reason']) {
      expect(schema?.properties, name).toHaveProperty(name);
      expect(schema?.required, name).not.toContain(name);
    }
  });
});
