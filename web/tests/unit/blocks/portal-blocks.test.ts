/**
 * «Блоки портала» (`W55B-WEB-BLOCKS`, plan §B3.9): what each block shows, and what it never
 * shows.
 *
 * Every assertion is taken from rendered markup (`renderToStaticMarkup` through the screen
 * harness; this suite has no DOM). Where a property is about what the markup does NOT
 * contain — no element made out of the portal's text, no raw machine token — the positive
 * half is asserted beside it, so a render that produced nothing could not pass.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { PortalBlock } from '@/shared/api';
import {
  DESCRIPTION_MARKER,
  GEOMETRY_MISMATCH_LABEL,
  RECOGNISED_FLAGS,
  RECOGNISED_MARKER,
  UNKNOWN_FLAG,
  UNKNOWN_PORTAL_STATUS,
} from '@/entities/block';
import { CropFigureView, PortalBlockCard, PortalBlockListView } from '@/widgets/portal-blocks';

import { newClient, renderScreen } from '../screens/harness';
import {
  BLOCKS_PROJECT_UID,
  BLOCKS_RUN_ID,
  KNOWN_FLAGS,
  TEST_CROP_SRC,
  UNKNOWN_FLAG_TOKEN,
  UNKNOWN_STATUS_TOKEN,
  everyKindOfBlock,
  imageBlock,
  omit,
  stampBlock,
  textBlock,
} from './fixtures';

function card(block: PortalBlock): string {
  return renderScreen(newClient(), createElement(PortalBlockCard, { block, cropSrc: TEST_CROP_SRC }));
}

function list(blocks: readonly PortalBlock[], over: Partial<Parameters<typeof PortalBlockListView>[0]> = {}): string {
  return renderScreen(
    newClient(),
    createElement(PortalBlockListView, {
      projectUid: BLOCKS_PROJECT_UID,
      blockCount: blocks.length,
      producedByRunId: BLOCKS_RUN_ID,
      blocks,
      cropSrc: TEST_CROP_SRC,
      hasMore: false,
      loadingMore: false,
      moreFailure: null,
      onMore: () => {},
      ...over,
    }),
  );
}

/** Decode the entities `renderToStaticMarkup` writes, so a test compares what a reader reads. */
function decode(text: string): string {
  return text
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#x27;/g, "'")
    .replace(/&amp;/g, '&');
}

/** The text nodes of a fragment, decoded, `<code>` contents left out (identifiers). */
function visibleText(markup: string): string {
  return decode(
    markup
      .replace(/<code>[\s\S]*?<\/code>/g, ' ')
      .replace(/<[^>]*>/g, ' ')
      .replace(/\s+/g, ' '),
  ).trim();
}

function count(markup: string, needle: string | RegExp): number {
  return typeof needle === 'string'
    ? markup.split(needle).length - 1
    : (markup.match(new RegExp(needle.source, needle.flags.includes('g') ? needle.flags : `${needle.flags}g`)) ?? []).length;
}

describe('a TEXT block shows the recognised text, marked, with its flags', () => {
  it('marks the text «распознано» and keeps the machine value in data-quote-source', () => {
    const markup = card(textBlock());
    expect(RECOGNISED_MARKER).toBe('распознано');
    expect(markup).toContain(`>${RECOGNISED_MARKER}<`);
    expect(markup).toContain('data-quote-source="recognised"');
    expect(markup).toMatch(/<pre[^>]*>Пояснительная записка\. Раздел 1\.<\/pre>/);
    expect(markup).toContain('data-portal-block-type="text"');
    expect(markup).toContain('>Текст<');
  });

  it('puts the marker on EVERY recognised text of a list, and on nothing else', () => {
    const blocks = everyKindOfBlock();
    const markup = list(blocks);
    const recognised = blocks.filter((block) => block.recognised_text !== undefined).length;
    expect(recognised).toBeGreaterThan(1);
    expect(count(markup, 'data-quote-source="recognised"')).toBe(recognised);
    expect(count(markup, `>${RECOGNISED_MARKER}<`)).toBe(recognised);
    expect(count(markup, /<pre[^>]*>/)).toBe(recognised);
  });

  it('shows each flag the backend emits as a Russian chip with a sentence, never the token', () => {
    const markup = card(
      textBlock({ recognised_text: { quote_source: 'recognised', text: 'Уровeнь', flags: [...KNOWN_FLAGS] } }),
    );
    const visible = visibleText(markup);
    for (const flag of KNOWN_FLAGS) {
      const presentation = RECOGNISED_FLAGS[flag];
      expect(presentation, `${flag} has no Russian label`).toBeDefined();
      expect(markup).toContain(`data-recognised-flag="${flag}"`);
      expect(visible).toContain(presentation?.label);
      expect(visible).toContain(presentation?.explanation);
      expect(visible).not.toContain(flag);
    }
    expect(count(markup, 'data-recognised-flag=')).toBe(KNOWN_FLAGS.length);
  });

  it('names a flag it does not know neutrally and does not print the token', () => {
    const markup = card(
      textBlock({ recognised_text: { quote_source: 'recognised', text: 'текст', flags: [UNKNOWN_FLAG_TOKEN] } }),
    );
    expect(markup).toContain(`data-recognised-flag="${UNKNOWN_FLAG_TOKEN}"`);
    expect(visibleText(markup)).toContain(UNKNOWN_FLAG.label);
    expect(visibleText(markup)).toContain(UNKNOWN_FLAG.explanation);
    expect(visibleText(markup)).not.toContain(UNKNOWN_FLAG_TOKEN);
  });

  it('says «Текст не распознан.» for a TEXT block the markdown did not hold, with no empty box', () => {
    const markup = card(omit(textBlock(), 'recognised_text'));
    expect(markup).toContain('Текст не распознан.');
    expect(markup).not.toContain('<pre');
    expect(markup).not.toContain(`>${RECOGNISED_MARKER}<`);
  });
});

