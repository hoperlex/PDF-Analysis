/**
 * `AR-V3-BETA-PACK-STATUS-WEB-01`: the settings panel that says whether the reviewed AR v3 pack
 * is installed.
 *
 * Two subjects. The pure classification of `getArV3BetaPackStatus` — three outcomes, the third a
 * fault that is never drawn as installed and never as an empty state — and the panel rendered
 * from a seeded cache in each of its five states (`D-53`: every assertion is on markup a
 * reviewer would see).
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { ApiError, queryKeys } from '@/shared/api';
import type { ArV3BetaPackStatus, ErrorCode } from '@/shared/api';
import { AR_V3_PACK_SCOPE_IDS, readArV3PackStatus } from '@/entities/audit-run';
import type { ArV3PackFaultReason, ArV3PackReading } from '@/entities/audit-run';
import {
  ATTESTATION_SENTENCE,
  PACK_NOT_INSTALLED_SENTENCE,
  PACK_READ_FAILED_TITLE,
  packDigestShown,
} from '@/widgets/ar-v3-beta-pack';
import { ArV3BetaPack } from '@/widgets/ar-v3-beta-pack';
import { AnalysisSettingsPage } from '@/_pages/analysis-settings';

import { newClient, renderScreen, seedError } from '../screens/harness';

import { NOT_INSTALLED_PACK, installedPackFixture, withoutMember } from './ar-v3-beta-pack-fixtures';

const REAL_DIGEST = '6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f';

const PROFILE_ID = 'ap_01M5AXG1K22R027A33VTKZ468P';
const BUNDLE_ID = 'pb_01M5AXG1K2JQQH7R4ACTBW8974';

/**
 * Identifiers the contract's patterns (`^ap_[0-9A-HJKMNP-TV-Z]{26}$`, `^pb_...`) refuse, one defect
 * each: not a ULID at all, padded, a trailing newline, lower case, the wrong length, a letter
 * Crockford leaves out, and the other kind's prefix. A pack with any of them is not installed.
 */
function malformedIdentifierCases(
  installed: ArV3BetaPackStatus,
): ReadonlyArray<readonly [string, unknown, ArV3PackFaultReason]> {
  const withProfile = (value: string) => ({ ...installed, analysis_profile_id: value });
  const withBundle = (value: string) => ({ ...installed, prompt_bundle_id: value });
  return [
    ['a profile id that is "x"', withProfile('x'), 'bad_identifier'],
    ['a profile id with a leading space', withProfile(` ${PROFILE_ID}`), 'bad_identifier'],
    ['a profile id with a trailing space', withProfile(`${PROFILE_ID} `), 'bad_identifier'],
    ['a profile id with a trailing newline', withProfile(`${PROFILE_ID}\n`), 'bad_identifier'],
    ['a lower-case profile id', withProfile(PROFILE_ID.toLowerCase()), 'bad_identifier'],
    ['a profile id one character short', withProfile(PROFILE_ID.slice(0, -1)), 'bad_identifier'],
    ['a profile id one character long', withProfile(`${PROFILE_ID}0`), 'bad_identifier'],
    ['a profile id with a letter Crockford omits', withProfile(`ap_01M5AXG1K22R027A33VTKZ468U`), 'bad_identifier'],
    ['a profile id with the bundle prefix', withProfile(BUNDLE_ID), 'bad_identifier'],
    ['a bundle id that is "x"', withBundle('x'), 'bad_identifier'],
    ['a bundle id with a leading space', withBundle(` ${BUNDLE_ID}`), 'bad_identifier'],
    ['a bundle id with a trailing newline', withBundle(`${BUNDLE_ID}\n`), 'bad_identifier'],
    ['a lower-case bundle id', withBundle(BUNDLE_ID.toLowerCase()), 'bad_identifier'],
    ['a bundle id one character short', withBundle(BUNDLE_ID.slice(0, -1)), 'bad_identifier'],
    ['a bundle id with the profile prefix', withBundle(PROFILE_ID), 'bad_identifier'],
  ];
}

function faultOf(body: unknown): ArV3PackFaultReason {
  const reading = readArV3PackStatus(body);
  if (reading.kind !== 'fault') throw new Error(`expected a fault, read ${reading.kind}`);
  return reading.reason;
}

