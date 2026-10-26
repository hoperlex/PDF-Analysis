/**
 * Mount a React tree that keeps its state, runs its effects and takes a click — in the node
 * test environment, with no DOM library.
 *
 * `tests/unit/screens/harness.ts` renders one static pass and says so: it cannot press a
 * button, run an effect or render the same instance twice. That is the right instrument for
 * "what does this state look like" and the wrong one for "what happens to this control while
 * the page around it changes" (`AR-V3-BETA-PACK-STATUS-WEB-FIX-01`: a start in flight must
 * survive the status panel's re-read failing). This file is the smallest thing that closes the
 * gap: `react-dom/client` against a hand-written node tree — ~100 lines, no dependency, and
 * `FRONTEND_LOCK.json` untouched.
 *
 * What it is NOT: a browser. There is no layout, no event propagation, no focus, no style, no
 * text selection. A press calls the `onClick` the React element carries, which is exactly what
 * a click on that button would call — except that a browser dispatches no click to a disabled
 * button, so neither does `press` (`AR-V3-BETA-PACK-STATUS-WEB-FIX-02`): it does nothing and
 * returns `false`, and a test that means to press a disabled button asserts that flag. Anything
 * that depends on a real event path (a label, a form submit, a portal) is outside it and must
 * not be tested here.
 */

import { act } from 'react';
import type { ReactElement } from 'react';
import { createRoot } from 'react-dom/client';

class FakeNode {
  readonly nodeType: number;
  readonly nodeName: string;
  readonly tagName: string;
  readonly namespaceURI = 'http://www.w3.org/1999/xhtml';
  readonly attributes: Record<string, string> = {};
  readonly style: Record<string, string> = {};
  readonly ownerDocument: FakeDocument;
  parentNode: FakeNode | null = null;
  childNodes: FakeNode[] = [];
  text = '';

  constructor(document: FakeDocument | null, name: string, nodeType = 1) {
    this.ownerDocument = document ?? (this as unknown as FakeDocument);
    this.nodeName = name;
    this.tagName = name.toUpperCase();
    this.nodeType = nodeType;
  }

  get firstChild(): FakeNode | null {
    return this.childNodes[0] ?? null;
  }
  get lastChild(): FakeNode | null {
    return this.childNodes[this.childNodes.length - 1] ?? null;
  }
  get nextSibling(): FakeNode | null {
    const siblings = this.parentNode?.childNodes ?? [];
    return siblings[siblings.indexOf(this) + 1] ?? null;
  }
  get nodeValue(): string {
    return this.text;
  }
  set nodeValue(value: string) {
    this.text = value;
  }
  get data(): string {
    return this.text;
  }
  set data(value: string) {
    this.text = value;
  }
  get textContent(): string {
    return this.nodeType === 3 ? this.text : this.childNodes.map((child) => child.textContent).join('');
  }
  set textContent(value: string) {
    for (const child of this.childNodes) child.parentNode = null;
    this.childNodes = [];
    if (value !== '') this.appendChild(this.ownerDocument.createTextNode(value));
  }

  appendChild(child: FakeNode): FakeNode {
    child.parentNode?.removeChild(child);
    child.parentNode = this;
    this.childNodes.push(child);
    return child;
  }
  insertBefore(child: FakeNode, reference: FakeNode | null): FakeNode {
    child.parentNode?.removeChild(child);
    child.parentNode = this;
    if (reference === null) this.childNodes.push(child);
    else this.childNodes.splice(this.childNodes.indexOf(reference), 0, child);
    return child;
  }
  removeChild(child: FakeNode): FakeNode {
    const index = this.childNodes.indexOf(child);
    if (index >= 0) this.childNodes.splice(index, 1);
    child.parentNode = null;
    return child;
  }
  setAttribute(name: string, value: unknown): void {
    this.attributes[name] = String(value);
  }
  removeAttribute(name: string): void {
    delete this.attributes[name];
  }
  getAttribute(name: string): string | null {
    return this.attributes[name] ?? null;
  }
  contains(other: FakeNode | null): boolean {
    for (let node = other; node !== null; node = node.parentNode) if (node === this) return true;
    return false;
  }
  addEventListener(): void {}
  removeEventListener(): void {}
  focus(): void {}
  blur(): void {}
}

class FakeDocument extends FakeNode {
  readonly defaultView: Record<string, unknown>;
  readonly documentElement: FakeNode;
  readonly body: FakeNode;
  readonly activeElement: FakeNode | null = null;

