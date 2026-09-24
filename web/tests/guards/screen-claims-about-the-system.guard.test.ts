/**
 * A screen may not tell a reviewer that this system lacks something it has.
 *
 * ## Why this exists, and why it is narrow on purpose
 *
 * `/projects` carried the subtitle *«Один локальный проверяющий. Без аутентификации,
 * ролей и разделения на организации.»* — and `SIGN_IN_LANDING_PATH` is `/projects`, so a
 * reviewer who had just typed a password was told, on the first screen the application
 * sent them to, that the system has no authentication.
 *
 * **It is a recurrence, which is what makes it worth an instrument.** `W37CERT4-2` found
 * this exact claim in wave 37 and repaired **one of its two carriers**. No guard was
 * added, and the second carrier lived seven more waves until `W44-JOURNEY` read it while
 * doing something else. *A repair that fixes an instance and not the class is a repair
 * with a timer on it.*
 *
 * ## What is checked, and what deliberately is not
 *
 * Only this: **a rendered screen may not deny a capability the frozen contract carries.**
 * The contract is the authority, so the guard cannot drift from the product the way prose
 * does — and when a capability genuinely leaves the contract, this guard goes quiet by
 * itself rather than having to be remembered.
 *
 * It does **not** judge whether a sentence is well written, whether a limitation is worth
 * stating, or anything about roles and tenancy — which really are absent, and which this
 * screen may and should still say. **A guard that tried to judge all claims would be
 * judging prose; this one judges a contradiction between two things in the repository.**
 */

import { describe, expect, it } from 'vitest';

import { derivedScreens, wellFormed } from '../unit/screens/route-screens';
import { newClient, renderScreen } from '../unit/screens/harness';

/** Well-formed identifiers, so every screen renders its real branch rather than its 404. */
const ULID = '01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const SEGMENTS = wellFormed({
  projectUid: `prj_${ULID}`,
  documentUid: `doc_${ULID}`,
  versionUid: `ver_${ULID}`,
  runId: `run_${ULID}`,
});
import { readText, REPO_ROOT } from './lib/repo';
import { join } from 'node:path';

/** A capability the contract demonstrably carries, and the denials of it. */
interface Capability {
  readonly name: string;
  /** True when the frozen contract carries this capability. */
  readonly inContract: (contract: string) => boolean;
  /** Phrases that deny it. Matched case-insensitively against rendered text. */
  readonly denials: readonly RegExp[];
}

const CAPABILITIES: readonly Capability[] = [
  {
    name: 'authentication',
    // `/auth/token` is the exchange a reviewer's password goes through. If it ever leaves
    // the contract, this capability stops being carried and the guard stops asking.
    inContract: (contract) => contract.includes('"/auth/token"'),
    denials: [
      /без\s+аутентификации/i,
      /нет\s+аутентификации/i,
      /no\s+authentication/i,
      /без\s+учётных\s+данных/i,
    ],
  },
];

const CONTRACT = readText(join(REPO_ROOT, 'contracts/api/v1/openapi.json'));

describe('a screen does not deny a capability this system has', () => {
  it('has at least one capability to ask about', () => {
    // Without this, emptying CAPABILITIES would turn the guard green and silent, which is
    // the shape `D-88` is about.
    expect(CAPABILITIES.length).toBeGreaterThan(0);
  });

  for (const capability of CAPABILITIES) {
    it(`no screen denies ${capability.name}`, () => {
      if (!capability.inContract(CONTRACT)) {
        // The capability is not in the contract, so denying it would be TRUE. Nothing to
        // check, and saying so out loud beats a silent skip.
        return;
      }
      const offences: string[] = [];
      for (const screen of derivedScreens()) {
        // The markup, not the source: a sentence assembled from three constants is still
        // a sentence a reviewer reads, and `D-61` is about guards that search source.
        //
        // `renderWith` is the harness every other screen guard uses, reused rather than
        // rebuilt -- two renderers would be two truths, and the older one keeps being
        // cited. A screen with no seeded data renders its empty or pending branch, which
        // is a real branch a reviewer meets and carries prose like any other.
        const text = renderScreen(newClient(), screen.make(SEGMENTS)).replace(/<[^>]*>/g, ' ');
        for (const denial of capability.denials) {
          const found = denial.exec(text);
          if (found !== null) {
            offences.push(`${screen.name}: "${found[0]}"`);
          }
        }
      }
      expect(
        offences.sort(),
        `these screens tell a reviewer that this system has no ${capability.name}, and the ` +
          'frozen contract says it does. A reviewer reaches most of these screens BY USING ' +
          'the capability the sentence denies.',
      ).toEqual([]);
    });
  }
});