describe('the pack status classification has exactly three outcomes', () => {
  it('reads the installed shape with every member, and keeps the six scopes in order', () => {
    const reading = readArV3PackStatus(installedPackFixture({ pack_sha256: REAL_DIGEST }));
    expect(reading.kind).toBe('installed');
    if (reading.kind !== 'installed') return;
    expect(reading.packSha256).toBe(REAL_DIGEST);
    expect(reading.scopeIds).toEqual(['F1', 'F2', 'A1', 'A2', 'S1', 'S2']);
    expect(reading.scopeIds).toEqual([...AR_V3_PACK_SCOPE_IDS]);
    expect(reading.review.reviewer).toBe('Иванова Мария Петровна');
    expect(reading.review.reviewed_at).toBe('2026-10-20');
  });

  it('reads the identifiers the contract pattern accepts, unchanged', () => {
    const reading = readArV3PackStatus(installedPackFixture());
    expect(reading.kind).toBe('installed');
    if (reading.kind !== 'installed') return;
    expect(reading.analysisProfileId).toBe(PROFILE_ID);
    expect(reading.promptBundleId).toBe(BUNDLE_ID);
  });

  it('reads not_installed only when it carries nothing else', () => {
    expect(readArV3PackStatus(NOT_INSTALLED_PACK)).toEqual({ kind: 'not_installed' });
    expect(faultOf({ state: 'not_installed', pack_sha256: REAL_DIGEST })).toBe('members_beside_not_installed');
    expect(faultOf({ state: 'not_installed', scope_ids: undefined })).toBe('members_beside_not_installed');
  });

  it('is a fault, never installed and never an empty state, when the answer breaks the contract', () => {
    const installed = installedPackFixture({ pack_sha256: REAL_DIGEST });
    const withoutReview = withoutMember(installed, 'review');
    const withoutScopes = withoutMember(installed, 'scope_ids');
    const withoutProfile = withoutMember(installed, 'analysis_profile_id');
    const cases: ReadonlyArray<readonly [string, unknown, ArV3PackFaultReason]> = [
      ['null', null, 'not_an_object'],
      ['an array', [installed], 'not_an_object'],
      ['a string', 'installed', 'not_an_object'],
      ['no state', {}, 'unknown_state'],
      ['an undeclared state', { state: 'withdrawn' }, 'unknown_state'],
      ['an upper-case state', { state: 'Installed' }, 'unknown_state'],
      ['installed without a review', withoutReview, 'missing_member'],
      ['installed without its scopes', withoutScopes, 'missing_member'],
      ['installed without its profile', withoutProfile, 'missing_member'],
      ['an invented member', { ...installed, snapshot_id: 'ns_x' }, 'unknown_member'],
      ...malformedIdentifierCases(installed),
      ['a digest of the wrong length', { ...installed, pack_sha256: REAL_DIGEST.slice(1) }, 'bad_digest'],
      ['an upper-case digest', { ...installed, pack_sha256: REAL_DIGEST.toUpperCase() }, 'bad_digest'],
      ['five scopes', { ...installed, scope_ids: ['F1', 'F2', 'A1', 'A2', 'S1'] }, 'bad_scope_list'],
      ['seven scopes', { ...installed, scope_ids: [...AR_V3_PACK_SCOPE_IDS, 'S3'] }, 'bad_scope_list'],
      ['scopes out of order', { ...installed, scope_ids: ['F2', 'F1', 'A1', 'A2', 'S1', 'S2'] }, 'bad_scope_list'],
      ['a repeated scope', { ...installed, scope_ids: ['F1', 'F1', 'A1', 'A2', 'S1', 'S2'] }, 'bad_scope_list'],
      ['scopes that are not an array', { ...installed, scope_ids: 'F1,F2,A1,A2,S1,S2' }, 'bad_scope_list'],
      ['a null review', { ...installed, review: null }, 'bad_attestation'],
      [
        'a blank reviewer',
        { ...installed, review: { ...installed.review, reviewer: '   ' } },
        'bad_attestation',
      ],
      [
        'a review date that is not a date',
        { ...installed, review: { ...installed.review, reviewed_at: '20 октября' } },
        'bad_attestation',
      ],
      [
        'an invented attestation member',
        { ...installed, review: { ...installed.review, verified: true } },
        'bad_attestation',
      ],
    ];
    for (const [name, body, reason] of cases) {
      const reading: ArV3PackReading = readArV3PackStatus(body);
      expect(reading.kind, name).toBe('fault');
      expect(faultOf(body), name).toBe(reason);
    }
  });

  it('shows the first twelve hex characters of the digest and says it is shortened', () => {
    expect(packDigestShown(REAL_DIGEST)).toBe('6d53674f688f…');
    expect(packDigestShown(REAL_DIGEST).replace('…', '')).toHaveLength(12);
  });
});

