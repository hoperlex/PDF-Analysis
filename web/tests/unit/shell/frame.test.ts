/**
 * The frame (`W50-SHELL-FRAME`): the guest state, the account menu, the addresses it links,
 * the footer, and the two layout states — on markup and on the CSS that lays them out.
 *
 * The keyboard, focus and outside-click behaviour of the menu and the disclosures are the
 * primitives' (`web/tests/unit/ui/**`) and are walked in a real browser on the lane stand
 * (`docs/program/W50-SHELL-FRAME.md`); this file holds what a static render can see.
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AppFrame, FRAME_FOOTER } from '@/_app';
import type { AppFrameSession } from '@/_app';
import { UNKNOWN_ROLE_LINE, accountMenuProps } from '@/_app/account-menu';
import styles from '@/_app/app-frame.module.css';
import { SESSION_CLOSE_PATH } from '@/features/sign-in';
import { SCREEN_REGISTRY } from '@/shared/config';

import {
  ADMIN_AND_EXPERT,
  ADMIN_ONLY,
  DEFAULT_CREDENTIAL,
  EXPERT,
  INCOMPLETE_PROFILE,
  LONGEST,
  LONGEST_LABEL,
  LONGEST_LOGIN,
  NO_ROLES,
  UNKNOWN_ROLE,
} from './subjects';

/** The frame rendered on its own: no query client, no router — so a hook that needed either throws. */
const frame = (session: AppFrameSession | null): string =>
  renderToStaticMarkup(createElement(AppFrame, { children: 'экран', session }));

/** Every `href` in the markup, in document order. */
const hrefs = (markup: string): string[] => [...markup.matchAll(/<a\b[^>]*\bhref="([^"]*)"/g)].map((m) => m[1] as string);

/** The declarations of one rule, read from the CSS file itself. */
function declarations(cssPath: string, selector: string): string {
  const css = readFileSync(fileURLToPath(new URL(cssPath, import.meta.url)), 'utf8');
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp(`(?:^|\\n)\\s*${escaped}\\s*\\{([^}]*)\\}`).exec(css)?.[1] ?? '';
}

const FRAME_CSS = '../../../src/_app/app-frame.module.css';
const GLOBALS = '../../../src/app/globals.css';

const ALL_SESSIONS = [EXPERT, ADMIN_AND_EXPERT, ADMIN_ONLY, NO_ROLES, UNKNOWN_ROLE, DEFAULT_CREDENTIAL, INCOMPLETE_PROFILE];

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('a guest', () => {
  it('sees the brand and one «Вход» link, and no navigation, menu or form', () => {
    const markup = frame(null);
    expect(hrefs(markup)).toEqual(['/', '/login']);
    expect(markup).toMatch(/<a class="am-app__signin" href="\/login">Вход<\/a>/);
    expect(markup).not.toContain('<nav');
    expect(markup).not.toContain('aria-haspopup');
    expect(markup).not.toContain('<form');
  });
});

