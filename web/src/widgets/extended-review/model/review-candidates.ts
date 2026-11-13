/** Presentation of retained candidates. It allocates no Finding identity and makes no decision. */
import type { Finding, Severity } from '@/shared/api';

export type CandidateRecord = Readonly<Record<string, unknown>>;
export const candidateText = (value: unknown): string => typeof value === 'string' ? value : '';
export const candidateObject = (value: unknown): CandidateRecord | null =>
  typeof value === 'object' && value !== null && !Array.isArray(value) ? value as CandidateRecord : null;
export const candidateObjects = (value: unknown): CandidateRecord[] =>
  Array.isArray(value) ? value.flatMap((item) => { const row = candidateObject(item); return row === null ? [] : [row]; }) : [];
export const candidateStrings = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
export const PROPOSAL_SEVERITIES: readonly Severity[] = ['critical', 'economic', 'operational', 'recommendation', 'check_adjacent'];
export const CONSOLIDATION_VERSIONS: readonly string[] = ['ensemble-linked-v1', 'strict-cross-window-v1', 'v2-flow-repair-v1'];

export interface ReviewCandidate {
  readonly key: string;
  readonly number: number;
  readonly title: string;
  readonly description: string;
  readonly members: readonly CandidateRecord[];
  readonly sources: readonly CandidateRecord[];
  readonly missingSources: readonly string[];
  readonly pages: readonly number[];
  readonly origin: 'text' | 'drawing' | 'cross_check' | 'unknown';
  readonly severity: Severity | undefined;
  readonly recommendations: readonly string[];
  readonly norms: readonly CandidateRecord[];
}

export function reviewCandidates(value: unknown, published: readonly Finding[] = []) {
  const result = candidateObject(value);
  const raw = candidateObjects(result?.observations);
  const sources = new Map(candidateObjects(result?.sources).map((source) => [candidateText(source.source_id), source]));
  for (const window of candidateObjects(result?.windows)) {
    for (const source of candidateObjects(window.sources)) sources.set(candidateText(source.source_id), source);
  }
  const publishedRefs = new Set(published.flatMap((finding) => [finding.observation, ...(finding.merged_observations ?? [])])
    .map((item) => item.extended_observation_ref).filter((item): item is string => typeof item === 'string'));
  const consolidation = candidateObject(result?.consolidation);
  const grouped = consolidation?.complete === true && CONSOLIDATION_VERSIONS.includes(candidateText(consolidation.version));
  const groups = grouped ? candidateObjects(result?.consolidated_observations) : [];
  const indices = groups.flatMap((group) => candidateObjects(group.origin_records).map((origin) => origin.raw_index));
  const validGroups = groups.length > 0 && indices.length === raw.length && new Set(indices).size === raw.length
    && indices.every((index) => typeof index === 'number' && Number.isSafeInteger(index) && index >= 0 && index < raw.length);
  const entries = validGroups ? groups.map((group) => ({ group,
    members: candidateObjects(group.origin_records).map((origin) => raw[origin.raw_index as number] as CandidateRecord) }))
    : raw.map((item) => ({ group: item, members: [item] }));
  const rows: ReviewCandidate[] = [];
  let publishedGroups = 0;
  for (const [index, entry] of entries.entries()) {
    const members = entry.members.filter((item) => !publishedRefs.has(candidateText(item.observation_id)));
    if (members.length === 0) { publishedGroups += 1; continue; }
    const representative = members.length === entry.members.length ? entry.group : members[0] ?? entry.group;
    const sourceIds = [...new Set(members.flatMap((item) => candidateStrings(item.source_ids)))];
    const bound = sourceIds.flatMap((key) => { const source = sources.get(key); return source === undefined ? [] : [source]; });
    const kinds = new Set(bound.map((source) => source.kind));
    const proposals = [...new Set(members.map((item) => item.proposed_severity)
      .filter((severity): severity is Severity => PROPOSAL_SEVERITIES.includes(severity as Severity)))];
    const recommendations = [...new Set(members.map((item) => candidateText(item.recommendation_text)).filter(Boolean))];
    const norms = new Map(members.flatMap((item) => candidateObjects(item.norm_candidates))
      .map((norm) => [`${candidateText(norm.paragraph_id)}:${candidateText(norm.quote)}`, norm]));
    rows.push({ key: candidateText(entry.group.group_id) || candidateText(entry.group.observation_id) || `retained:${index}`,
      number: index + 1, title: candidateText(representative.title), description: candidateText(representative.description),
      members, sources: bound, missingSources: sourceIds.filter((key) => !sources.has(key)),
      pages: [...new Set(bound.map((source) => source.page_number)
        .filter((page): page is number => typeof page === 'number' && Number.isSafeInteger(page) && page > 0))].sort((a, b) => a - b),
      origin: kinds.size > 1 ? 'cross_check' : kinds.has('image') ? 'drawing' : kinds.has('text') ? 'text' : 'unknown',
      severity: proposals.length === 1 ? proposals[0] : undefined, recommendations, norms: [...norms.values()] });
  }
  return { rows, rawCount: raw.length, groupCount: entries.length, publishedGroups,
    groupingIncomplete: grouped && !validGroups && raw.length > 0 };
}
