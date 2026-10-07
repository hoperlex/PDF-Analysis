/**
 * A rendered screen may not deny authentication while the frozen contract carries an
 * authentication scheme.
 *
 * This guard was added after /projects told a reviewer who had just signed in that the
 * system had no authentication. Its first version derived the route set, but rendered only
 * the cold branch and recognised four literal phrasings. Both closing W44 judges put the
 * same denial into different words and left all 1109 frontend tests green.
 *
 * The subject now has two independent halves:
 *
 * - capability comes from OpenAPI's securitySchemes, not from a path literal;
 * - prose comes from the state-aware contrast inventory, which already renders cold,
 *   loaded, refused, failed and widget-specific states.
 *
 * The language predicate is deliberately bounded. It composes an authentication vocabulary
 * with an absence/non-requirement vocabulary inside one visible sentence; it is not a claim
 * to solve arbitrary natural-language entailment. The controls below carry every wording
 * both closing judges used, so widening or narrowing that boundary is an explicit edit.
 */

import { describe, expect, it } from 'vitest';

import { FRAME_FOOTER } from '@/_app';

import { screens } from '../unit/styles/screens';
import { readText, REPO_ROOT } from './lib/repo';
import { join } from 'node:path';

interface OpenApiDocument {
  readonly components?: {
    readonly securitySchemes?: Readonly<Record<string, { readonly type?: unknown }>>;
  };
}

const CONTRACT = JSON.parse(
  readText(join(REPO_ROOT, 'contracts/api/v1/openapi.json')),
) as OpenApiDocument;

const SECURITY_SCHEME_TYPES = new Set([
  'apiKey',
  'http',
  'mutualTLS',
  'oauth2',
  'openIdConnect',
]);

function contractCarriesAuthentication(contract: OpenApiDocument): boolean {
  return Object.values(contract.components?.securitySchemes ?? {}).some(
    (scheme) => typeof scheme.type === 'string' && SECURITY_SCHEME_TYPES.has(scheme.type),
  );
}

const AUTHENTICATION_WORDS: readonly RegExp[] = [
  /аутентификац\p{L}*/iu,
  /авторизац\p{L}*/iu,
  /(?:^|\s)вход(?:ить|а|у|ом)?(?:\s+в\s+систему)?(?:\s|$)/iu,
  /уч[её]тн\p{L}*\s+данн\p{L}*/iu,
  /проверк\p{L}*\s+личност\p{L}*\s+пользовател\p{L}*/iu,
  /\bauthentication\b/iu,
  /\bsign[ -]?in\b/iu,
  /\bcredentials?\b/iu,
];

const ABSENCE_WORDS: readonly RegExp[] = [
  /(?:^|\s)без(?:\s|$)/iu,
  /(?:^|\s)нет(?=\s|[.,!?;:]|$)/iu,
  /отсутств\p{L}*/iu,
  /не\s+(?:выполня\p{L}*|использ\p{L}*|нуж\p{L}*|поддерж\p{L}*|треб\p{L}*)/iu,
  /\bno\b/iu,
  /\bwithout\b/iu,
  /\bnot\s+(?:used|required|supported)\b/iu,
];

