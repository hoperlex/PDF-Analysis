/**
 * The credentialed forward: what it attaches, what it refuses to carry, and what it
 * passes through untouched.
 *
 * Every expected value here is a literal. `OPERATING_CONSTRAINTS.md` §12: a test that
 * computed the expected header list from `FORWARDED_REQUEST_HEADERS` would share its
 * assumption with the module under test and would stay green if that list were emptied.
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { afterEach, describe, expect, it, vi } from 'vitest';

import type { FetchLike } from '@/shared/api';
import {
  BFF_BASE_PATH,
  ForwardPathError,
  STREAM_FROM_BYTES,
  UPSTREAM_DEADLINE_MS,
  buildUpstreamPath,
  forwardWithCredential,
  mintForwardCorrelationId,
} from '@/shared/api/credentialed-forward';

const UPSTREAM = 'http://api:8000';
const TOKEN = 'test-token-not-a-real-credential';
const TARGET = { upstream: UPSTREAM, token: TOKEN };

interface Seen {
  readonly url: string;
  readonly init: RequestInit;
}

/** A fetch that records the call and answers with what the test supplies. */
function recordingFetch(response: () => Response): { fetch: FetchLike; calls: Seen[] } {
  const calls: Seen[] = [];
  const fetch: FetchLike = (url, init) => {
    calls.push({ url, init });
    return Promise.resolve(response());
  };
  return { fetch, calls };
}

function headersOf(init: RequestInit): Headers {
  return new Headers(init.headers as HeadersInit);
}

const okJson = () =>
  new Response('{"items":[]}', {
    status: 200,
    headers: { 'content-type': 'application/json', 'x-correlation-id': 'cid-upstream' },
  });

