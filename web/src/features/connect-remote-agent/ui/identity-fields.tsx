'use client';

/**
 * The three fields every connection the wizard creates starts from (`EXEC2-WEB-WIZARD-01`): a name,
 * a pinned model, and the name that model answers under. The agent screen and the OpenRouter screen
 * share them, and only their labels differ.
 *
 * The model is a select over the pinned set the list answered with, for the reason `SettingsFields`
 * gives: a revision that names an unpinned model is refused by the server (`model_not_pinned`). The
 * gateway name follows the pin until the person has written their own. Nothing here is a secret;
 * the fields are read out of the posted form by `readIdentity`.
 */

import { useState } from 'react';

import type { ExecutorPinnedModel } from '@/shared/api';
import { FIELD_NAMES } from '@/features/manage-executor-connection';

import type { AgentIdentity } from '../model/agent-settings';

export interface IdentityFieldsProps {
  readonly pinnedModels: readonly ExecutorPinnedModel[];
  /** Distinguishes the ids of two forms on one page. */
  readonly idPrefix: string;
  readonly nameLabel: string;
  readonly modelLabel: string;
  readonly gatewayLabel: string;
  readonly gatewayHint: string;
  /** What the form starts from: a name already typed, a model already chosen. */
  readonly initial?: AgentIdentity | undefined;
  readonly defaultName?: string | undefined;
}

export function IdentityFields({
  pinnedModels, idPrefix, nameLabel, modelLabel, gatewayLabel, gatewayHint, initial, defaultName,
}: IdentityFieldsProps) {
  const firstPin = pinnedModels[0]?.pin_id ?? '';
  const [pinId, setPinId] = useState(initial?.pinId ?? firstPin);
  const [gatewayModel, setGatewayModel] = useState(initial?.gatewayModel ?? firstPin);
  const id = (name: string): string => `${idPrefix}-${name}`;
  const pinned = pinnedModels.find((model) => model.pin_id === pinId);

  function choosePin(next: string) {
    if (gatewayModel === '' || gatewayModel === pinId) setGatewayModel(next);
    setPinId(next);
  }

  return (
    <>
      <div className="am-form__field">
        <label htmlFor={id('name')}>{nameLabel}</label>
        <input
          id={id('name')}
          name={FIELD_NAMES.displayName}
          type="text"
          required
          maxLength={120}
          autoComplete="off"
          defaultValue={initial?.displayName ?? defaultName ?? ''}
        />
      </div>
      <div className="am-form__field">
        <label htmlFor={id('pin')}>{modelLabel}</label>
        <select id={id('pin')} name={FIELD_NAMES.pinId} value={pinId} required onChange={(event) => choosePin(event.target.value)}>
          {pinnedModels.map((model) => (
            <option key={model.pin_id} value={model.pin_id}>{model.pin_id}</option>
          ))}
        </select>
        {pinned === undefined ? null : (
          <p className="am-form__hint">
            Закреплённые тарифы: вход {pinned.input_per_mtok_usd} $, выход {pinned.output_per_mtok_usd} $ за миллион токенов.
          </p>
        )}
      </div>
      <div className="am-form__field">
        <label htmlFor={id('gateway')}>{gatewayLabel}</label>
        <input
          id={id('gateway')}
          name={FIELD_NAMES.gatewayModel}
          type="text"
          required
          maxLength={200}
          autoComplete="off"
          spellCheck={false}
          value={gatewayModel}
          onChange={(event) => setGatewayModel(event.target.value)}
        />
        <p className="am-form__hint">{gatewayHint}</p>
      </div>
    </>
  );
}
