import assert from 'node:assert/strict';
import test from 'node:test';

import {
  csvCells,
  formulaLikeCells,
  namesNeededBy,
  nightWindowMayRun,
  redactedExchange,
  templateNames,
} from './write.mjs';

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
