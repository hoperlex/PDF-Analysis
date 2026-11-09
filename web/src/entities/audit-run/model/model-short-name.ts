/**
 * A model's short name for the rail and the live line (`RUN-SCREEN-01a`): «Opus 5.5», «Sonnet 5», «GPT 6 sol».
 *
 * The input is a pin id (`RunExecutor.pin_id`, the key of the provider lock: `claude-opus-5-5`, `gpt-6-sol`). The name is for the
 * reader's eye only; it is never an identity, and the full pin id is what the dialog prints and what a tooltip carries. A pin id
 * this function does not recognise is returned as it is, trimmed: a screen that cannot shorten a name does not invent one.
 */

const isVersionPart = (part: string): boolean => /^\d+(?:\.\d+)*$/.test(part);

/** Digits joined by dots: `5`, `5-5` becomes `5.5`; a part that is not a version ends the run of digits. */
function versionAndRest(parts: readonly string[]): string {
  const version: string[] = [];
  let at = 0;
  while (at < parts.length && isVersionPart(parts[at] as string)) {
    version.push(parts[at] as string);
    at += 1;
  }
  const rest = parts.slice(at);
  return [version.join('.'), ...rest].filter((part) => part !== '').join(' ');
}

export function shortModelName(pinId: string | null | undefined): string | null {
  const id = typeof pinId === 'string' ? pinId.trim() : '';
  if (id === '') return null;
  const parts = id.split('-');
  const [head, family, ...tail] = parts;
  if (head === 'claude' && family !== undefined && !isVersionPart(family)) {
    return `${family.charAt(0).toUpperCase()}${family.slice(1)} ${versionAndRest(tail)}`.trim();
  }
  if (head === 'gpt' && family !== undefined) return `GPT ${versionAndRest([family, ...tail])}`.trim();
  return id;
}
