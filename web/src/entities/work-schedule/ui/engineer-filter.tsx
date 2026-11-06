/**
 * «Инженер: Все / <имя>» above the month and the reserve (`D-319`). The choice lives in the address, so the page owns it;
 * this only draws the select and, when the address named an engineer the read does not carry, says everyone is shown.
 */

import type { EngineerFilter } from '../model/engineer-filter';
import styles from './engineer-filter.module.css';

export interface EngineerFilterSelectProps {
  readonly engineers: readonly { readonly user_uid: string; readonly label: string }[];
  readonly filter: EngineerFilter;
  readonly onChange: (uid: string | null) => void;
}

export function EngineerFilterSelect({ engineers, filter, onChange }: EngineerFilterSelectProps) {
  return (
    <div className={styles.filter} data-schedule-filter={filter.uid ?? ''}>
      <label className={styles.field}>
        Инженер
        <select value={filter.uid ?? ''} onChange={(event) => onChange(event.target.value === '' ? null : event.target.value)}>
          <option value="">Все</option>
          {engineers.map((engineer) => (
            <option key={engineer.user_uid} value={engineer.user_uid}>
              {engineer.label}
            </option>
          ))}
        </select>
      </label>
      {filter.unknown ? (
        <span className={styles.unknown} data-schedule-filter-unknown="">
          Инженер из ссылки не найден среди действующих — показаны все.
        </span>
      ) : null}
    </div>
  );
}
