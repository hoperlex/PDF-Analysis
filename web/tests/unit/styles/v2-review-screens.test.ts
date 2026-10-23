/**
 * The contrast census reaches the v2 review markup (`WEB-REVIEW-FOLLOWUPS-01`, item 6).
 *
 * A screen added to `screens.ts` that renders a spinner, or a state it was not meant to,
 * would make every census assertion about it vacuous (`D-88`). So this file asks the screens
 * themselves: each v2 screen is in the set, is named once, and its markup holds the element
 * it was added to bring into the census. The census itself (`contrast.test.ts`) judges the
 * colour; this file only proves it was shown the thing.
 */

import { describe, expect, it } from 'vitest';

import { SEVERITY_VALUES } from '@/shared/api';

import { screens } from './screens';

const rendered = screens();

function markupOf(name: string): string {
  const matches = rendered.filter((screen) => screen.name === name);
  expect(matches, `the census holds exactly one screen named «${name}»`).toHaveLength(1);
  return matches[0]?.markup ?? '';
}

describe('the census holds a review screen with a v2 finding in it', () => {
  const markup = markupOf('ReviewPage loaded, v2 finding');

  it('is the loaded screen, not a spinner', () => {
    expect(markup).toContain('class="am-review__finding"');
    expect(markup).toContain('Ширина выхода указана как 0,7 м.');
  });

  it('shows the severity select with the model’s proposal beside it', () => {
    expect(markup).toContain('data-severity-control="accept"');
    expect(markup).toContain('data-proposed-severity="critical"');
    expect(markup).toContain('<select');
  });

  it('shows the decided severity in the panel and in the finding row', () => {
    expect((markup.match(/data-decided-severity="economic"/g) ?? []).length).toBeGreaterThanOrEqual(2);
  });

  it('shows the basis: the values, two norm citations and the merged observations', () => {
    expect(markup).toContain('data-finding-values');
    expect(markup).toContain('data-norm-citations="2"');
    expect(markup).toContain('data-merged-observations="2"');
  });

  it('shows a history whose accept carries a severity', () => {
    expect(markup).toContain('am-history__event');
    expect(markup).toMatch(/am-history__verdict[^>]*>[^<]*<\/span><span data-decided-severity="economic">/);
  });
});

describe('the census holds the panel with its severity refusal', () => {
  it('renders the refusal sentence and the proposal', () => {
    const markup = markupOf('DecisionPanel, v2 finding, severity refused');
    expect(markup).toContain('data-severity-refusal="severity_required"');
    expect(markup).toContain('data-proposed-severity="critical"');
  });
});

describe('the census holds the history and the knowledge base with a decided severity', () => {
  it('shows every one of the five severities in the history', () => {
    const markup = markupOf('DecisionHistory with severities');
    for (const severity of SEVERITY_VALUES) {
      expect(markup, severity).toContain(`data-severity="${severity}"`);
    }
  });

  it('shows a severity badge on the knowledge-base rows that carry one', () => {
    const markup = markupOf('KnowledgeBase with severities');
    expect(markup.match(/data-decided-severity=/g) ?? []).toHaveLength(4);
  });
});
