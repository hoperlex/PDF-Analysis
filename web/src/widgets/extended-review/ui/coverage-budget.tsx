import styles from './extended-review.module.css';

type RecordValue = Record<string, unknown>;
function object(value: unknown): RecordValue | null { return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as RecordValue : null; }
function count(value: unknown): string { return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? String(value) : '—'; }
const PHASE: Readonly<Record<string, string>> = {
  block_analysis: 'Визуальный анализ', comprehensive_analysis: 'Комплексная сверка', norm_verification: 'Нормативные цитаты',
  finding_review: 'Машинная критика', finding_correction: 'Предложения уточнения',
};

export function CoverageBudget({ mode, limits: value, estimatedText, pieceCharacters }: {
  readonly mode: unknown; readonly limits: unknown; readonly estimatedText: unknown; readonly pieceCharacters: unknown;
}) {
  const limits = object(value);
  if (limits === null && mode === undefined) return null;
  return <section className={styles.batchPanel} aria-label="Принятый план покрытия" data-coverage-budget-mode={typeof mode === 'string' ? mode : ''}>
    <h3>Принятый план покрытия</h3>
    {mode === 'source-sized-v1' ? <p>План комплексной сверки учитывает размер исходного текста. Показаны закреплённые при согласии пределы; прежние запуски сохраняют свои лимиты.</p> : <p>Показаны лимиты сохранённого плана. Они не расширяются автоматически при появлении нового режима.</p>}
    {typeof estimatedText === 'number' ? <p>Исходного текста в принятой оценке: {count(estimatedText)} символов. Целевой текстовый фрагмент: {count(pieceCharacters)} символов.</p> : null}
    {limits === null ? <p>Отдельные пределы процедур не переданы.</p> : <dl className={styles.coverageGrid}>{Object.entries(limits).filter(([phase, value]) => PHASE[phase] !== undefined && typeof value === 'number').map(([phase, value]) => <div key={phase}><dt>{PHASE[phase]}</dt><dd>до {count(value)} обращений в принятом окне</dd></div>)}</dl>}
    <p>Это верхние границы согласованного плана. Фактическое выполнение и остаток показаны в квитанциях пакетов; лимит не подтверждает полноту проверки.</p>
  </section>;
}