describe('the browser calls this app, and this app calls the API with the credential', () => {
  it('serves the forward at a same-origin relative base, so the bundle names no origin', () => {
    expect(BFF_BASE_PATH).toBe('/bff/v1');
  });

  it('attaches the credential it is given as a bearer token', async () => {
    const { fetch, calls } = recordingFetch(okJson);
    await forwardWithCredential(new Request('http://localhost/bff/v1/projects'), ['projects'], TARGET, {
      fetch,
    });
    expect(calls).toHaveLength(1);
    expect(headersOf(calls[0]!.init).get('authorization')).toBe(
      'Bearer test-token-not-a-real-credential',
    );
  });

  it('forwards to the upstream origin at the path the segments name', async () => {
    const { fetch, calls } = recordingFetch(okJson);
    await forwardWithCredential(
      new Request('http://localhost/bff/v1/runs/run_01/findings?limit=50&state=open'),
      ['runs', 'run_01', 'findings'],
      TARGET,
      { fetch },
    );
    expect(calls[0]!.url).toBe('http://api:8000/runs/run_01/findings?limit=50&state=open');
  });

  it('replaces a credential the browser tried to supply, and never merges one', async () => {
    const { fetch, calls } = recordingFetch(okJson);
    await forwardWithCredential(
      new Request('http://localhost/bff/v1/projects', {
        headers: { authorization: 'Bearer forged-by-the-browser' },
      }),
      ['projects'],
      TARGET,
      { fetch },
    );
    const sent = headersOf(calls[0]!.init).get('authorization');
    expect(sent).toBe('Bearer test-token-not-a-real-credential');
    expect(sent).not.toContain('forged-by-the-browser');
  });

  // `W53-CLOSE` `C-17`. The operations the contract publishes with an empty security
  // requirement are forwarded with `token: null`, and then nothing at all goes -- not the
  // browser's own header either, which the inbound allowlist already drops.
  it('sends no Authorization at all for a null credential, the browser’s included', async () => {
    const { fetch, calls } = recordingFetch(okJson);
    await forwardWithCredential(
      new Request('http://localhost/bff/v1/auth/token', {
        method: 'POST',
        headers: { authorization: 'Bearer forged-by-the-browser', 'content-type': 'application/json' },
        body: '{}',
      }),
      ['auth', 'token'],
      { upstream: UPSTREAM, token: null },
      { fetch },
    );
    expect(calls).toHaveLength(1);
    expect(headersOf(calls[0]!.init).has('authorization')).toBe(false);
    expect(headersOf(calls[0]!.init).get('content-type')).toBe('application/json');
  });

  it('carries exactly the five request headers the contract surface uses', async () => {
    const { fetch, calls } = recordingFetch(okJson);
    await forwardWithCredential(
      new Request('http://localhost/bff/v1/projects', {
        method: 'POST',
        body: '{"name":"x"}',
        headers: {
          accept: 'application/json',
          'content-type': 'application/json',
          'idempotency-key': 'idem-123',
          range: 'bytes=0-1023',
          'x-correlation-id': 'cid-from-browser',
          cookie: 'session=secret',
          'x-forwarded-for': '203.0.113.9',
          'user-agent': 'a browser',
        },
      }),
      ['projects'],
      TARGET,
      { fetch },
    );
    const sent = headersOf(calls[0]!.init);
    expect(sent.get('accept')).toBe('application/json');
    expect(sent.get('content-type')).toBe('application/json');
    expect(sent.get('idempotency-key')).toBe('idem-123');
    expect(sent.get('range')).toBe('bytes=0-1023');
    expect(sent.get('x-correlation-id')).toBe('cid-from-browser');
    // The allowlist half: a cookie, the proxy's own headers and the user agent do not go.
    expect(sent.get('cookie')).toBeNull();
    expect(sent.get('x-forwarded-for')).toBeNull();
    expect(sent.get('user-agent')).toBeNull();
    expect([...sent.keys()].sort()).toEqual([
      'accept',
      'authorization',
      'content-type',
      'idempotency-key',
      'range',
      'x-correlation-id',
    ]);
  });

  it('returns the upstream status and body bytes verbatim, so a 401 arrives as a 401', async () => {
    const envelope =
      '{"contract_version":"1.10.0","correlation_id":"cid-abc",' +
      '"error_code":"authentication_required","message":"No valid authenticated subject was presented.",' +
      '"retryable":false}';
    const { fetch } = recordingFetch(
      () =>
        new Response(envelope, {
          status: 401,
          headers: { 'content-type': 'application/json', 'x-correlation-id': 'cid-abc' },
        }),
    );
    const response = await forwardWithCredential(
      new Request('http://localhost/bff/v1/projects'),
      ['projects'],
      TARGET,
      { fetch },
    );
    expect(response.status).toBe(401);
    expect(await response.text()).toBe(envelope);
    expect(response.headers.get('x-correlation-id')).toBe('cid-abc');
  });

  it('republishes exactly its response headers and drops everything else', async () => {
    const { fetch } = recordingFetch(
      () =>
        new Response('bytes', {
          status: 200,
          headers: {
            'content-type': 'text/csv',
            'content-disposition': 'attachment; filename="run.csv"',
            'x-correlation-id': 'cid-csv',
            'set-cookie': 'upstream=leak',
            server: 'uvicorn',
            vary: 'Accept',
          },
        }),
    );
    const response = await forwardWithCredential(
      new Request('http://localhost/bff/v1/runs/run_01/export.csv'),
      ['runs', 'run_01', 'export.csv'],
      TARGET,
      { fetch },
    );
    expect(response.headers.get('content-type')).toBe('text/csv');
    expect(response.headers.get('content-disposition')).toBe('attachment; filename="run.csv"');
    expect(response.headers.get('x-correlation-id')).toBe('cid-csv');
    expect(response.headers.get('set-cookie')).toBeNull();
    expect(response.headers.get('server')).toBeNull();
    expect(response.headers.get('vary')).toBeNull();
    expect([...response.headers.keys()].sort()).toEqual([
      'content-disposition',
      'content-type',
      'x-correlation-id',
    ]);
  });

  // `W55B-FIX`: a crop is an image the browser keeps (X-4), and the upload gate's busy refusal
  // says when to try again (`W55B-QA-01` O-1); both answers reach the browser whole.
  it('carries a crop’s ETag and Cache-Control, and a busy refusal’s Retry-After, to the browser', async () => {
    const crop = recordingFetch(
      () =>
        new Response(new Uint8Array([137, 80, 78, 71]), {
          status: 200,
          headers: {
            'content-type': 'image/png',
            etag: '"6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f"',
            'cache-control': 'private, max-age=3600',
            'x-correlation-id': 'cid-crop',
          },
        }),
    );
    const cropped = await forwardWithCredential(
      new Request('http://localhost/bff/v1/versions/ver_01/portal-blocks/blk_01/crop'),
      ['versions', 'ver_01', 'portal-blocks', 'blk_01', 'crop'],
      TARGET,
      { fetch: crop.fetch },
    );
    expect(cropped.headers.get('etag')).toBe('"6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f"');
    expect(cropped.headers.get('cache-control')).toBe('private, max-age=3600');

    const busy = recordingFetch(
      () =>
        new Response('{"error_code":"dependency_unavailable"}', {
          status: 503,
          headers: { 'content-type': 'application/json', 'retry-after': '5', 'x-correlation-id': 'cid-busy' },
        }),
    );
    const refused = await forwardWithCredential(
      new Request('http://localhost/bff/v1/projects', { method: 'POST', body: '{"name":"x"}' }),
      ['projects'],
      TARGET,
      { fetch: busy.fetch },
    );
    expect(refused.status).toBe(503);
    expect(refused.headers.get('retry-after')).toBe('5');
  });

  // `W55A-CONTENT-01` (plan §A3.5). The viewer's PDF reader pages a large document by
  // asking for one byte range; the API answers `206` with the window and its position.
  it('passes one Range up and the 206 with its range headers down, verbatim', async () => {
    const window = new Uint8Array([37, 80, 68, 70]);
    const { fetch, calls } = recordingFetch(
      () =>
        new Response(window, {
          status: 206,
          headers: {
            'content-type': 'application/pdf',
            'content-length': '4',
            'content-range': 'bytes 0-3/58978',
            'accept-ranges': 'bytes',
            'x-correlation-id': 'cid-range',
          },
        }),
    );
    const response = await forwardWithCredential(
      new Request('http://localhost/bff/v1/versions/ver_01/content', {
        headers: { range: 'bytes=0-3' },
      }),
      ['versions', 'ver_01', 'content'],
      TARGET,
      { fetch },
    );
    expect(headersOf(calls[0]!.init).get('range')).toBe('bytes=0-3');
    expect(response.status).toBe(206);
    expect(response.headers.get('content-type')).toBe('application/pdf');
    expect(response.headers.get('content-length')).toBe('4');
    expect(response.headers.get('content-range')).toBe('bytes 0-3/58978');
    expect(response.headers.get('accept-ranges')).toBe('bytes');
    expect(new Uint8Array(await response.arrayBuffer())).toEqual(window);
  });

  it('declares the whole document’s length on a 200, so a stopped stream arrives short', async () => {
    const { fetch } = recordingFetch(
      () =>
        new Response('%PDF-1.7', {
          status: 200,
          headers: {
            'content-type': 'application/pdf',
            'content-length': '8',
            'accept-ranges': 'bytes',
            'x-correlation-id': 'cid-whole',
          },
        }),
    );
    const response = await forwardWithCredential(
      new Request('http://localhost/bff/v1/versions/ver_01/content'),
      ['versions', 'ver_01', 'content'],
      TARGET,
      { fetch },
    );
    expect(response.status).toBe(200);
    expect(response.headers.get('content-length')).toBe('8');
    expect(response.headers.get('accept-ranges')).toBe('bytes');
    expect(response.headers.get('content-range')).toBeNull();
  });

  it('drops content-length when the runtime decoded a content-encoding it does not republish', async () => {
    const { fetch } = recordingFetch(
      () =>
        new Response('{"items":[]}', {
          status: 200,
          headers: {
            'content-type': 'application/json',
            'content-encoding': 'gzip',
            'content-length': '7',
            'x-correlation-id': 'cid-gzip',
          },
        }),
    );
    const response = await forwardWithCredential(
      new Request('http://localhost/bff/v1/projects'),
      ['projects'],
      TARGET,
      { fetch },
    );
    expect(response.headers.get('content-encoding')).toBeNull();
    expect(response.headers.get('content-length')).toBeNull();
    expect(response.headers.get('content-type')).toBe('application/json');
  });

  it('sends a request body on a write and none on a read', async () => {
    const write = recordingFetch(okJson);
    await forwardWithCredential(
      new Request('http://localhost/bff/v1/projects', { method: 'POST', body: '{"name":"x"}' }),
      ['projects'],
      TARGET,
      { fetch: write.fetch },
    );
    expect(write.calls[0]!.init.body).toBeDefined();

    const read = recordingFetch(okJson);
    await forwardWithCredential(
      new Request('http://localhost/bff/v1/projects'),
      ['projects'],
      TARGET,
      { fetch: read.fetch },
    );
    expect(read.calls[0]!.init.body).toBeUndefined();
  });

  it('carries no body on a status that may not have one', async () => {
    const { fetch } = recordingFetch(() => new Response(null, { status: 204 }));
    const response = await forwardWithCredential(
      new Request('http://localhost/bff/v1/projects/p_1', { method: 'DELETE' }),
      ['projects', 'p_1'],
      TARGET,
      { fetch },
    );
    expect(response.status).toBe(204);
    expect(response.body).toBeNull();
  });
});

