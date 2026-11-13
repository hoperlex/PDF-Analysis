/** @jsxRuntime automatic */

type RecordValue = Record<string, unknown>;
const object = (value: unknown): RecordValue | null => typeof value === 'object' && value !== null && !Array.isArray(value) ? value as RecordValue : null;
const whole = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;

/** Counts are the runtime's receipts, never inferred from model confidence or from a negative norm lookup. */
export function InputAccounting({ value, reason }: { readonly value: unknown; readonly reason?: unknown }) {
  const row = object(value);
  if (row === null) return null;
  const { expected, valid, pending, refused, excluded } = row;
  if (![expected, valid, pending, refused, excluded].every(whole)) {
    return <p data-input-accounting="incomplete">Учет входных записей передан не полностью; полнота обработки не подтверждена.</p>;
  }
  const total = (valid as number) + (pending as number) + (refused as number) + (excluded as number);
  return <div data-input-accounting={total === expected ? 'balanced' : 'inconsistent'}>
    <p>Входных записей: {String(expected)}; проверено: {String(valid)}; ожидают обработки: {String(pending)}; технических отказов: {String(refused)}; исключено с основанием: {String(excluded)}.</p>
    {expected === 0 ? <p>Входных записей нет. {typeof reason === 'string' && reason !== '' ? `Основание: ${reason}.` : 'Основание не передано; выполнение обязательной проверки этим не подтверждено.'}</p> : null}
    {total === expected ? null : <p role="status">Сумма исходов не совпадает с числом входов. Полнота обработки требует проверки.</p>}
  </div>;
}
