/**
 * Whether a route parameter is shaped like a document or a version identity.
 *
 * The same rule `entities/project` states for `prj_<ULID>`, for the two identities the
 * new routes carry: the UI never parses an identifier for meaning, and this only
 * separates "the URL is malformed" from "the server says not found". A typo in a pasted
 * address therefore costs no request and does not render as a server failure.
 *
 * The patterns come from the generated contract constants; nothing here writes a regex
 * literal, because a hand-written copy of a contract pattern is a copy that drifts.
 */

import { DOCUMENT_UID_PATTERN, VERSION_UID_PATTERN } from '@/shared/api';

const DOCUMENT_UID_RE = new RegExp(DOCUMENT_UID_PATTERN);
const VERSION_UID_RE = new RegExp(VERSION_UID_PATTERN);

export function looksLikeDocumentUid(value: string): boolean {
  return DOCUMENT_UID_RE.test(value);
}

export function looksLikeVersionUid(value: string): boolean {
  return VERSION_UID_RE.test(value);
}
