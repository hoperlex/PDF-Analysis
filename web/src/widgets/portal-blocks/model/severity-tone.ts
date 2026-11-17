/**
 * The badge tone of a severity for a count that stands for several findings, the one `SeverityBadge` draws it in. `null` is a
 * page whose findings no expert has given a severity yet: the neutral tone, never one borrowed from the model's proposal
 * (AGENTS §4).
 *
 * The tone is computed once, in `entities/finding` (`UIP-S06-03`); this module keeps the name the tile and its tests use.
 */

export { severityTone } from '@/entities/finding';
export type { SeverityTone } from '@/entities/finding';
