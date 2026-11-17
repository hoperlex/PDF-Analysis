/**
 * The shared window (`UIP-G-04`): what it promises, shown on examples.
 *
 * The node test environment has no DOM, so the MARKUP is read off a server render and the BEHAVIOUR is
 * `attachModalDialog`, the function the client island calls, driven over a fake `<dialog>` and a fake
 * document. That focus really lands and that Esc really reaches the element is a browser's to show; what
 * this holds is every decision the window makes about them.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';
import { describe, expect, it } from 'vitest';

import { Dialog } from '@/shared/ui';
import type { DialogProps } from '@/shared/ui';
import { DIALOG_AUTOFOCUS_SELECTOR, DIALOG_FIELD_SELECTOR, attachModalDialog } from '@/shared/ui/dialog';
import type { DialogDocument, DialogFocusTarget, DialogHost } from '@/shared/ui/dialog';

import { WEB_ROOT } from '../../guards/lib/repo';
import { descendants, parseMarkup } from '../styles/contrast';
import type { Element } from '../styles/contrast';

// ===================================================================== the markup

const BODY = createElement('p', null, 'Тело окна');
const ACTIONS = [
  createElement('button', { key: 'cancel', type: 'button' }, 'Отмена'),
  createElement('button', { key: 'ok', type: 'button' }, 'Запустить'),
];

function render(props: Partial<DialogProps> = {}): Element[] {
  const markup = renderToStaticMarkup(
    createElement(Dialog, { title: 'Модели по этапам', onClose: () => undefined, children: BODY, ...props }),
  );
  return descendants(parseMarkup(markup));
}

const named = (elements: readonly Element[], tag: string): Element[] => elements.filter((el) => el.tag === tag);

describe('the window as markup', () => {
  it('is one native <dialog> named by its own heading', () => {
    const elements = render({ staticOpen: true });
    const dialogs = named(elements, 'dialog');
    expect(dialogs).toHaveLength(1);
    const labelledby = (dialogs[0] as Element).attrs.get('aria-labelledby');
    expect(labelledby, 'the dialog names no heading').toBeTruthy();
    const heading = elements.find((el) => el.attrs.get('id') === labelledby);
    expect(heading?.tag).toBe('h2');
  });

  it('draws the title and the close button in one row above the body, and the buttons below it', () => {
    const elements = render({ staticOpen: true, actions: ACTIONS });
    const dialog = elements.find((el) => el.tag === 'dialog') as Element;
    const [header, body, actions] = dialog.children;
    expect(header?.children.map((el) => el.tag), 'the title bar').toEqual(['h2', 'button']);
    expect(body?.attrs.has('data-dialog-body')).toBe(true);
    expect(actions?.attrs.has('data-dialog-actions')).toBe(true);
    expect(actions?.children.map((el) => el.tag)).toEqual(['button', 'button']);
    expect(dialog.children).toHaveLength(3);
  });

  it('has no row of buttons when it is given none', () => {
    const dialog = render({ staticOpen: true }).find((el) => el.tag === 'dialog') as Element;
    expect(dialog.children).toHaveLength(2);
    expect(descendants(dialog).some((el) => el.attrs.has('data-dialog-actions'))).toBe(false);
  });

  it('closes by a real button that has a name of its own', () => {
    const elements = render({ staticOpen: true });
    const header = (elements.find((el) => el.tag === 'dialog') as Element).children[0] as Element;
    const close = header.children[1] as Element;
    expect(close.tag).toBe('button');
    expect(close.attrs.get('type')).toBe('button');
    expect(close.attrs.get('aria-label')).toBe('Закрыть');
  });

  it('is drawn open only when asked to: otherwise the browser opens it with showModal', () => {
    expect(named(render({ staticOpen: true }), 'dialog')[0]?.attrs.has('open')).toBe(true);
    expect(named(render(), 'dialog')[0]?.attrs.has('open')).toBe(false);
  });

  it('carries the markers its owner gives it, and a width class for each size', () => {
    const marked = named(render({ staticOpen: true, markers: { 'data-run-models': 'window' } }), 'dialog')[0] as Element;
    expect(marked.attrs.get('data-run-models')).toBe('window');
    const widths = (['sm', 'md', 'lg'] as const).map((size) => [...(named(render({ size }), 'dialog')[0] as Element).classes].join(' '));
    expect(new Set(widths).size, 'the three sizes are three classes').toBe(3);
  });
});

/**
 * The handlers written on the `<dialog>` element itself. A server render prints none, so this reads the source: a press on
 * the dimmed page reaches the window as a click on the `<dialog>`, and any pointer handler there would be a way to close
 * it or to clear it by a press that is only a missed drag.
 */
