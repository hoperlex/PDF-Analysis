/**
 * The «Разбор» filters, the list/table switch and the chosen finding live in the address (`?verdict=`, `?severity=`,
 * `?view=`, `?finding=`) and the page READS them back through `useSearchParams`. Next patches `history.pushState` and
 * `history.replaceState` so that `useSearchParams` follows a write — but the patch passes a call straight through, with no
 * sync, when its first argument carries Next's own marker (`__NA` / `_N`), and `window.history.state` always does. A page
 * that wrote its address with `replaceState(window.history.state, …)` therefore changed the URL bar and nothing else: the
 * pressed button stayed pressed, the table never came, and the next write rebuilt the query from the stale parameters
 * (browser journey on a throwaway stand, 2026-11-07: `?view=table` then `?verdict=rejected` replaced it, both buttons
 * unchanged). Static rendering cannot see this — it has no history and no patch.
 *
 * The cure is the documented form: `null` as the data, as `workers`, `logs`, `work-schedule` and `section-optimisation` write.
 * The same writer in `version-compare` and `stage-compare` is reported in `DEBT_REGISTER.md` (D-341), not changed here.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { queryKeys } from '@/shared/api';
import type { Finding } from '@/shared/api';
import { EvidenceViewerEagerSeam, ReviewPage } from '@/_pages/review';

import { WEB_ROOT } from '../../guards/lib/repo';
import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import { newClient } from '../screens/harness';
import { PROJECT_UID, RUN_ID, finding, findingDetail, observation, runStatus } from './fixtures';
import { RoutedReviewAddress, currentSearch, resetRoutedAddress, writtenAddresses, writtenHow, writtenStates } from './routed-review-address';

const SOURCE = readFileSync(join(WEB_ROOT, 'src/_pages/review/ui/review-page.tsx'), 'utf8');

describe('«Разбор» writes its address in a form Next syncs to useSearchParams', () => {
  it('never hands window.history.state to pushState or replaceState', () => {
    expect(SOURCE).not.toMatch(/history\.(push|replace)State\(\s*(window\.)?history\.state/);
  });

  it('writes with null as the data', () => {
    expect(SOURCE).toMatch(/history\.replaceState\(\s*null\s*,/);
  });
});

/**
 * `UIP-S06-06`: what the page writes when a choice is pressed. The values the page opens with are never written: «Все» of the
 * verdicts is no `?verdict=`, the table is no `?view=`, and no severity is no `?severity=`; a saved link carries only a choice the
 * reader made. Mounted live under `routed-review-address.ts`, which gives the page an address that follows what it writes.
 */
const ULID = '01J9ZQ8K7NHVXW3T2R5M6P4Q';
const WAITING = `fnd_${ULID}B1`;
const ACCEPTED = `fnd_${ULID}B2`;
const REJECTED = `fnd_${ULID}B3`;

const RUN: Finding[] = [
  finding({ finding_uid: WAITING, current_verdict: 'pending', observation: observation({ proposed_severity: 'critical' }) }),
  finding({ finding_uid: ACCEPTED, current_verdict: 'accepted', decided_severity: 'critical', observation: observation({ proposed_severity: 'critical' }) }),
  finding({ finding_uid: REJECTED, current_verdict: 'rejected' }),
];

let live: LiveRender | null = null;

/**
 * The page opens a row of the table with an effect that asks the node for its `closest('tr')` and tests it against the browser's
 * `HTMLElement` (`opened-finding.tsx`); the test document has neither. The one case that comes back to the table with a finding open
 * is given both, as empty stand-ins, so that effect finds no row to scroll to and the rest of the page is the real one.
 */
function standInForTheBrowserScroll(host: unknown): void {
  const prototype = Object.getPrototypeOf(host) as { closest?: unknown };
  prototype.closest = () => null;
  vi.stubGlobal('HTMLElement', class {});
}

