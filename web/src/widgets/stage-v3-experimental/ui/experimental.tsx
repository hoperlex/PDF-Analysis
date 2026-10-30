import type { StageCardEvidence, StageChainRun, StageChangeCard } from '@/shared/api';
import { parameterRows } from '../model/report';
import { StageV3ParameterSources } from './report';

export type StageEngine = NonNullable<StageChainRun['engine']>;
const EXPERIMENT = 'v3_native_text_experimental';
const PROVENANCE = 'Эксперимент V3 на основе PDF-proverka. Используется только собственный текст PDF. Графика, сканы и проверка по нормативной базе в этот режим не входят.';

function object(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : null;
}
function text(value: unknown, empty = 'Не указано'): string {
  return typeof value === 'string' && value.trim() !== '' ? value : typeof value === 'number' && Number.isFinite(value) ? String(value) : empty;
}
function strings(value: unknown): string[] { return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []; }

export function StageEngineSelector({ value, disabled, onChange }: { readonly value: StageEngine; readonly disabled: boolean; readonly onChange: (engine: StageEngine) => void }) {
  return <div data-stage-engine-selector="">
    <label>Метод сравнения <select aria-label="Метод сравнения стадий" value={value} disabled={disabled}
      onChange={(event) => onChange(event.target.value === EXPERIMENT ? EXPERIMENT : 'classic')}>
      <option value="classic">Классическое сравнение</option>
      <option value={EXPERIMENT}>V3 · эксперимент, только текст PDF</option>
    </select></label>
    {value === EXPERIMENT ? <><p className="am-note">{PROVENANCE}</p><p className="am-note">Новый запуск закрепляет отдельный план обработки текста по частям. Его границы и фактическое покрытие показывает сервер; прежние принятые запуски сохраняют свой план.</p><p className="am-note">Требуется ИИ. Оценка и согласие относятся к одному следующему обращению к модели; затем — «Продолжить» с новой оценкой. Результаты предварительные, инженер их не подтверждал.</p></> : null}
  </div>;
}

const PROCEDURE_WORDS: Readonly<Record<string, string>> = {
  Mapper: 'Сопоставление фрагментов (Mapper)', Miner: 'Извлечение изменений (Miner)', Dedupe: 'Удаление повторов (Dedupe)',
  'Разбор непарных страниц': 'Разбор непарных страниц', 'Проверка параметров': 'Проверка параметров', 'Карточки V3': 'Карточки V3',
};
const STATE_WORDS: Readonly<Record<string, string>> = {
  queued: 'Ожидает', running: 'Выполняется', completed: 'Завершено', failed: 'Ошибка', partial: 'Неполный результат', paused: 'Приостановлено',
};
const COVERAGE_WORDS: Readonly<Record<string, string>> = {
  pages: 'Страниц', page_count: 'Страниц', left_pages: 'Страниц П', right_pages: 'Страниц Р',
  text_characters: 'Знаков', characters: 'Знаков', chars: 'Знаков', fragments: 'Фрагментов',
  left_fragments: 'Фрагментов П', right_fragments: 'Фрагментов Р', native_pages: 'Страниц с текстом',
  pages_total: 'Учтено страниц', pages_analysed: 'Страниц с выполненным разбором', pages_pending: 'Страниц ожидает разбора',
  pages_excluded: 'Страниц исключено с причиной', pages_failed: 'Страниц с ошибкой разбора',
  content_unmatched: 'Непарных страниц с содержимым', content_unmatched_pending: 'Непарных страниц ожидает разбора',
  native_text_plan: 'План обработки текста PDF',
};
const LIMIT_WORDS: Readonly<Record<string, string>> = {
  pages: 'Страниц суммарно по обеим сторонам', characters: 'Знаков исходного текста', fragments: 'Фрагментов исходного текста',
  pack_characters: 'Знаков на текстовый пакет', pack_blocks: 'Блоков на пакет', catalogue_blocks_per_page: 'Фрагментов каталога на страницу',
  catalogue_snippet_characters: 'Знаков в отрывке каталога', classification_units: 'Единиц классификации', events: 'Событий', parameters: 'Параметров', request_characters: 'Знаков в закодированном запросе',
};
function knownCount(value: unknown): string { return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? String(value) : '—'; }

