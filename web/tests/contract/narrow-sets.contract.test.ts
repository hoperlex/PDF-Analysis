/**
 * Contract guard: the frontend's hand-maintained subsets, held to their authority.
 *
 * `web/src/shared/api/run-state.ts` is the standard here, and it already carries a
 * compile-time partition proof in both directions against the generated `RunState` enum.
 * That proof is real and this file does not duplicate it: it proves every run state is
 * *classified*. It cannot prove the classification is the *right* one, because the
 * generated enum carries no terminal flag — the frontend's whole idea of which states are
 * terminal is a reading of `contracts/domain/v1/state-machines.json` that nothing had
 * checked.
 *
 * Two hand-written terminal splits exist on the two sides of the wire —
 * `TERMINAL_RUN_STATES` here and `_TERMINAL_STATES` in `src/auditmanager/runs/carrier.py`.
 * Neither is wrong to be hand-written; both are now pinned to the same contract, here and
 * in `tests/contract/domain_p02/test_narrow_sets_against_contracts.py`, so they cannot
 * drift apart without one of the two reddening.
 *
 * The contract files are read-only here. Every assertion is about a relationship — `⊆`,
 * `==`, "the difference is exactly this" — never about a count, because a count reddens on
 * every catalog change including the correct ones and teaches the next session to bump the
 * number instead of reading the change.
 */

import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

import { AUTHORIZATION_ERROR_CODES, NON_TERMINAL_RUN_STATES, TERMINAL_RUN_STATES } from '@/shared/api';
import { RUN_STATE_VALUES } from '@/shared/api/generated/types.gen';
import { REPO_ROOT, readJson } from '../guards/lib/repo';

const STATE_MACHINES_PATH = join(REPO_ROOT, 'contracts', 'domain', 'v1', 'state-machines.json');
const ERROR_CODES_PATH = join(REPO_ROOT, 'contracts', 'domain', 'v1', 'error-codes.json');

interface StateMachine {
  readonly initial: string;
  readonly transitions: Readonly<Record<string, readonly string[]>>;
  readonly terminal: readonly string[];
}

interface StateMachines {
  readonly machines: Readonly<Record<string, StateMachine>>;
}

interface ErrorCatalogEntry {
  readonly category: string;
}

interface ErrorCatalog {
  readonly categories: Readonly<Record<string, string>>;
  readonly codes: Readonly<Record<string, ErrorCatalogEntry>>;
}

function auditRun(): StateMachine {
  const machine = readJson<StateMachines>(STATE_MACHINES_PATH).machines.audit_run;
  if (machine === undefined) {
    throw new Error('state-machines.json no longer declares machines.audit_run');
  }
  return machine;
}

/** Every state the machine declares, from its own topology rather than from a list. */
function declaredStates(machine: StateMachine): Set<string> {
  const states = new Set<string>([machine.initial, ...machine.terminal]);
  for (const [origin, targets] of Object.entries(machine.transitions)) {
    states.add(origin);
    for (const target of targets) states.add(target);
  }
  return states;
}

describe('the run-state split is the contract machine, not a reading of it', () => {
  it('classifies as terminal exactly what machines.audit_run.terminal declares', () => {
    expect([...TERMINAL_RUN_STATES].sort()).toEqual([...auditRun().terminal].sort());
  });

  it('classifies as non-terminal exactly the rest of the machine', () => {
    const machine = auditRun();
    const nonTerminal = [...declaredStates(machine)].filter(
      (state) => !machine.terminal.includes(state),
    );
    expect([...NON_TERMINAL_RUN_STATES].sort()).toEqual(nonTerminal.sort());
  });

  it('and the generated enum is the same machine, so the compile-time proof is about this set', () => {
    // The partition proof in run-state.ts is stated against RUN_STATE_VALUES. If the
    // generated enum and the state machine ever disagreed, that proof would be about a
    // different set than the two assertions above, and all three could be green at once.
    expect([...RUN_STATE_VALUES].sort()).toEqual([...declaredStates(auditRun())].sort());
  });
});

describe('the authorization codes are the catalog category, not a taste', () => {
  const catalog = readJson<ErrorCatalog>(ERROR_CODES_PATH);

  it('is exactly the codes the catalog files under `authorization`', () => {
    const declared = Object.entries(catalog.codes)
      .filter(([, entry]) => entry.category === 'authorization')
      .map(([code]) => code);
    // `authorization.ts` already proves at compile time that these are catalog codes.
    // What it cannot say is that they are ALL of the category it claims to be — the
    // generated `ErrorCode` union carries no category. A twenty-third code filed under
    // `authorization` would otherwise render through a classifier's generic server-error
    // branch while this module claims to cover the category.
    expect([...AUTHORIZATION_ERROR_CODES].sort()).toEqual(declared.sort());
  });

  it('names a category the catalog actually declares', () => {
    expect(Object.keys(catalog.categories)).toContain('authorization');
  });

  it('is a strict narrowing of the catalog', () => {
    // A subset assertion that the whole catalog would also satisfy is half a check.
    expect(AUTHORIZATION_ERROR_CODES.length).toBeLessThan(Object.keys(catalog.codes).length);
  });
});