describe('the account menu', () => {
  it('opens from a button holding the avatar, named by the account, never from a div', () => {
    const markup = frame(EXPERT);
    const trigger = /<button\b([^>]*\baria-haspopup="menu"[^>]*)>(.*?)<\/button>/.exec(markup);
    expect(trigger, 'no menu button').not.toBeNull();
    expect(trigger?.[1]).toContain('aria-label="Учётная запись: Экспертова А. С."');
    expect(trigger?.[2]).toMatch(/^<span class="am-avatar am-avatar--\d\d" data-avatar-pair="\d\d" aria-hidden="true">ЭА<\/span>$/);
    expect(markup).not.toMatch(/<div\b[^>]*aria-haspopup/);
  });

  it('colours the avatar by the e-mail: the same login keeps its colour under another name', () => {
    const pair = (session: AppFrameSession): string => /data-avatar-pair="(\d\d)"/.exec(frame(session))?.[1] ?? '';
    expect(pair({ ...EXPERT, displayLabel: 'Другая В. Г.', initials: 'ДВ' })).toBe(pair(EXPERT));
  });

  it('names the account, its e-mail and its roles in the header', () => {
    const markup = frame(ADMIN_AND_EXPERT);
    expect(markup).toContain(`<p class="${styles.accountName}" data-account-name="">Проверкина А. С.</p>`);
    expect(markup).toContain(`<p class="${styles.accountLogin}" data-account-login="">администратор@пример.испытание</p>`);
    expect(markup).toContain(`<p class="${styles.accountRoles}" data-account-roles="">Роли: Эксперт, Администратор.</p>`);
    expect(frame(EXPERT)).toContain('>Роли: Эксперт.</p>');
    expect(frame(ADMIN_ONLY)).toContain('>Роли: Администратор.</p>');
  });

  it('says an empty role set is empty, in the home page\'s words', () => {
    expect(frame(NO_ROLES)).toContain(`<p class="${styles.accountRoles}" data-account-roles="">Роли не назначены.</p>`);
  });

  it('shows a typed fault for a role value it cannot name, and names neither it nor a guess', () => {
    const markup = frame(UNKNOWN_ROLE);
    expect(markup).toContain(
      `<p class="${styles.accountRoles}" data-account-fault="closed-vocabulary">${UNKNOWN_ROLE_LINE}</p>`,
    );
    expect(markup).not.toContain('auditor');
    expect(markup).not.toContain('data-account-roles');
  });

  it('holds Профиль and Сменить пароль as links, and Выйти as a POST — never a link', () => {
    const markup = frame(EXPERT);
    expect(markup).toMatch(/<a class="am-menu__item" role="menuitem" tabindex="-1" href="\/account">Профиль<\/a>/);
    expect(markup).toMatch(
      /<a class="am-menu__item" role="menuitem" tabindex="-1" href="\/account\/password">Сменить пароль<\/a>/,
    );
    expect(markup).toContain(
      `<form class="am-menu__form" action="${SESSION_CLOSE_PATH}" method="post"><button type="submit" class="am-menu__item" role="menuitem" tabindex="-1">Выйти</button></form>`,
    );
    expect(markup).not.toMatch(/<a\b[^>]*>Выйти<\/a>/);
    expect(accountMenuProps(EXPERT).items.map((item) => item.kind)).toEqual(['link', 'link', 'submit']);
  });

  it('is there for a default credential and an incomplete profile, which see no navigation', () => {
    for (const session of [DEFAULT_CREDENTIAL, INCOMPLETE_PROFILE]) {
      const markup = frame(session);
      expect(markup, session.login).toContain('aria-haspopup="menu"');
      expect(markup, session.login).not.toContain('<nav');
      expect(hrefs(markup), session.login).toEqual(['/', '/account', '/account/password']);
    }
  });

  it('renders the account as text: a hostile name cannot inject markup', () => {
    const markup = frame({ ...EXPERT, displayLabel: '<img src=x onerror=alert(1)> Э. А.', initials: 'ЭА' });
    expect(markup).not.toContain('<img');
    expect(markup).toContain('&lt;img src=x onerror=alert(1)&gt; Э. А.');
  });
});

describe('every address the frame links is a registry row', () => {
  it('for every session state and for a guest', () => {
    const registered = new Set<string>(SCREEN_REGISTRY.map((screen) => screen.address));
    for (const session of [null, ...ALL_SESSIONS]) {
      for (const href of hrefs(frame(session))) {
        expect(registered.has(href), `${session?.login ?? 'guest'} links ${href}`).toBe(true);
      }
    }
  });

  it('offers administrator links only to an admin and keeps every R-66 row visible', () => {
    const expert = new Set(hrefs(frame(EXPERT)));
    const admin = new Set(hrefs(frame(ADMIN_ONLY)));
    for (const screen of SCREEN_REGISTRY.filter((entry) => entry.inMenu)) {
      expect(admin.has(screen.address), screen.address).toBe(true);
      expect(expert.has(screen.address), screen.address).toBe(screen.group !== 'admin');
    }
    expect(expert.has('/optimisation')).toBe(false);
    expect(admin.has('/optimisation')).toBe(false);
  });
});