// `W55B-STREAM-01` (plan §B3.2). An upload is a portal bundle of up to 250 MiB: the forward
// hands the request's own stream to `fetch` and reads none of it, under a deadline that is
// ten seconds inside the proxy's. Every expected value is a literal.

/** A request body whose chunks are produced only when something reads them. */
function pulledOnDemand(chunks: number, size: number): { stream: ReadableStream<Uint8Array>; pulled: () => number } {
  let pulled = 0;
  const stream = new ReadableStream<Uint8Array>(
    {
      pull(controller) {
        if (pulled === chunks) {
          controller.close();
          return;
        }
        pulled += 1;
        controller.enqueue(new Uint8Array(size).fill(7));
      },
    },
    { highWaterMark: 0 },
  );
  return { stream, pulled: () => pulled };
}

const UPLOAD_URL = 'http://localhost/bff/v1/projects/prj_01/documents';
const UPLOAD_SEGMENTS = ['projects', 'prj_01', 'documents'] as const;

function uploadRequest(
  body: ReadableStream<Uint8Array>,
  extra: { signal?: AbortSignal; headers?: Record<string, string> } = {},
): Request {
  return new Request(UPLOAD_URL, {
    method: 'POST',
    body,
    duplex: 'half',
    headers: { 'content-type': 'multipart/form-data; boundary=x', ...extra.headers },
    ...(extra.signal === undefined ? {} : { signal: extra.signal }),
  } as RequestInit & { duplex: 'half' });
}

