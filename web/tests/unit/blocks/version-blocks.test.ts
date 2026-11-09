/**
 * «Блоки» as a tab of the version (`R-151m`).
 *
 * `/projects/[project_uid]/versions/[version_uid]/blocks` opens the block screen with the version taken from the
 * address: the tabs show at once, the context strip ends in «Блоки», and the screen refuses a malformed identifier,
 * a version of another project and a comparison-only version in words, never with an empty tab.
 */

import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { DocumentVersion } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { portalBlocksQueryOptions } from '@/entities/block';
import { BlocksPage, addressWithPage } from '@/_pages/blocks';

import { newClient, renderScreen, renderWith } from '../screens/harness';
import { BLOCKS_PROJECT_UID, BLOCKS_VERSION_UID, blocksVersion, everyKindOfBlock, portalPage } from './fixtures';

// The address the page layer reads `?page=` from; outside the app router the hooks answer `null`.
const navigation = vi.hoisted(() => ({ search: '' }));

vi.mock('next/navigation', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  usePathname: () => null,
  useSearchParams: () => new URLSearchParams(navigation.search),
}));

beforeEach(() => {
  vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', '/bff/v1');
});
afterEach(() => {
  vi.unstubAllEnvs();
  navigation.search = '';
});

const OTHER_PROJECT = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8Z';

function withVersion(version: DocumentVersion) {
  const client = newClient();
  client.setQueryData(queryKeys.versions.detail(BLOCKS_VERSION_UID), version);
  return client;
}

const tab = (client: ReturnType<typeof newClient>, projectUid = BLOCKS_PROJECT_UID, versionUid = BLOCKS_VERSION_UID) =>
  // A routed page: its strip offers the document's versions through the router, so the app router is mounted.
  renderScreen(client, createElement(BlocksPage, { projectUid, versionUid }));

describe('the version’s «Блоки» tab', () => {
  it('shows the tabs at once for the version in the address, with no chooser', () => {
    const markup = tab(withVersion(blocksVersion(true)));
    expect(markup).toContain('role="tablist"');
    expect(markup).not.toContain('1. Версия');
    expect(markup).not.toContain('Выбрать проект');
  });

  it('ends the context strip in «Блоки» and links back to the version', () => {
    const markup = tab(withVersion(blocksVersion(true)));
    expect(markup).toContain('data-context-level="blocks"');
    expect(markup).toContain(`href="/projects/${BLOCKS_PROJECT_UID}/versions/${BLOCKS_VERSION_UID}"`);
    expect(markup).toMatch(/aria-current="page"[^>]*>Блоки</);
  });

  it('says a version of another project is from another project, and links to its own tab', () => {
    const markup = tab(withVersion(blocksVersion(true, { project_uid: OTHER_PROJECT })));
    expect(markup).toContain('Эта версия из другого проекта.');
    expect(markup).toContain(`href="/projects/${OTHER_PROJECT}/versions/${BLOCKS_VERSION_UID}/blocks"`);
    expect(markup).not.toContain('role="tablist"');
  });

  it('says a comparison-only version has no blocks instead of drawing empty tabs', () => {
    const markup = tab(withVersion(blocksVersion(false, { upload_kind: 'comparison_pdf' })));
    expect(markup).toContain('Блоков нет.');
    expect(markup).not.toContain('role="tablist"');
  });

  it('refuses a malformed identifier without a request', () => {
    const client = newClient();
    const markup = tab(client, BLOCKS_PROJECT_UID, 'это-не-идентификатор');
    expect(markup).toContain('Это не адрес версии.');
    expect(client.getQueryCache().getAll()).toHaveLength(0);
  });

  it('the chooser at /blocks offers the version’s own tab once a version is chosen', () => {
    // The chooser is the same page without an address; its first step is still the project.
    expect(renderWith(newClient(), createElement(BlocksPage, {}))).toContain('1. Версия');
  });
});

describe('the page chosen above the tiles lives in the address of the version’s tab', () => {
  function withBlocks() {
    const client = withVersion(blocksVersion(true));
    client.setQueryData(portalBlocksQueryOptions(BLOCKS_VERSION_UID).queryKey, {
      pages: [portalPage(everyKindOfBlock())],
      pageParams: [undefined],
    });
    return client;
  }
  const chip = (markup: string, page: string) =>
    markup.match(new RegExp(`<button\\b[^>]*data-page-chip="${page}"[^>]*>`))?.[0] ?? '';

  it('opens on the page ?page=N names, so a reload or a link keeps it', () => {
    navigation.search = 'page=2';
    const markup = tab(withBlocks());
    expect(markup.split('data-portal-page=').length - 1).toBe(1);
    expect(markup).toContain('data-portal-page="2"');
    expect(chip(markup, '2')).toContain('aria-pressed="true"');
    expect(chip(markup, 'all')).toContain('aria-pressed="false"');
  });

  it('opens on «Все блоки» for ?page=all, for no parameter and for a value that names no page', () => {
    for (const search of ['page=all', '', 'page=0', 'page=abc', 'page=9']) {
      navigation.search = search;
      const markup = tab(withBlocks());
      expect(markup.split('data-portal-page=').length - 1, search).toBe(3);
      expect(chip(markup, 'all'), search).toContain('aria-pressed="true"');
    }
  });

  it('writes the choice into the address and keeps the other parameters', () => {
    const path = `/projects/${BLOCKS_PROJECT_UID}/versions/${BLOCKS_VERSION_UID}/blocks`;
    expect(addressWithPage(path, '', 3)).toBe(`${path}?page=3`);
    expect(addressWithPage(path, '', 'all')).toBe(`${path}?page=all`);
    expect(addressWithPage(path, 'page=2&tab=x', 5)).toBe(`${path}?page=5&tab=x`);
    expect(addressWithPage(path, 'page=2', 'all')).toBe(`${path}?page=all`);
  });
});
