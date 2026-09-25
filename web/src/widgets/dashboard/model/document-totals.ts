/**
 * Documents-per-project, computed over one loaded page of `listProjects`.
 *
 * Pure and framework-free, same discipline as `entities/project/model/project.ts`: the
 * widget decides layout, this decides meaning. `document_count` stays optional per
 * project — `projectDocumentCount` already draws the absent/zero line, `R-23`'s addendum
 * names as the rule for the whole dashboard: *"no invented numbers… a zero that nothing
 * computed is an invented number too."* This module sums only the projects that carried a
 * count and counts, separately, how many did not — it never folds an absent count into
 * the total as if it were zero.
 */

import type { Project } from '@/shared/api';
import { projectDocumentCount } from '@/entities/project';

export interface ProjectDocumentTotal {
  readonly project: Project;
  /** `null` when the server did not carry `document_count` for this project. */
  readonly count: number | null;
}

export interface DocumentTotalsSummary {
  readonly rows: readonly ProjectDocumentTotal[];
  /** Sum of `count` over every row where it is known. Never includes an absent count. */
  readonly knownTotal: number;
  /** How many projects contributed to `knownTotal`. */
  readonly knownProjectCount: number;
  /** How many projects carried no `document_count` at all. */
  readonly unknownProjectCount: number;
}

export function summarizeDocumentTotals(projects: readonly Project[]): DocumentTotalsSummary {
  const rows: ProjectDocumentTotal[] = projects.map((project) => ({
    project,
    count: projectDocumentCount(project),
  }));

  let knownTotal = 0;
  let knownProjectCount = 0;
  let unknownProjectCount = 0;
  for (const row of rows) {
    if (row.count === null) {
      unknownProjectCount += 1;
    } else {
      knownTotal += row.count;
      knownProjectCount += 1;
    }
  }

  return { rows, knownTotal, knownProjectCount, unknownProjectCount };
}
