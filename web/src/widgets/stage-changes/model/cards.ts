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
  partial: 'Прежнее решение относится к части свидетельств — требуется новая оценка', stale: 'Прежнее решение устарело',
};

export const MATERIALITY_WORDS = { material: 'Существенное изменение', non_material: 'Несущественное изменение', unknown: 'Существенность не определена' } as const;
export const IMPORTANCE_WORDS = { high: 'Высокая', normal: 'Обычная', unknown: 'Не определена' } as const;

export function groupedCards(cards: readonly StageChangeCard[]) {
  const sections: ReadonlyArray<{ kind: string; title: string; collapsed: boolean; includes: (card: StageChangeCard) => boolean }> = [
    { kind: 'project', title: CLASS_WORDS.PROJECT_CHANGE, collapsed: false,
      includes: (card) => card.class_name === 'PROJECT_CHANGE' && card.detail_increased !== true },
    { kind: 'detail', title: 'Детализация увеличена', collapsed: false,
      includes: (card) => card.class_name !== 'SERVICE_STRUCTURE' && card.detail_increased === true },
    { kind: 'material', title: 'Существенные изменения, требующие проверки', collapsed: false,
      includes: (card) => card.class_name === 'REVIEW' && card.detail_increased !== true && card.materiality === 'material' },
    { kind: 'non_material', title: 'Несущественные изменения, требующие проверки', collapsed: true,
      includes: (card) => card.class_name === 'REVIEW' && card.detail_increased !== true && card.materiality === 'non_material' },
    { kind: 'unknown', title: 'Требуют проверки · существенность не определена', collapsed: false,
      includes: (card) => card.class_name === 'REVIEW' && card.detail_increased !== true && (card.materiality === undefined || card.materiality === 'unknown') },
    { kind: 'service', title: CLASS_WORDS.SERVICE_STRUCTURE, collapsed: true,
      includes: (card) => card.class_name === 'SERVICE_STRUCTURE' },
  ];
  return sections.flatMap((section) => {
    const selected = cards.filter(section.includes);
    const categories = [...new Set(selected.map((card) => card.category))];
    return categories.map((category) => ({ key: `${section.kind}:${category}`, kind: section.kind,
      title: `${section.title} · ${CATEGORY_WORDS[category]}`, collapsed: section.collapsed,
      cards: selected.filter((card) => card.category === category) }));
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
