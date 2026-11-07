/**
 * `UI-B-09`: the block strip of the sheet a proposal names, behind a press.
 *
 * What is held: a closed strip is one button and asks for nothing (the cache stays empty), so a pass of many proposals adds no
 * request to its first render; the open strip reads the pass's version and shows the portal blocks narrowed to the proposal's
 * page; the card puts the strip across its full width under the row; a proposal that names no page has no strip.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { ProjectUid, VersionUid } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { portalBlocksQueryOptions } from '@/entities/block';
import {
  ProposalCard, ProposalListView, ProposalSheetBlocks, ProposalSheetBlocksBody, namedPage,
} from '@/widgets/optimisation-proposals';

import { BLOCKS_PROJECT_UID, BLOCKS_VERSION_UID, blocksVersion, everyKindOfBlock, portalPage } from '../blocks/fixtures';
import { newClient, renderScreen, seedError } from '../screens/harness';
import { pass, proposal, proposalPage } from './fixtures';

const PROJECT = BLOCKS_PROJECT_UID as ProjectUid;
const VERSION = BLOCKS_VERSION_UID as VersionUid;

describe('the strip behind its press', () => {
  it('is one closed button, and reads nothing until it is pressed', () => {
    const client = newClient();
    const markup = renderScreen(client, createElement(ProposalSheetBlocks, { projectUid: PROJECT, versionUid: VERSION, page: 2 }));
    expect(markup).toContain('data-proposal-sheet-blocks="2"');
    expect(markup).toMatch(/<button[^>]*aria-expanded="false"[^>]*>Блоки листа<\/button>/);
    expect(markup).not.toContain('data-portal-blocks-loaded');
    expect(client.getQueryCache().getAll()).toHaveLength(0);
  });

  it('shows the version’s blocks narrowed to the proposal’s page once open', () => {
    const client = newClient();
    client.setQueryData(queryKeys.versions.detail(VERSION), blocksVersion(true));
    client.setQueryData(portalBlocksQueryOptions(VERSION).queryKey, { pages: [portalPage(everyKindOfBlock())], pageParams: [undefined] });
    const markup = renderScreen(client, createElement(ProposalSheetBlocksBody, { projectUid: PROJECT, versionUid: VERSION, page: 2 }));
    expect(markup).toContain('data-portal-blocks-loaded=');
    // Page 2 of the fixture holds two blocks; page 1 is not drawn.
    expect(markup.split('data-portal-page=').length - 1).toBe(1);
    expect(markup).toContain('data-portal-page="2"');
  });

  it('names the refusal, and offers no strip, when the version could not be read', () => {
    const client = newClient();
    seedError(client, queryKeys.versions.detail(VERSION), new Error('refused'));
    const markup = renderScreen(client, createElement(ProposalSheetBlocksBody, { projectUid: PROJECT, versionUid: VERSION, page: 2 }));
    expect(markup).toContain('Версия не прочитана: блоков листа нет');
    expect(markup).not.toContain('data-portal-blocks-loaded');
  });

  it('says it while the version is on its way', () => {
    expect(renderScreen(newClient(), createElement(ProposalSheetBlocksBody, { projectUid: PROJECT, versionUid: VERSION, page: 2 })))
      .toContain('блоки листа');
  });
});

describe('the strip on the card', () => {
  const strip = createElement(ProposalSheetBlocks, { projectUid: PROJECT, versionUid: VERSION, page: 2 });

  it('is drawn inside the card after the verdict column when the container passes it', () => {
    const markup = renderScreen(newClient(), createElement(ProposalCard, { proposal: proposal(), controls: null, history: null, blocks: strip }));
    expect(markup).toContain('data-proposal-sheet-blocks="2"');
    expect(markup.indexOf('data-proposal-sheet-blocks')).toBeGreaterThan(markup.indexOf('Решение:'));
  });

  it('is not drawn by a card whose container passes none', () => {
    const markup = renderScreen(newClient(), createElement(ProposalCard, { proposal: proposal(), controls: null, history: null }));
    expect(markup).not.toContain('data-proposal-sheet-blocks');
  });

  it('is asked for per proposal by the list, and a proposal with no page gets none', () => {
    const named = proposal();
    const nameless = proposal({ optimisation_proposal_id: 'opr_01J9ZQ8K7NHVXW3T2R5M6P4Q8Z', page_number: 0 });
    expect(namedPage(named)).toBe(2);
    expect(namedPage(nameless)).toBeNull();
    const page = proposalPage({ optimisation_pass: pass(), items: [named, nameless] });
    const markup = renderScreen(newClient(), createElement(ProposalListView, {
      page, canDecide: false, onDecision: () => {}, onPage: null,
      blocksFor: (item) => (namedPage(item) === null ? null : strip),
    }));
    expect(markup.split('data-proposal-sheet-blocks=').length - 1).toBe(1);
  });
});