async function drain(stream: ReadableStream<Uint8Array>): Promise<number> {
  const reader = stream.getReader();
  let total = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) return total;
    total += value.byteLength;
  }
}

describe('a request body is streamed to the API under a deadline', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('hands fetch the request’s own stream, unread, with duplex half', async () => {
    const { stream, pulled } = pulledOnDemand(8, 1024);
    const request = uploadRequest(stream);
    let pulledAtCall = -1;
    let received = 0;
    const calls: Seen[] = [];
    const fetch: FetchLike = async (url, init) => {
      pulledAtCall = pulled();
      calls.push({ url, init });
      received = await drain(init.body as ReadableStream<Uint8Array>);
      return okJson();
    };

    const response = await forwardWithCredential(request, UPLOAD_SEGMENTS, TARGET, { fetch });

    expect(response.status).toBe(200);
    expect(calls[0]!.url).toBe('http://api:8000/projects/prj_01/documents');
    expect(calls[0]!.init.body).toBe(request.body);
    expect((calls[0]!.init as RequestInit & { duplex?: string }).duplex).toBe('half');
    // Nothing had read the body when the API was called: it was not buffered first.
    expect(pulledAtCall).toBe(0);
    // And every byte then arrived, through the stream and only through it.
    expect(received).toBe(8 * 1024);
    expect(headersOf(calls[0]!.init).get('content-type')).toBe('multipart/form-data; boundary=x');
  });

  it('streams the next version of a document exactly as it streams the first upload', async () => {
    // `W59-VERSION-UPLOAD-01`: `uploadDocumentVersion` is the other multipart operation. The
    // forward decides by the body, not by the path, so its bundle takes the same stream, the
    // same refusal of redirects and the same deadline -- nothing here holds it whole.
    const { stream, pulled } = pulledOnDemand(8, 1024);
    const request = new Request('http://localhost/bff/v1/projects/prj_01/documents/doc_01/versions', {
      method: 'POST',
      body: stream,
      duplex: 'half',
      headers: { 'content-type': 'multipart/form-data; boundary=x' },
    } as RequestInit & { duplex: 'half' });
    let pulledAtCall = -1;
    let received = 0;
    const calls: Seen[] = [];
    const fetch: FetchLike = async (url, init) => {
      pulledAtCall = pulled();
      calls.push({ url, init });
      received = await drain(init.body as ReadableStream<Uint8Array>);
      return okJson();
    };

    const response = await forwardWithCredential(
      request,
      ['projects', 'prj_01', 'documents', 'doc_01', 'versions'],
      TARGET,
      { fetch },
    );

    expect(response.status).toBe(200);
    expect(calls[0]!.url).toBe('http://api:8000/projects/prj_01/documents/doc_01/versions');
    expect(calls[0]!.init.body).toBe(request.body);
    expect((calls[0]!.init as RequestInit & { duplex?: string }).duplex).toBe('half');
    expect(calls[0]!.init.redirect).toBe('error');
    expect(calls[0]!.init.window).toBeNull();
    expect(calls[0]!.init.signal).toBeInstanceOf(AbortSignal);
    expect(pulledAtCall).toBe(0);
    expect(received).toBe(8 * 1024);
  });

  it('refuses redirects and names no window, so fetch neither clones the request nor tees its body', async () => {
    const { stream } = pulledOnDemand(2, 16);
    const { fetch, calls } = recordingFetch(okJson);
    await forwardWithCredential(uploadRequest(stream), UPLOAD_SEGMENTS, TARGET, { fetch });
    expect(calls[0]!.init.redirect).toBe('error');
    expect(calls[0]!.init.window).toBeNull();

    // A small JSON write is read whole and keeps fetch's defaults: nothing to tee.
    const json = recordingFetch(okJson);
    await forwardWithCredential(
      new Request('http://localhost/bff/v1/projects', { method: 'POST', body: '{"name":"x"}' }),
      ['projects'],
      TARGET,
      { fetch: json.fetch },
    );
    expect(json.calls[0]!.init.redirect).toBeUndefined();
    expect('window' in json.calls[0]!.init).toBe(false);
  });

  it('through the real fetch, the upload stream is read once and never teed', async () => {
    // `W55B-REHEARSAL-01` measured the BFF's resident set growing by about the upload's size:
    // undici's fetch cloned the request and teed the body, and the branch kept for a redirect
    // held every byte. Here the runtime's own fetch carries a 4 MiB stream to a real local
    // server; `tee` is watched on the stream class undici uses, and the server receives
    // every byte.
    const { createServer } = await import('node:http');
    let received = 0;
    const server = createServer((req, res) => {
      req.on('data', (chunk: Buffer) => {
        received += chunk.length;
      });
      req.on('end', () => {
        res.writeHead(201, { 'content-type': 'application/json' });
        res.end('{"ok":true}');
      });
    });
    await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
    const address = server.address();
    const port = typeof address === 'object' && address !== null ? address.port : 0;
    const tee = vi.spyOn(ReadableStream.prototype, 'tee');
    try {
      const { stream } = pulledOnDemand(64, 64 * 1024);
      const response = await forwardWithCredential(uploadRequest(stream), UPLOAD_SEGMENTS, {
        upstream: `http://127.0.0.1:${port}`,
        token: TOKEN,
      });
      expect(response.status).toBe(201);
      expect(received).toBe(64 * 64 * 1024);
      expect(tee).not.toHaveBeenCalled();
    } finally {
      tee.mockRestore();
      await new Promise<void>((resolve) => server.close(() => resolve()));
    }
  });

  it('never asks the request for its bytes whole', async () => {
    const { stream } = pulledOnDemand(2, 16);
    const request = uploadRequest(stream);
    const arrayBuffer = vi.spyOn(request, 'arrayBuffer');
    const blob = vi.spyOn(request, 'blob');
    const text = vi.spyOn(request, 'text');
    const { fetch } = recordingFetch(okJson);

    await forwardWithCredential(request, UPLOAD_SEGMENTS, TARGET, { fetch });

    expect(arrayBuffer).not.toHaveBeenCalled();
    expect(blob).not.toHaveBeenCalled();
    expect(text).not.toHaveBeenCalled();
    expect(request.bodyUsed).toBe(false);
  });

  it('streams a body that declares itself large, whatever its type', async () => {
    expect(STREAM_FROM_BYTES).toBe(1_048_576);
    const large = recordingFetch(okJson);
    const request = new Request('http://localhost/bff/v1/projects/prj_01/documents', {
      method: 'POST',
      body: pulledOnDemand(1, 8).stream,
      duplex: 'half',
      headers: { 'content-type': 'application/zip', 'content-length': '1048577' },
    } as RequestInit & { duplex: 'half' });
    await forwardWithCredential(request, UPLOAD_SEGMENTS, TARGET, { fetch: large.fetch });
    expect(large.calls[0]!.init.body).toBe(request.body);

    const small = recordingFetch(okJson);
    await forwardWithCredential(
      new Request('http://localhost/bff/v1/projects/prj_01/documents', {
        method: 'POST',
        body: '{"k":1}',
        headers: { 'content-type': 'application/json', 'content-length': '1048576' },
      }),
      UPLOAD_SEGMENTS,
      TARGET,
      { fetch: small.fetch },
    );
    expect(small.calls[0]!.init.body).toBeInstanceOf(ArrayBuffer);
  });

  it('still reads a small JSON write whole and sends nothing for a body that is empty', async () => {
    const json = recordingFetch(okJson);
    await forwardWithCredential(
      new Request('http://localhost/bff/v1/projects', { method: 'POST', body: '{"name":"x"}' }),
      ['projects'],
      TARGET,
      { fetch: json.fetch },
    );
    const sent = json.calls[0]!.init.body as ArrayBuffer;
    expect(sent).toBeInstanceOf(ArrayBuffer);
    expect(new TextDecoder().decode(sent)).toBe('{"name":"x"}');
    expect((json.calls[0]!.init as RequestInit & { duplex?: string }).duplex).toBeUndefined();

    const empty = recordingFetch(okJson);
    await forwardWithCredential(
      new Request('http://localhost/bff/v1/runs/run_01/cancel', { method: 'POST', body: '' }),
      ['runs', 'run_01', 'cancel'],
      TARGET,
      { fetch: empty.fetch },
    );
    expect(empty.calls[0]!.init.body).toBeUndefined();
    expect(empty.calls[0]!.init.signal).toBeUndefined();
  });

  it('carries a 290 second deadline on a write and aborts the upstream request when it passes', async () => {
    const deadline = new AbortController();
    const timeout = vi.spyOn(AbortSignal, 'timeout').mockReturnValue(deadline.signal);
    const { fetch, calls } = recordingFetch(okJson);

    await forwardWithCredential(uploadRequest(pulledOnDemand(1, 1).stream), UPLOAD_SEGMENTS, TARGET, {
      fetch,
    });

    expect(UPSTREAM_DEADLINE_MS).toBe(290_000);
    expect(timeout).toHaveBeenCalledTimes(1);
    expect(timeout).toHaveBeenCalledWith(290_000);
    const signal = calls[0]!.init.signal as AbortSignal;
    expect(signal.aborted).toBe(false);
    deadline.abort(new DOMException('timeout', 'TimeoutError'));
    expect(signal.aborted).toBe(true);
    expect((signal.reason as DOMException).name).toBe('TimeoutError');
  });

  it('puts the deadline on a small write as well, and on nothing that sends no body', async () => {
    const timeout = vi.spyOn(AbortSignal, 'timeout');
    const write = recordingFetch(okJson);
    await forwardWithCredential(
      new Request('http://localhost/bff/v1/projects', { method: 'POST', body: '{"name":"x"}' }),
      ['projects'],
      TARGET,
      { fetch: write.fetch },
    );
    expect(timeout).toHaveBeenCalledWith(290_000);
    expect(write.calls[0]!.init.signal).toBeDefined();

    const remove = recordingFetch(() => new Response(null, { status: 204 }));
    await forwardWithCredential(
      new Request('http://localhost/bff/v1/projects/p_1', { method: 'DELETE' }),
      ['projects', 'p_1'],
      TARGET,
      { fetch: remove.fetch },
    );
    expect(remove.calls[0]!.init.signal).toBeUndefined();
  });

  it('puts no deadline on a read, so a long download is not cut off', async () => {
    const timeout = vi.spyOn(AbortSignal, 'timeout');
    const { fetch, calls } = recordingFetch(okJson);

    await forwardWithCredential(
      new Request('http://localhost/bff/v1/versions/ver_01/content'),
      ['versions', 'ver_01', 'content'],
      TARGET,
      { fetch },
    );

    expect(timeout).not.toHaveBeenCalled();
    expect(calls[0]!.init.signal).toBeUndefined();
  });

  it('stops the upstream upload when the browser goes away, so the API’s slot is freed', async () => {
    const browser = new AbortController();
    const request = uploadRequest(pulledOnDemand(1, 1).stream, { signal: browser.signal });
    const { fetch, calls } = recordingFetch(okJson);

    await forwardWithCredential(request, UPLOAD_SEGMENTS, TARGET, { fetch });

    const signal = calls[0]!.init.signal as AbortSignal;
    expect(signal.aborted).toBe(false);
    browser.abort();
    expect(signal.aborted).toBe(true);
  });

  it('answers a deadline that passed as a retryable 503 that does not claim nothing was applied', async () => {
    const fetch: FetchLike = () =>
      Promise.reject(new DOMException('The operation was aborted due to timeout', 'TimeoutError'));

    const response = await forwardWithCredential(
      uploadRequest(pulledOnDemand(1, 1).stream, { headers: { 'x-correlation-id': 'cid-slow' } }),
      UPLOAD_SEGMENTS,
      TARGET,
      { fetch },
    );

    expect(response.status).toBe(503);
    const body = (await response.json()) as {
      error_code: string;
      retryable: boolean;
      message: string;
      correlation_id: string;
    };
    expect(body.error_code).toBe('dependency_unavailable');
    expect(body.retryable).toBe(true);
    expect(body.correlation_id).toBe('cid-slow');
    expect(body.message).toContain('мог быть выполнен');
    expect(body.message).not.toContain('Ничего не применено');
    expect(JSON.stringify(body)).not.toContain(TOKEN);
  });

  it('still says nothing was applied when an upload never reached the API', async () => {
    const fetch: FetchLike = () => Promise.reject(new Error('ECONNREFUSED'));
    const response = await forwardWithCredential(
      uploadRequest(pulledOnDemand(1, 1).stream),
      UPLOAD_SEGMENTS,
      TARGET,
      { fetch },
    );
    const body = (await response.json()) as { message: string };
    expect(response.status).toBe(503);
    expect(body.message).toContain('Ничего не применено');
  });

  it('reports a read that timed out as the unreachable API it always was', async () => {
    const fetch: FetchLike = () => Promise.reject(new DOMException('timeout', 'TimeoutError'));
    const response = await forwardWithCredential(
      new Request('http://localhost/bff/v1/projects'),
      ['projects'],
      TARGET,
      { fetch },
    );
    const body = (await response.json()) as { message: string };
    expect(body.message).toContain('Ничего не применено');
  });

  it('adds no undici agent or dispatcher: the transport stays the runtime’s own', () => {
    const source = readFileSync(
      fileURLToPath(new URL('../../../src/shared/api/credentialed-forward.ts', import.meta.url)),
      'utf8',
    );
    const code = source
      .split('\n')
      .filter((line) => !line.trim().startsWith('*') && !line.trim().startsWith('//') && !line.trim().startsWith('/*'))
      .join('\n');
    expect(code).not.toMatch(/undici/i);
    expect(code).not.toMatch(/dispatcher/);
    expect(code).not.toMatch(/new\s+Agent/);
    expect(code).not.toMatch(/headersTimeout|bodyTimeout/);
  });
});

