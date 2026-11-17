/**
 * Next configuration for the PC-01 web shell.
 *
 * Deliberately minimal: no rewrites to a backend origin, because the API base URL is a
 * runtime value read from `src/shared/config` and never baked into a build-time proxy.
 * No image domains, no i18n, no experimental flag — every one of those is a decision a
 * later slice owner would have to unpick.
 *
 * @type {import('next').NextConfig}
 */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  typescript: {
    // A type error is a build failure wherever a build is checked: `npm run typecheck` runs on
    // every candidate before it is published, and a local `npm run build` type-checks too.
    // The one exception is the production image (`infra/deploy/Dockerfile.web` sets
    // WEB_BUILD_SKIP_TYPECHECK=1): it builds an already-checked tree on the 4 GB serving host,
    // where the checker's ~2 GB peak made `build-overload` stop the deploy (owner, 2026-11-17).
    ignoreBuildErrors: process.env.WEB_BUILD_SKIP_TYPECHECK === '1',
  },
  eslint: {
    // `npm run lint` is the lint gate; the build does not silently re-run it.
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