/**
 * What may sit between two characters of one printed digest without hiding it from a reader:
 * white space (a no-break space and a newline included), the separators a digest is grouped with,
 * and the characters that print nothing — zero-width space, non-joiner, joiner, word joiner, the
 * byte-order mark and the soft hyphen.
 */
const DIGEST_SEPARATOR = '(?:\\s|-|_|:|\\u200b|\\u200c|\\u200d|\\u2060|\\ufeff|\\u00ad)';
const BETWEEN_HEX = new RegExp(`(?<=[0-9a-f])${DIGEST_SEPARATOR}+(?=[0-9a-f])`, 'g');

/** Lower-case, with the separators between two hex characters taken out. */
function squeezed(text: string): string {
  return text.toLowerCase().replace(BETWEEN_HEX, '');
}

/**
 * The longest stretch of `digest` that appears in `markup` as a person would read it. The rule is
 * a bound on this number, not on a particular attribute: a digest in a `title`, a `data-`
 * attribute, a comment or hidden text is in the DOM for any role whatever it is called.
 *
 * Reading, not byte matching: the comparison is case-insensitive, ignores the separators above
 * between hex characters, and is made twice — over the markup as written (attributes included)
 * and over its text with the tags taken out (a digest cut into sibling elements). Entity-encoded
 * characters are not decoded; React writes none for the characters above.
 */
function longestDigestRun(markup: string, digest: string): number {
  const needle = digest.toLowerCase();
  const views = [squeezed(markup), squeezed(markup.replace(/<[^>]*>/g, ''))];
  for (let length = needle.length; length > 0; length -= 1) {
    for (let start = 0; start + length <= needle.length; start += 1) {
      const piece = needle.slice(start, start + length);
      if (views.some((view) => view.includes(piece))) return length;
    }
  }
  return 0;
}

