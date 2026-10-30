import type { StageCardVerdictInput, StageChangeCard, StageChangeCategory, StageSystem } from '@/shared/api';

export interface VerdictDraft {
  readonly decision: 'accepted' | 'rejected';
  readonly reason: string;
  readonly expectedRevision: number;
}

export const CATEGORY_WORDS: Readonly<Record<StageChangeCategory, string>> = {
  areas: 'Площади', floors: 'Этажность', electrical_load: 'Электрические нагрузки',
  calculation_method: 'Метод расчёта', consumer_composition: 'Состав потребителей',
  room_composition: 'Состав помещений', dimensions: 'Размеры', materials: 'Материалы',
  equipment_parameters: 'Параметры оборудования', system_configuration: 'Состав системы',
  fire_safety: 'Пожарная безопасность', designation_rename: 'Обозначения',
  administrative: 'Служебные сведения', documentation_structure: 'Структура документации',
  formatting: 'Оформление', other_project: 'Другие проектные изменения',
  other_service: 'Другие служебные изменения', uncertain: 'Требует уточнения',
};

export const SYSTEM_WORDS: Readonly<Record<StageSystem, string>> = {
  unknown: 'Система не определена', architecture: 'Архитектура', structural: 'Конструкции',
  electrical: 'Электроснабжение', heating_ventilation: 'Отопление и вентиляция',
  water_sewage: 'Водоснабжение и канализация', fire_protection: 'Противопожарные системы',
  low_current: 'Слаботочные системы', technology: 'Технология', site: 'Генеральный план', other: 'Другая система',
};

export const CLASS_WORDS: Readonly<Record<StageChangeCard['class_name'], string>> = {
  PROJECT_CHANGE: 'Изменения проектных решений', REVIEW: 'Требуют проверки',
  SERVICE_STRUCTURE: 'Служебные и структурные изменения',
};

export const CARRYOVER_WORDS: Readonly<Record<NonNullable<StageChangeCard['carryover']>, string>> = {
  none: 'Решение не переносилось', full: 'Решение перенесено по тем же свидетельствам',
  partial: 'Решение перенесено частично — проверьте свидетельства', stale: 'Прежнее решение устарело',
};

export function groupedCards(cards: readonly StageChangeCard[]) {
  return (['PROJECT_CHANGE', 'REVIEW', 'SERVICE_STRUCTURE'] as const).flatMap((className) => {
    const selected = cards.filter((card) => card.class_name === className);
    const categories = [...new Set(selected.map((card) => card.category))];
    return categories.map((category) => ({ key: `${className}:${category}`, className,
      title: `${CLASS_WORDS[className]} · ${CATEGORY_WORDS[category]}`,
      collapsed: className === 'SERVICE_STRUCTURE', cards: selected.filter((card) => card.category === category) }));
  });
}

export function editVerdict(card: StageChangeCard, prior: VerdictDraft | undefined,
  decision: VerdictDraft['decision'], reason = prior?.reason ?? card.verdict?.reason ?? ''): VerdictDraft {
  return { decision, reason, expectedRevision: prior?.expectedRevision ?? card.verdict?.revision_no ?? 0 };
}

export function verdictUpdates(cards: readonly StageChangeCard[], drafts: Readonly<Record<string, VerdictDraft>>): StageCardVerdictInput[] {
  return cards.flatMap((card) => {
    const draft = drafts[card.card_id];
    const previous = card.verdict;
    if (card.class_name === 'SERVICE_STRUCTURE' || draft === undefined || (previous !== undefined && draft.decision === previous.decision && draft.reason.trim() === previous.reason)) return [];
    return [{ card_id: card.card_id, expected_revision: draft.expectedRevision,
      decision: draft.decision, reason: draft.reason.trim() }];
  });
}

export function rejectionReasonsMissing(updates: readonly StageCardVerdictInput[]): boolean {
  return updates.some((update) => update.decision === 'rejected' && update.reason.trim() === '');
}