describe('the frame makes no API call', () => {
  it('renders every state with no query client and no fetch', () => {
    const fetch = vi.fn(() => Promise.reject(new Error('the frame must not fetch')));
    vi.stubGlobal('fetch', fetch);
    for (const session of [null, ...ALL_SESSIONS]) expect(() => frame(session)).not.toThrow();
    expect(fetch).not.toHaveBeenCalled();
  });
});

describe('the footer', () => {
  it('says what W49 made true, and the sentence it replaced is gone', () => {
    for (const session of [null, EXPERT]) {
      const markup = frame(session);
      expect(markup).toContain(`<footer class="am-app__footer">${FRAME_FOOTER}</footer>`);
      expect(markup).not.toContain('разделения доступа');
      expect(markup).not.toContain('Один проверяющий');
    }
  });
});

describe('the two layout states, and the width at the 780 px floor', () => {
  it('puts both states in the markup, each in its own container', () => {
    const markup = frame(EXPERT);
    expect(markup).toContain(`<div class="${styles.row}" data-nav-state="row">`);
    expect(markup).toContain(`<div class="${styles.stacked}" data-nav-state="stacked">`);
    expect(markup).toMatch(/aria-expanded="false"[^>]*>Меню<\/button>/);
  });

  it('shows exactly one of them: the row above the breakpoint, the stacked list at or below 780 px', () => {
    const css = readFileSync(fileURLToPath(new URL(FRAME_CSS, import.meta.url)), 'utf8');
    expect(declarations(FRAME_CSS, '.stacked')).toMatch(/display\s*:\s*none/);
    const media = /@media\s*\(max-width:\s*([\d.]+)px\)\s*\{([\s\S]*?)\n\}/.exec(css);
    expect(media, 'no breakpoint').not.toBeNull();
    expect(Number(media?.[1])).toBeGreaterThanOrEqual(780);
    expect(media?.[2]).toMatch(/\.row\s*\{\s*display\s*:\s*none;?\s*\}/);
    expect(media?.[2]).toMatch(/\.stacked\s*\{\s*display\s*:\s*block;?\s*\}/);
  });

  it('keeps the bar wrapping rather than widening (the rule the width instrument relies on)', () => {
    expect(declarations(GLOBALS, '.am-app__bar')).toMatch(/flex-wrap\s*:\s*wrap/);
    expect(declarations(FRAME_CSS, '.row')).toMatch(/flex-wrap\s*:\s*wrap/);
    expect(declarations(FRAME_CSS, '.nav')).toMatch(/min-width\s*:\s*0/);
  });

  it('holds a 66-character name and a 254-character address whole, in a header that breaks them anywhere', () => {
    expect(LONGEST_LABEL).toHaveLength(66);
    expect(LONGEST_LOGIN).toHaveLength(254);
    const markup = frame(LONGEST);
    expect(markup).toContain(`>${LONGEST_LABEL}</p>`);
    expect(markup).toContain(`>${LONGEST_LOGIN}</p>`);
    const rule = declarations(FRAME_CSS, '.accountName,\n.accountLogin,\n.accountRoles');
    expect(rule).toMatch(/overflow-wrap\s*:\s*anywhere/);
    expect(rule).toMatch(/min-width\s*:\s*0/);
    // The popup that holds the header never exceeds the viewport less the bar's padding.
    expect(declarations(GLOBALS, '.am-menu__popup')).toMatch(/max-width\s*:\s*min\(20rem,\s*calc\(100vw - 32px\)\)/);
  });
});