describe('no more than twelve characters of the pack digest are in the markup', () => {
  it('measures a whole digest wherever it sits, so the bound below can fail', () => {
    expect(longestDigestRun(`<code title="${REAL_DIGEST}">6d53674f688f…</code>`, REAL_DIGEST)).toBe(64);
    expect(longestDigestRun(`<code data-digest="${REAL_DIGEST}"></code>`, REAL_DIGEST)).toBe(64);
    expect(longestDigestRun('<code>6d53674f688f…</code>', REAL_DIGEST)).toBe(12);
    expect(longestDigestRun('<code>nothing</code>', REAL_DIGEST)).toBeLessThan(3);
  });

  // `AR-V3-BETA-PACK-STATUS-WEB-FIX-02`, finding 3. The measure used to look for contiguous,
  // case-sensitive runs only, so a whole digest printed in upper case, or in groups of eight, or
  // with a zero-width character in it, measured as a few characters and passed the bound.
  const GROUPS = REAL_DIGEST.match(/.{8}/g) as string[];
  const upper = (text: string): string => text.toUpperCase();

  it('measures a whole digest in upper case, in groups, or with invisible separators', () => {
    const printed: ReadonlyArray<readonly [string, string]> = [
      ['upper case', `<code>${upper(REAL_DIGEST)}</code>`],
      ['mixed case', `<code>${REAL_DIGEST.slice(0, 20)}${upper(REAL_DIGEST.slice(20))}</code>`],
      ['groups of eight with spaces', `<code>${GROUPS.join(' ')}</code>`],
      ['groups of eight with hyphens', `<code>${GROUPS.join('-')}</code>`],
      ['groups of eight with underscores', `<code>${GROUPS.join('_')}</code>`],
      ['groups of eight with colons', `<code>${GROUPS.join(':')}</code>`],
      ['groups of eight with a no-break space', `<code>${GROUPS.join('\u00a0')}</code>`],
      ['groups of eight in upper case', `<code>${GROUPS.map(upper).join(' ')}</code>`],
      ['groups of eight with a newline and indentation', `<code>${GROUPS.join('\n    ')}</code>`],
      ['a zero-width space between groups', `<code>${GROUPS.join('\u200b')}</code>`],
      ['a zero-width non-joiner between groups', `<code>${GROUPS.join('\u200c')}</code>`],
      ['a zero-width joiner between groups', `<code>${GROUPS.join('\u200d')}</code>`],
      ['a word joiner between groups', `<code>${GROUPS.join('\u2060')}</code>`],
      ['a byte-order mark between groups', `<code>${GROUPS.join('\ufeff')}</code>`],
      ['a zero-width space after every character', `<code>${REAL_DIGEST.split('').join('\u200b')}</code>`],
      ['mixed separators', `<code>${GROUPS.map((group, index) => group + ['-', ' ', '_', ':'][index % 4]).join('')}</code>`],
      ['groups in sibling elements', GROUPS.map((group) => `<span>${group}</span>`).join('')],
      ['groups in sibling elements with spaces', GROUPS.map((group) => `<span>${group}</span>`).join(' ')],
      ['upper case, grouped, in a title', `<code title="${upper(GROUPS.join(' '))}">…</code>`],
      ['grouped in a data attribute', `<code data-digest="${GROUPS.join('-')}"></code>`],
    ];
    for (const [name, markup] of printed) {
      expect(longestDigestRun(markup, REAL_DIGEST), name).toBe(64);
    }
  });

  it('still reads the shortened form as twelve, in either case, and invents no run from other text', () => {
    expect(longestDigestRun('<code>6d53674f688f…</code>', REAL_DIGEST)).toBe(12);
    expect(longestDigestRun('<code>6D53674F688F…</code>', REAL_DIGEST)).toBe(12);
    expect(longestDigestRun('<code>6d53 674f 688f…</code>', REAL_DIGEST)).toBe(12);
    // Words, dates and class names are separated by the same characters; none of them is a digest.
    const prose =
      '<li class="am-state am-state--neutral" data-run-id="run_01J9ZQ8K7NHVXW3T2R5M6P4Q8B">' +
      'Создан 2026-09-10 08:00:00 UTC · decade-old facade: a bad deed</li>';
    expect(longestDigestRun(prose, REAL_DIGEST)).toBeLessThan(6);
  });
});

const panel = (client = newClient()): string => renderScreen(client, createElement(ArV3BetaPack));

