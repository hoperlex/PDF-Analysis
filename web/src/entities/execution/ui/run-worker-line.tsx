/**
 * One line naming the worker that holds a run, for the queue and run screens
 * (`W54-WORKERS-WEB`). Every kind of {@link RunWorker} says what it is; none of them
 * reads as "no worker" unless the whole registry was read and no worker named the run.
 */

import { routes } from '@/shared/lib';

import type { RunWorker } from '../model/workers';

export function RunWorkerLine({ worker }: { readonly worker: RunWorker }) {
  switch (worker.kind) {
    case 'held':
      return (
        <p data-run-worker="held">
          Исполнитель: <a href={routes.workers()}><code>{worker.workerId}</code></a>
        </p>
      );
    case 'unheld':
      return (
        <p data-run-worker="unheld">
          Исполнитель не указан: ни один зарегистрированный исполнитель не удерживает этот прогон.
        </p>
      );
    case 'beyond':
      return (
        <p data-run-worker="beyond">
          Исполнитель не найден на первой странице <a href={routes.workers()}>списка исполнителей</a>.
        </p>
      );
    case 'unreadable':
      return <p data-run-worker="unreadable">Исполнитель не прочитан: список исполнителей недоступен.</p>;
    case 'pending':
      return <p data-run-worker="pending">Исполнитель уточняется…</p>;
  }
}
