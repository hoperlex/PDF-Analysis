/**
 * The two pairs of equal choices of the wizard (`EXEC2-WEB-WIZARD-01`).
 *
 * **Equal means the same markup.** Neither card is the primary one: both are the same panel with the
 * same button, in the same size and rank, so the order on the screen is the only difference between
 * them. The first pair asks what is being connected (a remote agent or an API provider); the second
 * asks how the agent is installed (over SSH from the stand, or by one command the person runs). Each
 * is a view driven by props: it holds no state and sends nothing.
 */

import {
  KIND_CHOICES,
  KIND_CHOICE_TITLE,
  MANUAL_LABEL,
  PATH_CHOICES,
  PATH_CHOICE_TITLE,
} from '../model/words';
import styles from './connect-remote-agent.module.css';

export type KindChoice = 'agent' | 'api';
export type PathChoice = 'ssh' | 'command';

interface ChoiceCardProps {
  /** Machine names for a test: the kind on `data-wizard-kind`, the path on `data-agent-path`. */
  readonly kind?: string | undefined;
  readonly path?: string | undefined;
  readonly title: string;
  readonly text: string;
  readonly action: string;
  readonly onChoose: () => void;
}

function ChoiceCard({ kind, path, title, text, action, onChoose }: ChoiceCardProps) {
  return (
    <div className={`am-note ${styles.choice}`} data-wizard-kind={kind} data-agent-path={path}>
      <strong>{title}</strong>
      <p>{text}</p>
      <button className="am-button" type="button" onClick={onChoose}>{action}</button>
    </div>
  );
}

export interface KindChoiceViewProps {
  readonly onChoose: (choice: KindChoice) => void;
  /** Opens the old form with every field, for the kinds the two cards do not cover. */
  readonly onManual: () => void;
}

export function KindChoiceView({ onChoose, onManual }: KindChoiceViewProps) {
  return (
    <section className={styles.group} aria-label={KIND_CHOICE_TITLE} data-wizard-step="kind">
      <h3>{KIND_CHOICE_TITLE}</h3>
      <div className={styles.choices}>
        {(['agent', 'api'] as const).map((kind) => (
          <ChoiceCard
            key={kind}
            kind={kind}
            title={KIND_CHOICES[kind].title}
            text={KIND_CHOICES[kind].text}
            action={KIND_CHOICES[kind].action}
            onChoose={() => onChoose(kind)}
          />
        ))}
      </div>
      <p>
        <button className="am-button am-button--quiet am-button--small" type="button" data-wizard-manual onClick={onManual}>
          {MANUAL_LABEL}
        </button>
      </p>
    </section>
  );
}

export interface PathChoiceViewProps {
  readonly onChoose: (choice: PathChoice) => void;
}

export function PathChoiceView({ onChoose }: PathChoiceViewProps) {
  return (
    <section className={styles.group} aria-label={PATH_CHOICE_TITLE} data-wizard-step="path">
      <h3>{PATH_CHOICE_TITLE}</h3>
      <div className={styles.choices}>
        {(['ssh', 'command'] as const).map((path) => (
          <ChoiceCard
            key={path}
            path={path}
            title={PATH_CHOICES[path].title}
            text={PATH_CHOICES[path].text}
            action={PATH_CHOICES[path].action}
            onChoose={() => onChoose(path)}
          />
        ))}
      </div>
    </section>
  );
}