export function StageExperimentalProgress({ progress, state }: { readonly progress: unknown; readonly state: StageChainRun['state'] }) {
  const body = object(progress);
  const procedures = Array.isArray(body?.procedures) ? body.procedures.flatMap((item) => {
    const row = object(item);
    return row !== null && typeof row.name === 'string' ? [{ name: row.name, state: typeof row.state === 'string' ? row.state : '', planned: row.planned, completed: row.completed, pending: row.pending }] : [];
  }) : [];
  const coverage = object(body?.coverage);
  const limits = object(body?.limits);
  const plan = text(body?.plan_version, '');
  return <section aria-label="Процедуры экспериментального V3" data-stage-v3-progress="">
    <h3>V3 · эксперимент, только текст PDF</h3><p className="am-note">{PROVENANCE}</p>
    {state === 'paused' ? <p role="status">Приостановлено. Для следующего обращения откройте «Продолжить», ознакомьтесь с оценкой и подтвердите передачу.</p> : null}
    {body === null ? <p>Состояние процедур ещё не передано. Завершение не подтверждено.</p> : <>
      <p>Принятый план: {plan === 'windowed-v1' ? 'Обработка текста по частям · windowed-v1' : plan === 'native-text-v3/1' || !plan ? 'Исторический ограниченный план V3' : plan}.</p>
      {plan === 'native-text-v3/1' || !plan ? <p>У этого сохранённого плана исторические границы: до 16 страниц, 80 000 знаков и 400 фрагментов. Новые окна ему автоматически не добавляются.</p> : null}
      {limits === null ? null : <details><summary>Закреплённые границы плана</summary><dl>{Object.entries(limits).filter(([name, value]) => LIMIT_WORDS[name] !== undefined && typeof value === 'number').map(([name, value]) => <div key={name}><dt>{LIMIT_WORDS[name]}</dt><dd>{knownCount(value)}</dd></div>)}</dl></details>}
      <p>Состояние: {state === 'paused' ? STATE_WORDS.paused : STATE_WORDS[text(body.status, '')] ?? 'Не передано'} · текущая процедура: {PROCEDURE_WORDS[text(body.procedure, '')] ?? text(body.procedure, 'Ещё не началась')}</p>
      {typeof body.planned_units === 'number' ? <p>Из известных сохранённых единиц: завершено {knownCount(body.completed_units)} из {knownCount(body.planned_units)}, не завершено {knownCount(body.pending_units)}. Будущие единицы, ещё не созданные после ответов, в этот счётчик не входят.</p> : null}
      {body.source_version === undefined ? null : <p className="am-note">Основано на исходной версии: <code>{text(body.source_version)}</code>.</p>}
      {procedures.length === 0 ? <p>Список процедур ещё не получен.</p> : <><p>Подтверждено завершение процедур: {procedures.filter((item) => item.state === 'completed').length} из {procedures.length}.</p>
        <ol>{procedures.map((item, index) => <li key={`${item.name}-${index}`} data-v3-procedure={item.name} data-v3-procedure-state={item.state}>
          {PROCEDURE_WORDS[item.name] ?? item.name} · {state === 'paused' && item.state === 'running' ? 'Ожидает продолжения' : STATE_WORDS[item.state] ?? 'Состояние не подтверждено'}
          {typeof item.planned === 'number' ? <p>Известных единиц: {knownCount(item.planned)}; завершено: {knownCount(item.completed)}; не завершено: {knownCount(item.pending)}.</p> : null}
        </li>)}</ol></>}
      {coverage === null ? null : <dl>{Object.entries(coverage).filter(([, value]) => typeof value === 'number' || typeof value === 'string').map(([name, value]) => <div key={name}><dt>{COVERAGE_WORDS[name] ?? name}</dt><dd>{text(value)}</dd></div>)}</dl>}
      {typeof coverage?.complete === 'boolean' ? <p>{coverage.complete ? 'Запланированные текстовые процедуры охватили все учтённые страницы.' : 'Есть страницы без завершённого текстового разбора.'} Это не подтверждение полноты инженерной проверки.</p> : null}
      {typeof coverage?.catalogue_complete === 'boolean' ? <p>{coverage.catalogue_complete ? 'Каталог учтённых страниц построен; в нём используются ограниченные выдержки.' : 'Построение каталога учтённых страниц не завершено.'}</p> : null}
      {coverage?.unmatched_candidate_search_complete === false ? <p>Поиск встречных кандидатов для непарных страниц ограничен; полный поиск соответствий не подтверждён.</p> : null}
      {coverage?.semantic_comparison_complete === false ? <p>Глобальная смысловая полнота сравнения не подтверждена.</p> : null}
      {strings(body.limitations).length === 0 ? null : <ul>{strings(body.limitations).map((item, index) => <li key={index}>{item}</li>)}</ul>}
    </>}
  </section>;
}

