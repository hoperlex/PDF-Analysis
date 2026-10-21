/**
 * The run's Excel workbook as the browser names it (`W57B-NORMS-CATALOGUE-XLSX-01`).
 *
 * The workbook's layout belongs to the server (`exportRunXlsx`); the browser only names the
 * file it saves, as it does for the CSV (`csvFileName`), and the server's
 * `Content-Disposition` is the authority on the name it serves.
 */

/** Suggested download name, the CSV's with the workbook's extension. */
export function xlsxFileName(runId: string): string {
  return `${runId}-findings.xlsx`;
}
