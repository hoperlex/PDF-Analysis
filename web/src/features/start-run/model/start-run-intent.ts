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
 */

import type { ExecutorConnectionId, PresetId, StartRunRequest, VersionUid } from '@/shared/api';

export interface StartRunCommand {
  readonly versionUid: VersionUid;
  /** Minted once per intent by the caller and reused on every retry. */
  readonly idempotencyKey: string;
  /** The connection the person chose. Absent for «По умолчанию (маршрут)»; never `null`. */
  readonly executorConnectionId?: ExecutorConnectionId | undefined;
  /** The preset the person chose. Absent for «Без пресета»; never `null`; exclusive with the executor. */
  readonly presetId?: PresetId | undefined;
}

export interface StartRunIntent {
  /** What the idempotency key is minted for: the version, and the executor when one is chosen. */
  readonly signature: string;
  /** The command for a key the caller holds for `signature`. */
  readonly command: (idempotencyKey: string) => StartRunCommand;
}

/**
 * The intent of starting `versionUid` with the chosen preset, or on the chosen executor, or on the
 * route's when neither is chosen. A preset wins: the control never offers both, and the request
 * never carries both.
 */
export function startRunIntent(
  versionUid: VersionUid,
  executorConnectionId: ExecutorConnectionId | null,
  presetId: PresetId | null = null,
): StartRunIntent {
  const signature =
    presetId !== null
      ? `start-run:${versionUid}:preset:${presetId}`
      : executorConnectionId === null
        ? `start-run:${versionUid}`
        : `start-run:${versionUid}:executor:${executorConnectionId}`;
  return {
    signature,
    command: (idempotencyKey) => ({
      versionUid,
      idempotencyKey,
      ...(presetId !== null
        ? { presetId }
        : executorConnectionId === null
          ? {}
          : { executorConnectionId }),
    }),
  };
}

/** The request body of a command: `preset_id` or `executor_connection_id`, only when one was chosen. */
export function startRunBody({ versionUid, executorConnectionId, presetId }: StartRunCommand): StartRunRequest {
  if (presetId !== undefined) return { version_uid: versionUid, preset_id: presetId };
  return executorConnectionId === undefined
    ? { version_uid: versionUid }
    : { version_uid: versionUid, executor_connection_id: executorConnectionId };
}

/** The empty option of the selector is the default; any other value is a connection's id. */
export function chosenExecutor(optionValue: string): ExecutorConnectionId | null {
  return optionValue === '' ? null : optionValue;
}
