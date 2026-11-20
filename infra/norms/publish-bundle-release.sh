#!/usr/bin/env bash
# `FIRST-INSTALL-02` -- publish a verified norms bundle as the assets of a GitHub release and write the lock file the installer reads.
#
#   infra/norms/publish-bundle-release.sh --bundle DIR [--repo owner/name] [--tag TAG] [--token-file PATH] [--dry-run]
#
# Run by the owner, on the host that holds the bundle, once per new norms snapshot; see publish_bundle_release.py for what it does
# (it needs python3, tar and zstd). This wrapper only runs it at the lowest priority: nice, and ionice in the best-effort class's
# last level, because it reads the whole bundle (about 5 GB) and compresses it on a host other work shares.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
command=(python3 -I "$HERE/publish_bundle_release.py" "$@")
if command -v ionice >/dev/null 2>&1; then command=(ionice -c 2 -n 7 "${command[@]}"); fi
if command -v nice >/dev/null 2>&1; then command=(nice -n 10 "${command[@]}"); fi
exec "${command[@]}"
