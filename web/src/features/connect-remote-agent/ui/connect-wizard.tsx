'use client';

/**
 * «Добавить подключение» (`EXEC2-WEB-WIZARD-01`): what the administrator is connecting, and then the
 * screen for it.
 *
 *     вид подключения ── удалённый Ubuntu-агент ── название и модель ── способ установки ── A или B
 *                    ├─ API-провайдер ─────────── заготовка OpenRouter ── ключ ── проверка
 *                    └─ настроить вручную ─────── прежняя форма со всеми полями
 *
 * The wizard is a panel in «Подключения», not a fourth tab, and it is closed until the button is
 * pressed. The two main choices are equal; the manual form stays one quiet button below them, because
 * the older kinds (a command over SSH, a Claude Code session, any other gateway) are still created
 * there, and replacing the form would remove them.
 *
 * `ConnectWizardLauncher` is the button and the panel. It keeps the `data-executor-create` marker the
 * list has always carried for an administrator, and an expert sees nothing of it (the widget decides).
 */

import { useState } from 'react';

import type { ExecutorPinnedModel } from '@/shared/api';
import { CreateConnectionForm } from '@/features/manage-executor-connection';

import {
  MANUAL_LABEL,
  WIZARD_BACK_LABEL,
  WIZARD_CLOSE_LABEL,
  WIZARD_OPEN_LABEL,
} from '../model/words';
import { AgentSetup } from './agent-setup';
import { KindChoiceView } from './choices';
import type { KindChoice } from './choices';
import { OpenRouterSetup } from './openrouter-setup';
import styles from './connect-remote-agent.module.css';

type Screen = KindChoice | 'kind' | 'manual';

export interface ConnectWizardProps {
  readonly pinnedModels: readonly ExecutorPinnedModel[];
}

export function ConnectWizard({ pinnedModels }: ConnectWizardProps) {
  const [screen, setScreen] = useState<Screen>('kind');
  const back = () => setScreen('kind');
  return (
    <div className={styles.wizard} role="group" aria-label={WIZARD_OPEN_LABEL} data-connect-wizard={screen}>
      {screen === 'kind' ? (
        <KindChoiceView onChoose={(kind) => setScreen(kind)} onManual={() => setScreen('manual')} />
      ) : null}
      {screen === 'agent' ? <AgentSetup pinnedModels={pinnedModels} onBack={back} /> : null}
      {screen === 'api' ? <OpenRouterSetup pinnedModels={pinnedModels} onBack={back} /> : null}
      {screen === 'manual' ? (
        <section className={styles.group} aria-label={MANUAL_LABEL} data-wizard-step="manual">
          <CreateConnectionForm pinnedModels={pinnedModels} />
          <p>
            <button className="am-button am-button--quiet" type="button" onClick={back}>{WIZARD_BACK_LABEL}</button>
          </p>
        </section>
      ) : null}
    </div>
  );
}

export function ConnectWizardLauncher({ pinnedModels }: ConnectWizardProps) {
  const [open, setOpen] = useState(false);
  return (
    <section className="am-section" aria-label={WIZARD_OPEN_LABEL} data-executor-create>
      <button
        className="am-button"
        type="button"
        aria-expanded={open}
        data-connect-wizard-toggle
        onClick={() => setOpen((now) => !now)}
      >
        {open ? WIZARD_CLOSE_LABEL : WIZARD_OPEN_LABEL}
      </button>
      {open ? <ConnectWizard pinnedModels={pinnedModels} /> : null}
    </section>
  );
}
