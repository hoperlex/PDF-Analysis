'use client';

import { useMemo, useState } from 'react';
import styles from './extended-review.module.css';

/** Conservative text-only Markdown projection: no HTML execution or supplied links. */
export function ReadableReport({ markdown }: { readonly markdown: string }) {
  const [open, setOpen] = useState(false);
  const [limit, setLimit] = useState(100);
  const blocks = useMemo(() => {
    const result: { kind: 'heading' | 'paragraph' | 'list' | 'code'; lines: string[] }[] = [];
    if (!open) return result;
    let fenced = false;
    for (const line of markdown.split(/\r?\n/)) {
    if (/^\s*```/.test(line)) { fenced = !fenced; if (fenced) result.push({ kind: 'code', lines: [] }); continue; }
    if (fenced) { result[result.length - 1]?.lines.push(line); continue; }
    if (!line.trim()) { if (result[result.length - 1]?.kind === 'paragraph') result.push({ kind: 'paragraph', lines: [] }); continue; }
    const heading = /^\s*#{1,6}\s+(.+)$/.exec(line);
    if (heading?.[1]) { result.push({ kind: 'heading', lines: [heading[1]] }); continue; }
    const list = /^\s*(?:[-*]|\d+[.)])\s+(.+)$/.exec(line);
    if (list?.[1]) { if (result[result.length - 1]?.kind !== 'list') result.push({ kind: 'list', lines: [] }); result[result.length - 1]?.lines.push(list[1]); continue; }
    if (result[result.length - 1]?.kind !== 'paragraph') result.push({ kind: 'paragraph', lines: [] });
    result[result.length - 1]?.lines.push(line);
    }
    return result.filter((block) => block.lines.length > 0);
  }, [markdown, open]);
  return <details onToggle={(event) => setOpen(event.currentTarget.open)}><summary>Читать текст сохранённого отчёта</summary>{open ? <div className={styles.readableReport}>{blocks.slice(0, limit).map((block, index) => block.kind === 'heading' ? <h4 key={index}>{block.lines.join(' ')}</h4>
    : block.kind === 'list' ? <ul key={index}>{block.lines.map((line, number) => <li key={number}>{line}</li>)}</ul>
      : block.kind === 'code' ? <pre key={index}>{block.lines.join('\n')}</pre> : block.lines.length ? <p key={index}>{block.lines.join('\n')}</p> : null)}{blocks.length > limit ? <><p>Показано {limit} частей из {blocks.length}. Полный текст сохранён в выгрузках.</p><button type="button" className="am-button am-button--quiet" onClick={() => setLimit((value) => value + 100)}>Показать следующие 100 частей</button></> : null}</div> : null}</details>;
}