async function open(query: string): Promise<void> {
  const client = newClient();
  client.setDefaultOptions({ queries: { ...client.getDefaultOptions().queries, staleTime: Infinity } });
  const envelope = { next_cursor: null } as { next_cursor: null };
  client.setQueryData(queryKeys.runs.detail(RUN_ID), runStatus({ run_id: RUN_ID }));
  client.setQueryData(queryKeys.runs.findings(RUN_ID), { data: { items: RUN, page: envelope } });
  for (const one of RUN) {
    client.setQueryData(queryKeys.findings.detail(one.finding_uid), { data: findingDetail({ finding_uid: one.finding_uid }) });
    client.setQueryData(queryKeys.findings.decisions(one.finding_uid), { data: { items: [], page: envelope } });
  }
  live = await mountLive(
    createElement(
      QueryClientProvider,
      { client },
      createElement(
        'div',
        { ref: (node: unknown) => { if (node !== null) standInForTheBrowserScroll(node); } },
        createElement(
          EvidenceViewerEagerSeam.Provider,
          { value: () => null },
          createElement(
            RoutedReviewAddress,
            { pathname: `/projects/${PROJECT_UID}/runs/${RUN_ID}/review`, query },
            createElement(ReviewPage, { projectUid: PROJECT_UID, runId: RUN_ID }),
          ),
        ),
      ),
    ),
  );
}

const rows = (): string[] => [...(live as LiveRender).markup().matchAll(/data-row-key="(fnd_[A-Z0-9]+)"/g)].map((match) => match[1] as string);

beforeEach(() => {
  resetRoutedAddress();
  vi.stubGlobal('fetch', async () => {
    throw new TypeError('offline');
  });
});

afterEach(async () => {
  await live?.unmount();
  live = null;
  vi.unstubAllGlobals();
  resetRoutedAddress();
});

describe('«Разбор» writes only the choices the reader makes', () => {
  it('opens at an empty address as the table of every finding, the waiting first and the rejected last, and writes nothing', async () => {
    await open('');
    expect(rows()).toEqual([WAITING, ACCEPTED, REJECTED]);
    expect(live!.markup()).toContain('data-finding-table');
    expect(writtenAddresses()).toEqual([]);
  });

  it('writes the verdict choice, and no verdict at all when «Все» is pressed again', async () => {
    await open('');
    await live!.pressMarked('data-verdict-filter', 'waiting');
    expect(currentSearch()).toBe('verdict=waiting');
    expect(rows()).toEqual([WAITING]);
    await live!.pressMarked('data-verdict-filter', 'rejected');
    expect(currentSearch()).toBe('verdict=rejected');
    expect(rows()).toEqual([REJECTED]);
    await live!.pressMarked('data-verdict-filter', 'all');
    expect(currentSearch()).toBe('');
    expect(rows()).toEqual([WAITING, ACCEPTED, REJECTED]);
    expect(writtenStates.every((state) => state === null)).toBe(true);
    expect(writtenHow.every((how) => how === 'replace')).toBe(true);
  });

  it('writes the severity choice of a plate, and lifts it from the address when the plate is pressed again', async () => {
    await open('');
    await live!.pressMarked('data-severity-filter', 'critical');
    expect(currentSearch()).toBe('severity=critical');
    expect(rows()).toEqual([WAITING, ACCEPTED]);
    await live!.pressMarked('data-severity-filter', 'undetermined');
    expect(currentSearch()).toBe('severity=undetermined');
    expect(rows()).toEqual([REJECTED]);
    await live!.pressMarked('data-severity-filter', 'undetermined');
    expect(currentSearch()).toBe('');
    expect(rows()).toEqual([WAITING, ACCEPTED, REJECTED]);
  });

  it('writes `view=list` for the link «Показать списком», and no view when the link «Показать таблицей» brings the table back', async () => {
    await open('');
    expect(await live!.press('Показать списком')).toBe(true);
    expect(currentSearch()).toBe(`view=list&finding=${WAITING}`);
    expect(live!.markup()).not.toContain('data-finding-table');
    expect(await live!.press('Показать таблицей')).toBe(true);
    expect(currentSearch()).toBe(`finding=${WAITING}`);
    expect(live!.markup()).toContain('data-finding-table');
  });

  it('opens the earlier addresses as their successors: `?verdict=active` as «Все», `?severity=proposed:critical` as «critical»', async () => {
    await open('verdict=active&severity=proposed:critical');
    expect(rows()).toEqual([WAITING, ACCEPTED]);
    expect(live!.markup()).toMatch(/aria-pressed="true"[^>]*data-verdict-filter="all"/);
    expect(live!.markup()).toMatch(/aria-pressed="true"[^>]*data-severity-filter="critical"/);
    // The address is read, not rewritten: nothing is written until the reader presses something.
    expect(writtenAddresses()).toEqual([]);
  });
});
