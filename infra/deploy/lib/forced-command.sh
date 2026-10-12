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
