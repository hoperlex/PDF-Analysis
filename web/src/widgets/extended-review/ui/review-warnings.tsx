import { extendedExecutionReason } from './execution-reason';

const warningLabels: Record<string, string> = {
  native_pdf_page_render_no_ocr: 'Для визуального анализа созданы изображения страниц исходного PDF. Отдельное распознавание текста сканов не выполнялось.',
  portal_text_only_native_page_visuals: 'Portal-набор содержит только текстовые блоки. Для визуального анализа использованы настоящие изображения страниц PDF; это не сегментация портала.',
  remaining_blocks_not_reviewed: 'Часть блоков находится за пределами одобренного окна и не исследована.',
  geometry_blocks_not_available: 'Для части блоков нет подтверждённого изображения.',
  no_image_blocks_available: 'Нет доступных изображений блоков для визуального обзора.',
  merge_omitted_sources_retained: 'Не включённые в модельный свод исходные наблюдения сохранены отдельно.',
  text_observations_outside_merge_window: 'Часть текстовых наблюдений находится за пределами окна свода.',
  page_context_truncated: 'Текстовый контекст страниц ограничен по размеру; обзор не охватывает весь текст страницы.',
  visual_context_bounded_full_text_reviewed: 'Контекст отдельных изображений сокращён; полный текст страниц передан в комплексную сверку по частям.',
  norm_lookup_window_exhausted: 'Исчерпано окно поиска по корпусу; часть нормативных оснований не проверялась.',
  norm_semantic_lookup_failed: 'Поиск норм по смыслу завершился ошибкой; для части замечаний нормативные основания не проверены.',
  norm_semantic_lookup_window_exhausted: 'Исчерпан лимит поиска норм по смыслу; часть замечаний осталась без проверки по нормам.',
  merge_context_truncated: 'Для свода использованы сокращённые описания; подробные источники требуют экспертной сверки.',
};

/** Repeated receipts remain counted, without repeating the same sentence per batch. */
export function ReviewWarnings({ warnings }: { readonly warnings: unknown }) {
  if (!Array.isArray(warnings) || warnings.length === 0) return null;
  const counts = new Map<string, number>();
  for (const warning of warnings) {
    const code = typeof warning === 'string' ? warning : '';
    counts.set(code, (counts.get(code) ?? 0) + 1);
  }
  return <aside aria-label="Ограничения анализа"><ul>{[...counts].map(([code, count]) => <li key={code} data-review-warning={code}>
    {warningLabels[code] ?? extendedExecutionReason(code)}{count > 1 ? ` Повторений в записи: ${count}.` : ''}
  </li>)}</ul></aside>;
}
