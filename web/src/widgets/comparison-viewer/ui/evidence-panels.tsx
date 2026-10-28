/**
 * The evidence beside the sheet (`CMP-VIEWER-01`): the channel strip, the text changes, the service zones and «Как
 * сравнивалось». All of it is the engine's raw deterministic evidence, shown as it is (an AI layer never rewrites it).
 */

import { Fragment } from 'react';

import type {
  ComparisonChannels,
  ComparisonHowCompared,
  ComparisonServiceNote,
  ComparisonTextChange,
} from '@/shared/api';

import {
  CHANNEL_LABELS,
  CHANNEL_ORDER,
  TEXT_KIND_LABELS,
  UNKNOWN_TEXT_KIND_LABEL,
  WARNING_NOTE,
  noteTitle,
} from '../model/labels';
import { afterValues, beforeValues, markNumbers } from '../model/text-marks';
import type { TextPart } from '../model/text-marks';

import { BeforeAfter } from './before-after';
import styles from './comparison-viewer.module.css';

/**
 * The reasons that force «Нужна проверка» (`status.py` of the original, listed in its inventory §4.1), in words. A
 * reason this table does not know is shown with its code in brackets and the sentence «причина без описания», so that
 * nothing is hidden and nothing is invented; `CMP-VC-UI-01` owns the full list of sentences.
 */
export const REASON_WORDS: Readonly<Record<string, string>> = {
  MATCH_LOW_CONFIDENCE: 'листы сопоставлены с низкой уверенностью',
  MATCH_AMBIGUOUS: 'сопоставление неоднозначно',
  ALIGNMENT_UNRELIABLE: 'совмещение листов ненадёжно',
  DUPLICATE_SHEET: 'лист повторяется в комплекте',
  RENDER_FAILED: 'лист не удалось отрисовать',
  NO_TEXT_LAYER: 'нет текстового слоя',
  STAMP_NOT_RECOGNIZED: 'штамп не распознан',
  SPEC_NOT_PARSED: 'спецификация не разобрана',
};

export function reasonWords(code: string): string {
  return REASON_WORDS[code] ?? `причина без описания (${code})`;
}

export interface ChannelStripProps {
  readonly channels: ComparisonChannels | undefined;
  readonly reasons: readonly string[];
}

/** «Проверено: … / Не проверено: …» and «причины: …» (`version-comparison-viewer.js:62-73`). */
export function ChannelStrip({ channels, reasons }: ChannelStripProps) {
  const known = CHANNEL_ORDER.flatMap((name) => {
    const channel = channels?.[name as keyof ComparisonChannels];
    return channel === undefined ? [] : [{ name, channel }];
  });
  const checked = known.filter(({ channel }) => channel.state === 'checked');
  const unchecked = known.filter(({ channel }) => channel.state === 'unchecked');
  return (
    <section className={styles.panel} aria-label="Что проверено" data-channel-strip="">
      {known.length === 0 ? (
        <p className={styles.empty}>Каналы сравнения неизвестны: результата у листа ещё нет.</p>
      ) : (
        <>
          <p className={styles.channelLine}>
            <span className={styles.channelLabel}>Проверено:</span>{' '}
            {checked.length === 0
              ? 'ничего'
              : checked.map(({ name, channel }) => `${CHANNEL_LABELS[name]} (${channel.diffs ?? 0})`).join(', ')}
          </p>
          <p className={`${styles.channelLine} ${unchecked.length === 0 ? '' : styles.channelUnchecked}`.trim()}>
            <span className={styles.channelLabel}>Не проверено:</span>{' '}
            {unchecked.length === 0
              ? 'всё применимое проверено'
              : unchecked
                  .map(({ name, channel }) => `${CHANNEL_LABELS[name]}${channel.reason === undefined ? '' : ` — ${channel.reason}`}`)
                  .join('; ')}
          </p>
        </>
      )}
      {reasons.length === 0 ? null : (
        <p className={styles.reasons}>причины: {reasons.map(reasonWords).join('; ')}</p>
      )}
    </section>
  );
}

function Marked({ parts }: { readonly parts: readonly TextPart[] }) {
  return (
    <>
      {parts.map((part, index) =>
        part.marked ? (
          <mark key={index} className={styles.mark}>
            {part.text}
          </mark>
        ) : (
          <span key={index}>{part.text}</span>
        ),
      )}
    </>
  );
}

export interface TextChangesProps {
  readonly changes: readonly ComparisonTextChange[];
  /** A change with a place on the sheet can be shown there. */
  readonly onFocus?: (change: ComparisonTextChange) => void;
}

