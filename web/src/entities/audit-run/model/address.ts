/**
 * Whether a route parameter is shaped like a run identity.
 *
 * The same rule `entities/project` states for `prj_<ULID>` and `entities/document-version`
 * states for documents and versions. The pattern comes from the generated contract
 * constant; nothing here writes a regex literal, because a hand-written copy of a contract
 * pattern is a copy that drifts.
 *
 * `D-28`: this existed for three of the four dynamic route segments and not for runs, so a
 * malformed run address was the one malformed address that still cost a request.
 */

import { RUN_ID_PATTERN } from '@/shared/api';

const RUN_ID_RE = new RegExp(RUN_ID_PATTERN);

export function looksLikeRunId(value: string): boolean {
  return RUN_ID_RE.test(value);
}
