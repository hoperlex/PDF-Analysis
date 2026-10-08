/**
 * The project screen's section structure, and the one sentence it must not get wrong.
 *
 * `D-56` asks the interface to carry legacy's fourteen sections while the analysis reads
 * one — `R-18`'s stub rule applied to structure. Structure is cheap to render and easy to
 * render dishonestly, and the dishonest version is specific.
 *
 * **`W46-CLIENT`, `Y2-a`.** The screen used to call the restriction a *rule of intake* —
 * *"documents of section АР are what is accepted today"* — which reads as the server
 * refusing anything else. It measurably does not: a document the server stores under
 * another section is analysed by the same profile
 * (`docs/program/reviews/W46-JUDGE-Y.md` §2). The restriction lives in the analysis
 * prompt, not in intake, and predates this wave (`entities/project/model/section.ts`).
 * What the screen may state instead is a *rule about the analysis* — it is built for the
 * text of АР documents and is applied to whatever is uploaded, whichever section it is
 * stored under — and it may never state a *property of a file*: "this document belongs to
 * АР" is a claim no code here makes, and the list under the open section is the project's
 * whole document list rather than a list filtered by anything.
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

import { PROJECT_SECTIONS } from '@/entities/project';
import { ProjectDetailPage } from '@/_pages/project-detail';
import { ProjectSections } from '@/widgets/project-sections';

import { PROJECT_UID, render } from '../review/fixtures';
import { newClient, renderScreen } from './harness';

function screen(): string {
  return renderScreen(newClient(), createElement(ProjectDetailPage, { projectUid: PROJECT_UID }));
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

describe('the screen states a rule about the analysis and never a rule of intake', () => {
  it('says the analysis is built for one section’s text, not that intake refuses the rest', () => {
    // `W46-CLIENT`, `Y2-a`: a document the server stores under another section is
    // analysed by the same profile, so the old pin -- "Сейчас принимаются документы
    // раздела АР" -- read as an intake rule the server does not enforce. What the screen
    // says now is a fact about the analysis alone.
    const markup = screen();
    expect(markup).toContain('Анализ построен для текста раздела АР');
    expect(markup).toContain('применяется к любому загруженному документу');
  });

  it('says that a document’s section is stored and checked when an upload names one, and the product’s form does not offer that field', () => {
    // `F-3`, `W46-WIRE`: `W46-SEAL`'s reseal made the sentence this case used to pin
    // false -- the section IS stored (`document.section`, migration `0011`) and IS
    // checked (the upload refuses a malformed one with `422`). What stayed true is that
    // this product's own upload form offers a file and a title and nothing else, so no
    // document reaches this deployment through the product with a section attached, and
    // the document list below is still not filtered by section.
    const markup = screen();
    expect(markup).toContain('хранится и проверяется на сервере');
    expect(markup).toContain('форма загрузки этого продукта раздел не предлагает');
    expect(markup).toContain('ни один список здесь не отобран по разделу');
  });

  it('never says an upload leaves the section unchecked', () => {
    // W46-JUDGE-Z (Z-4): an upload naming `section=ZZ` is refused with 422 on `section`, so a
    // sentence saying intake checks the file's envelope "and not the section" is false.
    const markup = screen();
    expect(markup).not.toContain('проверяется конверт файла, а не раздел');
    expect(markup).not.toContain('раздел не проверяется');
  });

  it('never claims a document belongs to a section, and never says intake refuses another one', () => {
    const markup = screen();
    // The claim this screen must not make, in the forms it would take. Each is a sentence
    // the software cannot confirm: nothing in this repository reads a document's section
    // to decide whether to accept or to analyse it.
    for (const claim of [
      'относится к разделу',
      'документы раздела АР:</',
      'раздел документа: ',
      'определён раздел',
      'документ раздела АР —',
      'правило приёма',
      'принимаются документы раздела',
    ]) {
      expect(markup, `the screen asserts membership or an intake rule: ${claim}`).not.toContain(
        claim,
      );
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

  it('points at the section the analysis is built for, so the stub is not a dead end', () => {
    const markup = sections('POS');
    expect(markup).toContain('Отдельного анализа для этого раздела нет');
    expect(markup).toContain('анализ построен только для текста раздела АР');
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
