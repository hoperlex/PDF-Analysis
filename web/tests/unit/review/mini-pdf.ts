/**
 * A tiny PDF writer for the tests that need pdf.js to read a REAL page.
 *
 * Built in code rather than committed as a binary: the bytes are a pure function of the
 * arguments, a reader can see what is on each page, and no fixture can drift from the test
 * that depends on it. One standard Helvetica font, no embedded font program (the text layer
 * does not need one), no compression, a correct cross-reference table.
 *
 * Text is ASCII on purpose. Cyrillic needs an embedded font with a `ToUnicode` map, which is
 * most of a PDF writer; the Cyrillic and combining-mark cases are covered where the text
 * items are written by hand (`locate-quotation.test.ts`).
 */

export interface MiniPage {
  readonly width: number;
  readonly height: number;
  /** `/Rotate`, a multiple of 90. */
  readonly rotate?: 0 | 90 | 180 | 270;
  /** Raw content-stream operators. Use `text()` for the common case. */
  readonly content: string;
}

/** One `BT ... ET` block: `size`-point Helvetica with its origin at `(x, y)` in user space. */
export function text(x: number, y: number, size: number, ...runs: string[]): string {
  const shown = runs.map((run) => `(${run.replaceAll('\\', '\\\\').replaceAll('(', '\\(').replaceAll(')', '\\)')}) Tj`);
  return `BT /F1 ${size} Tf ${x} ${y} Td ${shown.join(' ')} ET`;
}

export function buildPdf(pages: readonly MiniPage[]): Uint8Array {
  const objects: string[] = [];
  const add = (body: string): number => objects.push(body);

  const font = add('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>');
  // Page objects come after their content streams; the Pages node is numbered first so the
  // pages can name it as their parent.
  const pagesId = font + 2 * pages.length + 1;
  const kids: number[] = [];
  for (const page of pages) {
    const content = add(
      `<< /Length ${page.content.length} >>\nstream\n${page.content}\nendstream`,
    );
    const rotate = page.rotate === undefined ? '' : ` /Rotate ${page.rotate}`;
    kids.push(
      add(
        `<< /Type /Page /Parent ${pagesId} 0 R /MediaBox [0 0 ${page.width} ${page.height}]${rotate} ` +
          `/Resources << /Font << /F1 ${font} 0 R >> >> /Contents ${content} 0 R >>`,
      ),
    );
  }
  const pagesNode = add(
    `<< /Type /Pages /Kids [${kids.map((id) => `${id} 0 R`).join(' ')}] /Count ${kids.length} >>`,
  );
  if (pagesNode !== pagesId) throw new Error('mini-pdf: page tree numbering is inconsistent');
  const catalog = add(`<< /Type /Catalog /Pages ${pagesNode} 0 R >>`);

  // Content is ASCII, so string length is byte length and offsets can be counted on the string.
  let out = '%PDF-1.4\n';
  const offsets: number[] = [];
  objects.forEach((body, index) => {
    offsets.push(out.length);
    out += `${index + 1} 0 obj\n${body}\nendobj\n`;
  });
  const xref = out.length;
  out += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (const offset of offsets) out += `${String(offset).padStart(10, '0')} 00000 n \n`;
  out += `trailer\n<< /Size ${objects.length + 1} /Root ${catalog} 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return new TextEncoder().encode(out);
}
