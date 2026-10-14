/**
 * The address an `<img>` loads one portal block's crop from (`streamVersionPortalBlockCrop`).
 *
 * **Why here.** `web/docs/PC01_UI_SEAM.md` §4: a slice never constructs a URL, and §3.4: a
 * widget does not take one. So the address is built in the transport seam, beside the
 * transport that builds every other path, and the «Блоки» widget asks for it with the
 * contract's own identities (`W55B-FIX`, `W55B-JUDGE-Y` Y-2; it was
 * `entities/block/api/crop-url.ts`, moved unchanged).
 *
 * **Why an address and not the generated client's `Blob`.** Every other binary this
 * application shows — a version's PDF, a norm document — is read through the generated
 * client into a `Blob` and an object URL, because a script holds it. A crop is an image the
 * BROWSER fetches: given the address, it fetches only the crops a reader scrolls to
 * (`loading="lazy"`), and sends the session cookie itself on this same-origin request, which
 * the BFF turns into the API credential as it does for every call. Reading forty-seven crops
 * (the owner's export) into memory as blobs the moment the tab opens would be the opposite.
 *
 * **The browser keeps them** (`W55B-FIX`, X-4): the API answers a crop with `ETag` (the PNG's
 * SHA-256) and `Cache-Control: private, max-age=3600`, and the BFF forwards both
 * (`FORWARDED_RESPONSE_HEADERS`), so a crop a reader scrolls back to within the hour comes from
 * the browser's own HTTP cache and asks nothing of the API. Before both headers this file's
 * claim that it did was not true.
 *
 * **Built from the contract, not typed out.** The path is the generated operation table's own
 * template (`OPERATIONS.streamVersionPortalBlockCrop.path`) and the base is the one the
 * transport uses (`getApiBaseUrl()`, which refuses an unconfigured build rather than
 * defaulting); each identifier is encoded the way the transport encodes a path parameter.
 * A renamed path in a reseal changes this address with it. The portal's own `crop_url` is
 * not on the wire and nothing here could reach it.
 */

import { getApiBaseUrl } from '../config';

import { ClientUsageError } from './errors';
import type { PortalBlockId, VersionUid } from './generated';
import { OPERATIONS } from './generated';

export function portalBlockCropUrl(versionUid: VersionUid, portalBlockId: PortalBlockId): string {
  const values: Readonly<Record<string, string>> = {
    version_uid: versionUid,
    portal_block_id: portalBlockId,
  };
  const path = OPERATIONS.streamVersionPortalBlockCrop.path.replace(
    /\{([^}]+)\}/g,
    (_match, name: string) => {
      const value = values[name];
      // A template parameter this builder does not supply is a reseal it has not followed:
      // said, never filled with an empty segment.
      if (value === undefined || value === '') {
        throw new ClientUsageError(
          `${OPERATIONS.streamVersionPortalBlockCrop.operationId}: параметр пути «${name}» ` +
            'требуется шаблоном и не был передан.',
        );
      }
      return encodeURIComponent(value);
    },
  );
  return `${getApiBaseUrl()}${path}`;
}
