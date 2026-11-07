'use client';

/**
 * «Назначить группу» (`setExecutorRoutingRule`, `EXEC2-WEB-GROUPS-01`, ADR-0026 decision 11): point
 * the rule of one work kind at the current revision of a group.
 *
 * Rules are append-only: a change adds a rule revision, and work already admitted keeps the rule
 * revision it was admitted on. Only a group that is not archived is offered, and it is offered with
 * the revision that is current now, which is the revision the rule will name. The rule is stored in
 * either routing mode; while the mode is the legacy one nothing reads it, and the form says so after
 * the save so nobody believes new work has moved.
 */

import { useId, useState } from 'react';

import type { ExecutorGroup, ExecutorRoutingMode, ExecutorWorkKind } from '@/shared/api';
import { EXECUTOR_WORK_KIND_VALUES } from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import { WORK_KIND_LABELS } from '@/entities/executor-connection';
import { groupFailure, ruleTargets } from '@/entities/executor-group';
import { useCommandKey } from '@/features/manage-executor-connection';
import { LoadingState } from '@/shared/ui';

import { useSetExecutorRoutingRule } from '../model/use-manage-executor-group';
import { GroupCommandFailure } from './group-command-failure';
import styles from './rule-editor.module.css';

export interface RuleEditorProps {
  readonly groups: readonly ExecutorGroup[];
  /** The routing mode now; the confirmation says whether the rule is used yet. */
  readonly mode: ExecutorRoutingMode;
}

export function RuleEditor({ groups, mode }: RuleEditorProps) {
  const save = useSetExecutorRoutingRule();
  const keys = useCommandKey();
  const [workKind, setWorkKind] = useState<ExecutorWorkKind | ''>('');
  const [groupId, setGroupId] = useState('');
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const kindId = useId();
  const groupFieldId = useId();
  const targets = ruleTargets(groups);
  const chosen = targets.find((one) => one.group_id === groupId);
  const ready = workKind !== '' && chosen !== undefined;

  async function submit() {
    if (workKind === '' || chosen === undefined || save.isPending) return;
    setFailure(null);
    setSaved(null);
    const revisionId = chosen.current_revision.group_revision_id;
    try {
      await save.mutateAsync({
        workKind,
        groupRevisionId: revisionId,
        idempotencyKey: keys.keyFor(JSON.stringify([workKind, revisionId])),
      });
      keys.release();
      setSaved(
        `Правило «${WORK_KIND_LABELS[workKind]}» сохранено: группа «${chosen.display_name}», версия ${chosen.current_revision.revision_no}.`
        + (mode === 'legacy'
          ? ' Пока включены основное и резервное подключения, правило хранится и не используется.'
          : ' Оно действует для работы, которую примут после этого.'),
      );
    } catch (error) {
      const failed = groupFailure(error, true);
      if (failed.kind !== 'unknown_outcome') keys.release();
      setFailure(failed);
    }
  }

  return (
    <form
      className={`am-form ${styles.form}`}
      data-rule-editor
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <div className={`am-form__field ${styles.field}`}>
        <label htmlFor={kindId}>Вид работы</label>
        <select
          id={kindId}
          value={workKind}
          disabled={save.isPending}
          onChange={(event) => {
            setSaved(null);
            setWorkKind(event.target.value === '' ? '' : (event.target.value as ExecutorWorkKind));
          }}
        >
          <option value="">Выберите вид работы</option>
          {EXECUTOR_WORK_KIND_VALUES.map((kind) => (
            <option key={kind} value={kind}>{WORK_KIND_LABELS[kind]}</option>
          ))}
        </select>
      </div>
      <div className={`am-form__field ${styles.field}`}>
        <label htmlFor={groupFieldId}>Группа для правила</label>
        <select
          id={groupFieldId}
          value={groupId}
          disabled={save.isPending}
          onChange={(event) => {
            setSaved(null);
            setGroupId(event.target.value);
          }}
        >
          <option value="">Выберите группу</option>
          {targets.map((group) => (
            <option key={group.group_id} value={group.group_id}>
              {`${group.display_name} · модель «${group.current_revision.pin_id}» · версия ${group.current_revision.revision_no}`}
            </option>
          ))}
        </select>
      </div>
      <div className={`am-form__row ${styles.submit}`}>
        {/* The click is the submission (and the Enter key in a field clicks this button): it is not sent twice. */}
        <button
          className="am-button"
          type="submit"
          disabled={!ready || save.isPending}
          onClick={(event) => {
            event.preventDefault();
            void submit();
          }}
        >
          Назначить группу
        </button>
      </div>
      {targets.length === 0 ? (
        <p className={`am-form__hint ${styles.wide}`} role="status" data-rule-editor-no-groups>
          Действующих групп нет: сначала создайте группу на вкладке «Группы».
        </p>
      ) : (
        <p className={`am-form__hint ${styles.wide}`}>Правило называет версию группы, которая текущая сейчас. Новая версия группы правило не сдвигает.</p>
      )}
      {save.isPending ? <LoadingState what="сохранение правила" /> : null}
      {saved !== null ? <p className="am-note" role="status" data-rule-saved>{saved}</p> : null}
      {failure !== null ? <GroupCommandFailure failure={failure} /> : null}
    </form>
  );
}
