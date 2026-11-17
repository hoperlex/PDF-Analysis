/**
 * `UIP-S03-01` (owner rulings Г3-B, Г6-C, Г7-B, Г12-B): the window «Новый объект» that the object selector opens.
 *
 * The node test environment has no DOM and fires no event, so what is shown here is what a server render and the pure functions
 * can show: the window's markup (the shared window, the page's own form in its window mode, the buttons in the window's row), the
 * model's rule for the row that opens it (and for the account that never sees it), the one function that makes a new object the
 * open one, the refusal as one line, and the form's promise that a refusal never empties the field (read off the form's source,
 * with the reading itself shown to be able to fail). That focus really lands, that Esc really closes and that a press on the
 * dimmed page does nothing are the shared window's own promises (`tests/unit/shared-ui/dialog.test.ts`); that the window's body
 * and buttons stay inside that window is read here.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';
import { describe, expect, it, vi } from 'vitest';

import { ApiError, TransportError, queryKeys } from '@/shared/api';
import type { Account, ErrorCode, ErrorEnvelope, Project } from '@/shared/api';
import { classifyCreateProjectFailure } from '@/entities/project';
import { CreateProjectFailureLine, CreateProjectForm, WINDOW_NAME_HINT } from '@/features/create-project';
import {
  NEW_OBJECT_CANCEL_LABEL,
  NEW_OBJECT_CREATE_LABEL,
  NEW_PROJECT_LABEL,
  NewObjectDialog,
  afterObjectCreated,
  buildSwitcherModel,
  switcherMenuProps,
} from '@/widgets/project-switcher';
import type { CreatedObjectEffects, SwitcherAddress, SwitcherList } from '@/widgets/project-switcher';

import { WEB_ROOT } from '../../guards/lib/repo';
import { newClient, renderWith } from '../screens/harness';
import { descendants, parseMarkup } from '../styles/contrast';
import type { Element } from '../styles/contrast';

const A = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const NEW = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8E';

const at = (pathname: string | null, search = ''): SwitcherAddress => ({ pathname, searchParams: new URLSearchParams(search) });
const READY: SwitcherList = { kind: 'ready', projects: [{ project_uid: A, name: 'Мост через Неву', created_at: '2026-11-03T09:30:00Z' }], more: false, refreshFailure: null };

function apiError(status: number, code: ErrorCode, retryable: boolean): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.57.0',
    error_code: code,
    message: 'Одна безопасная для вызывающей стороны фраза.',
    correlation_id: 'cid-new-object-1',
    retryable,
  };
  return new ApiError(status, envelope, 'cid-new-object-1');
}

const account = (roles: readonly string[]): Account => ({ user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', roles, last_project_uid: null }) as unknown as Account;

// ------------------------------------------------------------------------- the window as markup

/** One render of the window, drawn open (`staticOpen`), under a client that knows `roles` or nothing. */
function windowMarkup(roles?: readonly string[]): string {
  const client = newClient();
  if (roles !== undefined) client.setQueryData(queryKeys.account.me(), account(roles));
  return renderWith(client, createElement(NewObjectDialog, { onClose: () => undefined, onCreated: () => undefined, staticOpen: true }));
}

/** What the window's markup says of its own shape: the facts the tests below hold it to. */
function shapeOf(markup: string) {
  const elements = descendants(parseMarkup(markup));
  const dialog = elements.find((el) => el.tag === 'dialog');
  const within = dialog === undefined ? [] : descendants(dialog);
  const form = within.find((el) => el.tag === 'form');
  const body = within.find((el) => el.attrs.has('data-dialog-body'));
  const actions = within.find((el) => el.attrs.has('data-dialog-actions'));
  const title = within.find((el) => el.tag === 'h2');
  const input = within.find((el) => el.tag === 'input');
  const label = within.find((el) => el.tag === 'label');
  const submitters = within.filter((el) => el.tag === 'button' && el.attrs.get('type') === 'submit');
  const inForm = (el: Element): boolean => form !== undefined && descendants(form).includes(el);
  return { dialog, form, body, actions, title, input, label, submitters, inForm, within };
}

