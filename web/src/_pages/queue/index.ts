/** Public API of the `queue` page slice (`R-66`). */

export { QueuePage } from './ui/queue-page';
export type { QueuePageProps } from './ui/queue-page';

/** `?state=&period=`: the filter a link opens the queue with (second UX pass); the route reads it on the server. */
export type { QueueAddress } from './model/address';
export {
  EMPTY_QUEUE_ADDRESS,
  QUEUE_PERIOD_PARAM,
  QUEUE_STATE_PARAM,
  isQueueState,
  readQueueAddress,
  writeQueueAddress,
} from './model/address';