  constructor() {
    super(null, '#document', 9);
    this.documentElement = new FakeNode(this, 'html');
    this.body = new FakeNode(this, 'body');
    this.defaultView = {
      HTMLIFrameElement: class {},
      document: this,
      event: undefined,
      addEventListener() {},
      removeEventListener() {},
      // `next/link` defers its prefetch with `self.setTimeout` when there is no idle callback.
      setTimeout: (...args: Parameters<typeof setTimeout>) => setTimeout(...args),
      clearTimeout: (...args: Parameters<typeof clearTimeout>) => clearTimeout(...args),
    };
  }
  createElement(name: string): FakeNode {
    return new FakeNode(this, name);
  }
  createElementNS(_namespace: string, name: string): FakeNode {
    return new FakeNode(this, name);
  }
  createTextNode(text: string): FakeNode {
    const node = new FakeNode(this, '#text', 3);
    node.text = text;
    return node;
  }
  createComment(text: string): FakeNode {
    const node = new FakeNode(this, '#comment', 8);
    node.text = text;
    return node;
  }
}

function serialise(node: FakeNode): string {
  if (node.nodeType === 3) return node.text;
  if (node.nodeType === 8) return '';
  const attributes = Object.entries(node.attributes)
    .map(([name, value]) => ` ${name}="${value}"`)
    .join('');
  return `<${node.nodeName}${attributes}>${node.childNodes.map(serialise).join('')}</${node.nodeName}>`;
}

function descendants(node: FakeNode): FakeNode[] {
  return node.childNodes.flatMap((child) => [child, ...descendants(child)]);
}

/**
 * TanStack Query hands its notifications to React on a zero-delay timer, which `act` does not
 * wait for: without this a settled mutation would be read one tick before React heard of it.
 */
const tick = (): Promise<void> => new Promise((done) => setTimeout(done, 0));

type Clickable = { onClick?: (event: unknown) => void };

/** The props React stored on a node, which is where its `onClick` lives. */
function propsOf(node: FakeNode): Clickable {
  const key = Object.keys(node).find((name) => name.startsWith('__reactProps$'));
  return key === undefined ? {} : ((node as unknown as Record<string, Clickable>)[key] ?? {});
}

export interface LiveRender {
  /** The current tree as markup, after every pending effect and state update has run. */
  markup(): string;
  /** Render a new element into the same root: the same component instances, new props. */
  update(element: ReactElement): Promise<void>;
  /** Run `work` inside `act`, so the updates it causes are flushed before it returns. */
  settle(work: () => Promise<unknown> | unknown): Promise<void>;
  /**
   * Press the one button whose whole text is `label`. Throws when there is not exactly one.
   * Resolves `true` when the click was delivered and `false` when the button is disabled, in
   * which case nothing was called, as in a browser.
   */
  press(label: string): Promise<boolean>;
  /** How many buttons carry exactly this text. */
  count(label: string): number;
  unmount(): Promise<void>;
}

const GLOBALS = ['window', 'self', 'document', 'IS_REACT_ACT_ENVIRONMENT'] as const;

/** Mount `element` and flush its first render, effects included. Call `unmount` when done. */
export async function mountLive(element: ReactElement): Promise<LiveRender> {
  const document = new FakeDocument();
  const holder = globalThis as unknown as Record<string, unknown>;
  const before = GLOBALS.map((name) => [name, holder[name]] as const);
  holder.window = document.defaultView;
  holder.self = document.defaultView;
  holder.document = document;
  holder.IS_REACT_ACT_ENVIRONMENT = true;

  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container as unknown as Element);
  await act(async () => {
    root.render(element);
    await tick();
  });

  const buttons = (label: string): FakeNode[] =>
    descendants(container).filter((node) => node.nodeName === 'button' && node.textContent === label);

  return {
    markup: () => container.childNodes.map(serialise).join(''),
    update: async (next) => {
      await act(async () => {
        root.render(next);
        await tick();
      });
    },
    settle: async (work) => {
      await act(async () => {
        await work();
        await tick();
        await tick();
      });
    },
    press: async (label) => {
      const found = buttons(label);
      if (found.length !== 1) throw new Error(`expected one button «${label}», found ${found.length}`);
      const button = found[0] as FakeNode;
      // React writes a boolean `disabled` as a bare attribute; a browser would not dispatch the
      // click to a button that carries it.
      if (button.getAttribute('disabled') !== null) return false;
      const onClick = propsOf(button).onClick;
      if (onClick === undefined) throw new Error(`button «${label}» has no onClick`);
      await act(async () => {
        onClick({ type: 'click', preventDefault() {}, stopPropagation() {} });
        await tick();
        await tick();
      });
      return true;
    },
    count: (label) => buttons(label).length,
    unmount: async () => {
      await act(async () => {
        root.unmount();
      });
      // A notification still pending would reach React after the globals below are gone.
      await tick();
      await tick();
      for (const [name, value] of before) {
        if (value === undefined) delete holder[name];
        else holder[name] = value;
      }
    },
  };
}