export function handlersOnDialogElement(source: string): string[] {
  const tree = ts.createSourceFile('dialog.tsx', source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const found: string[] = [];
  const visit = (node: ts.Node): void => {
    if (ts.isJsxOpeningElement(node) || ts.isJsxSelfClosingElement(node)) {
      if (node.tagName.getText(tree) === 'dialog') {
        for (const attribute of node.attributes.properties) {
          if (ts.isJsxAttribute(attribute) && /^on[A-Z]/.test(attribute.name.getText(tree))) found.push(attribute.name.getText(tree));
        }
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(tree);
  return found;
}

describe('a press on the dimmed page, in the markup', () => {
  it('has no handler on the <dialog> element of the real component', () => {
    const source = readFileSync(join(WEB_ROOT, 'src', 'shared', 'ui', 'dialog.tsx'), 'utf8');
    expect(source).toContain('<dialog');
    expect(handlersOnDialogElement(source)).toEqual([]);
  });

  it('can fail: it names a handler written on the element and ignores one on a button', () => {
    expect(handlersOnDialogElement('const a = <dialog onClick={close} onPointerDown={x}>t</dialog>;')).toEqual(['onClick', 'onPointerDown']);
    expect(handlersOnDialogElement('const a = <dialog><button onClick={close}>t</button></dialog>;')).toEqual([]);
  });
});

// ===================================================================== the behaviour, over fakes

class FakeControl implements DialogFocusTarget {
  focused = 0;
  constructor(readonly name: string, public isConnected = true) {}
  focus(): void {
    this.focused += 1;
  }
}

class FakeEvent {
  prevented = false;
  preventDefault(): void {
    this.prevented = true;
  }
}

class FakeDialog implements DialogHost {
  open = false;
  showCalls = 0;
  closeCalls = 0;
  readonly listeners = new Map<string, Set<(event: FakeEvent) => void>>();
  autofocus: FakeControl | null = null;
  firstField: FakeControl | null = null;

  showModal(): void {
    this.open = true;
    this.showCalls += 1;
  }

  close(): void {
    if (!this.open) return;
    this.open = false;
    this.closeCalls += 1;
    this.emit('close');
  }

  on(type: 'cancel' | 'close', listener: (event: { preventDefault(): void }) => void): () => void {
    const set = this.listeners.get(type) ?? new Set();
    set.add(listener);
    this.listeners.set(type, set);
    return () => {
      set.delete(listener);
    };
  }

  query(selector: string): FakeControl | null {
    if (selector === DIALOG_AUTOFOCUS_SELECTOR) return this.autofocus;
    if (selector === DIALOG_FIELD_SELECTOR) return this.firstField;
    throw new Error(`unexpected selector ${selector}`);
  }

  /** What the browser does for any event on the element, `click` on its backdrop included. */
  emit(type: string): FakeEvent {
    const event = new FakeEvent();
    for (const listener of this.listeners.get(type) ?? []) listener(event);
    return event;
  }

  heard(): string[] {
    return [...this.listeners.entries()].filter(([, set]) => set.size > 0).map(([type]) => type).sort();
  }
}

const BODY_NODE = {};

function pageWith(active: FakeControl | null): DialogDocument {
  return { activeElement: active, body: BODY_NODE };
}

function opened(active: FakeControl | null = new FakeControl('opener')) {
  const dialog = new FakeDialog();
  let closes = 0;
  const detach = attachModalDialog(dialog, pageWith(active), { onClose: () => (closes += 1) });
  return { dialog, detach, closes: () => closes, opener: active };
}

describe('opening', () => {
  it('opens it as a modal, once, and does not open one that is already open', () => {
    const { dialog } = opened();
    expect(dialog.open).toBe(true);
    expect(dialog.showCalls).toBe(1);

    const already = new FakeDialog();
    already.open = true;
    attachModalDialog(already, pageWith(null), { onClose: () => undefined });
    expect(already.showCalls).toBe(0);
  });

  it('starts focus on the first field of the body when the author named no control', () => {
    const dialog = new FakeDialog();
    dialog.firstField = new FakeControl('field');
    attachModalDialog(dialog, pageWith(null), { onClose: () => undefined });
    expect(dialog.firstField.focused).toBe(1);
  });

  it('leaves focus to the browser when the author asked for a control with autofocus', () => {
    const dialog = new FakeDialog();
    dialog.autofocus = new FakeControl('chosen');
    dialog.firstField = new FakeControl('field');
    attachModalDialog(dialog, pageWith(null), { onClose: () => undefined });
    expect(dialog.firstField.focused).toBe(0);
    expect(dialog.autofocus.focused).toBe(0);
  });

  it('puts focus on nothing of its own when the body has no field: the browser picks the close button', () => {
    const dialog = new FakeDialog();
    expect(() => attachModalDialog(dialog, pageWith(null), { onClose: () => undefined })).not.toThrow();
  });
});

describe('Esc', () => {
  it('asks for the close and holds the browser back, so the window stays as it was', () => {
    const { dialog, closes } = opened();
    const event = dialog.emit('cancel');
    expect(event.prevented, 'the browser would have closed it behind the owner').toBe(true);
    expect(closes()).toBe(1);
    expect(dialog.open, 'the owner unmounts it; until then it stays open and keeps its fields').toBe(true);
    expect(dialog.closeCalls).toBe(0);
  });

  it('stops listening once detached', () => {
    const { dialog, detach, closes } = opened();
    detach();
    expect(dialog.heard()).toEqual([]);
    dialog.emit('cancel');
    expect(closes()).toBe(0);
  });
});

describe('a press on the dimmed page', () => {
  it('is not heard: only cancel and close are listened to, so it neither closes nor clears', () => {
    const { dialog, closes } = opened();
    expect(dialog.heard()).toEqual(['cancel', 'close']);
    const event = dialog.emit('click');
    expect(event.prevented).toBe(false);
    expect(closes()).toBe(0);
    expect(dialog.open).toBe(true);
    expect(dialog.closeCalls).toBe(0);
  });
});

describe('closing', () => {
  it('closes the element and returns focus to the control that held it before', () => {
    const { dialog, detach, opener, closes } = opened();
    detach();
    expect(dialog.open).toBe(false);
    expect((opener as FakeControl).focused).toBe(1);
    expect(closes(), 'unmounting is the owner closing it: no second request').toBe(0);
  });

  it('returns focus once when the browser closed it first, and says so to the owner', () => {
    const { dialog, detach, opener, closes } = opened();
    dialog.open = false;
    dialog.emit('close');
    expect((opener as FakeControl).focused).toBe(1);
    expect(closes()).toBe(1);
    detach();
    expect((opener as FakeControl).focused, 'the unmount after it must not focus again').toBe(1);
    expect(closes()).toBe(1);
  });

  it('does not give focus to a control that has left the page', () => {
    const gone = new FakeControl('gone', false);
    const { detach } = opened(gone);
    detach();
    expect(gone.focused).toBe(0);
  });

  it('has nothing to return to when focus was on the document body or nowhere', () => {
    const dialog = new FakeDialog();
    const detach = attachModalDialog(dialog, { activeElement: BODY_NODE as unknown as DialogFocusTarget, body: BODY_NODE }, { onClose: () => undefined });
    expect(() => detach()).not.toThrow();
    const nowhere = opened(null);
    expect(() => nowhere.detach()).not.toThrow();
    expect(nowhere.dialog.open).toBe(false);
  });

  it('survives being opened, closed and opened again, as a development render does', () => {
    const opener = new FakeControl('opener');
    const dialog = new FakeDialog();
    const page = pageWith(opener);
    const first = attachModalDialog(dialog, page, { onClose: () => undefined });
    first();
    const second = attachModalDialog(dialog, page, { onClose: () => undefined });
    expect(dialog.open).toBe(true);
    second();
    expect(dialog.open).toBe(false);
    expect(opener.focused).toBe(2);
  });
});
