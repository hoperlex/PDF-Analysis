/**
 * `D-329`: a lazy widget's server markup must not depend on what the server process has loaded.
 *
 * The product's `next/dynamic` wrappers (`_pages/<slice>/ui/lazy-*.tsx`) were server-rendered. In a
 * process that had not yet loaded a widget's chunk, the first request wrote the wrapper's
 * fallback and STREAMED the widget behind it (`<!--$?--><template id="B:0">` … `$RC`); from the
 * second request on the chunk was resolved and the widget was in the first bytes. The streamed
 * variant is revealed, and so hydrated, a few hundred milliseconds after the first paint. By
 * then a sibling that mounted with the page had often filled the same query-cache entry, so the
 * widget's first client render drew its data (`SectionsPanel`'s note) where the server had drawn
 * «Загрузка: разделы проекта…»: React error #418, once per route per server start (lane V,
 * 2026-11-07, 4 of 5 fresh stands; reproduced 3 of 16 cold loads on a throwaway server).
 *
 * The wrappers now pass `ssr: false`: the server writes the fallback on every request and the
 * widget exists only on the client. This test serves each wrapper TWICE through React's streaming
 * renderer and the app router's `next/dynamic` — once before the chunk has been asked for and once
 * after any loader the first response started has settled — and holds that
 *
 *   - the server wrote the wrapper's bare «Загрузка…» and nothing of the widget, with no streamed
 *     Suspense boundary (`<template id="B:`);
 *   - the two responses are the same bytes, so what the server sends no longer depends on the
 *     process's history;
 *   - the server never started loading the chunk (a loader that is called on the server is a
 *     loader that can still be in flight when the shell is written).
 *
 * Not modelled: the streaming itself. Under `renderToPipeableStream` here the boundary completes
 * before the first flush, so the pre-fix variant fails on the first two points (the widget is in
 * the response) rather than on a `$?` boundary; the streamed variant and the mismatch were
 * measured on a built server (`DEBT_REGISTER.md`, `D-329`).
 *
 * `next/dynamic` is the APP ROUTER's implementation (`next/dist/shared/lib/app-dynamic`), not the
 * pages one vitest would otherwise resolve, because that is the one the build bundles for `app/`.
 * It is wrapped only to count and await the loader's promises.
 */

import { Writable } from 'node:stream';

import { QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import type { ComponentType } from 'react';
import { renderToPipeableStream } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

import { newClient } from '../screens/harness';
import { PROJECT_UID, RUN_ID, VERSION_UID } from '../review/fixtures';

const loader = vi.hoisted(() => ({ started: 0, promises: [] as Promise<unknown>[] }));

vi.mock('next/dynamic', async () => {
  const mod = (await import('next/dist/shared/lib/app-dynamic')) as unknown as {
    default: ((...args: unknown[]) => unknown) & { default?: (...args: unknown[]) => unknown };
  };
  const appDynamic = typeof mod.default.default === 'function' ? mod.default.default : mod.default;
  return {
    default: (load: () => Promise<unknown>, options?: unknown) =>
      appDynamic(() => {
        loader.started += 1;
        const promise = load();
        loader.promises.push(promise);
        return promise;
      }, options),
  };
});

/** One response of the streaming renderer, everything it writes to the end of the stream. */
function serve(element: ReturnType<typeof createElement>): Promise<string> {
  return new Promise((resolve, reject) => {
    const chunks: string[] = [];
    const sink = new Writable({
      write(chunk: Buffer | string, _encoding, done) {
        chunks.push(String(chunk));
        done();
      },
    });
    sink.on('finish', () => resolve(chunks.join('')));
    const stream = renderToPipeableStream(element, {
      onShellReady() {
        stream.pipe(sink);
      },
      onShellError: reject,
      // A boundary that gives up on the server (`BailoutToCSRError`) is the design of `ssr: false`.
      onError() {},
    });
  });
}

const BARE_FALLBACK = '>Загрузка…<';

const WRAPPERS: readonly {
  readonly name: string;
  readonly path: string;
  readonly exported: string;
  readonly props: Record<string, unknown>;
}[] = [
  { name: 'the front door’s section overview', path: '@/_pages/home/ui/lazy-home-sections', exported: 'LazyHomeSections', props: {} },
  { name: 'the dashboard', path: '@/_pages/dashboard/ui/lazy-dashboard', exported: 'LazyDashboard', props: {} },
  {
    name: 'the knowledge base',
    path: '@/_pages/knowledge-base/ui/lazy-knowledge-base',
    exported: 'LazyKnowledgeBase',
    props: { records: [], entries: [], isLoading: true },
  },
  {
    name: 'the run progress',
    path: '@/_pages/run/ui/lazy-run-progress',
    exported: 'LazyRunProgress',
    props: { projectUid: PROJECT_UID, runId: RUN_ID },
  },
  {
    name: 'the stage comparison',
    path: '@/_pages/stage-comparison/ui/lazy-stage-comparison',
    exported: 'LazyStageComparison',
    props: { versionUid: VERSION_UID },
  },
];

describe('D-329: a lazy widget is served the same before and after the server has loaded it', () => {
  for (const wrapper of WRAPPERS) {
    it(`${wrapper.name}: the response does not change once the chunk is resolved`, async () => {
      const module = (await import(/* @vite-ignore */ wrapper.path)) as Record<string, ComponentType<Record<string, unknown>>>;
      const Wrapper = module[wrapper.exported];
      expect(Wrapper, `${wrapper.path} exports ${wrapper.exported}`).toBeDefined();
      const page = () => createElement(QueryClientProvider, { client: newClient() }, createElement(Wrapper!, wrapper.props));

      const startedBefore = loader.started;
      const first = await serve(page());
      // Whatever chunk the first response started loading, let it finish before the second.
      await Promise.allSettled(loader.promises.splice(0));
      await new Promise((resolve) => setTimeout(resolve, 25));
      const second = await serve(page());

      expect(first).toBe(second);
      expect(first, 'no Suspense boundary is streamed').not.toContain('<template id="B:');
      expect(first, 'the wrapper’s own fallback is what the server writes').toContain(BARE_FALLBACK);
      expect(loader.started - startedBefore, 'the server must not start loading the widget').toBe(0);
    });
  }
});
