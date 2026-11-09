'use client';

/**
 * The form of a group (`EXEC2-WEB-GROUPS-01`, ADR-0026 decision 10): a name, the model every member
 * shares, and the members. It makes a new group or, given one, adds a new **revision** of it: the
 * full settings, never a patch, and the earlier revision is kept. Work already admitted on an
 * earlier revision finishes on it; the rules that name the group are not moved to the new revision.
 *
 * **A group is homogeneous, and the form says so before the server refuses.** Every member names a
 * connection and the current revision of it; that revision must pin exactly the group's model and
 * name on the gateway, and share its billing. The picker offers each connection with its current
 * revision and flags, beside the member, a pin, a model name or a billing that disagrees with the
 * group (`memberProblem`). A connection that disagrees cannot be added, a member that disagrees is
 * named in an alert, and the button stays disabled until the combination is valid. The server checks
 * the same rule again and its typed refusal is worded by `groupFailure`.
 *
 * The first member chosen into an empty form fills the three shared fields from its revision, so
 * the common case is one click. A connection's readiness (a finished `ok` probe on the current key)
 * is shown and does not block: a group may be saved ahead of the probe that makes a member eligible,
 * and the group's capacity view says who would be chosen now.
 *
 * One idempotency key per intent. The signature carries the group (or «new») and the whole request,
 * so an unchanged repeat after an unknown outcome is the same command, and an edit is another one.
 */

import { useId, useState } from 'react';

import type { ExecutorBilling, ExecutorConnectionId, ExecutorGroup, ExecutorPinnedModel } from '@/shared/api';
import { EXECUTOR_BILLING_VALUES } from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import { BILLING_LABELS, KIND_LABELS } from '@/entities/executor-connection';
import type { GroupDraft, MemberCandidate } from '@/entities/executor-group';
import {
  GROUP_MEMBERS_MAX,
  GROUP_NAME_MAX_LENGTH,
  MEMBER_PROBLEM_SENTENCES,
  STRATEGY_SENTENCE,
  createGroupBody,
  draftFromRevision,
  groupDraftProblem,
  groupFailure,
  memberProblem,
  memberRevisionIsStale,
  reviseGroupBody,
} from '@/entities/executor-group';
import { useCommandKey } from '@/features/manage-executor-connection';
import { LoadingState } from '@/shared/ui';

import { useCreateExecutorGroup, useReviseExecutorGroup } from '../model/use-manage-executor-group';
import { GroupCommandFailure } from './group-command-failure';
import styles from './group-form.module.css';

export interface GroupFormProps {
  /** The group to revise; absent for a new one. */
  readonly group?: ExecutorGroup | undefined;
  /** Every connection, each with its current revision, as `memberCandidates` read them. */
  readonly candidates: readonly MemberCandidate[];
  /** The models of the provider lock a group may pin. */
  readonly pinnedModels: readonly ExecutorPinnedModel[];
  /** Called after the server accepted the command, so the screen can close the form. */
  readonly onSaved?: (() => void) | undefined;
}

const BILLING_SHORT: Readonly<Record<ExecutorBilling, string>> = {
  metered: 'тарифицируется',
  not_metered: 'не тарифицируется',
};

/** The first selected member that disagrees with the group, in words, or `null`. */
function selectedMemberAlert(
  memberIds: readonly ExecutorConnectionId[],
  candidates: readonly MemberCandidate[],
  settings: GroupDraft['settings'],
): string | null {
  for (const id of memberIds) {
    const candidate = candidates.find((one) => one.connectionId === id);
    if (candidate === undefined) continue;
    const found = memberProblem(candidate, settings);
    if (found !== null) return `Подключение «${candidate.name}»: ${MEMBER_PROBLEM_SENTENCES[found]}.`;
  }
  return null;
}

const EMPTY_DRAFT: GroupDraft = { name: '', settings: { pinId: '', gatewayModel: '', billing: '' }, memberIds: [] };

