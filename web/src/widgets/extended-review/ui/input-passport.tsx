'use client';

type Row = Record<string, unknown>;
function object(value: unknown): Row | null { return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as Row : null; }
function rows(value: unknown): Row[] { return Array.isArray(value) ? value.flatMap((item) => object(item) === null ? [] : [item as Row]) : []; }
function text(value: unknown): string { return typeof value === 'string' ? value : ''; }
function count(value: unknown): string { return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? String(value) : '—'; }
const sheetLabels: Record<string, string> = { found: 'Найден', unresolved: 'Соответствие не установлено', external: 'Внешний документ', missing: 'Отсутствует' };
const textStates: Readonly<Record<string, string>> = { present: 'непустой текст передан', visual_required: 'нужна визуальная проверка', empty: 'текстовый слой пуст', blank_verified: 'пустая страница подтверждена' };

export function InputPassport({ value }: { readonly value: unknown }) {
  const passport = object(value);
  if (passport === null) return null;
  const register = object(passport.sheet_register);
  const entries = rows(register?.entries);
  return <section aria-label="Паспорт входного комплекта" data-input-passport="">
    <h3>Паспорт входного комплекта</h3>
    <p>Страниц PDF: {count(passport.page_count)} · изображений: {count(passport.crop_count)}. Проверка изображений: {passport.crop_verification === 'verified' ? 'хеши совпали' : passport.crop_verification === 'not_required' ? 'изображений нет' : 'ещё не завершена'}.</p>
    <details><summary>Контрольные суммы входа</summary><p>SHA256 исходного PDF: <code>{text(passport.pdf_sha256) || 'Не передан'}</code>.</p><p>SHA256 состава изображений: <code>{text(passport.crop_manifest_sha256) || 'Не передан'}</code>.</p></details>
    <p>{passport.source_coverage_complete === true ? 'Все страницы представлены в подготовленных материалах.' : passport.source_coverage_complete === false ? 'Часть страниц не представлена в подготовленных материалах.' : 'Покрытие страниц не передано.'} Это покрытие входа; комплектность проверяется отдельно по ведомости. Наличие пустого текстового слоя не подтверждает, что страница пуста.</p>
    <details><summary>Участие страниц в анализе</summary><ul>{rows(passport.pages).map((page) => <li key={count(page.page_number)}>Стр. {count(page.page_number)}: {textStates[text(page.text_state)] ?? `текст ${page.text_available === true ? 'передан' : 'не передан'}`}; изображений {Array.isArray(page.crop_ids) ? page.crop_ids.length : '—'}; пропусков {Array.isArray(page.skipped) ? page.skipped.length : '—'}.</li>)}</ul></details>
    <details><summary>Ведомость листов · {entries.length}</summary>
      {entries.length === 0 ? <p>Ведомость листов не удалось однозначно выделить из подготовленного текста. Полнота комплекта по ведомости не подтверждена.</p>
        : <ul>{entries.map((entry, index) => <li key={index}>Лист {text(entry.sheet_label)} · {text(entry.title)} — {sheetLabels[text(entry.status)] ?? 'Соответствие не установлено'}{Array.isArray(entry.page_numbers) && entry.page_numbers.length ? `; страницы PDF: ${entry.page_numbers.join(', ')}` : ''}. Основание на стр. {count(entry.register_page)}: <q>{text(entry.quote)}</q>.</li>)}</ul>}
      <p>Неустановленное соответствие не доказывает отсутствие листа. Исходный файл и изображения сохраняются без изменений.</p>
    </details>
  </section>;
}
