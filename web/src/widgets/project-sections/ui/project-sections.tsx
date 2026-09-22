'use client';

/**
 * The project's sections, as structure a reviewer can see and move through.
 *
 * **Why the structure exists before the analysis does.** `R-18`'s rule for this alpha is
 * that a part of the product that is not built is shown as an honest stub rather than
 * hidden, so a reviewer sees the shape of the thing being built. `D-56` applies that rule
 * to sections: legacy organises every piece of work by section and carries fourteen,
 * ours analyses one, and the answer is fourteen sections of which thirteen say so.
 *
 * **The one sentence this widget exists to get right.** A document's section is checked
 * nowhere in this system. The upload envelope checks the media type, the size, the page
 * count and the text layer; the `AR` restriction lives in the analysis prompt and in the
 * names of fixtures. So this screen states a **rule of intake** — *documents of section
 * АР are what is accepted today* — and never a property of a file. "This document belongs
 * to АР" is a claim no code here can confirm, and the list below is the project's whole
 * document list, not a list filtered by section. Both facts are on the screen.
 *
 * **What it does not do.** No counts and no totals per section. There is no section field
 * in the contract to count over, and inventing one in the interface would be a number the
 * server never sent — the same class of mistake as rendering an absent `document_count`
 * as `0`. That is the second half of `D-56` and it waits for a contract.
 *
 * **State, not address.** The open section lives in React state, not in the URL. Sections
 * are a structure inside one screen; the route tree, `tests/e2e/pc01/journey/manifest.json`
 * and the conformance guard describe the same six screens they did before, and the
 * analysed section is what a fresh tab opens on, so a pasted project URL still renders
 * the documents and the upload exactly as it did.
 */

import { useState } from 'react';
import type { ReactNode } from 'react';

import { RoutePlaceholder } from '@/shared/ui';
import {
  ANALYSED_SECTION_CODE,
  PROJECT_SECTIONS,
  findProjectSection,
  projectSectionTitle,
} from '@/entities/project';
import type { ProjectSectionCode } from '@/entities/project';

import styles from './project-sections.module.css';

export interface ProjectSectionsProps {
  /** The address of the screen these sections sit on, for the stub's `data-route`. */
  readonly route: string;
  /** The section open on arrival. The analysed one, unless a caller says otherwise. */
  readonly initialSection?: ProjectSectionCode | undefined;
  /** What the analysed section opens: this project's documents and the upload. */
  readonly children: ReactNode;
}

/** The mark of the section the analysis is built for, for use in a sentence. */
const ANALYSED_ABBR =
  findProjectSection(ANALYSED_SECTION_CODE)?.abbr ?? ANALYSED_SECTION_CODE;

export function ProjectSections({ route, initialSection, children }: ProjectSectionsProps) {
  const [openCode, setOpenCode] = useState<ProjectSectionCode>(
    initialSection ?? ANALYSED_SECTION_CODE,
  );

  const open = findProjectSection(openCode) ?? PROJECT_SECTIONS[0]!;

  return (
    <div data-open-section={open.code}>
      <h2>Разделы проекта</h2>
      <nav aria-label="Разделы проекта">
        <ul className={styles.tabs}>
          {PROJECT_SECTIONS.map((section) => (
            <li key={section.code}>
              <button
                type="button"
                className={
                  section.code === open.code
                    ? 'am-button am-button--small'
                    : 'am-button am-button--quiet am-button--small'
                }
                data-section={section.code}
                data-analysed={section.analysed ? 'true' : 'false'}
                aria-current={section.code === open.code ? 'true' : undefined}
                onClick={() => setOpenCode(section.code)}
              >
                <span className={styles.abbr}>{section.abbr}</span> {section.name}
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <p className={styles.rule} data-section-rule="intake">
        Разделы — это навигация. Раздел документа нигде не хранится и не проверяется, поэтому
        ни один список здесь не отобран по разделу.
      </p>

      {open.analysed ? (
        <section className="am-section" data-section-panel={open.code}>
          <h2>{projectSectionTitle(open)}</h2>
          <div className="am-state" role="note">
            <p className="am-state__title">Что сейчас принимается</p>
            <div className="am-state__detail">
              <p>
                Сейчас принимаются документы раздела {ANALYSED_ABBR}: анализ рассчитан на текст
                этого раздела. Это правило приёма, а не свойство файла — при загрузке
                проверяется только конверт, а принадлежность документа разделу не проверяется
                и нигде не сохраняется.
              </p>
              <p>Ниже — все документы проекта, в порядке, в котором их вернул сервер.</p>
            </div>
          </div>
          {children}
        </section>
      ) : (
        <RoutePlaceholder
          screen={projectSectionTitle(open)}
          route={route}
          promise={`Анализ этого раздела ещё не делается: сейчас принимаются документы раздела ${ANALYSED_ABBR}. Раздел появится в одной из следующих версий, и ничего из уже загруженного при этом не теряется.`}
        />
      )}
    </div>
  );
}
