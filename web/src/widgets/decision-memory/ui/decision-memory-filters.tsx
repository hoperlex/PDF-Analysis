'use client';

/**
 * The five filters of the memory's list, in one row, each label beside its control. «Проект» is not here: the screen's
 * `?project=` is the list's `origin_project_uid`. Each control is a plain select; `'all'` is the absence of the filter.
 */

import { CATEGORY_LABELS } from '@/entities/expert-decision';
import {
  MEMORY_DATA_CLASS_CHOICES,
  MEMORY_DATA_CLASS_LABELS,
  MEMORY_STATUS_CHOICES,
  MEMORY_STATUS_LABELS,
  MEMORY_VERDICT_CHOICES,
  MEMORY_VERDICT_LABELS,
} from '@/entities/decision-memory';
import type { MemoryDataClassChoice, MemoryFilters, MemoryStatusChoice, MemoryVerdictChoice } from '@/entities/decision-memory';
import { PROJECT_SECTIONS, projectSectionTitle } from '@/entities/project';

import styles from './decision-memory.module.css';

export interface DecisionMemoryFiltersProps {
  readonly value: MemoryFilters;
  readonly onChange: (patch: Partial<MemoryFilters>) => void;
}

const CATEGORY_CODES = Object.keys(CATEGORY_LABELS) as readonly (keyof typeof CATEGORY_LABELS)[];

export function DecisionMemoryFilters({ value, onChange }: DecisionMemoryFiltersProps) {
  return (
    <div className={styles.filters} role="group" aria-label="Отбор дел памяти" data-memory-filters="">
      <div className="am-kb__filter">
        <label htmlFor="memory-filter-status">Состояние</label>
        <select
          id="memory-filter-status"
          value={value.status}
          onChange={(event) => onChange({ status: event.target.value as MemoryStatusChoice })}
        >
          {MEMORY_STATUS_CHOICES.map((choice) => (
            <option key={choice} value={choice}>{choice === 'all' ? 'Любое состояние' : MEMORY_STATUS_LABELS[choice]}</option>
          ))}
        </select>
      </div>
      <div className="am-kb__filter">
        <label htmlFor="memory-filter-verdict">Вердикт</label>
        <select
          id="memory-filter-verdict"
          value={value.verdict}
          onChange={(event) => onChange({ verdict: event.target.value as MemoryVerdictChoice })}
        >
          {MEMORY_VERDICT_CHOICES.map((choice) => (
            <option key={choice} value={choice}>{choice === 'all' ? 'Любой вердикт' : MEMORY_VERDICT_LABELS[choice]}</option>
          ))}
        </select>
      </div>
      <div className="am-kb__filter">
        <label htmlFor="memory-filter-category">Категория</label>
        <select id="memory-filter-category" value={value.category} onChange={(event) => onChange({ category: event.target.value })}>
          <option value="all">Любая категория</option>
          {CATEGORY_CODES.map((code) => (
            <option key={code} value={code}>{CATEGORY_LABELS[code]}</option>
          ))}
        </select>
      </div>
      <div className="am-kb__filter">
        <label htmlFor="memory-filter-section">Раздел</label>
        <select id="memory-filter-section" value={value.section} onChange={(event) => onChange({ section: event.target.value })}>
          <option value="all">Любой раздел</option>
          {PROJECT_SECTIONS.map((section) => (
            <option key={section.code} value={section.code}>{projectSectionTitle(section)}</option>
          ))}
        </select>
      </div>
      <div className="am-kb__filter">
        <label htmlFor="memory-filter-class">Данные</label>
        <select
          id="memory-filter-class"
          value={value.dataClass}
          onChange={(event) => onChange({ dataClass: event.target.value as MemoryDataClassChoice })}
        >
          {MEMORY_DATA_CLASS_CHOICES.map((choice) => (
            <option key={choice} value={choice}>{choice === 'all' ? 'Любые данные' : MEMORY_DATA_CLASS_LABELS[choice]}</option>
          ))}
        </select>
      </div>
    </div>
  );
}