describe('UIP-S03-01: the window is the shared window with the page\'s own form in it', () => {
  const markup = windowMarkup(['expert']);
  const shape = shapeOf(markup);

  it('is one native <dialog>, marked, drawn open and named by its heading «Новый объект»', () => {
    expect(shape.dialog?.tag).toBe('dialog');
    expect(shape.dialog?.attrs.has('data-new-object-dialog')).toBe(true);
    expect(shape.dialog?.attrs.has('open')).toBe(true);
    expect(shape.title?.attrs.get('id')).toBe(shape.dialog?.attrs.get('aria-labelledby'));
    expect(/<h2\b[^>]*>([^<]*)<\/h2>/.exec(markup)?.[1]).toBe(NEW_PROJECT_LABEL);
    expect(NEW_PROJECT_LABEL).toBe('Новый объект');
  });

  it('holds the form in its body and the buttons in its own row below, in the order «Отмена», «Создать»', () => {
    expect(shape.body !== undefined && shape.form !== undefined && descendants(shape.body).includes(shape.form)).toBe(true);
    expect(shape.actions?.children.map((el) => el.tag)).toEqual(['button', 'button']);
    const texts = [...(/data-dialog-actions=""[^>]*>([\s\S]*?)<\/div>/.exec(markup)?.[1] ?? '').matchAll(/<button\b[^>]*>([^<]*)<\/button>/g)].map((m) => m[1]);
    expect(texts).toEqual([NEW_OBJECT_CANCEL_LABEL, NEW_OBJECT_CREATE_LABEL]);
    expect([NEW_OBJECT_CANCEL_LABEL, NEW_OBJECT_CREATE_LABEL]).toEqual(['Отмена', 'Создать']);
    const [cancel, create] = shape.actions?.children as [Element, Element];
    expect(cancel.attrs.get('type')).toBe('button');
    expect(create.attrs.get('type')).toBe('submit');
  });

  it('has the one field «Название объекта», tied to its label, with the original\'s example as the hint', () => {
    expect(shape.input?.attrs.get('type')).toBe('text');
    expect(shape.input?.attrs.get('name')).toBe('name');
    expect(shape.label?.attrs.get('for')).toBe(shape.input?.attrs.get('id'));
    expect(/<label\b[^>]*>([^<]*)<\/label>/.exec(markup)?.[1]).toBe('Название объекта');
    expect(WINDOW_NAME_HINT).toBe('Например: 215. ЖК «Панорама»');
    expect(shape.input?.attrs.get('placeholder')).toBe(WINDOW_NAME_HINT);
    expect(shape.within.filter((el) => el.tag === 'input')).toHaveLength(1);
  });

  it('submits by the button\'s own `form` attribute: the form has no button of its own, so Enter and the button are one submit', () => {
    const [create] = shape.submitters;
    expect(shape.submitters).toHaveLength(1);
    expect(create?.attrs.get('form')).toBe(shape.form?.attrs.get('id'));
    expect(shape.form?.attrs.get('id')).toBeTruthy();
    expect(shape.within.filter((el) => el.tag === 'button' && shape.inForm(el))).toEqual([]);
  });

  it('says nothing of the object it has not made: no code, no «Создан …» line, no problem line', () => {
    expect(markup).not.toContain('prj_');
    expect(markup).not.toContain('data-created-project');
    expect(markup).not.toContain('data-create-problem');
    expect(markup).not.toContain('data-create-failure');
    expect(markup).not.toContain('Создан ');
  });

  it('keeps its field apart from the page\'s: a window opened over the page «Объекты» does not repeat the page\'s id', () => {
    expect(shape.input?.attrs.get('id')).not.toBe('new-project-name');
    expect(markup).not.toContain('id="new-project-name"');
  });

  it('holds «Создать» while an account known not to be an expert would be refused, and offers it to an expert or an unknown account', () => {
    const disabled = (roles?: readonly string[]) => shapeOf(windowMarkup(roles)).submitters[0]?.attrs.has('disabled');
    expect(disabled(['expert'])).toBe(false);
    expect(disabled(undefined)).toBe(false);
    expect(disabled(['viewer'])).toBe(true);
  });

  it('is told apart from the page\'s form by the same reading: the page form has its own button, a strong label and the page\'s id', () => {
    const page = renderWith(newClient(), createElement(CreateProjectForm, {}));
    const read = shapeOf(`<dialog open>${page}</dialog>`);
    // the facts the window passes are the facts the page form fails, so the reading is able to fail
    expect(read.within.filter((el) => el.tag === 'button' && read.inForm(el))).toHaveLength(1);
    expect(read.input?.attrs.get('id')).toBe('new-project-name');
    expect(read.form?.attrs.has('id')).toBe(false);
    expect(page).toContain('<strong>Новый объект</strong>');
    expect(markup).not.toContain('<strong>Новый объект</strong>');
  });
});

