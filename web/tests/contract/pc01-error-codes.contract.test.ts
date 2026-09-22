/**
 * `D-40`: the PC-01 render subset, derived from the contract instead of copied into it.
 *
 * `PC01_ERROR_CODES` states its own meaning — the catalog codes a PC-01 screen can be
 * handed. That meaning has been false twice. `W15-AUTH` found the list missing **both**
 * authorization codes, correct before `R-3` and false after it, and corrected it by hand.
 * `W25-SEAL` found it missing `staged_upload_lost`, and `D-40` says why that is the same
 * defect: a hand-kept subset of a resealable surface with nothing reading it.
 *
 * **What is derived and what is not.** The contract pins a *status* per response, never a
 * code per operation: `409` alone covers eight catalog codes. The only place the document
 * says which of them a given operation can emit is the description of the response
 * component that operation names. So the derivation is:
 *
 *   for every non-2xx response an operation declares
 *     -> the `components/responses` entry it `$ref`s
 *     -> the catalog codes that entry's description names in backticks,
 *        plus the code whose name the entry itself is (`NotFound` -> `not_found`)
 *     -> keep those the catalog assigns to the status it was declared at.
 *
 * The last step is load-bearing and is asserted to be: descriptions carry **cross
 * references** — `PermissionDenied` names `dependency_credential_refused` to say it is
 * *not* this response — and without the status filter those become false members.
 *
 * **The one thing this cannot see** is registered in :data:`BLIND_SPOTS` with its reason,
 * rather than tolerated by an inequality. `InternalError` names `analysis_failed` in words
 * — *"a declared run failure"* — and not as a code.
 *
 * No count is written down here. A reseal that adds a code to a response this surface
 * declares reddens this file by itself, which is what `D-40` asks for and what the two
 * hand corrections before it did not leave behind.
 */

import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

import { ERROR_CODE_VALUES, PC01_ERROR_CODES } from '@/shared/api';
import { CONTRACT_PATH, REPO_ROOT, readJson } from '../guards/lib/repo';

/** The frozen domain catalog. Read here rather than exported: only this guard needs it. */
const ERROR_CATALOG_PATH = join(REPO_ROOT, 'contracts', 'domain', 'v1', 'error-codes.json');

interface Catalog {
  readonly codes: Record<string, { readonly http: number }>;
}

interface Contract {
  readonly paths: Record<
    string,
    Record<
      string,
      {
        operationId?: string;
        responses?: Record<string, { $ref?: string }>;
        security?: ReadonlyArray<Record<string, unknown>>;
      }
    >
  >;
  readonly components: { readonly responses: Record<string, { readonly description: string }> };
}

const contract = readJson<Contract>(CONTRACT_PATH);
const catalog = readJson<Catalog>(ERROR_CATALOG_PATH);

/**
 * Entries this list carries that the derivation cannot reach, each with the reason.
 *
 * This is a register of **documented gaps in the contract's prose**, not a licence to add
 * codes: anything here must be justified by what the document says in words. Adding to it
 * is how a session says out loud "the contract states this in a form no checker can read".
 */
const BLIND_SPOTS: Readonly<Record<string, string>> = {
  analysis_failed:
    'the InternalError response names it as "a declared run failure" in words, not as a code',
};

/** `not_found` -> `NotFound`, the naming the contract's response components already use. */
function pascal(code: string): string {
  return code
    .split('_')
    .map((word) => `${word.charAt(0).toUpperCase()}${word.slice(1)}`)
    .join('');
}

const CODE_BY_COMPONENT_NAME = new Map(
  Object.keys(catalog.codes).map((code) => [pascal(code), code] as const),
);

/**
 * Every operation in the document, and whether the root credential requirement reaches it.
 *
 * `W34-CONTRACT`: `issueToken` overrides the root `security` with the empty requirement,
 * because it is the operation a caller with no credential uses to obtain one. Read off the
 * document rather than named here, so a second operation that opened itself the same way
 * would be reported by the assertion below rather than waved through by a name check.
 */
