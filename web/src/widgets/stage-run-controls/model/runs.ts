import type { StageChainRun } from '@/shared/api';

export const RUN_WORDS: Record<StageChainRun['state'], string> = {
  queued: 'В очереди', running: 'Выполняется', paused: 'Приостановлено',
  completed: 'Завершено', failed: 'Ошибка', cancelled: 'Отменено',
};

export const STEP_WORDS: Readonly<Record<number, string>> = {
  1: 'Связи листов', 2: 'Исключение одинакового текста', 3: 'Расхождения',
  4: 'ИИ-ревизия', 5: 'Классификация и починка связей', 6: 'Синтез', 7: 'Карточки',
};

export function latestFullRun(runs: readonly StageChainRun[]): StageChainRun | undefined {
  return runs.filter((run) => run.kind === 'full')
    .sort((left, right) => Date.parse(right.created_at) - Date.parse(left.created_at))[0];
}

export function runActive(run: StageChainRun | undefined): boolean {
  return run !== undefined && ['queued', 'running', 'paused'].includes(run.state);
}

/** Retain a command's key after an uncertain response; a changed payload is a new intent. */
export class IntentKey {
  private held: { signature: string; key: string } | null = null;
  constructor(private readonly create: () => string) {}
  for(payload: unknown): string {
    const signature = JSON.stringify(payload);
    if (this.held?.signature !== signature) this.held = { signature, key: this.create() };
    return this.held.key;
  }
  clear() { this.held = null; }
}

export const STAGE_RUN_KEYS = {
  list: (pairId: string) => ['stage-full-runs', pairId] as const,
  run: (runId: string) => ['stage-full-run', runId] as const,
  map: (pairId: string) => ['stage-sheet-map', pairId, 'current'] as const,
};
