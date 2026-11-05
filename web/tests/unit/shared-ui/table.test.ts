/**
 * The shared table (`R-150f`), minimal version: native table, scoped column headers, an optional caption
 * and the current row marked.
 */
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { Table } from '@/shared/ui';

type Row = { readonly id: string; readonly name: string };

describe('Table', () => {
  const markup = renderToStaticMarkup(
    createElement(Table<Row>, {
      caption: 'Строки',
      columns: [
        { key: 'id', header: 'Код', cell: (row: Row) => row.id },
        { key: 'name', header: 'Имя', cell: (row: Row) => row.name },
      ],
      rows: [
        { id: 'a', name: 'Первая' },
        { id: 'b', name: 'Вторая' },
      ],
      rowKey: (row: Row) => row.id,
      currentKey: 'b',
    }),
  );

  it('renders a native table with scoped headers and the caption', () => {
    expect(markup).toContain('<table');
    expect(markup).toContain('<caption');
    expect(markup).toContain('Строки');
    expect(markup.match(/scope="col"/g)).toHaveLength(2);
  });

  it('renders every row and marks only the current one', () => {
    expect(markup).toContain('Первая');
    expect(markup).toContain('Вторая');
    expect(markup.match(/aria-current="true"/g)).toHaveLength(1);
    expect(markup).toMatch(/aria-current="true"[^>]*data-row-key="b"|data-row-key="b"[^>]*aria-current="true"/);
  });
});
