/**
 * Look at one screen, in a cold browser, and write down exactly what it rendered.
 *
 * `W28-LIVE` needed a reading of a screen the write half does not press through -- the
 * findings list of a run it had just driven -- and needed it under the same rules as
 * everything else in this directory: a separate operating-system browser process with a
 * throwaway profile, the response bodies fetched from the browser before it dies, and
 * `innerText` rather than a status code (`D-28`).
 *
 * It asserts nothing. `journey.mjs` and `refusals.mjs` are the instruments with exit
 * codes; this one is a window, and its exit code says only whether the browser could be
 * driven to the address at all. Keeping it assertion-free is deliberate: a reading tool
 * that also judged would invite the judgement to be written after the reading.
 *
 *     node tests/e2e/pc01/journey/look.mjs --origin http://127.0.0.1:PORT \
 *       --path /projects/prj_.../runs/run_.../findings [--out <dir>]
 *
 * Prints the rendered text to stdout and writes the full envelope -- every request the
 * browser made, with `Authorization` recorded by presence only -- to `<out>/look.json`.
 */

import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { withColdBrowser } from './cdp.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));

function parseArgs(argv) {
  const args = { origin: undefined, paths: [], out: undefined };
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === '--origin') args.origin = argv[++i];
    else if (argv[i] === '--path') args.paths.push(argv[++i]);
    else if (argv[i] === '--out') args.out = argv[++i];
    else {
      console.error(`look: unknown argument '${argv[i]}'`);
      process.exit(2);
    }
  }
  return args;
}

const args = parseArgs(process.argv.slice(2));
if (!args.origin || args.paths.length === 0) {
  console.error(
    'look: --origin and at least one --path are required. There is no default origin: ' +
      'a reading is a reading of something in particular.',
  );
  process.exit(2);
}

const ORIGIN = args.origin.replace(/\/+$/, '');
const OUT_DIR = resolve(args.out ?? join(HERE, '.out'));
mkdirSync(OUT_DIR, { recursive: true });

const readings = [];
for (const path of args.paths) {
  const url = ORIGIN + path;
  const reading = { path, url };
  readings.push(reading);
  try {
    await withColdBrowser(async (page) => {
      await page.goto(url);
      reading.landedOn = await page.location();
      reading.bodyText = await page.evaluate(
        "document.body ? document.body.innerText.replace(/\\n{3,}/g, '\\n\\n') : ''",
      );
      reading.exchanges = page.exchanges();
      reading.consoleErrors = page.consoleErrors();
      reading.pageErrors = page.pageErrors();
    });
  } catch (error) {
    reading.drivingError = error.message;
  }
  console.log('='.repeat(72));
  console.log(`${path}  ->  ${reading.landedOn ?? '(not reached)'}`);
  if (reading.drivingError) console.log(`could not be driven: ${reading.drivingError}`);
  console.log('-'.repeat(72));
  console.log(reading.bodyText ?? '');
}

const envelope = { origin: ORIGIN, at: new Date().toISOString(), readings };
const target = join(OUT_DIR, 'look.json');
writeFileSync(target, JSON.stringify(envelope, null, 2));
console.log(`\nenvelope: ${target}`);
process.exit(readings.some((r) => r.drivingError) ? 1 : 0);