describe('the forward reaches nothing above the API base', () => {
  it('builds a path from segments, percent-encoding each one', () => {
    expect(buildUpstreamPath(['runs', 'run_01HZ', 'findings'])).toBe('/runs/run_01HZ/findings');
    // A space and a `?` are encoded rather than allowed to end the path or start a query.
    expect(buildUpstreamPath(['projects', 'a b?c'])).toBe('/projects/a%20b%3Fc');
  });

  it('refuses a dot segment, an empty segment and a separator inside a segment', () => {
    expect(() => buildUpstreamPath(['..'])).toThrow(ForwardPathError);
    expect(() => buildUpstreamPath(['runs', '..', '..', 'admin'])).toThrow(ForwardPathError);
    expect(() => buildUpstreamPath(['.'])).toThrow(ForwardPathError);
    expect(() => buildUpstreamPath([''])).toThrow(ForwardPathError);
    expect(() => buildUpstreamPath([])).toThrow(ForwardPathError);
  });

  it('answers a traversal attempt with a contract envelope and never calls the API', async () => {
    const { fetch, calls } = recordingFetch(okJson);
    const response = await forwardWithCredential(
      new Request('http://localhost/bff/v1/..'),
      ['..', '..', 'etc'],
      TARGET,
      { fetch },
    );
    expect(calls).toHaveLength(0);
    expect(response.status).toBe(404);
    const body = (await response.json()) as { error_code: string; retryable: boolean };
    expect(body.error_code).toBe('not_found');
    expect(body.retryable).toBe(false);
  });
});

