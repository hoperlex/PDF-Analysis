/**
 * The project screen's section structure, and the one sentence it must not get wrong.
 *
 * `D-56` asks the interface to carry legacy's fourteen sections while the analysis reads
 * one — `R-18`'s stub rule applied to structure. Structure is cheap to render and easy to
 * render dishonestly, and the dishonest version is specific: **a document's section is
 * checked nowhere in this system.** The upload envelope checks the media type, the byte
 * size, the page count and the text layer; the `AR` restriction lives in the analysis
 * prompt and in fixture names. So the screen may state a *rule of intake* and may never
 * state a *property of a file*, and the list under the open section is the project's whole
 * document list rather than a list filtered by anything.
 *
 * These cases assert that distinction as text on the screen, because it is the only place
 * it exists: no type, no schema and no query can carry it.
 *
 * What one static render pass can see is the *resting* state — `tests/unit/screens/
 * harness.ts` states that it cannot fire a handler. So the open section is reached by
 * rendering the widget at that section rather than by clicking a tab, and what the click
 * itself does is left to the browser journey. Both branches are rendered here, which is
 * what the page alone could not offer.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { AppRouterContext } from 'next/dist/shared/lib/app-router-context.shared-runtime';
import type { AppRouterInstance } from 'next/dist/shared/lib/app-router-context.shared-runtime';

import { PROJECT_SECTIONS } from '@/entities/project';
import { ProjectDetailPage } from '@/_pages/project-detail';
import { ProjectSections } from '@/widgets/project-sections';

import { PROJECT_UID, render } from '../review/fixtures';
import { newClient, renderWith } from './harness';

/** A router that records instead of navigating. Nothing in one render pass calls it. */
function stubRouter(): AppRouterInstance {
  return {
    push: () => {},
    replace: () => {},
    back: () => {},
    forward: () => {},
    refresh: () => {},
    prefetch: () => {},
  } as unknown as AppRouterInstance;
}

function screen(): string {
  return renderWith(
    newClient(),
    createElement(
      AppRouterContext.Provider,
      { value: stubRouter() },
      createElement(ProjectDetailPage, { projectUid: PROJECT_UID }),
    ),
  );
}

/** The widget alone, opened at one section, with a stand-in for the documents. */
function sections(code: string | undefined): string {
  return render(
    createElement(ProjectSections, {
      route: `/projects/${PROJECT_UID}`,
      ...(code === undefined ? {} : { initialSection: code as never }),
      children: 'документы проекта',
    }),
  );
}

describe('the project screen carries the whole section structure', () => {
  it('offers every section legacy has, by its Russian name', () => {
    const markup = screen();
    for (const section of PROJECT_SECTIONS) {
      expect(markup, `${section.code} is missing from the screen`).toContain(section.name);
      expect(markup).toContain(section.abbr);
    }
  });

  it('addresses each one by its machine code, which stays out of the prose', () => {
    const markup = screen();
    for (const section of PROJECT_SECTIONS) {
      expect(markup).toContain(`data-section="${section.code}"`);
    }
    // The count is read off the markup rather than trusted: a registry that lost a row
    // would still satisfy the loop above.
    const marked = markup.match(/data-section="/g) ?? [];
    expect(marked.length).toBe(PROJECT_SECTIONS.length);
  });

  it('marks the open one, so a reviewer can see where they are', () => {
    const markup = screen();
    expect(markup).toContain('aria-current="true"');
    expect((markup.match(/aria-current="true"/g) ?? []).length).toBe(1);
    expect(markup).toContain('data-open-section="AR"');
  });
});

describe('a fresh tab opens on the section the analysis is built for', () => {
  it('renders the project’s documents and the upload without a click', () => {
    const markup = screen();
    // `D-16`'s property, unchanged by the sections: the documents are asked for on mount
    // and the upload is on the screen a pasted URL renders.
    expect(markup).toContain('Документы');
    expect(markup).toContain('id="upload-file"');
    expect(markup).toContain('Что принимается');
    expect(markup).toContain('data-section-panel="AR"');
  });

  it('does not render the not-available stub over the analysed section', () => {
    expect(screen()).not.toContain('Раздел пока недоступен');
  });
});

describe('the screen states a rule of intake and never a property of a file', () => {
  it('says what is accepted today', () => {
    const markup = screen();
    expect(markup).toContain('Сейчас принимаются документы раздела АР');
  });

  it('says that a document’s section is stored nowhere and checked nowhere', () => {
    const markup = screen();
    expect(markup).toContain('не проверяется');
    expect(markup).toContain('нигде не сохраняется');
    expect(markup).toContain('ни один список здесь не отобран по разделу');
  });

  it('never claims a document belongs to a section', () => {
    const markup = screen();
    // The claim this screen must not make, in the forms it would take. Each is a sentence
    // the software cannot confirm: nothing in this repository reads a document's section.
    for (const claim of [
      'относится к разделу',
      'документы раздела АР:</',
      'раздел документа: ',
      'определён раздел',
      'документ раздела АР —',
    ]) {
      expect(markup, `the screen asserts membership: ${claim}`).not.toContain(claim);
    }
  });
});

describe('a section without analysis says so, and offers nothing it cannot do', () => {
  it('renders the shared stub rather than a list or a form', () => {
    const markup = sections('KJ');
    expect(markup).toContain('Раздел пока недоступен');
    expect(markup).toContain('Конструкции железобетонные (КЖ)');
    expect(markup).toContain('Этот раздел ещё не готов.');
    expect(markup).toContain('data-open-section="KJ"');
  });

  it('offers no upload and no document list from a section nothing reads', () => {
    const markup = sections('KJ');
    expect(markup).not.toContain('id="upload-file"');
    expect(markup).not.toContain('документы проекта');
    expect(markup).not.toContain('data-section-panel=');
  });

  it('points at the section that is accepted, so the stub is not a dead end', () => {
    expect(sections('POS')).toContain('сейчас принимаются документы раздела АР');
  });

  it('carries the screen’s own route on the stub, for whoever reads the DOM', () => {
    expect(sections('GP')).toContain(`data-route="/projects/${PROJECT_UID}"`);
  });

  it('opens on the analysed section when no section is named', () => {
    const markup = sections(undefined);
    expect(markup).toContain('data-open-section="AR"');
    expect(markup).toContain('документы проекта');
  });
});
