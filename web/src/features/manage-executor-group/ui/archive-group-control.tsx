'use client';

/**
 * «В архив» for a group (`archiveExecutorGroup`, `EXEC2-WEB-GROUPS-01`, ADR-0026 decision 10).
 *
 * Asks first: archiving is one-way and is not deletion. An archived group takes no revision, rule
 * or run; work already admitted on it finishes. **A group a rule still names cannot be archived**,
 * and the control says so before it sends anything: it is disabled while `routedWorkKinds` is not
 * empty, with the work kinds named. The server refuses the same case with `conflict`
 * (`group_routed`), and that refusal is worded by `groupFailure` for a screen that read an older
 * list.
 */

import { useState } from 'react';

import type { ExecutorGroup, ExecutorWorkKind } from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import { WORK_KIND_LABELS } from '@/entities/executor-connection';
import { groupFailure } from '@/entities/executor-group';
import { useCommandKey } from '@/features/manage-executor-connection';

import { useArchiveExecutorGroup } from '../model/use-manage-executor-group';
import { GroupCommandFailure } from './group-command-failure';

export interface ArchiveGroupControlProps {
  readonly group: ExecutorGroup;
}

function routedSentence(kinds: readonly ExecutorWorkKind[]): string {
  return kinds.map((kind) => `«${WORK_KIND_LABELS[kind]}»`).join(', ');
}

export function ArchiveGroupControl({ group }: ArchiveGroupControlProps) {
  const archive = useArchiveExecutorGroup();
  const keys = useCommandKey();
  const [asking, setAsking] = useState(false);
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);
  const routed = group.routed_work_kinds;

  async function confirm() {
    setFailure(null);
    try {
      await archive.mutateAsync({ groupId: group.group_id, idempotencyKey: keys.keyFor(group.group_id) });
      keys.release();
      setAsking(false);
    } catch (error) {
      const failed = groupFailure(error, true);
      if (failed.kind !== 'unknown_outcome') keys.release();
      setFailure(failed);
    }
  }

  if (routed.length > 0) {
    return (
      <p className="am-note" role="status" data-group-archive="routed">
        В архив группу убрать нельзя: правило направляет на неё работу ({routedSentence(routed)}). Сначала назначьте
        этим видам работы другую группу на вкладке «Правила».
      </p>
    );
  }

  return (
    <>
      {asking ? (
        <div role="group" aria-label="Подтверждение архивирования группы" data-group-archive="asking">
          <p className="am-note">
            Убрать группу «{group.display_name}» в архив насовсем? Новых версий, правил и прогонов на неё больше не
            будет. Работа, которую уже приняли на группу, дойдёт до конца. Группа не удаляется, а её название освободится.
          </p>
          <button className="am-button am-button--small" type="button" disabled={archive.isPending} onClick={() => void confirm()}>
            {failure?.kind === 'unknown_outcome' ? 'Повторить с тем же ключом' : 'Подтвердить архивирование'}
          </button>{' '}
          <button
            className="am-button am-button--quiet am-button--small"
            type="button"
            disabled={archive.isPending}
            onClick={() => {
              setAsking(false);
              setFailure(null);
              keys.release();
            }}
          >
            Отмена
          </button>
        </div>
      ) : (
        <button className="am-button am-button--quiet am-button--small" type="button" onClick={() => setAsking(true)}>
          В архив
        </button>
      )}
      {failure !== null ? <GroupCommandFailure failure={failure} /> : null}
    </>
  );
}
