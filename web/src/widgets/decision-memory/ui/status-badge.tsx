import { MEMORY_STATUS_LABELS, MEMORY_STATUS_TONES } from '@/entities/decision-memory';
import type { MemoryStatus } from '@/entities/decision-memory';

/** A case's standing as a badge; the contract value stays on `data-memory-status-badge`. */
export function MemoryStatusBadge({ status }: { readonly status: MemoryStatus }) {
  return (
    <span className={`am-badge am-badge--${MEMORY_STATUS_TONES[status]}`} data-memory-status-badge={status}>
      <span className="am-badge__label">{MEMORY_STATUS_LABELS[status]}</span>
    </span>
  );
}
