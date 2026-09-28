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
 * **The one sentence this widget exists to get right.** A document's section is stored
 * and checked on the server when an upload names one — this product's own upload form does
 * not offer that field, so every document it accepts arrives without one
 * (`entities/project/model/section.ts`). The `AR` restriction lives in the analysis
 * prompt, not in intake: the analysis is built for the text of `AR` documents and is
 * applied to whatever is uploaded, whichever section the server stores it under. So this
 * screen states a rule about the analysis, never a rule of intake and never a property of
 * a file — "this document belongs to АР" is a claim no code here makes, and the list below
 * is the project's whole document list, not one filtered by section. Both facts are on the
 * screen (`docs/program/reviews/W46-JUDGE-Y.md` §2, `Y2-a`).
 *
 * **What it does not do.** No counts and no totals per section here.
 * `getDashboardSummary` now counts published documents per section, server-side
 * (`/dashboard`'s own sections panel) — but that is a different read this widget does not
 * make, and inventing a count here from this widget's own document list would be a number
 * this screen never asked the server for.
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
        Разделы — это навигация. Раздел документа хранится и проверяется на сервере, когда его
        называют при загрузке; форма загрузки этого продукта раздел не предлагает, поэтому ни
        один список здесь не отобран по разделу.
      </p>

      {open.analysed ? (
        <section className="am-section" data-section-panel={open.code}>
          <h2>{projectSectionTitle(open)}</h2>
          <div className="am-state" role="note">
            <p className="am-state__title">Что сейчас принимается</p>
            <div className="am-state__detail">
              <p>
                Анализ построен для текста раздела {ANALYSED_ABBR} — это единственный профиль
                анализа, который есть у продукта, и он применяется к любому загруженному
                документу вне зависимости от того, под каким разделом сервер его хранит. Раздел
                документа сервер хранит и проверяет, когда его называют при загрузке, но форма
                загрузки этого продукта его не предлагает, поэтому документ, отправленный через
                неё, остаётся без раздела.
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
          promise={`Отдельного анализа для этого раздела нет: анализ построен только для текста раздела ${ANALYSED_ABBR} и применяется к любому загруженному документу вне зависимости от того, под каким разделом он сохранён. Раздел появится в одной из следующих версий как самостоятельный экран, и ничего из уже загруженного при этом не теряется.`}
        />
      )}
    </div>
  );
}
