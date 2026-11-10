/**
 * How a model is named on a screen (`HOSTS-WEB-01`, plan 2026-11-09 §7.2): without the provider prefix.
 *
 * The catalogue spells a model by its pin (`claude-opus-5-5`, `gpt-6.1-sol`). A server row reads
 * «Opus 5.5 · Sonnet 5.5 · gpt-6-sol»: the Claude pins lose `claude-` and the dash between the major and the minor
 * number, the Codex pins are already short and stay as they are. A pin this function does not know is shown as it is,
 * never guessed at.
 */

const CLAUDE_PIN = /^claude-(opus|sonnet|haiku)-(\d+)(?:-(\d+))?$/;

export function modelLabel(modelId: string): string {
  const match = CLAUDE_PIN.exec(modelId);
  if (match === null) return modelId;
  const family = match[1] as string;
  const version = match[3] === undefined ? (match[2] as string) : `${match[2] as string}.${match[3]}`;
  return `${family.slice(0, 1).toUpperCase()}${family.slice(1)} ${version}`;
}

/** The names of several models, once each, in the order they come, joined as a row reads them. */
export function modelLabels(modelIds: readonly string[]): string {
  return [...new Set(modelIds)].map(modelLabel).join(' · ');
}
