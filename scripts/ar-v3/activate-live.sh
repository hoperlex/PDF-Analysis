#!/usr/bin/env bash
# AR v3 beta activation on the live host: steps 10a (is the snapshot there?), 10b (promote six sets), 11 (seal, install,
# restart) of docs/program/AR-V3-LIVE-ACTIVATION-OWNER-STEPS-01.md, as one script that stops at the first refusal.
#
# Run it from the repository clone that is deployed, as the operator who runs `docker compose` there:
#
#   scripts/ar-v3/activate-live.sh --bundles /path/to/ar-v3-bundles.tar --check   # READ ONLY: tools present, six plans
#   scripts/ar-v3/activate-live.sh --bundles /path/to/ar-v3-bundles.tar           # the same, then asks before each write
#   scripts/ar-v3/activate-live.sh --rollback                                     # withdraw the pack (asks first)
#
# What it never does: print the deployment environment, mint a set id, edit a bundle, push, or touch the database
# other than through promote_cli (the six sets) and v3_pack_cli (read only). It does not run any step without the
# preceding step's expected line. Nothing in it was run against a live host when it was written; the first run on a
# host is `--check`.
#
# Exit codes: 2 usage or precondition, 3 tools missing from the image, 4 a plan did not match, 5 a promotion was not
# verified, 6 seal or offline verify failed, 7 install or restart failed, 8 the operator declined.
set -euo pipefail
umask 077

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
DEPLOY="$ROOT/infra/deploy"
ENV_FILE="${ALPHA_ENV_FILE:-$DEPLOY/env/alpha.env}"
COMPOSE_FILE="$DEPLOY/compose.server.yml"
PROMOTE_DOC="$ROOT/docs/program/AR-V3-PROMOTE-01.md"
DECISIONS="$ROOT/docs/program/ar-v3-beta/decisions.json"
SCOPES="$ROOT/docs/program/ar-v3-beta/scopes.json"
PACK_DST="$DEPLOY/ar-v3-pack/pack.json"
VAR=AR_V3_BETA_PACK_MANIFEST
VAR_VALUE=/run/ar-v3/pack.json
SETS=(F1 F2 A1 A2 S1 S2)
# The bundles archive made on the development host (sha256 of .local/ar-v3-draft/ar-v3-bundles.tar, 2026-10-28).
EXPECTED_BUNDLES_SHA256=4d91ad7ab812e287d8615a87fd9b4348621cc1b45f6b22177df9fbde766083f2
WORK="$ROOT/.local/ar-v3-activation"

BUNDLES="" CHECK=0 ROLLBACK=0
while [ $# -gt 0 ]; do
    case "$1" in
        --bundles) BUNDLES="${2:?--bundles needs a file}"; shift 2 ;;
        --bundles-sha256) EXPECTED_BUNDLES_SHA256="${2:?--bundles-sha256 needs a digest}"; shift 2 ;;
        --check) CHECK=1; shift ;;
        --rollback) ROLLBACK=1; shift ;;
        -h|--help) sed -n '2,17p' "${BASH_SOURCE[0]}"; exit 0 ;;
        *) echo "activate-live.sh: unknown argument: $1" >&2; exit 2 ;;
    esac
done

say() { printf 'activate-live: %s\n' "$*"; }
die() { local code="$1"; shift; printf 'activate-live: STOP: %s\n' "$*" >&2; exit "$code"; }

confirm() {   # confirm WORD "what happens": the operator types WORD, anything else declines
    printf '\n%s\nType %s to go on, anything else stops: ' "$2" "$1" >&2
    local answer=""
    read -r answer || true
    [ "$answer" = "$1" ] || die 8 "declined; nothing further was done"
}

[ -r "$COMPOSE_FILE" ] || die 2 "$COMPOSE_FILE is missing: run this from the deployed clone"
[ -r "$ENV_FILE" ] || die 2 "$ENV_FILE is missing or unreadable (set ALPHA_ENV_FILE to override)"
command -v docker >/dev/null || die 2 "docker is not on PATH"
DC=(docker compose --env-file "$ENV_FILE" --file "$COMPOSE_FILE")

set_env_var() {   # edit the environment file in place, keep its mode and owner, keep one backup, print no value
    local backup tmp
    backup="$ENV_FILE.bak-$(date -u +%Y%m%dT%H%M%SZ)"
    cp -p "$ENV_FILE" "$backup"
    tmp="$(mktemp)"
    grep -v -E "^[[:space:]]*(export[[:space:]]+)?$VAR=" "$ENV_FILE" > "$tmp" || true
    if [ "$1" = set ]; then printf '%s=%s\n' "$VAR" "$VAR_VALUE" >> "$tmp"; fi
    cat "$tmp" > "$ENV_FILE"
    rm -f "$tmp"
    say "$ENV_FILE edited ($1 $VAR); the previous file is kept as $backup (mode unchanged, contains secrets)"
}

wait_running() {   # api and worker both running after `up -d`
    for _ in $(seq 1 30); do
        local running
        running="$("${DC[@]}" ps --status running --services 2>/dev/null || true)"
        if grep -qx api <<<"$running" && grep -qx worker <<<"$running"; then return 0; fi
        sleep 2
    done
    return 1
}