describe('the forward answers an ErrorEnvelope even when the API never did', () => {
  it('reports an unreachable API as a retryable dependency_unavailable', async () => {
    const fetch: FetchLike = () => Promise.reject(new Error('ECONNREFUSED'));
    const response = await forwardWithCredential(
      new Request('http://localhost/bff/v1/projects', {
        headers: { 'x-correlation-id': 'cid-from-browser' },
      }),
      ['projects'],
      TARGET,
      { fetch },
    );
    expect(response.status).toBe(503);
    const body = (await response.json()) as {
      error_code: string;
      retryable: boolean;
      correlation_id: string;
      contract_version: string;
      message: string;
    };
    expect(body.error_code).toBe('dependency_unavailable');
    // The catalog pins this one retryable, and the envelope is where the client reads it.
    expect(body.retryable).toBe(true);
    expect(body.contract_version).toBe('1.10.0');
    expect(body.correlation_id).toBe('cid-from-browser');
    // The credential must not appear in anything the browser can read.
    expect(JSON.stringify(body)).not.toContain(TOKEN);
  });

  it('mints a correlation id the contract pattern accepts when the browser sent none', async () => {
    const minted = mintForwardCorrelationId();
    expect(minted).toMatch(/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/);
    expect(minted.startsWith('web-')).toBe(true);

    const fetch: FetchLike = () => Promise.reject(new Error('down'));
    const response = await forwardWithCredential(
      new Request('http://localhost/bff/v1/projects'),
      ['projects'],
      TARGET,
      { fetch },
    );
    const body = (await response.json()) as { correlation_id: string };
    expect(body.correlation_id).toMatch(/^web-[0-9a-f]{32}$/);
    expect(response.headers.get('x-correlation-id')).toBe(body.correlation_id);
  });
});
