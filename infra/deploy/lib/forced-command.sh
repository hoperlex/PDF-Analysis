# shellcheck shell=bash
# shellcheck disable=SC2034  # FC_BUNDLE_KEY_ERE and its parts are read by the scripts that source this file
# `W54-TRANSPORT-01` -- ONE DISPATCHER FOR EVERY FORCED-COMMAND KEY ON THE STAND.
#
# Sourced, never run. A key's script (`receive-bundle.sh` for the inbound key; the copy
# key's `copy-serve.sh` from `W54-STAND-COPY-01`) sets `FC_NAME`, registers its verbs and
# hands `SSH_ORIGINAL_COMMAND` to `fc_dispatch`:
#
#   FC_NAME=receive-bundle.sh
#   . "$HERE/lib/forced-command.sh"
#   fc_register status '^status$' verb_status
#   fc_dispatch "${SSH_ORIGINAL_COMMAND-}"
#
# THE COMMAND STRING IS DATA, NEVER CODE. It is not passed to `eval`, `sh -c`, `bash -c`,
# `source` or any other interpreter, here or in a handler. It is checked against a short
# character set, matched against ONE anchored extended regular expression per verb, and
# only then split on single spaces into words -- which, after those two checks, cannot
# contain a quote, a glob, a separator, a redirection or a newline. The handler receives
# the words as positional parameters. A later lane adds a verb by one `fc_register` line
# and one refusal case in that key's test; nothing else here changes.
#
# REFUSALS. Every refusal exits 3 and prints `<script>: REFUSED [<guard>]: <reason>`. The
# guard's name in brackets is what the suites assert on, and every guard sits between
# `# >>> guard: <name>` / `# <<< guard: <name>` markers: the suite deletes ONE block from a
# copy of the script and shows the copy no longer produces that refusal, and it fails when
# a marker has no case (`test_bundle_transport_refusals.py`). Do not remove a marker
# without removing its test.
#
# THE BUNDLE TREE RULES live here too, because the sending side (`push-bundle.sh`, on the
# development host) and the receiving side (`receive-bundle.sh`, on the stand) must apply
# the same rule to the same tree; two copies of a rule drift.

#: Upper bound on the command string. The longest frozen verb today is
#: `retrieval-set-build` with five arguments (W57a), well under this.
FC_MAX_COMMAND_BYTES=512

#: Every character any registered grammar can need. Anything else -- quotes, `$`, `;`,
#: `|`, `&`, `/`, `*`, a tab, a newline -- is refused before a verb is even looked up.
FC_CHARSET_ERE='^[A-Za-z0-9._+ -]+$'

FC_VERBS=()
FC_GRAMMARS=()
FC_HANDLERS=()

# --- the bundle name (`<KEY>`) ------------------------------------------------------
#
# `<KEY>` is the bundle directory's name: `<content_key>+<bundle digest>`.
#
# `<content_key>` is the snapshot key `norms/snapshot.py` and `norms/repair.py` mint, in
# every form W54 can produce (`W54-PLAN.md` §3.3, §3.4):
#
#   <window>+<d>d.<12 hex>                      the base corpus
#   <window>+<d>d+<n>r.<12 hex>                 n > 0 repairs applied, nothing unreliable
#   <window>+<d>d+<n>r+<m>u.<12 hex>            m > 0 unreliable blocks (n may be 0)
#   ... followed by +seg-<profile>              `D-126`: a segmentation profile other
#                                               than `markdown-v1`
#
# where <window> is `YYYY-MM-DD..YYYY-MM-DD` or `undated`. `+0r` alone is not a key: with
# nothing repaired and nothing unreliable the key is the base key (`0018`'s
# `ck_norms_snapshot_raw_key`).
#
# `<bundle digest>` is 64 lowercase hex: the SHA-256 of the bundle's `SHA256SUMS` file,
# which lists every other regular file in the bundle (see `fc_check_bundle_tree`).
FC_BUNDLE_WINDOW_ERE='(undated|[0-9]{4}-[0-9]{2}-[0-9]{2}\.\.[0-9]{4}-[0-9]{2}-[0-9]{2})'
FC_BUNDLE_REPAIRS_ERE='(\+[1-9][0-9]{0,5}r(\+[1-9][0-9]{0,5}u)?|\+0r\+[1-9][0-9]{0,5}u)?'
FC_CONTENT_KEY_ERE="${FC_BUNDLE_WINDOW_ERE}\\+(0|[1-9][0-9]{0,5})d${FC_BUNDLE_REPAIRS_ERE}\\.[0-9a-f]{12}(\\+seg-[a-z0-9]+(-[a-z0-9]+)*)?"
FC_BUNDLE_KEY_ERE="${FC_CONTENT_KEY_ERE}\\+[0-9a-f]{64}"

