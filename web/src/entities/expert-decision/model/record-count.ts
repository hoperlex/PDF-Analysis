/**
 * «N записей» — how many decision-journal entries match the filters, said in Russian.
 *
 * The number is `DecisionRecordPage.total` (`UI-PARITY-P0A`): the count over every page of the
 * listing, not the length of the page on screen. The noun agrees with it, and agreement is
 * decided here, once, from the number: «1 запись», «2 записи», «5 записей», «11 записей»,
 * «21 запись», «112 записей». A bare «N записей» for every N would read wrongly for one in
 * three of them.
 */

export function recordCountLabel(total: number): string {
  const lastTwo = total % 100;
  const last = total % 10;
  let noun: string;
  if (lastTwo >= 11 && lastTwo <= 14) noun = 'записей';
  else if (last === 1) noun = 'запись';
  else if (last >= 2 && last <= 4) noun = 'записи';
  else noun = 'записей';
  return `${total} ${noun}`;
}
