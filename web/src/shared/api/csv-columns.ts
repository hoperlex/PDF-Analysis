/**
 * The frozen CSV column contract — `OD-11`, `P02_SEAMS.md` section 6.
 *
 * Seventeen columns in this exact order. `B5` produces the file and `B8` downloads it;
 * this constant exists so the download panel can say what the user is about to get, and
 * so a contract test can prove the frontend's idea of the column list has not drifted
 * from the seam document. Nothing here generates a CSV: the export endpoint is
 * synchronous and the browser never builds one from cached data.
 *
 * The bytes are fixed too, and stated here because they change what "open this file"
 * means: UTF-8 **with a byte-order mark**, comma delimiter, CRLF line ending, RFC 4180
 * quoting. The BOM is there because the intended reader opens the file in Excel, which
 * otherwise mis-decodes Cyrillic.
 *
 * Granularity is one row per evidence item: a finding with three quotations produces
 * three rows sharing columns 1-11 and 14-17.
 */

export const CSV_COLUMNS = [
  'project_uid',
  'document_uid',
  'version_uid',
  'run_id',
  'run_state',
  'provider_mode',
  'finding_uid',
  'finding_observation_id',
  'category',
  'finding_text',
  'recommendation_text',
  'evidence_page',
  'evidence_quote',
  'current_verdict',
  'latest_comment',
  'latest_decision_id',
  'decision_recorded_at',
] as const;

export type CsvColumn = (typeof CSV_COLUMNS)[number];

/** The byte-level facts a download panel may state to the user without guessing. */
export const CSV_ENCODING = {
  charset: 'utf-8',
  byteOrderMark: true,
  delimiter: ',',
  lineEnding: '\r\n',
  quoting: 'RFC 4180',
  /** A null projection column is the empty string, never `null` and never `NULL`. */
  nullRepresentation: '',
} as const;

/** Suggested download name. The server's `Content-Disposition` wins if it sends one. */
export function csvFileName(runId: string): string {
  return `${runId}-findings.csv`;
}
