'use client';

/**
 * A read-only box with a «Скопировать» button (`EXEC2-WEB-WIZARD-01`).
 *
 * Used for the install command, the `authorized_keys` line and the official login commands. The
 * value is selectable in the box, so a browser that refuses the clipboard still leaves the person a
 * way to copy it. A command is shown in a box and never composed into a sentence, so the sentence
 * stays Russian and the command stays exactly what its owner documents.
 *
 * `line` is one line in an input (a short command); `block` is a wrapping text area (the install
 * command, which carries a download address and a checksum). The box holds nothing but the value it
 * is given: no storage, no log, no copy kept after the component unmounts.
 */

import { useState } from 'react';

import { COPIED_LABEL, COPY_LABEL } from '../model/words';
import styles from './connect-remote-agent.module.css';

export interface CopyBoxProps {
  readonly value: string;
  /** Names the box for assistive technology and for a test. */
  readonly label: string;
  readonly variant: 'line' | 'block';
  /** A machine name on `data-agent-copy`, so a test can find this box among others. */
  readonly name: string;
}

export function CopyBox({ value, label, variant, name }: CopyBoxProps) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
    } catch {
      // No clipboard permission: the text stays selectable in the box.
      setCopied(false);
    }
  }

  return (
    <div className="am-form__field">
      {variant === 'line' ? (
        <input
          className={styles.copy}
          type="text"
          readOnly
          value={value}
          spellCheck={false}
          aria-label={label}
          data-agent-copy={name}
          onFocus={(event) => event.currentTarget.select()}
        />
      ) : (
        <textarea
          className={styles.copy}
          readOnly
          rows={4}
          value={value}
          spellCheck={false}
          aria-label={label}
          data-agent-copy={name}
          onFocus={(event) => event.currentTarget.select()}
        />
      )}
      <div className="am-form__row">
        <button
          className="am-button am-button--quiet am-button--small"
          type="button"
          data-agent-copy-button={name}
          onClick={() => void copy()}
        >
          {COPY_LABEL}
        </button>
        {copied ? <span role="status" className="am-form__hint">{COPIED_LABEL}</span> : null}
      </div>
    </div>
  );
}