describe('the pack panel in each of its five states', () => {
  it('loading: no panel yet, and no start-related claim', () => {
    const markup = panel();
    expect(markup).toContain('Загрузка: статуса пакета проверенных норм АР v3…');
    expect(markup).not.toContain('data-ar-v3-pack-status="installed"');
    expect(markup).not.toContain('data-ar-v3-pack-status="not_installed"');
  });

  it('error: its own sentence, the correlation id and a retry — not the installed or empty panel', () => {
    const client = newClient();
    seedError(
      client,
      queryKeys.runs.arV3PackStatus(),
      new ApiError(
        503,
        {
          contract_version: '1.10.0',
          error_code: 'dependency_unavailable' as ErrorCode,
          message: 'm',
          correlation_id: 'cid-pack',
          retryable: true,
        },
        'cid-pack',
      ),
    );
    const markup = panel(client);
    expect(markup).toContain(PACK_READ_FAILED_TITLE);
    expect(PACK_READ_FAILED_TITLE).toBe('Не удалось прочитать статус пакета проверенных норм АР v3');
    expect(markup).toContain('data-ar-v3-pack-status="error"');
    expect(markup).toContain('cid-pack');
    expect(markup).toContain('>Повторить</button>');
    expect(markup).not.toContain(PACK_NOT_INSTALLED_SENTENCE);
    expect(markup).not.toContain('data-ar-v3-pack-state="installed"');
  });

  it('not installed: the fixed sentence, and nothing about a reviewer', () => {
    const client = newClient();
    client.setQueryData(queryKeys.runs.arV3PackStatus(), NOT_INSTALLED_PACK);
    const markup = panel(client);
    expect(markup).toContain('data-ar-v3-pack-state="not_installed"');
    expect(markup).toContain('Пакет проверенных норм АР v3 не установлен: запуск шести проверок недоступен.');
    expect(markup).not.toContain('Запись рецензента');
    expect(markup).not.toContain('<button');
  });

  it('installed: profile, shortened digest, six scopes, the attestation and the fixed caveat', () => {
    const client = newClient();
    client.setQueryData(queryKeys.runs.arV3PackStatus(), installedPackFixture({ pack_sha256: REAL_DIGEST }));
    const markup = panel(client);
    expect(markup).toContain('data-ar-v3-pack-state="installed"');
    expect(markup).toContain('ap_01M5AXG1K22R027A33VTKZ468P');
    expect(markup).toContain('>6d53674f688f…<');
    expect(markup).toContain('data-ar-v3-pack-scopes="F1 F2 A1 A2 S1 S2"');
    expect(markup).toContain('F1, F2, A1, A2, S1, S2');
    for (const text of [
      'Иванова Мария Петровна',
      'главный эксперт по разделу АР',
      '2026-10-20',
      'решение владельца № 146',
      'шесть карт норм и шесть наборов источников для жилых домов Ф1.3',
    ]) {
      expect(markup, text).toContain(text);
    }
    expect(markup).toContain(
      'Запись рецензента приложена при установке пакета; система её не проверяет, цитаты остаются ' +
        'предварительными и требуют проверки эксперта.',
    );
    expect(ATTESTATION_SENTENCE).toBe(
      'Запись рецензента приложена при установке пакета; система её не проверяет, цитаты остаются ' +
        'предварительными и требуют проверки эксперта.',
    );
  });

  it('installed: the 64-character digest is nowhere in the markup, only its first twelve characters', () => {
    const client = newClient();
    client.setQueryData(queryKeys.runs.arV3PackStatus(), installedPackFixture({ pack_sha256: REAL_DIGEST }));
    const markup = panel(client);
    expect(markup).not.toContain(REAL_DIGEST);
    // Exactly the twelve shown: none hidden elsewhere, and the twelve are there (not a vacuous pass).
    expect(longestDigestRun(markup, REAL_DIGEST)).toBe(12);
    // The same on the screen that mounts the panel.
    const screen = renderScreen(client, createElement(AnalysisSettingsPage));
    expect(screen).toContain('data-ar-v3-pack-state="installed"');
    expect(screen).not.toContain(REAL_DIGEST);
    expect(longestDigestRun(screen, REAL_DIGEST)).toBe(12);
  });

  it('installed: a reviewer\'s free text is escaped, never markup', () => {
    const client = newClient();
    const fixture = installedPackFixture();
    client.setQueryData(queryKeys.runs.arV3PackStatus(), {
      ...fixture,
      review: { ...fixture.review!, scope_statement: '<script>решение</script>' },
    });
    const markup = panel(client);
    expect(markup).toContain('&lt;script&gt;решение&lt;/script&gt;');
    expect(markup).not.toContain('<script>решение</script>');
  });

  it('fault: says the answer breaks the contract and draws neither installed nor empty', () => {
    for (const body of [
      withoutMember(installedPackFixture(), 'review'),
      { state: 'withdrawn' },
      { ...installedPackFixture(), scope_ids: ['F1', 'F2'] },
    ]) {
      const client = newClient();
      client.setQueryData(queryKeys.runs.arV3PackStatus(), body);
      const markup = panel(client);
      expect(markup).toContain('data-ar-v3-pack-status="fault"');
      expect(markup).toContain('Ответ сервера не соответствует контракту');
      expect(markup).not.toContain('data-ar-v3-pack-state=');
      expect(markup).not.toContain(PACK_NOT_INSTALLED_SENTENCE);
      expect(markup).not.toContain('Запись рецензента');
    }
  });
});

describe('«Настройки анализа» mounts the pack panel above the group review', () => {
  it('puts the panel before the lookup form and after the frozen source preview', () => {
    const client = newClient();
    client.setQueryData(queryKeys.runs.arV3PackStatus(), installedPackFixture());
    const markup = renderScreen(client, createElement(AnalysisSettingsPage));
    const preview = markup.indexOf('data-ar-v3-beta-status');
    const pack = markup.indexOf('data-ar-v3-pack-status="installed"');
    const review = markup.indexOf('data-ar-v3-group-review');
    expect(preview).toBeGreaterThan(-1);
    expect(pack).toBeGreaterThan(preview);
    expect(review).toBeGreaterThan(pack);
  });
});
