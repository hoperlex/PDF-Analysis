/**
 * The one way to fill `queryKeys.runs.findings(runId)`: the COMPLETE list of a run's findings.
 *
 * `listRunFindings` answers one page, 50 by default and 200 at most, and says whether there
 * is another in `page.next_cursor`. A screen that read one page showed a run with 107
 * findings as a run with 50, while the CSV and XLSX exports carried all 107 -- a truncation
 * nothing on the screen admitted to. So the list is read to its end here, once, and a
 * consumer never sees a page.
 *
 * **All or nothing.** The `queryFn` resolves only when the last page has arrived. If any
 * page fails, the whole read fails with that page's own error and the cache holds no list
 * at all: there is no partial value a screen could show as if it were complete (AGENTS §4,
 * no silent fallback). The same goes for a server that contradicts itself -- a cursor it
 * already handed out, a finding that arrives twice, a list that never ends -- which is
 * reported as `RunFindingsReadFault` rather than cut short.
 *
 * **One shape per key** (`D-57`). Several screens read this key: the review screen, the run
 * screen's findings tile and the portal page's findings. Each used to build its own `queryFn`;
 * with the list now paged, a screen that filled the key with one page would silently truncate
 * the others. The
 * cached value is the generated client's `{ data: FindingPage }` -- `items` is the whole
 * list and `page.next_cursor` is `null`, because nothing follows it -- so every reader that
 * took `.data.items` before takes it now. The `queryFn` lives here, beside the key it
 * fills, and `web/tests/unit/review/run-findings-complete.test.ts` holds that no other site
 * names the key as a `queryKey`.
 *
 * The cursor is opaque: it is handed back exactly as received, never parsed or built.
 */

import type { Cursor, Finding, FindingPage, RunId } from '@/shared/api';
import { listRunFindings, queryKeys } from '@/shared/api';

/** The contract's largest page: the fewest requests the server allows for a long run. */
export const RUN_FINDINGS_PAGE_LIMIT = 200;

/**
 * A bound on the loop, not on the data: 1000 pages of 200 is far beyond a run the product
 * produces, and a server that still has a next cursor after it is not paging.
 */
export const RUN_FINDINGS_MAX_PAGES = 1000;

/** The cached value: the generated envelope's body, with every finding in `items`. */
export interface CompleteRunFindings {
  readonly data: FindingPage;
}

/**
 * The server's paging contradicted itself, so the list cannot be called complete.
 *
 * Not an `ApiError`: no response carried it. The message is Russian and caller-safe -- it
 * names what was wrong, never a cursor, a path or a payload.
 */
export class RunFindingsReadFault extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'RunFindingsReadFault';
  }
}

const NOT_COMPLETE = 'Список находок не показан, чтобы не выдать часть за целое.';

/**
 * Read every page of one run's findings, in the order the server gave them.
 *
 * `signal` goes to every request, and is checked between pages so an abort ends the loop
 * rather than waiting for the next response.
 */
export async function readAllRunFindings(
  runId: RunId,
  signal: AbortSignal,
): Promise<CompleteRunFindings> {
  const items: Finding[] = [];
  const identities = new Set<string>();
  const cursors = new Set<string>();
  let cursor: Cursor | undefined;

  for (let pages = 1; ; pages += 1) {
    signal.throwIfAborted();
    if (pages > RUN_FINDINGS_MAX_PAGES) {
      throw new RunFindingsReadFault(
        `Сервер не закончил список находок за ${RUN_FINDINGS_MAX_PAGES} страниц. ${NOT_COMPLETE}`,
      );
    }

    const response = await listRunFindings(
      {
        path: { run_id: runId },
        query: { limit: RUN_FINDINGS_PAGE_LIMIT, ...(cursor === undefined ? {} : { cursor }) },
      },
      { signal },
    );

    for (const finding of response.data.items) {
      if (identities.has(finding.finding_uid)) {
        throw new RunFindingsReadFault(
          `Одна и та же находка пришла на двух страницах списка. ${NOT_COMPLETE}`,
        );
      }
      identities.add(finding.finding_uid);
      items.push(finding);
    }

    const next = response.data.page.next_cursor;
    if (next === null || next === undefined) break;
    if (cursors.has(next)) {
      throw new RunFindingsReadFault(`Сервер повторил курсор списка находок. ${NOT_COMPLETE}`);
    }
    cursors.add(next);
    cursor = next;
  }

  return { data: { items, page: { next_cursor: null } } };
}

/** Options for one run's complete finding list, ready for `useQuery` or `fetchQuery`. */
export function runFindingsQueryOptions(runId: RunId) {
  return {
    queryKey: queryKeys.runs.findings(runId),
    queryFn: ({ signal }: { signal: AbortSignal }): Promise<CompleteRunFindings> =>
      readAllRunFindings(runId, signal),
  };
}