if [ "$ROLLBACK" = 1 ]; then
    confirm ROLLBACK "Withdraw the AR v3 pack: remove $VAR from $ENV_FILE and recreate api and worker.
A Run that is queued or running when they restart dies as failed (see the Rollback section of
AR-V3-LIVE-ACTIVATION-OWNER-STEPS-01.md). Published findings stay. Look at «Очередь» first."
    set_env_var unset
    "${DC[@]}" up -d --no-deps api worker </dev/null
    wait_running || die 7 "api and worker are not both running; read: ${DC[*]} logs --tail 40 api worker"
    say "pack withdrawn; the sealed file at $PACK_DST may stay (nothing reads it without the variable)"
    exit 0
fi

[ -n "$BUNDLES" ] || die 2 "--bundles /path/to/ar-v3-bundles.tar is required"
[ -r "$BUNDLES" ] || die 2 "$BUNDLES is not readable"
for needed in "$DECISIONS" "$SCOPES" "$PROMOTE_DOC"; do
    [ -r "$needed" ] || die 2 "$needed is missing: deploy a tree that holds docs/program/ar-v3-beta/{decisions,scopes}.json and AR-V3-PROMOTE-01.md"
done

GOT_SHA="$(sha256sum "$BUNDLES" | cut -d' ' -f1)"
say "bundles archive sha256 $GOT_SHA"
[ "$GOT_SHA" = "$EXPECTED_BUNDLES_SHA256" ] \
    || die 2 "the archive digest differs from the expected $EXPECTED_BUNDLES_SHA256 (pass --bundles-sha256 only if the integrator gave you a new one)"

# --- workspace: bundles and scopes come in as a read-only bind mount; ABSOLUTE and inside the clone (a missing source
# --- arrives as an EMPTY directory: DEPLOYMENT_RUNBOOK.md, «a mount arrives empty»).
rm -rf "$WORK"
mkdir -p "$WORK/out"
chmod 0700 "$WORK"
tar -C "$WORK" -xf "$BUNDLES"
cp "$SCOPES" "$WORK/scopes.json"
for s in "${SETS[@]}"; do [ -s "$WORK/bundle-$s/request.json" ] || die 2 "bundle-$s is missing or empty in the archive"; done
[ -s "$WORK/scopes.json" ] || die 2 "scopes.json is empty"

cli() {   # one tool call in a throw-away api container, as the operator's uid, stdin closed
    "${DC[@]}" run --rm --no-deps -T --user "$(id -u):$(id -g)" -v "$WORK:/work:ro" --entrypoint python api "$@" </dev/null
}

if ! cli -m auditmanager.norms.retrieval.promote_cli --help >/dev/null 2>&1 \
    || ! cli -m auditmanager.runs.v3_pack_cli --help >/dev/null 2>&1; then
    die 3 "promote_cli or v3_pack_cli is not in the deployed api image: have the integrator deploy a tree that holds them"
fi
say "TOOLS PRESENT"

# --- seal values from the single source, section 6a of the promote record, read and checked BEFORE anything is planned or written
sec6a() { awk '/^### 6a\./{f=1;next} f&&/^## /{exit} f' "$PROMOTE_DOC"; }
field() { sec6a | awk -F'|' -v key="\`--$1\`" 'index($2,key){ n=split($3,a,"`"); if(n>=3){print a[2]; exit} }'; }
REVIEWER="$(field reviewer)" CAPACITY="$(field capacity)" DECISION_REF="$(field decision-ref)" SCOPE_STATEMENT="$(field scope-statement)"
for pair in REVIEWER CAPACITY DECISION_REF SCOPE_STATEMENT; do
    [ -n "${!pair}" ] || die 2 "section 6a of AR-V3-PROMOTE-01.md holds no value for $pair: the tree is not the one this script was written for"
done
DECISIONS_SHA="$(sha256sum "$DECISIONS" | cut -d' ' -f1)"
grep -qF "$DECISIONS_SHA" <<<"$DECISION_REF" \
    || die 2 "sha256 of decisions.json ($DECISIONS_SHA) is not the digest in the decision-ref of section 6a: the decisions changed after the review"
say "seal values read from section 6a; sha256 of decisions.json matches the decision-ref"

# --- step 10a / 10b-1: read-only plans. A missing or different snapshot shows here, before anything is written.
PROMOTE=(-m auditmanager.norms.retrieval.promote_cli)
for s in "${SETS[@]}"; do
    if ! cli "${PROMOTE[@]}" plan "/work/bundle-$s" > "$WORK/out/plan-$s.txt" 2>&1; then
        sed -n '1,12p' "$WORK/out/plan-$s.txt" >&2
        die 4 "plan $s was refused. If the output names a missing snapshot, import the norms first: STAND-NORMS-IMPORT-RUNBOOK-01.md. Do not edit a bundle."
    fi
    grep -qx 'verdict: matched' "$WORK/out/plan-$s.txt" \
        || { sed -n '1,12p' "$WORK/out/plan-$s.txt" >&2; die 4 "plan $s did not print 'verdict: matched'"; }