describe('the portal text is text: nothing in it becomes an element, an attribute or a link', () => {
  const PAYLOAD =
    '<script>alert(1)</script>\n<img src=x onerror=alert(1)>\n[ссылка](javascript:alert(1))\n&lt; останется как есть';

  for (const where of ['recognised text', 'portal description'] as const) {
    it(`renders a ${where} carrying markup as literal characters`, () => {
      const block =
        where === 'recognised text'
          ? textBlock({ recognised_text: { quote_source: 'recognised', text: PAYLOAD, flags: [] } })
          : imageBlock({ portal_description: PAYLOAD });
      const markup = card(block);

      // No element was made out of it: no script, no second image, no link, no handler.
      expect(markup).not.toMatch(/<script/i);
      expect(count(markup, /<img\b/)).toBe(where === 'recognised text' ? 0 : 1);
      expect(markup).not.toMatch(/<[^>]*\son[a-z]+=/i);
      expect(markup).not.toMatch(/href="javascript:/i);
      expect(markup).not.toContain('dangerouslySetInnerHTML');

      // And the characters are all there, escaped: a reader sees exactly what the portal sent.
      expect(markup).toContain('&lt;script&gt;alert(1)&lt;/script&gt;');
      expect(markup).toContain('&lt;img src=x onerror=alert(1)&gt;');
      expect(markup).toContain('[ссылка](javascript:alert(1))');
      expect(markup).toContain('&amp;lt; останется как есть');
      const body = /<(?:pre|p) class="[^"]*text[^"]*">([\s\S]*?)<\/(?:pre|p)>/.exec(markup)?.[1];
      expect(body === undefined ? undefined : decode(body)).toBe(PAYLOAD);
    });
  }
});

describe('an IMAGE block shows the crop this product cut, and the portal description marked', () => {
  it('points an <img> at the crop address with its own size, lazily, with a Russian alt', () => {
    const block = imageBlock();
    const markup = card(block);
    const img = /<img\b[^>]*>/.exec(markup)?.[0] ?? '';
    expect(img).toContain(`src="${TEST_CROP_SRC(block)}"`);
    expect(img).toContain('width="1177"');
    expect(img).toContain('height="593"');
    expect(img).toContain('loading="lazy"');
    const alt = /alt="([^"]*)"/.exec(img)?.[1] ?? '';
    expect(alt).toMatch(/[А-Яа-яЁё]/);
    expect(alt).toContain('страницы 1');
    expect(markup).toContain('Размер, пикс.: 1177 × 593.');
    expect(markup).toContain('data-portal-block-type="image"');
  });

  it('stands a sentence in for an image that failed to load, never a broken icon', () => {
    const markup = renderScreen(
      newClient(),
      createElement(CropFigureView, {
        src: '/bff/v1/x', widthPx: 10, heightPx: 20, alt: 'фрагмент', failed: true, onError: () => {},
      }),
    );
    expect(markup).not.toContain('<img');
    expect(markup).toContain('Изображение не удалось загрузить.');
    expect(markup).toContain('data-portal-crop="failed"');
  });

  it('marks the portal description with the words the plan fixes', () => {
    expect(DESCRIPTION_MARKER).toBe('описание портала — в анализе не используется');
    const markup = card(imageBlock());
    expect(markup).toContain(`>${DESCRIPTION_MARKER}<`);
    expect(markup).toContain('data-portal-description');
    expect(visibleText(markup)).toContain(`${DESCRIPTION_MARKER} План первого этажа с осями А–Г и 1–4.`);
  });

  it('says the crop is not cut on a mismatch page, visibly, and asks for no image', () => {
    const block = omit(imageBlock({ geometry: 'geometry_mismatch' }), 'crop');
    const markup = card(block);
    expect(GEOMETRY_MISMATCH_LABEL).toBe('страница не совпала с PDF — фрагмент не вырезан');
    expect(markup).toContain(`>${GEOMETRY_MISMATCH_LABEL}<`);
    expect(markup).toContain('data-portal-geometry="geometry_mismatch"');
    expect(markup).not.toContain('<img');
    expect(markup).toContain('Фрагмент не вырезан: страница портала не совпала со страницей PDF.');
  });

  it('prints no mismatch sentence for a page that agreed', () => {
    const markup = card(imageBlock());
    expect(markup).toContain('data-portal-geometry="ok"');
    expect(markup).not.toContain(GEOMETRY_MISMATCH_LABEL);
  });
});

