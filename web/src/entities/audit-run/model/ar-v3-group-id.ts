import type { ArV3RunGroupId } from '@/shared/api';

/** Validate only the opaque address shape; it conveys no group semantics. */
export function looksLikeArV3GroupId(value: unknown): value is ArV3RunGroupId {
  return typeof value === 'string' && /^arg_[0-9A-HJKMNP-TV-Z]{26}$/.test(value);
}
