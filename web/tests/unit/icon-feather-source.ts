/**
 * Feather's own files, as fetched, frozen here so the copy can be checked against its
 * source without a network.
 *
 * `D-52` records the obligation: the geometry in `shared/ui/icon.tsx` is Feather's, MIT,
 * and a copy carries a notice. `web/NOTICE` discharges it by naming the Feather file each
 * icon came from. That claim is only worth something if it can be checked, and checking it
 * by fetching from GitHub would make a test depend on the network and on whatever `main`
 * says today -- so the bytes that were actually copied are recorded here instead, with the
 * URL and digest they were taken from.
 *
 * Retrieved 2026-09-22 from
 * `https://raw.githubusercontent.com/feathericons/feather/main/icons/<name>.svg`.
 * Each digest below is `sha256` of the fetched file, unmodified.
 *
 * These strings are Feather's work, not this repository's, and are reproduced under the
 * MIT licence whose text `web/NOTICE` carries in full.
 *
 * Nothing imports this outside `icon-provenance.test.ts`. It is evidence, not a module the
 * application builds on: `shared/ui/icon.tsx` holds the geometry the application renders.
 */

/** Feather file name -> the document as fetched. */
export const FEATHER_SVG: Readonly<Record<string, string>> = {
  // sha256 d479596013ee6703bb7bb30515c5306e8624499643d947d9b9576d9003650b33
  'folder':
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>',

  // sha256 2d2602aaaf18c691bd579bdc7fb07604cb70ff8b5b1db1e5e7997975824a9446
  'file-text':
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>',

  // sha256 4803c6dfbe4b6440e8695d86aefc2fdd98392e51fae2e590e993d94f8ce59d1c
  'layers':
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>',

  // sha256 c28e8199498d8f2083022a1af3cf67481806a96d069ff918b263f6d80e0e0990
  'play-circle':
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/></svg>',

  // sha256 07104ec4551b0d83a24d27d2b2f729c91ef0a1ed04532dfcfaa34495108f8df0
  'flag':
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>',

  // sha256 5f27d6498c8d1746ef65458aedc42b51052a4ef1c52fb5d0cd900c19676a9db3
  'search':
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',

  // sha256 26e60cb6ec402216b27e2eeac412841b1ef8e6d36e770f85888f55b01c8a37f5
  'download':
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>',

  // sha256 064372f5e25f78f8187888761abd8c61fa6e6620ee68adc9871416363d1ff983
  'upload':
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>',

  // sha256 1df722c1758fb0cb4868c38eb038fecf64c3717fe09ceaeb43783b70d027a1c4
  'check':
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',

  // sha256 9d855cf8aab176e80a0448bee43c56338d28c59ec91637ce034cced006e282a2
  'x':
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',

  // sha256 6b348b2fb5661dd43e4cedc32c167a4b389809660037f91cf6351667967202d9
  'message-square':
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',

  // sha256 a71d26dae8d7bd2c172a502258e13793ecf3fa80935d42f7fa692b8d182d0794
  'arrow-left':
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>',

  // sha256 f341a7b2b0f0ce280c2ff80ba7b4519323e2503d66575443ffe07c8f0a87123d
  'arrow-right':
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>',

  // sha256 e39e7c659afaa9e714dfd419cf3a2e0bc732ee31f003eb8a78dd248afc6b2d72
  'alert-triangle':
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',

  // sha256 e47498ca4bedaef470e42a6a70cbac15373869853a82f38642998887edf6cfc6
  'alert-circle':
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',

  // sha256 0954a83db1736bb3e7108a00111ba5fccae9e16c6c711993cbe3c9984dc8aaec
  'check-circle':
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',

  // sha256 6c346fdb49a8af368b91a07fb43a8b8d9419af84ca005a06ac075679a9ee2380
  sun:
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>',
  // sha256 ff41660bed6944d45049192d789b6c453ec133bd3e3ccb232907013c1a5ac2af
  moon:
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>',
};
