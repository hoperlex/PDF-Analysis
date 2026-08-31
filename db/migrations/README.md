# Database migrations

One migration head owner per wave. Use forward migrations and expand→backfill→switch→contract for incompatible changes. A `down` file is not a substitute for data recovery. Migration tests must cover clean install, supported upgrade, and safe re-run/backfill behavior.
