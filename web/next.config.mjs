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
    // A type error is a build failure. Never relaxed.
    ignoreBuildErrors: false,
  },
  eslint: {
    // `npm run lint` is the lint gate; the build does not silently re-run it.
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