done
say "ALL SIX PLANS MATCHED"
grep -h -E '^(catalogue_sha256|prompt_part_characters|set_sha256):' "$WORK"/out/plan-*.txt | sort | uniq -c || true
say "expected: prompt_part_characters F1 19249, F2 11958, A1 15032, A2 14143, S1 21921, S2 18930; set_sha256 per scope in AR-V3-PROMOTE-01.md section 4"
if [ "$CHECK" = 1 ]; then say "CHECK OK: nothing was written. Run again without --check to promote, seal and install."; exit 0; fi

# --- step 10b-2: promote and replay, one scope at a time
confirm PROMOTE "WRITES to the live database: promotes the six norm retrieval sets (F1 F2 A1 A2 S1 S2) with their fixed set ids,
then replays each one (nothing changes on a replay). The step is idempotent; it stops at the first refusal."
for s in "${SETS[@]}"; do
    cli "${PROMOTE[@]}" promote "/work/bundle-$s" > "$WORK/out/promote-$s.txt" 2>&1 \
        || { sed -n '1,12p' "$WORK/out/promote-$s.txt" >&2; die 5 "promote $s failed (exit 2 refused, 3 uncertain: the output names the next command). Stop and report."; }
    grep -qx 'promote: verified' "$WORK/out/promote-$s.txt" || die 5 "promote $s did not print 'promote: verified'"
    grep -qx 'replayed: true' "$WORK/out/promote-$s.txt" && say "scope $s was already promoted by an earlier attempt (replayed: true): its digests are read, no new id is made"
    cli "${PROMOTE[@]}" promote "/work/bundle-$s" > "$WORK/out/replay-$s.txt" 2>&1 \
        || die 5 "the replay of $s failed"
    if ! grep -qx 'promote: verified' "$WORK/out/replay-$s.txt" || ! grep -qx 'replayed: true' "$WORK/out/replay-$s.txt"; then
        die 5 "the replay of $s did not print 'promote: verified' and 'replayed: true'"
    fi
done
say "ALL SIX PROMOTED AND REPLAYED"

# --- step 11: seal against the live database (read only); its values were read and checked before step 10a above

"${DC[@]}" run --rm --no-deps -T --user "$(id -u):$(id -g)" -v "$WORK:/work:ro" -v "$WORK/out:/out" \
    --entrypoint python api -m auditmanager.runs.v3_pack_cli seal --scopes /work/scopes.json \
    --reviewer "$REVIEWER" --capacity "$CAPACITY" --reviewed-at "$(date -u +%F)" \
    --decision-ref "$DECISION_REF" --scope-statement "$SCOPE_STATEMENT" --out /out/pack.json </dev/null \
    > "$WORK/out/seal.txt" 2>&1 || { sed -n '1,12p' "$WORK/out/seal.txt" >&2; die 6 "seal was refused (scope_unverified means a scope does not select exactly one verified set in the live database); nothing was written"; }
[ -s "$WORK/out/pack.json" ] || die 6 "seal wrote no pack.json"

"${DC[@]}" run --rm --no-deps -T --user "$(id -u):$(id -g)" -v "$WORK/out:/out:ro" \
    --entrypoint python api -m auditmanager.runs.v3_pack_cli verify --manifest /out/pack.json </dev/null \
    > "$WORK/out/verify-offline.txt" 2>&1 || { sed -n '1,12p' "$WORK/out/verify-offline.txt" >&2; die 6 "offline verify failed"; }
grep -q '^v3-pack OK' "$WORK/out/verify-offline.txt" || die 6 "offline verify did not print 'v3-pack OK'"
say "$(grep '^v3-pack OK' "$WORK/out/verify-offline.txt" | head -n 1)"

# --- install and apply: `up -d`, never `restart` (a container's environment is fixed when it is created)
confirm INSTALL "Installs the sealed pack and RECREATES api and worker with $VAR set.
Any AR v3 Run that is queued or running right now will fail when they restart. Look at «Очередь» first."
install -d "$(dirname "$PACK_DST")"
install -m 0644 "$WORK/out/pack.json" "$PACK_DST"
say "installed $PACK_DST"
set_env_var set
"${DC[@]}" up -d --no-deps api worker </dev/null
if ! wait_running; then
    "${DC[@]}" logs --tail 20 api worker 2>&1 | grep -i -E "ConfigurationError|AR_V3" >&2 || true
    die 7 "api and worker are not both running. Read: ${DC[*]} logs --tail 40 api worker. To withdraw: $0 --rollback"
fi
"${DC[@]}" exec -T api python -m auditmanager.runs.v3_pack_cli verify --manifest "$VAR_VALUE" </dev/null \
    || die 7 "the running api does not accept the manifest. To withdraw: $0 --rollback"
say "DONE. Open «Настройки анализа»: the pack panel must show the six scopes and the attestation exactly as sealed."
say "Step 12 (acceptance with the live provider call) is separate and needs PROXY_LLM_BASE_URL and PROXY_LLM_TOKEN."
