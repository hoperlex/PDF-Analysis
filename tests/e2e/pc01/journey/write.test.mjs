import assert from 'node:assert/strict';
import test from 'node:test';
import { runInNewContext } from 'node:vm';

import {
  csvCells,
  csvShape,
  formulaLikeCells,
  namesNeededBy,
  nightWindowMayRun,
  redactedExchange,
  templateNames,
} from './write.mjs';
import { locatorExpression } from './cdp.mjs';

test('the night window runs on a recorded origin and on nothing else unless it is told', () => {
  assert.equal(nightWindowMayRun({ providerMode: 'recorded', allowSpend: false }), true);
  for (const providerMode of ['live', 'proxy', null, undefined, 'accepted']) {
    assert.equal(nightWindowMayRun({ providerMode, allowSpend: false }), false, String(providerMode));
  }
  assert.equal(nightWindowMayRun({ providerMode: 'live', allowSpend: true }), true);
  assert.equal(nightWindowMayRun({ providerMode: null, allowSpend: 'yes' }), false);
});

test('a CSV cell that a spreadsheet would run is found, whatever quoting it wears', () => {
  const csv = '﻿a,b,c\r\n"=SUM(1)",plain,"-1"\r\n"  @x",\'=kept,+1\r\n"say ""hi""",,x\r\n';
  assert.deepEqual(csvCells(csv).slice(0, 4), ['a', 'b', 'c', '=SUM(1)']);
  assert.deepEqual(formulaLikeCells(csvCells(csv)), ['=SUM(1)', '-1', '  @x', '+1']);
  assert.ok(csvCells(csv).includes('say "hi"'));
  assert.deepEqual(formulaLikeCells(csvCells('﻿h\r\n\'=escaped\r\n')), []);
});

test('a CSV is counted in whole rows of the header\'s width, quoted line breaks and an empty file included', () => {
  assert.deepEqual(csvShape('\ufeffa,b,c\r\n'), { columns: 3, rows: 0 });
  assert.deepEqual(csvShape('\ufeffa,b,c\r\n1,,3\r\n"x\r\ny",\'=z,\r\n'), { columns: 3, rows: 2 });
  assert.deepEqual(csvShape('a,b,c\n1,2\n'), { columns: 3, rows: null });
  assert.equal(csvShape('').rows, null);
});

test('a password never survives in a request body the envelope keeps', () => {
  const form = redactedExchange({ requestBody: 'current_password=a%21&new_password=b&confirm_new_password=b' });
  assert.equal(form.requestBody, 'current_password=(redacted)&new_password=(redacted)&confirm_new_password=(redacted)');
  const json = redactedExchange({ requestBody: '{"temporary_password":"x y","note":"keep"}' });
  assert.equal(json.requestBody, '{"temporary_password":"(redacted)","note":"keep"}');
  const untouched = { requestBody: 'name=value' };
  assert.equal(redactedExchange(untouched), untouched);
  assert.equal(redactedExchange({ requestBody: null }).requestBody, null);
});

test('what a step needs is what its templates mention, minus what it binds, makes or declares constant', () => {
  const step = {
    at: '/projects/{project_uid}/versions/{version_uid}',
    bind: { version_uid: 'second_version_uid' },
    constants: { section_code: 'AR' },
    expects_api: [
      { path: '/sections/{section_code}/specification' },
      { path: '/x/{version_uid}', bind: { version_uid: 'version_uid' } },
    ],
    captures: [{ as: ['made_here'] }],
    expects_present: [{ selector: '[data-x="{made_here}"]', text_matches: '^{other_one}$' }],
  };
  assert.deepEqual(namesNeededBy(step).sort(), ['other_one', 'project_uid', 'second_version_uid', 'version_uid']);
  assert.deepEqual(templateNames('{a} and {b_c} but not {D}'), ['a', 'b_c']);
});

/** A page of rows, each with one button: just enough DOM for the locator's script to run on. */
function rowsOf(...rows) {
  const owners = rows.map(({ words, button }) => ({ innerText: words, button }));
  const buttons = owners.map((owner) => ({
    innerText: owner.button,
    closest: (selector) => (selector === 'li' ? owner : null),
  }));
  return { querySelectorAll: (selector) => (selector === 'li button' ? buttons : []) };
}

test('a control is found in the row whose words name it, and never in the first row instead', () => {
  const document = rowsOf(
    { words: 'Другой проект\nВыбрать проект', button: 'Выбрать проект' },
    { words: 'W22-E2E write half 2026-10-22\nВыбрать проект', button: 'Выбрать проект' },
  );
  const find = (within) => runInNewContext(locatorExpression('li button', null, within), { document });
  const second = find({ selector: 'li', text_contains: 'write half 2026-10-22' });
  assert.equal(second.closest('li').innerText.startsWith('W22-E2E'), true, 'the row that names the project');
  assert.equal(find({ selector: 'li', text_contains: 'a project nobody made' }), null, 'no such row matches nothing');
  assert.equal(find({ selector: 'ul', text_contains: 'write half' }), null, 'no such kind of row matches nothing');
  assert.equal(find(null).closest('li').innerText.startsWith('Другой'), true, 'without a row, the first control');
  const labelled = runInNewContext(locatorExpression('li button', 'Выбрать проект', { selector: 'li', text_contains: 'write half' }), { document });
  assert.equal(labelled.closest('li').innerText.startsWith('W22-E2E'), true, 'text and row together');
});

test('the words a wait is for count among what a step needs', () => {
  const step = { at: '/blocks', actions: [{ do: 'wait_for', selector: 'li', text_contains: '{version_uid}', bound_ms: 1 }] };
  assert.deepEqual(namesNeededBy(step), ['version_uid']);
});

test('the words that name a row count among what a step needs', () => {
  const step = {
    at: '/blocks',
    actions: [{ do: 'click', selector: 'li button', within: { selector: 'li', text_contains: '{third_version_uid}' } }],
  };
  assert.deepEqual(namesNeededBy(step), ['third_version_uid']);
  const stamped = { at: '/blocks', actions: [{ do: 'click', selector: 'li button', within: { selector: 'li', text_contains: 'name %STAMP%' } }] };
  assert.deepEqual(namesNeededBy(stamped), []);
});
