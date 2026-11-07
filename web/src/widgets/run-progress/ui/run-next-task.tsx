'use client';

/** @jsxRuntime automatic */

/**
 * «Следующая задача» on a waiting run's page (`UI-B-70`): the original's card of the queue's next job, as far as this
 * installation's data goes. The words and the figures are `runNextTask`'s (`entities/audit-run`); this reads the queue's
 * first page (the entry the side menu's «Очередь» counter reads, so no second question when the menu is there) for a session
 * the queue is open to, and draws what it got. A session the queue is closed to, a read still in flight and a read that
 * failed each leave out the queue's part and keep the run's own reason, and the failure says so rather than showing
 * an empty card as if the queue were empty.
 */

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';

import type { RunStatus } from '@/shared/api';
import { routes } from '@/shared/lib';
import { screenAt } from '@/shared/config';
import { screenRolesAdmit } from '@/shared/config/screen-registry';
import { useMe } from '@/entities/account';
import { nextTaskPlace, nextTaskWhy, nextTaskWork, runNextTask } from '@/entities/audit-run';
import { queueQueryOptions } from '@/entities/execution';

import styles from './run-progress.module.css';

export function RunNextTask({ status }: { readonly status: RunStatus }) {
  const me = useMe();
  const queue = screenAt('/queue');
  const mayRead = me.data !== undefined && queue !== undefined && screenRolesAdmit(queue.roles, me.data.roles);
  const page = useQuery({ ...queueQueryOptions(), enabled: mayRead });
  const task = runNextTask(status, mayRead && !page.isError ? page.data : undefined);
  const place = nextTaskPlace(task);
  const work = nextTaskWork(task);
  return (
    <section className={`${styles.panel} ${styles.nextTask}`} aria-label="Следующая задача" data-run-next-task={task.read}>
      <h2>Следующая задача</h2>
      <p className={styles.caption}>
        Что уйдёт в работу раньше и почему эта задача ждёт. Порядок очереди — приоритет, затем время приёма; какой исполнитель
        возьмёт задачу, очередь не сообщает.
      </p>
      <dl className={styles.facts}>
        {place === null ? null : <><dt>Эта задача</dt><dd data-next-task-place={task.position ?? 'none'}>{place}</dd></>}
        {task.next === null ? null : (
          <>
            <dt>Первой уйдёт</dt>
            <dd data-next-task-first={task.next.run_id}>
              {task.next.project_name} · {task.next.document_name} · версия {task.next.version_ordinal}
              {' · '}
              <Link href={routes.run(task.next.project_uid, task.next.run_id)}>Открыть прогон</Link>
            </dd>
          </>
        )}
        <dt>Почему ждёт</dt>
        <dd data-next-task-why="">{nextTaskWhy(task).join(' ')}</dd>
        {work === null ? null : <><dt>Сейчас</dt><dd data-next-task-work="">{work}</dd></>}
      </dl>
      {mayRead && page.isError ? (
        <p role="status" data-next-task-unread="">Очередь прочитать не удалось: место в ней и соседние задачи не показаны. Причина ожидания выше взята из самого прогона.</p>
      ) : null}
      {task.read === 'partial' ? <p className={styles.caption}>По первой странице очереди.</p> : null}
      {mayRead ? <p className={styles.caption}><Link href={routes.queue()}>Открыть всю очередь →</Link></p> : null}
    </section>
  );
}