/** «Текст: N изменений» with «было → стало» and the numbers that changed marked. */
export function TextChanges({ changes, onFocus }: TextChangesProps) {
  return (
    <section className={styles.panel} aria-label="Изменения текста" data-text-changes={changes.length}>
      <h3 className={styles.panelTitle}>Текст: {changes.length} {changeWord(changes.length)}</h3>
      {changes.length === 0 ? (
        <p className={styles.empty}>Изменений текста нет.</p>
      ) : (
        <ul className={styles.list}>
          {changes.map((change, index) => (
            <li key={index}>
              <button
                type="button"
                className={styles.item}
                disabled={change.box === undefined || onFocus === undefined}
                onClick={() => onFocus?.(change)}
              >
                <span className={styles.itemClass}>{TEXT_KIND_LABELS[change.kind] ?? UNKNOWN_TEXT_KIND_LABEL}</span>
                <BeforeAfter
                  before={change.before === undefined ? undefined : <Marked parts={markNumbers(change.before, beforeValues(change.numbers))} />}
                  after={change.after === undefined ? undefined : <Marked parts={markNumbers(change.after, afterValues(change.numbers))} />}
                />
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function changeWord(count: number): string {
  const last = count % 10;
  const tens = count % 100;
  if (last === 1 && tens !== 11) return 'изменение';
  if (last >= 2 && last <= 4 && (tens < 12 || tens > 14)) return 'изменения';
  return 'изменений';
}

export interface ServiceNotesProps {
  readonly notes: readonly ComparisonServiceNote[];
}

/** «Служебные зоны и пометки» and the sentence that the disappearance of a warning confirms nothing. */
export function ServiceNotes({ notes }: ServiceNotesProps) {
  const hasWarning = notes.some((note) => note.kind === 'warning');
  return (
    <section className={styles.panel} aria-label="Служебные зоны и пометки" data-service-notes={notes.length}>
      <h3 className={styles.panelTitle}>Служебные зоны и пометки: {notes.length}</h3>
      {hasWarning ? <p className={styles.noteStrong}>{WARNING_NOTE}</p> : null}
      {notes.length === 0 ? (
        <p className={styles.empty}>Изменений в служебных зонах нет.</p>
      ) : (
        <ul className={styles.list}>
          {notes.map((note, index) => (
            <li key={index} className={styles.item}>
              <span className={styles.itemClass}>
                {noteTitle(note.kind, note.change)}
                {note.zone === undefined ? '' : `, зона «${note.zone}»`}
                {note.field === undefined ? '' : `, поле «${note.field}»`}
              </span>
              <BeforeAfter before={note.before} after={note.after} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export interface HowComparedProps {
  readonly how: ComparisonHowCompared | undefined;
}

/** «Как сравнивалось»: the transform of B onto A, the resolution, the tolerance and what was set aside. */
export function HowCompared({ how }: HowComparedProps) {
  const rows: [string, string][] = how === undefined ? [] : [
    ['Алгоритм', how.algo_version],
    ['Разрешение', `${how.dpi} точек на дюйм`],
    ['Допуск', `${how.tolerance_pt} пт`],
    ...(how.transform === undefined ? [] : [['Совмещение B на A', how.transform.map((n) => String(Math.round(n * 1000) / 1000)).join(', ')] as [string, string]]),
    ...(how.within_tolerance_count === undefined ? [] : [['В пределах допуска', String(how.within_tolerance_count)] as [string, string]]),
    ...(how.noise_count === undefined ? [] : [['Шум', String(how.noise_count)] as [string, string]]),
    ...(how.separated_objects === undefined ? [] : [['Отделённых объектов', String(how.separated_objects)] as [string, string]]),
    ...(how.aligned_blocks === undefined ? [] : [['Совмещённых блоков', String(how.aligned_blocks)] as [string, string]]),
  ];
  return (
    <section className={styles.panel} aria-label="Как сравнивалось" data-how-compared="">
      <h3 className={styles.panelTitle}>Как сравнивалось</h3>
      {rows.length === 0 ? (
        <p className={styles.empty}>Сведений о сравнении нет.</p>
      ) : (
        <dl className={styles.facts2}>
          {rows.map(([term, value]) => (
            <Fragment key={term}>
              <dt className={styles.term}>{term}</dt>
              <dd className={styles.value}>{value}</dd>
            </Fragment>
          ))}
        </dl>
      )}
    </section>
  );
}