describe('UIP-S03-01: the form in its window mode, and the page\'s form unchanged', () => {
  it('takes the id it is given and makes its field\'s id from it', () => {
    const markup = renderWith(newClient(), createElement(CreateProjectForm, { mode: 'window', formId: 'window-form' }));
    expect(markup).toContain('id="window-form"');
    expect(markup).toContain('id="window-form-name"');
    expect(markup).toContain('for="window-form-name"');
    expect(markup).toContain('data-create-project-form="window"');
  });

  it('makes an id of its own when it is given none, and still has no button', () => {
    const markup = renderWith(newClient(), createElement(CreateProjectForm, { mode: 'window' }));
    expect(/<form\b[^>]*\bid="([^"]+)"/.exec(markup)?.[1]).toBeTruthy();
    expect(markup).not.toContain('<button');
  });

  it('leaves the page\'s form as it was: its own «Создать», its id, its label and its placeholder', () => {
    const markup = renderWith(newClient(), createElement(CreateProjectForm, {}));
    expect(markup).toContain('id="new-project-name"');
    expect(markup).toContain('>Создать</button>');
    expect(markup).toContain('placeholder="Название объекта"');
    expect(markup).not.toContain('data-create-project-form');
  });

  it('says the same thing to an account that is not an expert, in the window and on the page', () => {
    const client = newClient();
    client.setQueryData(queryKeys.account.me(), account(['viewer']));
    for (const mode of ['page', 'window'] as const) {
      const markup = renderWith(client, createElement(CreateProjectForm, { mode }));
      expect(markup, mode).toContain('Создавать объекты может эксперт.');
      expect(markup, mode).not.toContain('<input');
    }
  });
});

// ------------------------------------------------------------------------- the refusal, as one line

describe('UIP-S03-01: a refusal of the create is one line in the window', () => {
  const FAILURES: readonly [string, unknown][] = [
    ['a refused name', apiError(422, 'validation_failed', false)],
    ['a dependency that is down', apiError(503, 'dependency_unavailable', true)],
    ['no right to create', apiError(403, 'permission_denied', false)],
    ['a key in progress', apiError(409, 'idempotency_key_in_progress', true)],
    ['no route to the API', new TransportError('Нет связи.', { retryable: true })],
    ['something nobody classified', new Error('x')],
  ];

  it.each(FAILURES)('%s: an alert paragraph that says what was refused, with no button and no block', (_name, error) => {
    const failure = classifyCreateProjectFailure(error);
    const markup = renderToStaticMarkup(createElement(CreateProjectFailureLine, { failure }));
    expect(markup.match(/<p\b/g)).toHaveLength(1);
    expect(markup).toContain('role="alert"');
    expect(markup).toContain(`data-create-failure="${failure.kind}"`);
    expect(markup).toContain(failure.title.replace(/&/g, '&amp;'));
    expect(markup).not.toContain('<button');
    expect(markup).not.toContain('<h');
  });

  it('carries the correlation id when the server gave one, and says nothing of it when it did not', () => {
    const given = renderToStaticMarkup(createElement(CreateProjectFailureLine, { failure: classifyCreateProjectFailure(apiError(503, 'dependency_unavailable', true)) }));
    expect(given).toContain('Код обращения: cid-new-object-1');
    const none = renderToStaticMarkup(createElement(CreateProjectFailureLine, { failure: classifyCreateProjectFailure(new Error('x')) }));
    expect(none).not.toContain('Код обращения');
  });

  it('can fail: the page\'s block is not a line (it has a heading and a retry button), so the reading above tells the two apart', () => {
    const source = readFileSync(join(WEB_ROOT, 'src/features/create-project/ui/create-project-form.tsx'), 'utf8');
    expect(source).toContain('retryLabel');
    expect(source).toContain('<ErrorState');
    const line = readFileSync(join(WEB_ROOT, 'src/features/create-project/ui/create-project-failure-line.tsx'), 'utf8');
    expect(line).not.toContain('<ErrorState');
    expect(line).not.toContain('<button');
    expect(line).not.toContain('onRetry');
  });
});