export function GroupForm({ group, candidates, pinnedModels, onSaved }: GroupFormProps) {
  const initial = group === undefined ? EMPTY_DRAFT : draftFromRevision(group.display_name, group.current_revision);
  const [name, setName] = useState(initial.name);
  const [pinId, setPinId] = useState(initial.settings.pinId);
  const [gatewayModel, setGatewayModel] = useState(initial.settings.gatewayModel);
  const [billing, setBilling] = useState<ExecutorBilling | ''>(initial.settings.billing);
  const [memberIds, setMemberIds] = useState<readonly ExecutorConnectionId[]>(initial.memberIds);
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const create = useCreateExecutorGroup();
  const revise = useReviseExecutorGroup();
  const keys = useCommandKey();
  const nameId = useId();
  const pinFieldId = useId();
  const gatewayId = useId();
  const billingId = useId();
  const membersId = useId();
  const pending = create.isPending || revise.isPending;
  const revising = group !== undefined;

  const draft: GroupDraft = { name, settings: { pinId, gatewayModel, billing }, memberIds };
  const problem = groupDraftProblem(draft, candidates, !revising);
  const offered = candidates.filter((one) => !one.archived || memberIds.includes(one.connectionId));
  const stale = new Set(
    (group?.current_revision.members ?? [])
      .filter((member) => memberRevisionIsStale(member, candidates))
      .map((member) => member.connection_id),
  );
  // A selected member that disagrees with the group is an alert; what is merely missing is a hint.
  const memberAlert = selectedMemberAlert(memberIds, candidates, draft.settings);
  const knownPin = pinId === '' || pinnedModels.some((one) => one.pin_id === pinId);

  function touched() {
    setFailure(null);
    setSaved(null);
  }

  function toggle(candidate: MemberCandidate, checked: boolean) {
    touched();
    if (!checked) {
      setMemberIds(memberIds.filter((id) => id !== candidate.connectionId));
      return;
    }
    // The first member chosen into an empty form names the group's model, name on the gateway and billing.
    if (
      memberIds.length === 0 && pinId === '' && gatewayModel.trim() === '' && billing === ''
      && candidate.pinId !== null && candidate.gatewayModel !== null && candidate.billing !== null
    ) {
      setPinId(candidate.pinId);
      setGatewayModel(candidate.gatewayModel);
      setBilling(candidate.billing);
    }
    setMemberIds([...memberIds, candidate.connectionId]);
  }

  async function submit() {
    if (problem !== null || pending) return;
    setFailure(null);
    setSaved(null);
    try {
      if (group === undefined) {
        const body = createGroupBody(draft, candidates);
        if (body === null) return;
        await create.mutateAsync({ body, idempotencyKey: keys.keyFor(JSON.stringify(['new', body])) });
        keys.release();
        setSaved(`Группа «${body.display_name}» создана.`);
        setName('');
        setPinId('');
        setGatewayModel('');
        setBilling('');
        setMemberIds([]);
      } else {
        const body = reviseGroupBody(draft, candidates, group.current_revision.members);
        if (body === null) return;
        await revise.mutateAsync({
          groupId: group.group_id, body, idempotencyKey: keys.keyFor(JSON.stringify([group.group_id, body])),
        });
        keys.release();
        setSaved(
          `Новая версия группы «${group.display_name}» сохранена. Работа, принятая на прежнюю версию, дойдёт до конца на ней. Правила остаются на прежней версии, пока вы не назначите новую на вкладке «Правила».`,
        );
      }
      onSaved?.();
    } catch (error) {
      const failed = groupFailure(error, true);
      if (failed.kind !== 'unknown_outcome') keys.release();
      setFailure(failed);
    }
  }

  return (
    <form
      className="am-form am-form--two"
      data-group-form={revising ? 'revise' : 'create'}
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      {group !== undefined ? (
        <p className="am-form__hint">
          Название группы «{group.display_name}» не меняется. Новая версия повторяет состав и модель, которые вы зададите ниже.
        </p>
      ) : (
        <div className="am-form__field">
          <label htmlFor={nameId}>Название группы</label>
          <input
            id={nameId}
            type="text"
            maxLength={GROUP_NAME_MAX_LENGTH}
            value={name}
            disabled={pending}
            autoComplete="off"
            onChange={(event) => {
              touched();
              setName(event.target.value);
            }}
          />
          <p className="am-form__hint">
            До {GROUP_NAME_MAX_LENGTH} знаков. Названия действующих групп не повторяются, а после создания название не меняется.
          </p>
        </div>
      )}

      <div className="am-form__field">
        <label htmlFor={pinFieldId}>Модель группы</label>
        <select
          id={pinFieldId}
          value={pinId}
          disabled={pending}
          onChange={(event) => {
            touched();
            setPinId(event.target.value);
          }}
        >
          <option value="">Выберите модель</option>
          {knownPin ? null : <option value={pinId}>{pinId}</option>}
          {pinnedModels.map((model) => (
            <option key={model.pin_id} value={model.pin_id}>{model.pin_id}</option>
          ))}
        </select>
        {pinnedModels.length === 0 ? (
          <p className="am-form__hint" role="status">
            Закреплённых моделей нет: модель выбирается из замка провайдера, который читает список подключений.
          </p>
        ) : null}
      </div>

      <div className="am-form__field">
        <label htmlFor={gatewayId}>Имя модели на шлюзе</label>
        <input
          id={gatewayId}
          type="text"
          value={gatewayModel}
          disabled={pending}
          autoComplete="off"
          onChange={(event) => {
            touched();
            setGatewayModel(event.target.value);
          }}
        />
        <p className="am-form__hint">Оно должно совпадать у всех подключений группы буква в букву.</p>
      </div>

      <div className="am-form__field">
        <label htmlFor={billingId}>Тарификация группы</label>
        <select
          id={billingId}
          value={billing}
          disabled={pending}
          onChange={(event) => {
            touched();
            setBilling(event.target.value === '' ? '' : (event.target.value as ExecutorBilling));
          }}
        >
          <option value="">Выберите тарификацию</option>
          {EXECUTOR_BILLING_VALUES.map((value) => (
            <option key={value} value={value}>{BILLING_LABELS[value]}</option>
          ))}
        </select>
        <p className="am-form__hint">Смешанные группы не принимаются: тарификация и тарифы у всех подключений одни.</p>
      </div>

      <div className={styles.members} role="group" aria-labelledby={membersId} data-group-members>
        <p id={membersId} className={styles.membersLabel}>Состав группы</p>
        {offered.length === 0 ? (
          <p className="am-form__hint" role="status" data-group-members-empty>
            Подключений для состава пока нет: сначала добавьте подключение на вкладке «Подключения».
          </p>
        ) : (
          <ul className={styles.memberList}>
            {offered.map((candidate) => {
              const checked = memberIds.includes(candidate.connectionId);
              const flag = memberProblem(candidate, draft.settings);
              const full = !checked && memberIds.length >= GROUP_MEMBERS_MAX;
              return (
                <li key={candidate.connectionId} className={styles.member} data-group-member={candidate.connectionId}>
                  <label className={styles.memberHead}>
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={pending || full || (!checked && flag !== null)}
                      onChange={(event) => toggle(candidate, event.target.checked)}
                    />
                    {candidate.name}
                  </label>
                  <span className="am-form__hint">
                    {KIND_LABELS[candidate.kind]}
                    {candidate.pinId === null || candidate.gatewayModel === null || candidate.billing === null
                      ? ' · настройки не заданы или не прочитаны'
                      : ` · модель «${candidate.pinId}», имя на шлюзе «${candidate.gatewayModel}», ${BILLING_SHORT[candidate.billing]}`}
                    {` · одновременных прогонов: ${candidate.capacity}`}
                  </span>
                  {flag === null ? null : (
                    <span className="am-form__hint" data-group-member-flag={flag}>
                      Не подходит группе: {MEMBER_PROBLEM_SENTENCES[flag]}.
                    </span>
                  )}
                  {stale.has(candidate.connectionId) ? (
                    <span className="am-form__hint" data-group-member-stale>
                      Группа помнит прежнюю версию настроек подключения; новая версия группы возьмёт текущую.
                    </span>
                  ) : null}
                  {candidate.readiness === null ? null : (
                    <span className="am-form__hint" data-group-member-readiness>
                      Сейчас не готово к работе: {candidate.readiness}.
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        )}
        <p className="am-form__hint">{STRATEGY_SENTENCE}</p>
      </div>

      {memberAlert === null ? null : (
        <p className="am-form__problem" role="alert" data-group-problem>{memberAlert}</p>
      )}
      {problem !== null && memberAlert === null ? (
        <p className="am-form__hint" role="status" data-group-incomplete>{problem}</p>
      ) : null}

      <div className="am-form__row">
        {/* The click is the submission (and the Enter key in a field clicks this button): it is not sent twice. */}
        <button
          className="am-button"
          type="submit"
          disabled={pending || problem !== null}
          onClick={(event) => {
            event.preventDefault();
            void submit();
          }}
        >
          {revising ? 'Сохранить новую версию' : 'Создать группу'}
        </button>
      </div>
      {pending ? <LoadingState what="сохранение группы" /> : null}
      {saved !== null ? <p className="am-note" role="status" data-group-saved>{saved}</p> : null}
      {failure !== null ? <GroupCommandFailure failure={failure} /> : null}
    </form>
  );
}