function operationsWithSecurity(): Array<{ operationId: string; requiresCredential: boolean }> {
  const found: Array<{ operationId: string; requiresCredential: boolean }> = [];
  for (const item of Object.values(contract.paths)) {
    for (const operation of Object.values(item)) {
      if (!operation.operationId) continue;
      found.push({
        operationId: operation.operationId,
        // Absent -> the document root applies. Present and empty -> no credential.
        requiresCredential: (operation.security ?? [{}]).length > 0,
      });
    }
  }
  return found;
}

const requiresCredential = (operationId: string): boolean =>
  operationsWithSecurity().find((entry) => entry.operationId === operationId)
    ?.requiresCredential ?? true;

/** Every `(operationId, status, responseComponent)` the document declares for a failure. */
function declaredFailureResponses(): Array<{
  operationId: string;
  status: string;
  component: string;
}> {
  const found: Array<{ operationId: string; status: string; component: string }> = [];
  for (const item of Object.values(contract.paths)) {
    for (const operation of Object.values(item)) {
      if (!operation.operationId) continue;
      for (const [status, response] of Object.entries(operation.responses ?? {})) {
        if (status.startsWith('2')) continue;
        const ref = response.$ref;
        expect(ref, `${operation.operationId} declares ${status} inline, not as a component`).toBeDefined();
        found.push({
          operationId: operation.operationId,
          status,
          component: (ref as string).slice((ref as string).lastIndexOf('/') + 1),
        });
      }
    }
  }
  return found;
}

/** The catalog codes a response component's own description names, before any filtering. */
function codesNamedBy(component: string): Set<string> {
  const description = contract.components.responses[component]?.description ?? '';
  const named = new Set<string>();
  for (const code of Object.keys(catalog.codes)) {
    if (description.includes(`\`${code}\``)) named.add(code);
  }
  const byName = CODE_BY_COMPONENT_NAME.get(component);
  if (byName) named.add(byName);
  return named;
}

/** The codes a response component can carry at the status it was declared at. */
function codesCarriedAt(component: string, status: string): Set<string> {
  return new Set(
    [...codesNamedBy(component)].filter((code) => catalog.codes[code]?.http === Number(status)),
  );
}

/** Every catalog code the PC-01 operations can put in front of a screen. */
function reachableCodes(): Set<string> {
  const reachable = new Set<string>();
  for (const { status, component } of declaredFailureResponses()) {
    for (const code of codesCarriedAt(component, status)) reachable.add(code);
  }
  return reachable;
}

const sorted = (codes: Iterable<string>): string[] => [...codes].sort();

describe('the derivation reads the document and is not vacuous', () => {
  it('finds a component-backed failure response on every operation', () => {
    const declared = declaredFailureResponses();
    const operations = new Set(declared.map(({ operationId }) => operationId));
    // No literal, for the reason this whole file exists: the floor is the document's own
    // operation count, so a reseal moves both sides together and a truncated document
    // still cannot pass. The lower bound is what stops the two shrinking to nothing.
    expect(operations.size).toBe(operationsWithSecurity().length);
    expect(operations.size).toBeGreaterThan(10);
    // Every operation declares at least a 401, so the floor is real. The 403 is
    // `permission_denied` -- an authenticated subject refused a resource -- so it belongs
    // to the operations the credential requirement reaches, and not to the exchange that
    // produces the credential.
    for (const operationId of operations) {
      const statuses = declared
        .filter((entry) => entry.operationId === operationId)
        .map(({ status }) => status);
      expect(statuses, `${operationId} declares no 401`).toContain('401');
      if (requiresCredential(operationId)) {
        expect(statuses, `${operationId} declares no 403`).toContain('403');
      } else {
        expect(
          statuses,
          `${operationId} carries no credential, so it has no authenticated subject to deny`,
        ).not.toContain('403');
      }
    }
  });

  it('opens exactly one operation to a caller holding no credential', () => {
    // `W34-CONTRACT`. The branch above is only worth something if the set it branches on
    // is pinned: an operation that quietly dropped its `security` would otherwise be
    // excused from the 403 rule by the same code that is meant to catch it.
    const open = operationsWithSecurity()
      .filter((entry) => !entry.requiresCredential)
      .map((entry) => entry.operationId)
      .sort();
    expect(open).toEqual(['issueToken']);
  });

  it('reads at least one catalog code out of every failure response the document declares', () => {
    // The killer for a derivation that quietly stops working: dropping the backtick scan
    // empties `UploadRejected`, dropping the name match empties `NotFound`, and either
    // mutation would otherwise shrink the derived set and pass a superset assertion.
    const empty: string[] = [];
    for (const { status, component } of declaredFailureResponses()) {
      if (codesCarriedAt(component, status).size === 0) empty.push(`${component} at ${status}`);
    }
    expect(sorted(new Set(empty))).toEqual([]);
  });

  it('keeps the status filter load-bearing, because descriptions cross-reference', () => {
    // `PermissionDenied` names `dependency_credential_refused` to say it is NOT that code.
    // Without the filter a cross reference becomes a member, so this pins that the
    // document really does contain one and that the filter removes it.
    const crossReferenced = declaredFailureResponses().filter(({ status, component }) =>
      [...codesNamedBy(component)].some((code) => catalog.codes[code]?.http !== Number(status)),
    );
    expect(crossReferenced.length).toBeGreaterThan(0);
    for (const { status, component } of crossReferenced) {
      for (const code of codesCarriedAt(component, status)) {
        expect(catalog.codes[code]?.http, `${component} at ${status} carries ${code}`).toBe(
          Number(status),
        );
      }
    }
  });

  it('derives codes that are all in the catalog', () => {
    const derived = reachableCodes();
    expect(derived.size).toBeGreaterThan(0);
    for (const code of derived) {
      expect([...ERROR_CODE_VALUES], `${code} is not a catalog code`).toContain(code);
    }
  });
});