/** Visible sentence-sized segments; block boundaries must not invent a cross-node claim. */
function visibleSegments(markup: string): readonly string[] {
  return markup
    .replace(/<\/(?:button|div|footer|form|h[1-6]|header|li|main|p|section)>/giu, '\n')
    .replace(/<[^>]*>/gu, ' ')
    .replace(/&nbsp;/giu, ' ')
    .replace(/&(?:amp|quot|#39);/giu, ' ')
    .split(/\n+|(?<=[.!?])\s+/u)
    .map((part) => part.replace(/\s+/gu, ' ').trim())
    .filter((part) => part.length > 0);
}

function authenticationDenials(markup: string): readonly string[] {
  return visibleSegments(markup).filter(
    (sentence) =>
      AUTHENTICATION_WORDS.some((word) => word.test(sentence)) &&
      ABSENCE_WORDS.some((word) => word.test(sentence)),
  );
}

describe('screens do not deny authentication carried by the contract', () => {
  it('derives the capability from securitySchemes and does not go vacuous today', () => {
    expect(contractCarriesAuthentication({})).toBe(false);
    expect(
      contractCarriesAuthentication({
        components: { securitySchemes: { bearerAuth: { type: 'http' } } },
      }),
    ).toBe(true);
    expect(contractCarriesAuthentication(CONTRACT)).toBe(true);
  });

  it('recognises the bounded denial vocabulary, including both judges\' paraphrases', () => {
    const denials = [
      'Без аутентификации.',
      'Аутентификации в этой установке нет.',
      'Система не использует аутентификацию.',
      'Вход не требуется.',
      'Входить в систему не требуется.',
      'Приложение работает без входа в систему.',
      'Проверка личности пользователя в приложении не выполняется.',
      'Для работы учётные данные не нужны.',
      'No authentication.',
      'Sign-in is not required.',
    ];
    const permitted = [
      'Аутентификация обязательна.',
      'Вход выполнен.',
      'Учётные данные приняты.',
      'Authentication is required.',
    ];

    for (const sentence of denials) {
      expect(authenticationDenials(`<p>${sentence}</p>`), sentence).toEqual([sentence]);
    }
    for (const sentence of permitted) {
      expect(authenticationDenials(`<p>${sentence}</p>`), sentence).toEqual([]);
    }
  });

  it('finds no denial in any state-aware rendered screen', () => {
    if (!contractCarriesAuthentication(CONTRACT)) return;

    const offences = screens().flatMap((screen) =>
      authenticationDenials(screen.markup).map((sentence) => ({
        screen: screen.name,
        sentence,
      })),
    );

    expect(
      offences,
      'These rendered states deny authentication, while components.securitySchemes carries it. ' +
        'The renderer is the state-aware contrast inventory; the vocabulary boundary is tested above.',
    ).toEqual([]);
  });
});

/*
 * `W50-SHELL-FRAME`. The same rule for roles: a rendered screen may not deny roles, or a
 * separation of access between accounts, while the frozen contract declares `Role`.
 *
 * Two sentences reached a reviewer on every screen and in the project list after W49 gave the
 * alpha a role set (`R-55`, `R-60`): the frame's footer, «Альфа-версия. Один проверяющий, без
 * разделения доступа между учётными записями.», and the `/projects` subtitle «Одна учётная
 * запись на эту установку. Ролей и разделения на организации пока нет.». Both are red controls
 * below. The capability is read from `components.schemas.Role` — a schema with a non-empty
 * enum — never from a literal list of role names, and the prose from the same state-aware
 * inventory as the authentication half above. The vocabulary is bounded the same way: a role
 * or access-separation word and an absence word in one visible sentence. «Роли не назначены.»
 * — a fact about one account, which the home page and the account menu say — is permitted.
 */

interface RoleContract {
  readonly components?: {
    readonly schemas?: Readonly<Record<string, { readonly enum?: unknown }>>;
  };
}

function contractDeclaresRoles(contract: RoleContract): boolean {
  const values = contract.components?.schemas?.Role?.enum;
  return Array.isArray(values) && values.length > 0;
}

const ROLE_WORDS: readonly RegExp[] = [
  /(?:^|[^\p{L}])рол(?:ь|и|ей|ям|ями|ях|ью)(?=[^\p{L}]|$)/iu,
  /разделени\p{L}*\s+(?:доступа|прав|ролей|на\s+организац\p{L}*)/iu,
  /\broles?\b/iu,
  /\baccess\s+control\b/iu,
  /\bseparation\s+of\s+(?:access|duties|roles)\b/iu,
];

/**
 * A sentence about what ONE account holds — «у вашей учётной записи нет роли…», which `/403`
 * says — is a fact about that account and affirms that roles exist; it is not a claim about the
 * system. The possessive construction is what marks it.
 */
const ACCOUNT_FACT: readonly RegExp[] = [
  /(?:^|\s)у\s+(?:вашей\s+|этой\s+)?уч[её]тн\p{L}*\s+запис\p{L}*/iu,
  /(?:^|\s)у\s+вас(?=\s|[.,!?;:]|$)/iu,
];

function roleDenials(markup: string): readonly string[] {
  return visibleSegments(markup).filter(
    (sentence) =>
      ROLE_WORDS.some((word) => word.test(sentence)) &&
      ABSENCE_WORDS.some((word) => word.test(sentence)) &&
      !ACCOUNT_FACT.some((word) => word.test(sentence)),
  );
}

describe('screens do not deny the roles carried by the contract', () => {
  it('derives the capability from components.schemas.Role and does not go vacuous today', () => {
    expect(contractDeclaresRoles({})).toBe(false);
    expect(contractDeclaresRoles({ components: { schemas: { Role: { enum: [] } } } })).toBe(false);
    expect(contractDeclaresRoles({ components: { schemas: { Role: { enum: ['x'] } } } })).toBe(true);
    expect(contractDeclaresRoles(CONTRACT as RoleContract)).toBe(true);
  });

  it('recognises the bounded denial vocabulary, with the old footer and the old /projects subtitle', () => {
    const denials = [
      'Альфа-версия. Один проверяющий, без разделения доступа между учётными записями.',
      'Одна учётная запись на эту установку. Ролей и разделения на организации пока нет.',
      'Ролей нет.',
      'Без ролей.',
      'Роли не используются.',
      'Разделения доступа в этой установке нет.',
      'No roles.',
      'There is no access control.',
    ];
    const permitted = [
      FRAME_FOOTER,
      'Роли: Эксперт, Администратор.',
      'Роли не назначены.',
      'Роли учётной записи не распознаны.',
      'У вашей учётной записи нет роли, которая открывает этот экран.',
      'Этот экран открывается только с ролью Администратор, а у вашей учётной записи её нет.',
      'Roles are required.',
    ];
    for (const sentence of denials) {
      // The last sentence of the segmenter's split carries the denial; the first of the old
      // footer («Альфа-версия.») is its own segment and is not one.
      expect(roleDenials(`<p>${sentence}</p>`).length, sentence).toBeGreaterThan(0);
    }
    for (const sentence of permitted) {
      expect(roleDenials(`<p>${sentence}</p>`), sentence).toEqual([]);
    }
  });

  it('finds no denial in any state-aware rendered screen', () => {
    if (!contractDeclaresRoles(CONTRACT as RoleContract)) return;
    const offences = screens().flatMap((screen) =>
      roleDenials(screen.markup).map((sentence) => ({ screen: screen.name, sentence })),
    );
    expect(
      offences,
      'These rendered states deny roles or a separation of access, while components.schemas.Role ' +
        'declares a role set. The renderer is the state-aware contrast inventory; the vocabulary ' +
        'boundary is tested above.',
    ).toEqual([]);
  });
});