describe('a STAMP block shows its type and nothing the wire does not carry', () => {
  it('has no ordinal, no text, no crop and no description', () => {
    const markup = card(stampBlock());
    expect(markup).toContain('>Штамп<');
    expect(markup).toContain('data-portal-block-type="stamp"');
    expect(markup).not.toContain('порядок у портала');
    expect(markup).not.toContain('<pre');
    expect(markup).not.toContain('<img');
    expect(markup).not.toContain(DESCRIPTION_MARKER);
  });
});

describe('the portal status, the ordinal and the polygon are said as the response carries them', () => {
  it('names the two statuses the portal sends, and an unknown one neutrally', () => {
    expect(visibleText(card(textBlock()))).toContain('распознан порталом');
    expect(visibleText(card(textBlock({ status: 'failed' })))).toContain('сбой распознавания портала');
    const unknown = card(textBlock({ status: UNKNOWN_STATUS_TOKEN }));
    expect(visibleText(unknown)).toContain(UNKNOWN_PORTAL_STATUS.label);
    expect(visibleText(unknown)).not.toContain(UNKNOWN_STATUS_TOKEN);
    expect(unknown).toContain(`data-portal-status="${UNKNOWN_STATUS_TOKEN}"`);
  });

  it('prints the ordinal and the number of vertices, and computes nothing else', () => {
    const markup = card(imageBlock({ ordinal: 7, polygon_points: [[0, 0], [1, 0], [1, 1]] }));
    expect(visibleText(markup)).toContain('порядок у портала: 7');
    expect(visibleText(markup)).toContain('вершин в контуре: 3');
    expect(markup).not.toContain('<svg');
    expect(markup).not.toContain('<polygon');
  });
});

describe('the list groups blocks under their PDF page, in the API order', () => {
  it('opens one section per page, names a differing portal label, and keeps the order', () => {
    const blocks = everyKindOfBlock();
    const markup = list(blocks);
    expect(count(markup, 'data-portal-page=')).toBe(3);
    expect(visibleText(markup)).toContain('Страница 1 ');
    expect(visibleText(markup)).toContain('Страница 2 (у портала — 5)');
    expect(visibleText(markup)).not.toContain('Страница 1 (у портала');
    const ids = [...markup.matchAll(/data-portal-block-type="([a-z]+)"/g)].map((m) => m[1]);
    expect(ids).toEqual(blocks.map((block) => block.block_type));
  });

  it('prints the version block count the API reports beside the count loaded', () => {
    const blocks = everyKindOfBlock();
    const markup = list(blocks, { blockCount: 129, hasMore: true });
    expect(visibleText(markup)).toContain(`Блоков в комплекте: 129. Показано: ${blocks.length}.`);
    expect(markup).toContain('>Показать ещё<');
    expect(markup).toContain(`>${BLOCKS_RUN_ID}<`);
  });

  it('offers no «Показать ещё» once the API reports no next page', () => {
    expect(list(everyKindOfBlock())).not.toContain('Показать ещё');
  });

  it('puts no English word and no machine token on the screen for any value it shows', () => {
    const visible = visibleText(list(everyKindOfBlock(), { hasMore: true }));
    const latin = (visible.match(/[A-Za-z_]{2,}/g) ?? []).filter((word) => word !== 'PDF');
    expect(latin).toEqual([]);
    for (const token of ['text', 'image', 'stamp', 'recognized', 'failed', 'geometry_mismatch', UNKNOWN_STATUS_TOKEN, UNKNOWN_FLAG_TOKEN, ...KNOWN_FLAGS]) {
      expect(visible).not.toContain(token);
    }
  });
});