describe('the PC-01 render subset against the surface it claims to cover', () => {
  it('is never narrower than what the document can put in front of a screen', () => {
    // `D-40` itself: on the tree that raised it, this assertion names `staged_upload_lost`.
    const listed = new Set<string>(PC01_ERROR_CODES);
    const missing = sorted([...reachableCodes()].filter((code) => !listed.has(code)));
    expect(
      missing,
      'the contract can return these and PC01_ERROR_CODES does not list them. Widen the ' +
        'list -- a code the surface emits and the subset omits is D-40, twice corrected by ' +
        'hand and never guarded. Do NOT register it as a blind spot: that register is for ' +
        'codes the document states in words rather than as codes.',
    ).toEqual([]);
  });

  it('is never wider than the surface, except where the contract says so in words', () => {
    const derived = reachableCodes();
    const unexplained = sorted(
      (PC01_ERROR_CODES as readonly string[]).filter(
        (code) => !derived.has(code) && !(code in BLIND_SPOTS),
      ),
    );
    expect(
      unexplained,
      'these are listed as PC-01 renderable and nothing in the document declares them on ' +
        'this surface. Remove them, or register the reason in BLIND_SPOTS.',
    ).toEqual([]);
  });

  it('keeps every registered blind spot a real one', () => {
    // A register that outlived its reason is the literal coming back. Each entry must
    // still be a catalog code and must still be invisible to the derivation.
    const derived = reachableCodes();
    for (const [code, reason] of Object.entries(BLIND_SPOTS)) {
      expect([...ERROR_CODE_VALUES], `${code} is not a catalog code`).toContain(code);
      expect(PC01_ERROR_CODES as readonly string[], `${code} is registered but not listed`).toContain(code);
      expect(derived.has(code), `${code} is derivable now; drop it from BLIND_SPOTS`).toBe(false);
      expect(reason.length).toBeGreaterThan(20);
    }
  });

  it('holds no code at a status no operation on this surface declares', () => {
    const statuses = new Set(declaredFailureResponses().map(({ status }) => Number(status)));
    const unreachable = sorted(
      Object.keys(catalog.codes).filter((code) => !statuses.has(catalog.codes[code]?.http ?? -1)),
    );
    // Not vacuous: `unsupported_contract_version` is a 400 and no operation declares one.
    expect(unreachable).toContain('unsupported_contract_version');
    for (const code of unreachable) {
      expect(PC01_ERROR_CODES as readonly string[], `${code} cannot reach a screen`).not.toContain(code);
    }
  });

  it('lists each code once', () => {
    expect(PC01_ERROR_CODES).toHaveLength(new Set(PC01_ERROR_CODES).size);
  });
});
