/**
 * One start, as the request it sends and the intent its idempotency key belongs to
 * (`EXEC-PAR-WEB-01`).
 *
 * **The executor is part of the request, so it is part of the intent.** `executor_connection_id`
 * is in the payload the stand compares an idempotency key by: the same version on another
 * executor is another request, and sending it under the first one's key is
 * `idempotency_key_reuse`, which is terminal. So the signature the key is minted for carries the
 * choice, and the request is built from the same value as the signature — one function, one
 * argument — so the two cannot disagree about what was chosen.
 *
 * **«По умолчанию (маршрут)» is the absence of the field, never `null`.** The contract refuses
 * `null` (`422 validation_failed` on `executor_connection_id`), and an absent field is the start
 * that follows the stand's route exactly as it did before the choice existed. The signature of a
 * start without a choice is the one it always had, so an unchanged page keeps its key.
 *
 * **A preset is a second way to make the same choice** (`ANALYSIS-PRESETS-01`). The request then
 * carries `preset_id` and not the executor the preset names: the stand resolves the preset's current
 * version in the start's own transaction, and the same key with the executor chosen by hand is
 * another request. The signature carries the preset, so choosing another one is another intent.
 *
 * **A group is a third way, and the three are exclusive** (`EXEC2-WEB-GROUPS-01`, ADR-0026 decisions 12
 * to 14). `executor_group_id` names an executor group instead of a connection or a preset: the stand
 * admits the run on the group's current revision, and the connection is chosen when the work is sent.
 * It is exclusive with `executor_connection_id` and `preset_id` (`422 validation_failed`), so the
 * command and the body hold **at most one** of the three — a group beats a preset, which beats a
 * connection — and a caller that supplies two still sends one. The signature carries the group, so
 * choosing another group is another intent. «Автоматически (по типу задачи)» is the absence of all
 * three, as «По умолчанию (маршрут)» always was.
 *
 * **The one-button control sends none of the three** (`RUN-START-ONE-01a`, plan v3 §8): the request names no
 * executor, group or preset, and the server's automatic route applies. The selectors stay in the command and
 * the body because they are fields of the contract and of its idempotency payload, and a caller that sets
 * one still gets exactly one.
 *
 * The optional raised-limit choice is also part of the request and the intent. With the switch
 * off, both the signature and body keep their earlier shape for existing idempotency keys.
 * A cost-approved start additionally pins the estimate digest and exact approved ceiling.
 * Agreement gates submission; merely unchecking/rechecking an unchanged payload is still its retry.
 */

import type { ExecutorConnectionId, ExecutorGroupId, PresetId, StartRunRequest, VersionUid } from '@/shared/api';

export type RunCostConsent = NonNullable<StartRunRequest['cost_consent']>;

export interface StartRunCommand {
  readonly versionUid: VersionUid;
  /** Minted once per intent by the caller and reused on every retry. */
  readonly idempotencyKey: string;
  /** The connection the person chose. Absent for «По умолчанию (маршрут)»; never `null`. */
  readonly executorConnectionId?: ExecutorConnectionId | undefined;
  /** The preset the person chose. Absent for «Без пресета»; never `null`; exclusive with the executor. */
  readonly presetId?: PresetId | undefined;
  /** The person explicitly chose the temporary raised-limit policy. Absent for the standard policy. */
  readonly relaxedLimits?: true | undefined;
  readonly costConsent?: RunCostConsent | undefined;
  /** The executor group the person chose. Absent unless a group was chosen; never `null`; exclusive with the other two. */
  readonly executorGroupId?: ExecutorGroupId | undefined;
}

export interface StartRunIntent {
  /** What the idempotency key is minted for: the version, and the executor when one is chosen. */
  readonly signature: string;
  /** The command for a key the caller holds for `signature`. */
  readonly command: (idempotencyKey: string) => StartRunCommand;
}

/**
 * The intent of starting `versionUid` with the chosen group, or the chosen preset, or on the chosen
 * executor, or on the route's (or the rule's) when none is chosen. A group wins over a preset and a
 * preset over an executor: the control never offers more than one, and the request never carries more
 * than one.
 */
export function startRunIntent(
  versionUid: VersionUid,
  executorConnectionId: ExecutorConnectionId | null,
  presetId: PresetId | null = null,
  relaxedLimits = false,
  costConsent?: RunCostConsent,
  executorGroupId: ExecutorGroupId | null = null,
): StartRunIntent {
  const baseSignature =
    executorGroupId !== null
      ? `start-run:${versionUid}:group:${executorGroupId}`
      : presetId !== null
        ? `start-run:${versionUid}:preset:${presetId}`
        : executorConnectionId === null
          ? `start-run:${versionUid}`
          : `start-run:${versionUid}:executor:${executorConnectionId}`;
  const selectedSignature = relaxedLimits ? `${baseSignature}:relaxed-limits` : baseSignature;
  return {
    signature: costConsent === undefined ? selectedSignature
      : `${selectedSignature}:cost:${costConsent.estimate_digest}:${costConsent.ceiling_micros}:${costConsent.confirmed}`,
    command: (idempotencyKey) => ({
      versionUid,
      idempotencyKey,
      ...(relaxedLimits ? { relaxedLimits: true } : {}),
      ...(costConsent === undefined ? {} : { costConsent }),
      ...(executorGroupId !== null
        ? { executorGroupId }
        : presetId !== null
          ? { presetId }
          : executorConnectionId === null
            ? {}
            : { executorConnectionId }),
    }),
  };
}

/**
 * The request body of a command: `executor_group_id`, `preset_id` or `executor_connection_id`, only
 * when one was chosen, and **never more than one**. The first of the three that is present wins, in
 * the order group, preset, connection — the server refuses a body that carries two.
 */
export function startRunBody({
  versionUid, executorConnectionId, presetId, relaxedLimits, costConsent, executorGroupId,
}: StartRunCommand): StartRunRequest {
  return {
    version_uid: versionUid,
    ...(relaxedLimits ? { relaxed_limits: true } : {}),
    ...(costConsent === undefined ? {} : { cost_consent: costConsent }),
    ...(executorGroupId !== undefined
      ? { executor_group_id: executorGroupId }
      : presetId !== undefined
        ? { preset_id: presetId }
        : executorConnectionId === undefined
          ? {}
          : { executor_connection_id: executorConnectionId }),
  };
}
