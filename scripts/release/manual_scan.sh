#!/usr/bin/env bash
# `PROD-09-MANUAL-SCAN-01` -- the manual dependency and image scan of the production release
# checklist (`ADR-0021` section 7, line 3; `AD-05` confirmed by `R-146w`; accepted risk `A-3`).
#
# THE OWNER RUNS THIS BY HAND from a machine that can reach the vulnerability feeds. There is no
# CI and no schedule (`R-146h`), and this file must not become either. It installs nothing,
# downloads nothing itself and changes no file in the checkout; the scanners it calls are the
# ones the operator has installed, and they are the ones that use the network.
#
#   scripts/release/manual_scan.sh --check-tools    which required tool is missing; no scan
#   scripts/release/manual_scan.sh                  print the inventory, run the scanners
#
# WHAT IT PRINTS. An inventory first -- the resolved Python packages of `uv.lock`, the npm
# packages of `web/package-lock.json`, the image references that carry a digest in
# `infra/deploy/compose.server.yml` -- then one section per scanner with that scanner's own
# output quoted line by line behind `    | `, then a last line that begins `MANUAL SCAN RESULT:`.
# Attach the whole output and its date to the release record and decide each finding.
#
# THE SCANNERS (all required; a missing one is never skipped quietly):
#
#   pip-audit   the registry packages of `uv.lock`, as `name==version` lines, with
#               `--no-deps --disable-pip --strict`
#   npm audit   `npm audit --package-lock-only --prefix <root>/web`
#   an image scanner, NAMED BY THE OPERATOR in MANUAL_SCAN_IMAGE_SCANNER: the command words up
#               to the image reference, which the helper appends -- for example
#               `MANUAL_SCAN_IMAGE_SCANNER="<scanner> <subcommand> <flags that make a finding
#               exit non-zero>"`. `ADR-0021` section 7 says "an image scanner the operator has
#               installed" and names none, so this file names none either.
#
# THE RULE: the last line says `NO FINDINGS` only when every scanner above was present, ran and
# exited 0, and the inventory could be read. A scanner that is missing, that cannot reach its
# vulnerability database (every scanner above exits non-zero then) or that reports a finding
# makes the last line `NOT COMPLETE` and the exit status non-zero. The helper trusts each
# scanner's exit status; it cannot tell a clean database from a scanner that lies.
#
# WHAT IT DOES NOT COVER, said in the output every time: images the host builds (`api`, `web`,
# `worker`, ... whose `image:` carries no digest) are listed and not scanned by reference; the
# `FROM` lines of the Dockerfiles are not read. `D-122` stays open: this helper makes the
# absence of a scan visible at every release, it does not close the debt.
#
# EXIT: 0 no finding and everything ran; 1 a scanner exited non-zero; 2 a required tool is
# missing, an input could not be read, or the inventory shows something the scanners cannot
# cover (a package from a non-registry source, no image digest at all); 64 usage.
#
# Test seam: MANUAL_SCAN_ROOT names another tree (default: the checkout this file is in).

set -u -o pipefail
export LC_ALL=C

