/**
 * The dot that marks a section (`UIP-G-17`): a circle in the section's colour and nothing else.
 *
 * It is drawn beside the section's code or its name and never alone, so the colour is not the only thing that
 * says which section it is; for that reason it is hidden from assistive technology. It reads the colour from
 * the shared list (`sectionColourStyle`), so the menu, a section's heading, the sections table and the work
 * schedule show one colour for one section. `null` is a document without a confirmed section and draws the
 * neutral dot. No hooks and no state: a server page may render it.
 */

import type { ProjectSectionCode } from '../model/section';
import { sectionColourStyle } from '../model/section-colour';
import styles from './section-dot.module.css';

export interface SectionDotProps {
  /** The section, or `null` for «Без раздела». */
  readonly code: ProjectSectionCode | null;
}

export function SectionDot({ code }: SectionDotProps) {
  return (
    <span
      className={styles.dot}
      style={sectionColourStyle(code)}
      data-section-dot={code ?? 'none'}
      aria-hidden="true"
    />
  );
}
