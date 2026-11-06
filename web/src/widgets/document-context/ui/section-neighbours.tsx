'use client';

/**
 * `UI-A-28`: «‹ Предыдущий · N из M · Следующий ›» between the documents of one section, as the original moves
 * between the projects of a section, in our nouns.
 *
 * **Where the numbers come from.** The document's current version carries its expert-confirmed section
 * (`classification.section_code`); the neighbours are the section's own listing (`listDocuments` with
 * `section_code`, contract 1.20.0) in the order the section page shows (`order=audit`, `UI-A-49`), followed page
 * after page to the end of the cursor (`useSectionDocumentWalk`). N is the document's place in that listing and M
 * its length; the links go to the neighbours' own pages.
 *
 * **When it says nothing.** No confirmed section, a section of one document, a document the section's listing does
 * not hold (an archived one), a listing still loading and a listing that failed all draw nothing: a position from
 * part of the listing would be a wrong N or M, and the page does not wait on it.
 */

import Link from 'next/link';

import type { ProjectUid } from '@/shared/api';
import { routes } from '@/shared/lib';
import type { SectionPosition } from '@/entities/document-version';
import { documentCardTitle, sectionPosition, useSectionDocumentWalk } from '@/entities/document-version';
import type { ProjectSection } from '@/entities/project';
import { findProjectSection } from '@/entities/project';

import styles from './document-context.module.css';

export const PREVIOUS_DOCUMENT_LABEL = '‹ Предыдущий';
export const NEXT_DOCUMENT_LABEL = 'Следующий ›';

export interface SectionNeighboursProps {
  readonly projectUid: string;
  readonly documentUid: string;
  /** The section the document's current version is confirmed for; absent while it is not. */
  readonly sectionCode?: string | undefined;
}

export interface SectionNeighboursViewProps {
  readonly projectUid: string;
  readonly section: ProjectSection;
  readonly place: SectionPosition;
}

/** The strip itself, from a position already known. Pure, so the markup is tested without a query client. */
export function SectionNeighboursView({ projectUid, section, place }: SectionNeighboursViewProps) {
  const link = (version: SectionPosition['previous'], label: string, rel: 'prev' | 'next') =>
    version === null ? (
      <span className={styles.neighbourOff} data-neighbour={rel} data-neighbour-end="">{label}</span>
    ) : (
      <Link href={routes.document(projectUid, version.document_uid)} rel={rel} title={documentCardTitle(version)} data-neighbour={rel}>
        {label}
      </Link>
    );
  return (
    <nav
      className={styles.neighbours}
      aria-label={`Документы раздела ${section.abbr}`}
      data-section-neighbours={section.code}
      data-neighbour-position={place.position}
      data-neighbour-total={place.total}
    >
      {link(place.previous, PREVIOUS_DOCUMENT_LABEL, 'prev')}{' '}
      <span className={styles.neighbourSeparator} aria-hidden="true">·</span>{' '}
      <span className={styles.neighbourPosition}>{place.position} из {place.total}</span>{' '}
      <span className={styles.neighbourSeparator} aria-hidden="true">·</span>{' '}
      {link(place.next, NEXT_DOCUMENT_LABEL, 'next')}
    </nav>
  );
}

function SectionNeighboursWalk({ projectUid, documentUid, section }: {
  readonly projectUid: string;
  readonly documentUid: string;
  readonly section: ProjectSection;
}) {
  const walk = useSectionDocumentWalk(projectUid as ProjectUid, section.code);
  if (walk.status !== 'complete') return null;
  const place = sectionPosition(walk.items, documentUid);
  if (place === null || place.total < 2) return null;
  return <SectionNeighboursView projectUid={projectUid} section={section} place={place} />;
}

export function SectionNeighbours({ projectUid, documentUid, sectionCode }: SectionNeighboursProps) {
  const section = sectionCode === undefined ? null : findProjectSection(sectionCode);
  if (section === null) return null;
  // Keyed, so another section (or project) is another walk and never inherits this one's cursors.
  return <SectionNeighboursWalk key={`${projectUid}:${section.code}`} projectUid={projectUid} documentUid={documentUid} section={section} />;
}