#: One path inside a bundle: ASCII components that cannot be `.`, `..` or hidden.
FC_BUNDLE_COMPONENT_ERE='[A-Za-z0-9_+=-][A-Za-z0-9._+=-]{0,127}'
FC_BUNDLE_PATH_ERE="${FC_BUNDLE_COMPONENT_ERE}(/${FC_BUNDLE_COMPONENT_ERE}){0,7}"

fc_refuse() {
    local guard="$1" reason="$2"
    shift 2
    printf '%s: REFUSED [%s]: %s\n' "${FC_NAME:-forced-command}" "$guard" "$reason" >&2
    [ "$#" -eq 0 ] || printf '  %s\n' "$@" >&2
    exit 3
}

# fc_register <verb> <anchored ERE for the whole command> <handler function>
fc_register() {
    FC_VERBS+=("$1")
    FC_GRAMMARS+=("$2")
    FC_HANDLERS+=("$3")
}

fc_verbs() {
    local verb
    for verb in "${FC_VERBS[@]}"; do
        printf '%s ' "$verb"
    done
}

# fc_dispatch <command string>
fc_dispatch() {
    local command="$1" verb index found=-1
    local -a words

    # >>> guard: command-present
    if [ -z "$command" ]; then
        fc_refuse command-present "this key runs only its forced command, and was given no verb." \
            "verbs: $(fc_verbs)"
    fi
    # <<< guard: command-present

    # >>> guard: command-length
    if [ "${#command}" -gt "$FC_MAX_COMMAND_BYTES" ]; then
        fc_refuse command-length "the command is ${#command} bytes; at most $FC_MAX_COMMAND_BYTES are read."
    fi
    # <<< guard: command-length

    # >>> guard: command-charset
    if ! [[ $command =~ $FC_CHARSET_ERE ]]; then
        fc_refuse command-charset "the command holds a character no verb accepts." \
            "allowed: letters, digits, space and . _ + -; nothing is interpreted by a shell."
    fi
    # <<< guard: command-charset

    verb="${command%% *}"
    for index in "${!FC_VERBS[@]}"; do
        if [ "${FC_VERBS[$index]}" = "$verb" ]; then
            found="$index"
        fi
    done

    # >>> guard: verb-known
    if [ "$found" -lt 0 ]; then
        fc_refuse verb-known "'$verb' is not a verb of this key." "verbs: $(fc_verbs)"
    fi
    # <<< guard: verb-known

    # >>> guard: verb-grammar
    if ! [[ $command =~ ${FC_GRAMMARS[$found]} ]]; then
        fc_refuse verb-grammar "'$verb' was given arguments its grammar does not admit." \
            "grammar: ${FC_GRAMMARS[$found]}"
    fi
    # <<< guard: verb-grammar

    IFS=' ' read -r -a words <<< "$command"
    "${FC_HANDLERS[$found]}" "${words[@]:1}"
}

