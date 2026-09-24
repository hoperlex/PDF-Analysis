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