const VERIFICATION_WORDS: Readonly<Record<string, string>> = {
  CONFIRMED: 'Подтверждено машинной сверкой', CORRECTED: 'Уточнено машинной сверкой',
  CONFLICT: 'Противоречие — нужна проверка', UNREADABLE: 'Не удалось прочитать',
};

export function StageExperimentalParameters({ experimental, card, onOpenEvidence }: { readonly experimental: unknown;
  readonly card?: StageChangeCard; readonly onOpenEvidence?: (evidence: StageCardEvidence, card: StageChangeCard) => void }) {
  const body = object(experimental);
  if (body === null || body.engine !== EXPERIMENT) return null;
  const parameters = Array.isArray(body.parameters) ? body.parameters.flatMap((value) => { const row = object(value); return row === null ? [] : [row]; }) : [];
  const reportRows = card === undefined ? [] : parameterRows(card);
  return <section aria-label="Параметры экспериментального V3" data-stage-v3-parameters="">
    <h5>Параметры V3 · предварительная машинная сверка</h5>
    <p>Только текст PDF. Инженер не подтверждал результат. Соответствие нормам не проверялось.</p>
    {body.engineering_subject === undefined ? null : <p>Объект: {text(body.engineering_subject)}</p>}
    {body.change_summary === undefined ? null : <p>{text(body.change_summary)}</p>}
    {parameters.length === 0 ? <p>Структурированные параметры не переданы.</p> : <div style={{ overflowX: 'auto' }}><table>
      <thead><tr><th>Параметр</th><th>Было</th><th>Стало</th><th>Единица</th><th>Место</th><th>Машинная сверка</th></tr></thead>
      <tbody>{parameters.map((parameter, index) => {
        const verification = object(parameter.verification);
        const verdict = text(verification?.verdict, '');
        const reportRow = reportRows[index];
        return <tr key={index} data-v3-parameter="" data-v3-verification={verdict || 'PENDING'}>
          <th scope="row">{text(parameter.name)}</th><td>{text(parameter.old_value)}</td><td>{text(parameter.new_value)}</td>
          <td>{text(parameter.unit, '—')}</td><td>{text(parameter.location)}</td>
          <td><strong>{VERIFICATION_WORDS[verdict] ?? 'Не проверено'}</strong>
            {verification?.explanation === undefined ? null : <p>{text(verification.explanation)}</p>}
            {verdict !== 'CORRECTED' ? null : <p>После сверки: {text(verification?.old_value)} → {text(verification?.new_value)} {text(verification?.unit, '')}.</p>}
            {Array.isArray(verification?.evidence_refs) ? <ul>{verification.evidence_refs.map((reference, number) => {
              const item = object(reference);
              return <li key={number}>{typeof reference === 'string' ? reference : item === null ? 'Ссылка на источник не передана' : text(item.evidence_id ?? item.source_id ?? item.fragment_id ?? item.block_id, 'Ссылка на источник не передана')}</li>;
            })}</ul> : null}
            {card === undefined || reportRow === undefined ? null : <StageV3ParameterSources
              parameter={reportRow} card={card} onOpenEvidence={onOpenEvidence} />}
          </td>
        </tr>;
      })}</tbody>
    </table></div>}
    {body.quality === undefined ? null : <p>Качество: {text(body.quality, 'Не определено')}</p>}
  </section>;
}
