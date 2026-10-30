import type { ExtendedRunReview, Finding, RunStatus } from '@/shared/api';

export type SavedResultSide = {
  readonly run: RunStatus;
  readonly findings: readonly Finding[] | null;
  readonly extended: ExtendedRunReview | null;
  readonly extendedUnavailable: boolean;
  readonly receivedAt: string;
};
type RecordValue = Record<string, unknown>;
export type SavedResultRow = {
  readonly key: string;
  readonly kind: 'finding' | 'preliminary';
  readonly comparison: 'same' | 'changed' | 'left_only' | 'right_only';
  readonly left: RecordValue | null;
  readonly right: RecordValue | null;
  readonly leftIndex: number | null;
  readonly rightIndex: number | null;
  readonly matchBasis: 'finding_uid' | 'exact_source_content' | 'exact_preliminary' | null;
  readonly expertStateChanged: boolean | null;
};
export function savedObject(value: unknown): RecordValue | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as RecordValue : null;
}
function objects(value: unknown): RecordValue[] {
  return Array.isArray(value) ? value.flatMap((entry) => { const row = savedObject(entry); return row === null ? [] : [row]; }) : [];
}
export function hasSavedPreliminary(side: SavedResultSide): boolean {
  return side.extended !== null && !['unavailable', 'not_started', 'running'].includes(side.extended.status)
    && Array.isArray(savedObject(side.extended.result)?.observations);
}
function stable(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stable).join(',')}]`;
  const object = savedObject(value);
  return object === null ? JSON.stringify(value) ?? 'null' : `{${Object.keys(object).sort().map((key) => `${JSON.stringify(key)}:${stable(object[key])}`).join(',')}}`;
}
function findingPartitions(row: RecordValue): RecordValue[] | null {
  const canonical = savedObject(row.observation);
  if (canonical === null) return null;
  const merged = row.merged_observations ?? [];
  if (!Array.isArray(merged) || merged.some((entry) => savedObject(entry) === null)) return null;
  return [canonical, ...merged.map((entry) => savedObject(entry)!)];
}
function anchorContent(value: unknown): string {
  const anchor = savedObject(value);
  return anchor === null ? stable(value) : stable(Object.fromEntries(Object.entries(anchor).filter(([key]) => key !== 'evidence_ordinal')));
}
function observationContent(row: RecordValue): string {
  const content = Object.fromEntries(Object.entries(row).filter(([key]) => !['run_id', 'finding_observation_id', 'provenance'].includes(key)));
  if (Array.isArray(content.evidence)) content.evidence = content.evidence.map(anchorContent).sort();
  if (Array.isArray(content.norm_citations)) content.norm_citations = content.norm_citations.map(stable).sort();
  return stable(content);
}
function findingContent(row: RecordValue): string {
  const partitions = findingPartitions(row);
  return stable({ category: row.category, observations: partitions === null ? row : partitions.map(observationContent).sort() });
}
/** Strict display correspondence only; source offsets remain in their original page/block space. */
function exactFindingKey(row: RecordValue, side: SavedResultSide): string | null {
  if (row.project_uid !== side.run.project_uid || row.version_uid !== side.run.version_uid) return null;
  const partitions = findingPartitions(row);
  if (partitions === null) return null;
  const keys: string[] = [];
  for (const observation of partitions) {
    if (observation.run_id !== side.run.run_id || typeof observation.category !== 'string'
      || typeof observation.finding_text !== 'string' || !observation.finding_text.trim()
      || typeof observation.recommendation_text !== 'string' || !Array.isArray(observation.evidence) || observation.evidence.length === 0) return null;
    for (const raw of observation.evidence) {
      const anchor = savedObject(raw);
      if (anchor === null || typeof anchor.page_number !== 'number' || !Number.isSafeInteger(anchor.page_number) || anchor.page_number <= 0
        || typeof anchor.quote !== 'string' || !anchor.quote.trim() || typeof anchor.char_start !== 'number'
        || !Number.isSafeInteger(anchor.char_start) || anchor.char_start < 0 || typeof anchor.char_end !== 'number'
        || !Number.isSafeInteger(anchor.char_end) || anchor.char_end <= anchor.char_start
        || anchor.char_end - anchor.char_start !== Array.from(anchor.quote).length
        || (anchor.block_id !== undefined && anchor.block_id !== null && (typeof anchor.block_id !== 'string' || !anchor.block_id))) return null;
    }
    keys.push(stable({ category: observation.category, text: observation.finding_text, recommendation: observation.recommendation_text,
      required_value: observation.required_value, stated_value: observation.stated_value,
      evidence: observation.evidence.map((raw) => {
        const anchor = savedObject(raw)!;
        return stable({ page_number: anchor.page_number, quote: anchor.quote, char_start: anchor.char_start, char_end: anchor.char_end, block_id: anchor.block_id ?? null });
      }).sort() }));
  }
  return stable({ project_uid: row.project_uid, version_uid: row.version_uid, category: row.category, observations: keys.sort() });
}
function expertState(row: RecordValue): string {
  return stable({ current_verdict: row.current_verdict, decided_severity: row.decided_severity ?? null });
}
function preliminaryIndex(side: SavedResultSide) {
  const result = savedObject(side.extended?.result);
  const sources = new Map<string, string>();
  const conflicts = new Set<string>();
  for (const source of objects(result?.sources)) {
    if (typeof source.source_id !== 'string') continue;
    const identity = stable(Object.fromEntries(['version_uid', 'kind', 'source_type', 'page_number', 'bbox_norm',
      'crop_sha256', 'text_sha256', 'artifact_sha256', 'quote', 'quote_source'].filter((field) => source[field] !== undefined).map((field) => [field, source[field]])));
    if (sources.has(source.source_id) && sources.get(source.source_id) !== identity) conflicts.add(source.source_id);
    if (source.version_uid !== undefined && source.version_uid !== side.run.version_uid) conflicts.add(source.source_id);
    if (typeof source.page_number !== 'number' || ![source.crop_sha256, source.text_sha256, source.artifact_sha256, source.quote].some((value) => typeof value === 'string' && value.length > 0)) conflicts.add(source.source_id);
    sources.set(source.source_id, identity);
  }
  return objects(result?.observations).map((row, index) => {
    const ids = Array.isArray(row.source_ids) ? row.source_ids : [];
    const bound = ids.length > 0 && ids.every((id) => typeof id === 'string' && sources.has(id) && !conflicts.has(id));
    const match = bound && typeof row.title === 'string' && typeof row.description === 'string'
      ? stable({ title: row.title, description: row.description, category: row.category,
        sources: [...new Set(ids.map((id) => sources.get(String(id))))].sort(),
        primary_text: savedObject(row.original_primary_observation)?.finding_text,
        primary_recommendation: savedObject(row.original_primary_observation)?.recommendation_text }) : null;
    return { row, index, match };
  });
}

/** Read-only correspondence: durable finding identity or exact wording and actual source binding. */
export function compareSavedResults(left: SavedResultSide, right: SavedResultSide): readonly SavedResultRow[] {
  if (left.run.project_uid !== right.run.project_uid || left.run.version_uid !== right.run.version_uid) throw new Error('Для сопоставления сохранённых находок нужны прогоны одного проекта и одной неизменяемой версии.');
  const result: SavedResultRow[] = [];
  // An unavailable list is not an empty side. Do not publish one-sided finding differences for it.
  if (left.findings !== null && right.findings !== null) {
    const targets = new Map(right.findings.map((row, index) => [row.finding_uid, { row, index }]));
    const leftIds = new Set(left.findings.map((row) => row.finding_uid));
    const exact = new Map<string, { indices: number[]; next: number }>();
    right.findings.forEach((row, index) => {
      // Reserve durable-ID matches before any content match can consume them.
      if (leftIds.has(row.finding_uid)) return;
      const key = exactFindingKey(row, right);
      if (key === null) return;
      const bucket = exact.get(key) ?? { indices: [], next: 0 };
      bucket.indices.push(index); exact.set(key, bucket);
    });
    left.findings.forEach((row, index) => {
      let target = targets.get(row.finding_uid);
      let basis: SavedResultRow['matchBasis'] = target === undefined ? null : 'finding_uid';
      if (target === undefined) {
        const key = exactFindingKey(row, left);
        const bucket = key === null ? undefined : exact.get(key);
        const targetIndex = bucket === undefined ? undefined : bucket.indices[bucket.next];
        if (bucket !== undefined && targetIndex !== undefined) {
          bucket.next += 1;
          const candidate = right.findings[targetIndex]!;
          target = { row: candidate, index: targetIndex }; basis = 'exact_source_content';
        }
      }
      if (target !== undefined) targets.delete(target.row.finding_uid);
      result.push({ key: `finding:left:${index}`, kind: 'finding', comparison: target === undefined ? 'left_only'
        : findingContent(row) === findingContent(target.row) ? 'same' : 'changed', left: row,
        right: target?.row ?? null, leftIndex: index, rightIndex: target?.index ?? null, matchBasis: basis,
        expertStateChanged: target === undefined ? null : expertState(row) !== expertState(target.row) });
    });
    for (const target of targets.values()) result.push({ key: `finding:right:${target.index}`, kind: 'finding', comparison: 'right_only',
      left: null, right: target.row, leftIndex: null, rightIndex: target.index, matchBasis: null, expertStateChanged: null });
  }
  if (hasSavedPreliminary(left) && hasSavedPreliminary(right)) {
    const first = preliminaryIndex(left);
    const second = preliminaryIndex(right);
    const targets = new Map<string, number[]>();
    second.forEach((entry, index) => { if (entry.match !== null) { const bucket = targets.get(entry.match) ?? []; bucket.push(index); targets.set(entry.match, bucket); } });
    const used = new Set<number>();
    for (const entry of first) {
      const targetIndex = entry.match === null ? undefined : targets.get(entry.match)?.shift();
      const target = targetIndex === undefined ? undefined : second[targetIndex];
      if (targetIndex !== undefined) used.add(targetIndex);
      const annotations = (row: RecordValue) => stable(Object.fromEntries(['review', 'critic', 'correction', 'norm_assessment', 'norm_status',
        'norm_review_status', 'norm_candidates'].map((field) => [field, row[field]])));
      result.push({ key: `preliminary:left:${entry.index}`, kind: 'preliminary', comparison: target === undefined ? 'left_only'
        : annotations(entry.row) === annotations(target.row) ? 'same' : 'changed', left: entry.row, right: target?.row ?? null,
        leftIndex: entry.index, rightIndex: target?.index ?? null, matchBasis: target === undefined ? null : 'exact_preliminary', expertStateChanged: null });
    }
    second.forEach((entry, index) => { if (!used.has(index)) result.push({ key: `preliminary:right:${index}`, kind: 'preliminary',
      comparison: 'right_only', left: null, right: entry.row, leftIndex: null, rightIndex: index, matchBasis: null, expertStateChanged: null }); });
  }
  return result;
}

export function savedResultText(row: RecordValue | null): string {
  if (row === null) return '';
  const observation = savedObject(row.observation);
  return observation === null ? [row.title, row.description].filter((value) => typeof value === 'string').join('\n') : String(observation.finding_text ?? '');
}
export function savedResultPages(row: RecordValue | null, side: SavedResultSide): readonly number[] {
  if (row === null) return [];
  const observation = savedObject(row.observation);
  const sources = observation === null ? objects(savedObject(side.extended?.result)?.sources).filter((source) => Array.isArray(row.source_ids) && row.source_ids.includes(source.source_id))
    : (findingPartitions(row) ?? [observation]).flatMap((partition) => objects(partition.evidence));
  return [...new Set(sources.flatMap((source) => typeof source.page_number === 'number' && Number.isSafeInteger(source.page_number) && source.page_number > 0 ? [source.page_number] : []))].sort((a, b) => a - b);
}
