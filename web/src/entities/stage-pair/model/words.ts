import type { StagePair } from '@/shared/api';

export function completenessLabel(value: StagePair['completeness']): string {
  switch (value) {
    case 'full': return 'Полный комплект';
    case 'partial': return 'Неполный комплект';
    case 'unknown': return 'Полнота не указана';
  }
}

export function suggestionReason(value: string): string {
  switch (value) {
    case 'section_designation_exact': return 'Совпадают раздел и подтверждённый шифр';
    case 'section_title_hint_exact': return 'Совпадают раздел и название';
    default: return 'Причина предложения не распознана; проверьте документы перед решением';
  }
}