# fc_check_bundle_tree <bundle directory> <KEY>
#
# The one rule for a bundle tree, applied before it is sent and again after it arrives:
#
#   * `SHA256SUMS` is a regular file and its SHA-256 is the digest at the end of `<KEY>`;
#   * every line is `<64 hex><two spaces><path>` (GNU `sha256sum`'s text form) with a path
#     of plain ASCII components -- never absolute, never `.` or `..` -- and no path twice;
#   * the tree holds exactly the listed regular files plus `SHA256SUMS` and directories:
#     no extra file, no missing file, no symlink, device or pipe;
#   * every listed file has its listed SHA-256 (the bytes are re-read, never trusted).
#
# The paths are checked BEFORE `sha256sum --check` runs, because that command opens any
# path a line names -- `../../etc/shadow` included.
fc_check_bundle_tree() {
    local tree="$1" key="$2" sums digest actual listed present strays failures
    sums="$tree/SHA256SUMS"
    digest="${key##*+}"

    # >>> guard: sums-present
    if [ -L "$sums" ] || [ ! -f "$sums" ]; then
        fc_refuse sums-present "the bundle has no SHA256SUMS file (a regular file is required)."
    fi
    # <<< guard: sums-present

    # >>> guard: sums-match-key
    actual="$(sha256sum < "$sums")"
    actual="${actual%% *}"
    if [ "$actual" != "$digest" ]; then
        fc_refuse sums-match-key "SHA256SUMS hashes to $actual; the bundle name says $digest."
    fi
    # <<< guard: sums-match-key

    # >>> guard: sums-well-formed
    if [ ! -s "$sums" ] \
        || LC_ALL=C grep -Evq "^[0-9a-f]{64}  ${FC_BUNDLE_PATH_ERE}\$" "$sums" \
        || LC_ALL=C grep -Eq '  SHA256SUMS$' "$sums" \
        || [ -n "$(cut -c67- "$sums" | LC_ALL=C sort | uniq -d)" ]; then
        fc_refuse sums-well-formed "SHA256SUMS is empty, names a path outside the bundle's grammar, names itself, or names a path twice."
    fi
    # <<< guard: sums-well-formed

    # >>> guard: files-match-sums
    listed="$(cut -c67- "$sums" | LC_ALL=C sort)"
    present="$(find "$tree" -mindepth 1 ! -type d -printf '%P\n' | LC_ALL=C grep -vx 'SHA256SUMS' | LC_ALL=C sort || true)"
    strays="$(find "$tree" -mindepth 1 ! -type d ! -type f -printf '%P\n')"
    if [ -n "$strays" ] || [ "$listed" != "$present" ]; then
        fc_refuse files-match-sums "the bundle's files are not exactly the files SHA256SUMS lists, as regular files." \
            "$(diff <(printf '%s\n' "$listed") <(printf '%s\n' "$present") | LC_ALL=C grep -E '^[<>]' | head -n 5 || true)" \
            "${strays:+not a regular file: $(printf '%s' "$strays" | head -n 1)}"
    fi
    # <<< guard: files-match-sums

    # >>> guard: sums-verify
    if ! failures="$(cd "$tree" && sha256sum --check --strict --quiet SHA256SUMS 2>&1)"; then
        fc_refuse sums-verify "a file's bytes differ from SHA256SUMS." \
            "$(printf '%s' "$failures" | head -n 5)"
    fi
    # <<< guard: sums-verify
}

# --- the copy record (`W54-STAND-COPY-01`) --------------------------------------------
#
# `copy-serve.sh` (the copy key) writes the record; `receive-bundle.sh` reads it before an
# import and turns an open record into an import record; `pull-copy.sh` and
# `scripts/stand-copy/restore-test.sh` read it on the development host. The importer
# (`W54-BUNDLE-01`) reads the same file as JSON. `deploy.sh` reads five of its keys with
# its own ten-line reader, because it must run from a checkout that stages it alone.
#
# THE RECORD IS JSON IN ONE CANONICAL LAYOUT, so a shell can read and rewrite it without
# a JSON parser (the stand promises bash, docker, curl, sed and git; not python3, not jq):
#
#   {
#     "record_version": 1,
#     "<key>": <one JSON value on this one line>,
#     ...
#     "<last key>": <value>
#   }
#
# Every top-level key is on its own line, indented by exactly two spaces, and every value
# -- objects and arrays included -- is on that same line. No string in it holds a quote or
# a backslash: every value is a stamp, a digest, a name, a count or a UTC time that this
# code produced. A file that is not in this layout is not a record (`fc_record_valid`).
# The full schema is in `docs/program/W54-STAND-COPY-01.md` §3.

#: `<STAMP>`: the UTC second the copy (or waiver) was opened, `YYYYMMDDTHHMMSSZ`.
FC_STAMP_ERE='[0-9]{8}T[0-9]{6}Z'

#: One fingerprint line, as the fingerprint query prints it: `<table>|<rows>|<sha256>`.
FC_FINGERPRINT_LINE_ERE='^[a-z_][a-z0-9_]*\|(0|[1-9][0-9]*)\|[0-9a-f]{64}$'

# fc_record_value <file> <key>: the raw JSON value of a top-level key, without its comma.
# Fails unless the key is on exactly one line.
fc_record_value() {
    local file="$1" key="$2" lines
    lines="$(sed -n "s/^  \"$key\": \(.*\)\$/\1/p" "$file" 2>/dev/null)" || return 1
    [ -n "$lines" ] || return 1
    [ "$(printf '%s\n' "$lines" | wc -l)" -eq 1 ] || return 1
    printf '%s\n' "${lines%,}"
}