// ------------------------------------------------------------------------- what is typed is not lost

/** The names of the properties whose function bodies hold a `setName('')` call: `''` for one that is in no property of a call. */
export function whereTheNameIsCleared(source: string): string[] {
  const tree = ts.createSourceFile('form.tsx', source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const found: string[] = [];
  const visit = (node: ts.Node): void => {
    if (ts.isCallExpression(node) && ts.isIdentifier(node.expression) && node.expression.text === 'setName') {
      const [argument] = node.arguments;
      if (argument !== undefined && ts.isStringLiteral(argument) && argument.text === '') {
        let up: ts.Node | undefined = node.parent;
        let property = '';
        while (up !== undefined) {
          if (ts.isPropertyAssignment(up) && ts.isIdentifier(up.name)) {
            property = up.name.text;
            break;
          }
          up = up.parent;
        }
        found.push(property);
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(tree);
  return found;
}

describe('UIP-S03-01: what was typed is lost only by a success', () => {
  const source = readFileSync(join(WEB_ROOT, 'src/features/create-project/ui/create-project-form.tsx'), 'utf8');

  it('empties the field in one place, the `onSuccess` of the send; a refusal, a close by a press on the page and a retry leave it', () => {
    expect(whereTheNameIsCleared(source)).toEqual(['onSuccess']);
  });

  it('can fail: a field emptied before the send, or on its failure, is read as a place that is not `onSuccess`', () => {
    const early = source.replace('    setCreated(null);\n', "    setCreated(null);\n    setName('');\n");
    expect(early).not.toBe(source);
    expect(whereTheNameIsCleared(early)).not.toEqual(['onSuccess']);
    const onError = source.replace('        onSuccess: (project) => {', "        onError: () => {\n          setName('');\n        },\n        onSuccess: (project) => {");
    expect(onError).not.toBe(source);
    expect(whereTheNameIsCleared(onError)).toEqual(['onError', 'onSuccess']);
  });

  it('a retry is the same command: the same name is the same intent key (the form mints it from the trimmed name)', () => {
    expect(source).toContain('useIntentKey(`create-project:${trimmed}`)');
  });
});

// ------------------------------------------------------------------------- the row that opens the window

describe('UIP-S03-01: the row «Новый объект» opens the window where the island can, and is a link where it cannot', () => {
  const entries = (list: SwitcherList = READY, mayCreate?: boolean) => buildSwitcherModel(at('/dashboard', `project=${A}`), list, mayCreate === undefined ? {} : { mayCreate }).entries;
  const created = (list: SwitcherList = READY, mayCreate?: boolean) => entries(list, mayCreate).filter((entry) => entry.kind === 'link' && entry.creates === true);

  it('is the last entry, marked as the one that makes an object, and still the address of the list\'s form', () => {
    const all = entries();
    expect(all[all.length - 1]).toEqual({ kind: 'link', label: 'Новый объект', href: '/projects', creates: true });
    expect(created()).toHaveLength(1);
    expect(entries({ kind: 'loading' }).map((entry) => entry.label)).toEqual(['Все объекты', 'Новый объект']);
  });

  it('is left out when the account is known not to be an expert, and nothing else of the menu changes', () => {
    expect(created(READY, false)).toEqual([]);
    expect(entries(READY, false).map((entry) => entry.label)).toEqual(['Мост через Неву', 'Все объекты']);
    expect(entries(READY, true)).toEqual(entries(READY));
    expect(entries(READY, false)).toEqual(entries(READY).slice(0, -1));
  });

  it('is an action with the island\'s handler, and the plain link without it (the first render, the census)', () => {
    const model = buildSwitcherModel(at('/dashboard', `project=${A}`), READY);
    const onCreate = vi.fn();
    const withHandler = switcherMenuProps(model, () => undefined, onCreate).items;
    const last = withHandler[withHandler.length - 1];
    expect(last).toEqual({ kind: 'action', label: 'Новый объект', onChoose: onCreate });
    if (last?.kind === 'action') last.onChoose?.();
    expect(onCreate).toHaveBeenCalledTimes(1);

    const without = switcherMenuProps(model, () => undefined).items;
    expect(without[without.length - 1]).toEqual({ kind: 'link', label: 'Новый объект', href: '/projects' });
  });

  it('can fail: no other row becomes an action because a handler was given (every object, «Все объекты» and the list stay links)', () => {
    const model = buildSwitcherModel(at('/dashboard', `project=${A}`), { ...READY, more: true });
    const items = switcherMenuProps(model, () => undefined, () => undefined).items;
    expect(items.map((item) => [item.kind, item.label])).toEqual([
      ['link', 'Мост через Неву'],
      ['link', 'Все объекты'],
      ['link', 'Остальные объекты — в списке'],
      ['action', 'Новый объект'],
    ]);
  });
});

// ------------------------------------------------------------------------- the new object becomes the open one

describe('UIP-S03-01: the object the window made becomes the open one, as a click on its row does', () => {
  const run = (address: SwitcherAddress) => {
    const calls: string[] = [];
    const effects: CreatedObjectEffects = {
      remember: (uid) => calls.push(`remember ${uid}`),
      navigate: (href) => calls.push(`navigate ${href}`),
      close: () => calls.push('close'),
    };
    const project: Project = { project_uid: NEW, name: '215. ЖК «Панорама»', created_at: '2026-11-17T09:30:00Z' };
    afterObjectCreated(address, project, effects);
    return calls;
  };

  it('keeps the choice, opens the address, and closes the window: in that order', () => {
    expect(run(at('/dashboard', `project=${A}`))).toEqual([`remember ${NEW}`, `navigate /dashboard?project=${NEW}`, 'close']);
  });

  it('on a screen that follows the object, drops what meant something only inside the old object and keeps the rest', () => {
    const calls = run(at('/dashboard', `project=${A}&section=AR&tab=x&view=compact`));
    expect(calls[1]).toBe(`navigate /dashboard?project=${NEW}&view=compact`);
  });

  it('on a silent address of a screen that follows the object, writes the new one in', () => {
    expect(run(at('/dashboard'))[1]).toBe(`navigate /dashboard?project=${NEW}`);
  });

  it('after «Все объекты» (?project=all), leaves it for the new object', () => {
    expect(run(at('/dashboard', 'project=all'))[1]).toBe(`navigate /dashboard?project=${NEW}`);
  });

  it('on a required or a global screen, opens the new object\'s own page', () => {
    expect(run(at(`/projects/${A}`))[1]).toBe(`navigate /projects/${NEW}`);
    expect(run(at('/queue'))[1]).toBe(`navigate /projects/${NEW}`);
    expect(run(at('/projects'))[1]).toBe(`navigate /projects/${NEW}`);
  });

  it('asks for the new object and for no other', () => {
    for (const address of [at('/dashboard', `project=${A}`), at('/queue'), at(null)]) {
      expect(run(address)[0], JSON.stringify(address.pathname)).toBe(`remember ${NEW}`);
    }
  });
});
