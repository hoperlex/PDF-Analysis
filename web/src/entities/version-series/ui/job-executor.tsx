'use client';

/**
 * The executor of a comparison AI job (`EXEC2-FOLLOWUP-01`): the planned group and model before the job's first call to the
 * model, the connection and model it is actually on after it, and — while it waits for an executor — why and since when. The words
 * are `jobExecutorSentence` / `jobWaitSentence`'s; the machine values are in `data-job-binding` and `data-job-wait-reason`.
 *
 * Only when the job waits for a runner on a group is the precise reason read, from the group's capacity, by `GroupWaitDetail`
 * (`entities/executor-group`), which also says that the wait ends; every other job mounts no read at all. A job that existed before
 * groups draws nothing, so the screens that show a job are drawn as they always were.
 */

import { GroupWaitDetail } from '@/entities/executor-group';

import { jobExecutorLine, jobExecutorSentence, jobWaitSentence } from '../model/job-executor';
import type { JobExecutorSource } from '../model/job-executor';

export interface JobExecutorProps {
  readonly job: JobExecutorSource;
}

export function JobExecutor({ job }: JobExecutorProps) {
  const line = jobExecutorLine(job);
  if (line === null) return null;
  const wait = jobWaitSentence(line);
  return (
    <div className="am-note" data-job-executor="" data-job-binding={line.phase} data-job-wait-reason={line.waitReason}>
      <p>{jobExecutorSentence(line)}</p>
      {wait === null ? null : <p role="status">{wait}</p>}
      {line.waitReason === 'runner_offline' && line.groupId !== undefined ? (
        <GroupWaitDetail groupId={line.groupId} waitReason={line.waitReason} waitingSince={line.waitingSince} />
      ) : null}
    </div>
  );
}