# fc_record_string <file> <key>: the characters of a top-level string; fails for null,
# a number, an object, or a string holding a quote or a backslash.
fc_record_string() {
    local value
    value="$(fc_record_value "$1" "$2")" || return 1
    [[ $value =~ ^\"([^\"\\]*)\"$ ]] || return 1
    printf '%s\n' "${BASH_REMATCH[1]}"
}

# fc_json_member <one-line object> <name>: the first member called <name> in it -- a
# string's characters, or a number, true, false or null as written.
fc_json_member() {
    local object="$1" name="$2" string_ere scalar_ere
    string_ere="\"$name\": \"([^\"\\\\]*)\""
    scalar_ere="\"$name\": (-?[0-9]+|true|false|null)[,}]"
    if [[ $object =~ $string_ere ]] || [[ $object =~ $scalar_ere ]]; then
        printf '%s\n' "${BASH_REMATCH[1]}"
        return 0
    fi
    return 1
}

# fc_json_words <one-line array of plain strings>: one word per line.
fc_json_words() {
    printf '%s\n' "$1" | grep -oE '"[a-z_]+"' | tr -d '"' || true
}

# fc_record_valid <file>: 0 only for a regular file in the canonical layout whose
# `record_version` is 1 and whose `stamp`, `kind` and `state` are readable.
fc_record_valid() {
    local file="$1"
    [ -f "$file" ] && [ ! -L "$file" ] && [ -r "$file" ] || return 1
    awk '
        NR == 1 { if ($0 != "{") bad = 1; next }
        { line[NR] = $0 }
        END {
            if (NR < 3 || line[NR] != "}") bad = 1
            for (i = 2; i < NR; i++) {
                if (line[i] !~ /^  "[a-z0-9_]+": [^ ]/) bad = 1
                if (i < NR - 1 && line[i] !~ /,$/) bad = 1
                if (i == NR - 1 && line[i] ~ /,$/) bad = 1
                if (line[i] ~ /\\/) bad = 1
            }
            exit bad
        }' "$file" || return 1
    [ "$(fc_record_value "$file" record_version)" = 1 ] || return 1
    [[ $(fc_record_string "$file" stamp) =~ ^${FC_STAMP_ERE}$ ]] || return 1
    case "$(fc_record_string "$file" kind)" in copy|test_data_waiver) ;; *) return 1 ;; esac
    case "$(fc_record_string "$file" state)" in open|closed) ;; *) return 1 ;; esac
}

# fc_record_set <file> <key> <raw JSON value>: rewrite exactly one top-level line, keeping
# its comma, atomically (a temporary file beside it, then a rename).
fc_record_set() {
    local file="$1" key="$2" value="$3" tmp
    case "$value" in *\\*|*$'\n'*) return 1 ;; esac
    tmp="$file.tmp.$$"
    if ! awk -v prefix="  \"$key\": " -v value="$value" '
            index($0, prefix) == 1 {
                comma = ($0 ~ /,$/) ? "," : ""
                print prefix value comma
                found++
                next
            }
            { print }
            END { exit (found == 1) ? 0 : 1 }' "$file" > "$tmp"; then
        rm -f -- "$tmp"
        return 1
    fi
    chmod 0644 -- "$tmp"
    mv -f -- "$tmp" "$file"
}

# fc_lock_held <lock file>: 0 while another process holds the flock(2) lock on it. A lock
# file that cannot be opened counts as held: the safe direction for every caller.
fc_lock_held() {
    local lock="$1"
    [ -e "$lock" ] || return 1
    ! flock --nonblock "$lock" true 2>/dev/null
}

fc_now() {
    date -u +%Y-%m-%dT%H:%M:%SZ
}

# fc_epoch <UTC time as fc_now writes it>
fc_epoch() {
    [[ $1 =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]] || return 1
    date -u -d "$1" +%s
}

# fc_fingerprint_lines_valid <query output>: one well-formed line per table, at least one,
# in strictly increasing byte order (the query sorts by name; a repeat or a gap in the
# order means the output is not the query's).
fc_fingerprint_lines_valid() {
    local lines="$1"
    [ -n "$lines" ] || return 1
    printf '%s\n' "$lines" | grep -Evq "$FC_FINGERPRINT_LINE_ERE" && return 1
    [ "$(printf '%s\n' "$lines" | cut -d'|' -f1)" = "$(printf '%s\n' "$lines" | cut -d'|' -f1 | sort -u)" ]
}

# fc_fingerprint_json <query output>: the record's `fingerprint` value, on one line. Its
# `sha256` is the SHA-256 of the query output, one line per table, each ending in a newline.
fc_fingerprint_json() {
    local lines="$1" digest tables
    digest="$(printf '%s\n' "$lines" | sha256sum | cut -c1-64)"
    tables="$(printf '%s\n' "$lines" \
        | awk -F'|' '{ printf "%s\"%s\": {\"rows\": %s, \"sha256\": \"%s\"}", (NR > 1 ? ", " : ""), $1, $2, $3 }')"
    printf '{"algorithm": "stand-fingerprint-v1", "sha256": "%s", "tables": {%s}}\n' "$digest" "$tables"
}
