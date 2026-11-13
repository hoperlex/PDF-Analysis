import type { Finding, FindingDetail } from '@/shared/api';

export type VerificationSubject = Pick<Finding | FindingDetail, 'observation' | 'merged_observations'>;

const REASONS: Readonly<Record<string, string>> = {
  source_binding_unverified: 'Точная привязка источника не подтверждена.',
  quotation_absent: 'Цитата не найдена в заявленном фрагменте.',
  quotation_on_different_page: 'Цитата относится к другой странице.',
  span_outside_page: 'Указанный диапазон выходит за границы страницы.',
  span_outside_block: 'Указанный диапазон выходит за границы блока.',
  span_length_mismatch: 'Длина цитаты не совпадает с указанным диапазоном.',
  quote_in_recognised_text: 'Цитата найдена только в распознанном слое; нужна сверка с исходной страницей.',
  norm_label_unknown: 'Нормативный источник не удалось однозначно определить.',
  norm_quote_too_short: 'Нормативной цитаты недостаточно для точной привязки.',
  norm_quote_ambiguous: 'Нормативная цитата не позволяет однозначно выбрать фрагмент.',
  norm_quote_absent: 'Нормативная цитата не найдена в указанном источнике.',
  norm_value_not_in_quote: 'Заявленное нормативное значение не подтверждено цитатой.',
  stated_value_not_in_evidence: 'Значение из проекта не подтверждено переданным свидетельством.',
  block_not_in_run_geometry: 'Блок не найден в разметке этого прогона.',
  block_crop_mismatch: 'Изображение блока не совпало с сохранённым источником.',
  block_quote_not_in_recognised: 'Цитата не найдена в распознанном тексте блока.',
};

export function verificationReasonLabel(reason: string): string {
  return REASONS[reason] ?? 'Точная привязка источника требует ручной проверки.';
}

/** Review admission is separate from proof. Only the server's explicit unverified variant permits missing evidence. */
export function unverifiedReason(finding: VerificationSubject): string | null {
  for (const observation of [finding.observation, ...(finding.merged_observations ?? [])]) {
    if (observation.grounding_kind !== 'unverified') continue;
    const reason = observation.unverified_reason;
    if (typeof reason === 'string' && reason.trim() !== '') return reason;
  }
  return null;
}
