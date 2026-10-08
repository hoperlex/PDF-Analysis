/** A bounded retry for the browser's initial GET navigation only. */

import { setTimeout as sleepFor } from 'node:timers/promises';

const NETWORK_CHANGE = 'net::ERR_NETWORK_CHANGED';
const RETRY_DELAYS_MS = Object.freeze([1000, 3000, 6000]);

export async function navigateWithTransientRetry(
  send,
  url,
  { sleep = sleepFor, onRetry = () => {} } = {},
) {
  for (let index = 0; index <= RETRY_DELAYS_MS.length; index += 1) {
    const result = await send('Page.navigate', { url });
    const attempts = index + 1;
    if (result.errorText !== NETWORK_CHANGE || index === RETRY_DELAYS_MS.length) {
      return { result, attempts };
    }
    const delayMs = RETRY_DELAYS_MS[index];
    onRetry({ attempts, delayMs, errorText: result.errorText });
    await sleep(delayMs);
  }
  throw new Error('navigation retry budget is unreachable');
}