# No `dirname`: this must run, and say what is missing, with a bare PATH.
case "${BASH_SOURCE[0]}" in
    */*) HERE="${BASH_SOURCE[0]%/*}" ;;
    *) HERE="." ;;
esac
HERE="$(cd -- "$HERE" && pwd)"
ROOT="${MANUAL_SCAN_ROOT:-$(cd -- "$HERE/../.." && pwd)}"
IMAGE_SCANNER_VAR="MANUAL_SCAN_IMAGE_SCANNER"
IMAGE_SCANNER=()
if [ -n "${MANUAL_SCAN_IMAGE_SCANNER:-}" ]; then
    IFS=' ' read -r -a IMAGE_SCANNER <<< "$MANUAL_SCAN_IMAGE_SCANNER"
fi

usage() {
    cat <<'EOF'
Usage:
  manual_scan.sh --check-tools   list the required tools; exit non-zero naming each missing one
  manual_scan.sh                 inventory, then pip-audit, npm audit and the operator's image scanner
  manual_scan.sh --help

Environment:
  MANUAL_SCAN_IMAGE_SCANNER   the image scanner command, words only, no shell syntax; the helper
                              appends one image reference. It must exit non-zero on a finding.
Exit: 0 no finding; 1 a scanner exited non-zero; 2 not complete (tool or input missing); 64 usage.
EOF
}

MODE="scan"
case "${1:-}" in
    "") ;;
    --check-tools) MODE="check" ;;
    -h | --help) usage; exit 0 ;;
    *) echo "manual_scan.sh: unknown argument: $1" >&2; usage >&2; exit 64 ;;
esac
if [ "$#" -gt 1 ]; then
    echo "manual_scan.sh: too many arguments" >&2; usage >&2; exit 64
fi

# --- the required tools ------------------------------------------------------------------------

MISSING=()        # one "<tool>: <reason>" per missing tool
HAVE_PYTHON=0
HAVE_PIP_AUDIT=0
HAVE_NPM=0
HAVE_IMAGE_SCANNER=0

check_tools() {
    local path
    MISSING=()
    echo "== Required tools"
    if path="$(command -v python3)" && python3 -I -c 'import tomllib, json, hashlib' >/dev/null 2>&1; then
        HAVE_PYTHON=1
        echo "ok      python3 ($path; reads the lock files)"
    else
        MISSING+=("python3: not found, or older than 3.11 (no tomllib); it reads uv.lock and the other inputs")
    fi
    if path="$(command -v pip-audit)"; then
        HAVE_PIP_AUDIT=1
        echo "ok      pip-audit ($path)"
    else
        MISSING+=("pip-audit: not found on PATH")
    fi
    if path="$(command -v npm)"; then
        HAVE_NPM=1
        echo "ok      npm ($path; npm audit)"
    else
        MISSING+=("npm: not found on PATH (npm audit)")
    fi
    if [ "${#IMAGE_SCANNER[@]}" -eq 0 ]; then
        MISSING+=("image scanner: $IMAGE_SCANNER_VAR is not set; ADR-0021 names no image scanner, set it to the command of the one you have installed")
    elif path="$(command -v "${IMAGE_SCANNER[0]}")"; then
        HAVE_IMAGE_SCANNER=1
        echo "ok      image scanner (${IMAGE_SCANNER[*]} -> $path)"
    else
        MISSING+=("image scanner: '${IMAGE_SCANNER[0]}' (from $IMAGE_SCANNER_VAR) not found on PATH")
    fi
    local m
    for m in "${MISSING[@]+"${MISSING[@]}"}"; do
        echo "MISSING $m"
    done
}

if [ "$MODE" = "check" ]; then
    check_tools
    if [ "${#MISSING[@]}" -gt 0 ]; then
        echo "CHECK-TOOLS: NOT READY -- ${#MISSING[@]} required tool(s) missing (listed above as MISSING)"
        echo "manual_scan.sh: ${#MISSING[@]} required tool(s) missing; a scan would be NOT COMPLETE" >&2
        exit 2
    fi
    echo "CHECK-TOOLS: READY -- every required tool is present"
    exit 0
fi

# --- the scan -----------------------------------------------------------------------------------

TMP="$(mktemp -d "${TMPDIR:-/tmp}/manual-scan.XXXXXX")" || {
    echo "manual_scan.sh: cannot create a temporary directory; NOT COMPLETE" >&2
    echo "MANUAL SCAN RESULT: NOT COMPLETE -- no temporary directory"
    exit 2
}
trap 'rm -rf -- "$TMP"' EXIT

NOT_RUN=()        # scanners that did not run, with the reason
FINDINGS=()       # scanners that exited non-zero
RAN_CLEAN=()      # scanners that ran and exited 0
GAPS=()           # inventory facts the scanners cannot cover

echo "manual_scan.sh -- manual dependency and image scan (ADR-0021 section 7, line 3)"
echo "date (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "tree: $ROOT"
echo "This does not close D-122. It lists what ran; the operator decides each finding."
echo
check_tools
echo

# The inventory. One python3 program reads the three inputs and writes what the scanners are fed.
INVENTORY_OK=0
if [ "$HAVE_PYTHON" -eq 1 ]; then
    python3 -I - "$ROOT" "$TMP" <<'PY'
import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path

root, tmp = Path(sys.argv[1]), Path(sys.argv[2])
errors: list[str] = []
gaps: list[str] = []


def read(rel: str) -> bytes | None:
    try:
        return (root / rel).read_bytes()
    except OSError as exc:
        errors.append(f"cannot read {rel}: {exc.strerror}")
        return None


def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


print("== Inventory")

blob = read("uv.lock")
registry: list[tuple[str, str]] = []
if blob is not None:
    print(f"uv.lock sha256 {digest(blob)}")
    try:
        packages = tomllib.loads(blob.decode("utf-8")).get("package", [])
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"cannot parse uv.lock: {exc}")
        packages = []
    for pkg in packages:
        source = pkg.get("source", {})
        if "registry" in source:
            registry.append((pkg["name"], pkg["version"]))
        elif "virtual" in source:
            print(f"project itself, not a dependency: {pkg['name']}")
        else:
            kind = next(iter(source), "none")
            gaps.append(f"python package {pkg['name']} {pkg.get('version', '?')} has source {kind}, not a registry")
    registry.sort()
    print(f"python packages from a registry: {len(registry)}")
    for name, version in registry:
        print(f"  {name}=={version}")
    (tmp / "requirements.txt").write_text("".join(f"{n}=={v}\n" for n, v in registry), encoding="utf-8")
    if not registry:
        errors.append("uv.lock lists no registry package: pip-audit would audit nothing")

blob = read("web/package-lock.json")
if blob is not None:
    print(f"web/package-lock.json sha256 {digest(blob)}")
    try:
        lock = json.loads(blob)
        entries = lock["packages"]
    except (ValueError, KeyError) as exc:
        errors.append(f"cannot read the packages of web/package-lock.json: {exc!r}")
        entries = {}
    npm: set[str] = set()
    for key, entry in entries.items():
        if key == "" or entry.get("link"):
            continue
        name = key.rsplit("node_modules/", 1)[-1]
        if "version" in entry:
            npm.add(f"{name}@{entry['version']}")
        else:
            gaps.append(f"npm package {name} at {key} has no version")
    print(f"npm packages: {len(npm)}")
    for item in sorted(npm):
        print(f"  {item}")
    if not npm:
        errors.append("web/package-lock.json lists no package: npm audit would audit nothing")

blob = read("infra/deploy/compose.server.yml")
digests: list[str] = []
if blob is not None:
    print(f"infra/deploy/compose.server.yml sha256 {digest(blob)}")
    lines = [ln for ln in blob.decode("utf-8", "replace").splitlines() if not ln.lstrip().startswith("#")]
    text = "\n".join(lines)
    for ref in re.findall(r"[A-Za-z0-9][A-Za-z0-9._/:-]*@sha256:[0-9a-f]{64}", text):
        if ref not in digests:
            digests.append(ref)
    built = sorted({m for m in re.findall(r"^\s*image:\s*(.+?)\s*$", text, re.M) if "@sha256:" not in m})
    print(f"image references with a digest: {len(digests)}")
    for ref in digests:
        print(f"  {ref}")
    print(f"images tagged without a digest, built on the host, NOT scanned by this helper: {len(built)}")
    for ref in built:
        print(f"  {ref}")
    (tmp / "images.txt").write_text("".join(f"{r}\n" for r in digests), encoding="utf-8")
    if not digests:
        errors.append("compose.server.yml names no image digest: the image scanner would scan nothing")

print()
for item in gaps:
    print(f"GAP {item}")
for item in errors:
    print(f"INPUT ERROR {item}")
sys.exit(2 if (errors or gaps) else 0)
PY
    case "$?" in
        0) INVENTORY_OK=1 ;;
        *) GAPS+=("the inventory (see GAP and INPUT ERROR lines above)") ;;
    esac
else
    echo "== Inventory"
    echo "NOT READ: python3 is missing"
    GAPS+=("the inventory (python3 missing)")
fi
echo

quote_file() {
    local line
    while IFS= read -r line || [ -n "$line" ]; do
        printf '    | %s\n' "$line"
    done < "$1"
}

# run_scanner <label> <command word>...: run it, quote its output, record its exit status.
run_scanner() {
    local label="$1" rc
    shift
    echo "== $label"
    echo "command: $*"
    "$@" > "$TMP/scanner.out" 2>&1
    rc=$?
    quote_file "$TMP/scanner.out"
    if [ "$rc" -eq 0 ]; then
        echo "RESULT $label: exit 0, no finding reported"
        RAN_CLEAN+=("$label")
    else
        echo "FINDING $label: exit $rc -- the scanner's output is quoted above; decide it or fix it"
        FINDINGS+=("$label (exit $rc)")
    fi
    echo
}

if [ "$HAVE_PIP_AUDIT" -eq 0 ]; then
    NOT_RUN+=("pip-audit (missing)")
elif [ ! -s "$TMP/requirements.txt" ]; then
    NOT_RUN+=("pip-audit (no requirement list from the inventory)")
else
    run_scanner "pip-audit" pip-audit --requirement "$TMP/requirements.txt" --no-deps --disable-pip --strict
fi

if [ "$HAVE_NPM" -eq 0 ]; then
    NOT_RUN+=("npm audit (missing)")
elif [ ! -r "$ROOT/web/package-lock.json" ]; then
    NOT_RUN+=("npm audit (web/package-lock.json unreadable)")
else
    run_scanner "npm audit" npm audit --package-lock-only --prefix "$ROOT/web"
fi

if [ "$HAVE_IMAGE_SCANNER" -eq 0 ]; then
    NOT_RUN+=("image scanner (missing)")
elif [ ! -s "$TMP/images.txt" ]; then
    NOT_RUN+=("image scanner (no image digest in the inventory)")
else
    while IFS= read -r ref; do
        run_scanner "image scanner: $ref" "${IMAGE_SCANNER[@]}" "$ref"
    done < "$TMP/images.txt"
fi

# --- the verdict --------------------------------------------------------------------------------

echo "== Result"
echo "scanners that ran and exited 0: ${#RAN_CLEAN[@]}"
for item in "${RAN_CLEAN[@]+"${RAN_CLEAN[@]}"}"; do echo "  $item"; done
for item in "${FINDINGS[@]+"${FINDINGS[@]}"}"; do echo "FINDING $item"; done
for item in "${NOT_RUN[@]+"${NOT_RUN[@]}"}"; do echo "NOT RUN $item"; done
for item in "${GAPS[@]+"${GAPS[@]}"}"; do echo "GAP $item"; done
echo "NOT COVERED by this helper: images the host builds (listed in the inventory) and the FROM lines of the Dockerfiles; D-122 stays open."

if [ "${#NOT_RUN[@]}" -gt 0 ] || [ "${#GAPS[@]}" -gt 0 ] || [ "$INVENTORY_OK" -ne 1 ]; then
    echo "MANUAL SCAN RESULT: NOT COMPLETE -- ${#NOT_RUN[@]} scanner(s) not run, ${#GAPS[@]} gap(s), ${#FINDINGS[@]} finding(s)"
    echo "manual_scan.sh: NOT COMPLETE (see NOT RUN, GAP and FINDING lines)" >&2
    exit 2
fi
if [ "${#FINDINGS[@]}" -gt 0 ]; then
    echo "MANUAL SCAN RESULT: NOT COMPLETE -- ${#FINDINGS[@]} scanner run(s) exited non-zero (FINDING lines above)"
    echo "manual_scan.sh: ${#FINDINGS[@]} scanner run(s) exited non-zero" >&2
    exit 1
fi
echo "MANUAL SCAN RESULT: NO FINDINGS -- every required scanner ran and exited 0 (it trusts their exit status; images the host builds are not covered)"
exit 0
