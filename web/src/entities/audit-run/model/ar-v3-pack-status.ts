/**
 * Reading the answer of `getArV3BetaPackStatus` (`AR-V3-BETA-PACK-STATUS-WEB-01`).
 *
 * The server answers one of two shapes. `{ state: "not_installed" }` carries nothing else;
 * `{ state: "installed", ... }` carries the profile and prompt-bundle ids, the sealed pack
 * digest, the six scope ids in order and the reviewer's five-field attestation. Anything
 * else is a **fault**, not an empty state and not an installed pack: a response that omits a
 * member, invents one, names a state the contract does not, carries an identifier or digest
 * the contract's pattern refuses, or lists another set of scopes is a response this client
 * cannot vouch for. The screen that offers to start six checks must never do so on the
 * strength of such an answer, so the reading has exactly three outcomes and the third is not
 * "probably installed".
 *
 * The attestation is a record of what the pack manifest said. Nothing here, and nothing on
 * the server, checks that a review took place; a reading that carries one says so in words
 * on the screen (`widgets/ar-v3-beta-pack`) and does not turn it into a verdict.
 */

import type { ArV3BetaPackReview } from '@/shared/api';

/** The six scopes of the AR v3 beta pack, in the order the server serves them. */
export const AR_V3_PACK_SCOPE_IDS = ['F1', 'F2', 'A1', 'A2', 'S1', 'S2'] as const;

export type ArV3PackScopeId = (typeof AR_V3_PACK_SCOPE_IDS)[number];

/** Why a response is a fault. Goes on a `data-` attribute; the screen says one sentence. */
export type ArV3PackFaultReason =
  | 'not_an_object'
  | 'unknown_state'
  | 'members_beside_not_installed'
  | 'unknown_member'
  | 'missing_member'
  | 'bad_identifier'
  | 'bad_digest'
  | 'bad_scope_list'
  | 'bad_attestation';

export type ArV3PackReading =
  | { readonly kind: 'not_installed' }
  | {
      readonly kind: 'installed';
      readonly analysisProfileId: string;
      readonly promptBundleId: string;
      /** The whole sealed digest, 64 lowercase hex characters. */
      readonly packSha256: string;
      readonly scopeIds: readonly ArV3PackScopeId[];
      readonly review: ArV3BetaPackReview;
    }
  | { readonly kind: 'fault'; readonly reason: ArV3PackFaultReason };

const INSTALLED_MEMBERS: readonly string[] = [
  'state',
  'analysis_profile_id',
  'prompt_bundle_id',
  'pack_sha256',
  'scope_ids',
  'review',
];

const REVIEW_MEMBERS = ['reviewer', 'capacity', 'reviewed_at', 'decision_ref', 'scope_statement'] as const;

const SHA256_HEX = /^[0-9a-f]{64}$/;
// The contract's own patterns for `AnalysisProfileId` and `PromptBundleId`: a Crockford ULID
// body after the prefix. `$` with no `m` flag does not stop before a trailing newline in
// JavaScript, so a value with one is not an identifier here.
const ANALYSIS_PROFILE_ID = /^ap_[0-9A-HJKMNP-TV-Z]{26}$/;
const PROMPT_BUNDLE_ID = /^pb_[0-9A-HJKMNP-TV-Z]{26}$/;
const ISO_DATE = /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

const fault = (reason: ArV3PackFaultReason): ArV3PackReading => ({ kind: 'fault', reason });

/**
 * Classify one `getArV3BetaPackStatus` body. Total: every input is one of the three outcomes.
 *
 * An attestation member that is blank is a fault: a pack "reviewed by" nobody is not an
 * attested pack, and printing the blank would read as one.
 */
export function readArV3PackStatus(body: unknown): ArV3PackReading {
  if (!isRecord(body)) return fault('not_an_object');
  const keys = Object.keys(body);

  if (body.state === 'not_installed') {
    return keys.length === 1 ? { kind: 'not_installed' } : fault('members_beside_not_installed');
  }
  if (body.state !== 'installed') return fault('unknown_state');

  if (keys.some((key) => !INSTALLED_MEMBERS.includes(key))) return fault('unknown_member');
  if (INSTALLED_MEMBERS.some((key) => !(key in body))) return fault('missing_member');

  const { analysis_profile_id: profileId, prompt_bundle_id: bundleId, pack_sha256: digest } = body;
  if (!isNonEmptyString(profileId) || !isNonEmptyString(bundleId)) return fault('missing_member');
  if (!ANALYSIS_PROFILE_ID.test(profileId) || !PROMPT_BUNDLE_ID.test(bundleId)) return fault('bad_identifier');
  if (typeof digest !== 'string' || !SHA256_HEX.test(digest)) return fault('bad_digest');

  const scopes = body.scope_ids;
  if (
    !Array.isArray(scopes) ||
    scopes.length !== AR_V3_PACK_SCOPE_IDS.length ||
    scopes.some((scope, index) => scope !== AR_V3_PACK_SCOPE_IDS[index])
  ) {
    return fault('bad_scope_list');
  }

  const review = body.review;
  if (!isRecord(review)) return fault('bad_attestation');
  if (Object.keys(review).length !== REVIEW_MEMBERS.length) return fault('bad_attestation');
  for (const member of REVIEW_MEMBERS) {
    if (!isNonEmptyString(review[member])) return fault('bad_attestation');
  }
  if (!ISO_DATE.test(review.reviewed_at as string)) return fault('bad_attestation');

  return {
    kind: 'installed',
    analysisProfileId: profileId,
    promptBundleId: bundleId,
    packSha256: digest,
    scopeIds: AR_V3_PACK_SCOPE_IDS,
    review: {
      reviewer: review.reviewer as string,
      capacity: review.capacity as string,
      reviewed_at: review.reviewed_at as string,
      decision_ref: review.decision_ref as string,
      scope_statement: review.scope_statement as string,
    },
  };
}
