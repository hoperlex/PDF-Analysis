import { readFileSync } from 'node:fs';

import { describe, expect, it } from 'vitest';

import { MENU_GROUP_LABELS } from '@/_app/navigation';
import { SCREEN_REGISTRY } from '@/shared/config/screen-registry';

type Note = { version: string; items: { screen: string; where: string }[] };

const version = readFileSync(new URL('../../../../VERSION', import.meta.url), 'utf8').trim();
const readNote = (name: string): Note =>
  JSON.parse(readFileSync(new URL(`../../../../release-notes/${name}.json`, import.meta.url), 'utf8')) as Note;

function currentScreenFailures(note: Note): string[] {
  // Archived paths are historical display data. Only VERSION binds to today's registry.
  if (note.version !== version) return [];
  return note.items.flatMap((item) => {
    const screen = SCREEN_REGISTRY.find((row) => row.address === item.screen);
    if (!screen) return [`unknown screen: ${item.screen}`];
    const group = screen.group in MENU_GROUP_LABELS
      ? MENU_GROUP_LABELS[screen.group as keyof typeof MENU_GROUP_LABELS]
      : null;
    const prefix = group === null ? screen.label : `${group} › ${screen.label}`;
    return item.where === prefix || item.where.startsWith(`${prefix} › `)
      ? []
      : [`wrong display path: ${item.where}`];
  });
}

describe('authored release screen paths', () => {
  it('binds the current note to registry addresses and labels', () => {
    expect(readNote(version).version).toBe(version);
    expect(currentScreenFailures(readNote(version))).toEqual([]);
  });

  it('fails a missing current screen and a stale current display path', () => {
    const missing = readNote(version);
    missing.items[0] = { screen: '/removed', where: 'Главная' };
    expect(currentScreenFailures(missing)).toEqual(['unknown screen: /removed']);
    const stale = readNote(version);
    stale.items[0] = { screen: '/projects', where: 'Старая группа › Проекты' };
    expect(currentScreenFailures(stale)).toEqual(['wrong display path: Старая группа › Проекты']);
  });

  it('does not revalidate an archived address when navigation changes', () => {
    const history = readNote('0.2.0');
    history.items[0] = { screen: '/retired-after-release', where: 'Старое меню › Архив' };
    expect(currentScreenFailures(history)).toEqual([]);
  });
});
