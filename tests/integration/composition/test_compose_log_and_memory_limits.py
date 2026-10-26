"""`ERASE-WRAP-01` for `PROD-05b` -- log rotation and the memory-limit MECHANISM of `compose.server.yml`.

What the compose file promises (`ADR-0021` section 4, `R-146n` item 2, `D-166`):

* every long-running service rotates its `json-file` log (`max-size` and `max-file`), so a chatty container cannot fill the
  disk of a 4 GB host;
* every long-running service has a `mem_limit:` that is read from `ALPHA_MEM_LIMIT_<SERVICE>` and is `0` -- Docker's
  "no limit" -- when the variable is unset or empty. NO NUMBER IS INVENTED: the measurement `PROD-05a` has not been taken
  (`R-146ad`), and a limit below the worker's footprint kills it in the middle of a run. A literal number in the file, or a
  default that is not "no limit", is exactly the invention this test refuses;
* the three one-shot services (`s3-init`, `migrate`, `release-notes`) carry neither: a memory limit on a migration is a
  migration that dies for the wrong reason.

There is no docker here and no YAML parser in the test environment, so the file is read by indentation (the neighbours'
idiom, `test_acme_overlay.py`) and `docker compose`'s own variable interpolation is reimplemented in `render` -- and that
reimplementation is itself tested against the documented rules, so the renderer is not trusted blindly. The set of
problems is one function, `problems`, applied to the real file (it must find none) and to mutated copies (it must find
the one that was introduced).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
COMPOSE = ROOT / "infra/deploy/compose.server.yml"
EXAMPLE = ROOT / "infra/deploy/env/alpha.env.example"

LONG_RUNNING = ("postgres", "s3", "api", "worker", "web", "proxy")
ONE_SHOT = ("s3-init", "migrate", "release-notes")
VAR = "ALPHA_MEM_LIMIT_"


# --- reading the file by indentation ------------------------------------------------------------------------------


def code_lines(text: str) -> list[str]:
    """The lines of a YAML file that are not comments or blank, trailing whitespace gone."""
    return [line.rstrip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]


def _mapping(lines: list[tuple[int, str]]) -> dict[str, object]:
    """A nested mapping from ``(indent, text)`` lines. Only the `logging` block is read this way: it is plain
    ``key: value`` and ``key:`` lines, which is all it may contain."""
    out: dict[str, object] = {}
    if not lines:
        return out
    base = lines[0][0]
    i = 0
    while i < len(lines):
        indent, text = lines[i]
        assert indent == base, f"unexpected indentation at {text!r}"
        key, _, value = text.partition(":")
        j = i + 1
        while j < len(lines) and lines[j][0] > base:
            j += 1
        out[key] = value.strip() if value.strip() else _mapping(lines[i + 1 : j])
        i = j
    return out


def services(text: str) -> dict[str, dict[str, object]]:
    """``{service: {key: scalar | [child lines, stripped]}}`` for a two-space-indented compose file; the `logging` key
    is a nested mapping instead."""
    found: dict[str, dict[str, object]] = {}
    children: dict[str, dict[str, list[tuple[int, str]]]] = {}
    lines = code_lines(text)
    service = key = ""
    for line in lines[lines.index("services:") + 1 :]:
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if indent == 0:
            break
        if indent == 2 and stripped.endswith(":"):
            service, key = stripped[:-1], ""
            found[service], children[service] = {}, {}
        elif indent == 4 and service:
            name, _, value = stripped.partition(":")
            key = name
            if value.strip():
                found[service][key] = value.strip()
            else:
                children[service][key] = []
        elif indent > 4 and service and key in children[service]:
            children[service][key].append((indent, stripped))
    for name, body in children.items():
        for key, sub in body.items():
            found[name][key] = _mapping(sub) if key == "logging" else [item for _, item in sub]
    return found


# --- docker compose's variable interpolation, as documented -------------------------------------------------------

_TOKEN = re.compile(r"\$\$|\$\{([A-Za-z_][A-Za-z0-9_]*)(?:(:-|-|:\?|\?)([^}]*))?\}")


class Unset(Exception):
    """A `${NAME:?message}` whose variable is unset or empty: `docker compose` refuses to render the file."""


def interpolate(value: str, env: dict[str, str]) -> str:
    def one(match: re.Match[str]) -> str:
        if match.group(0) == "$$":
            return "$"
        name, operator, argument = match.group(1), match.group(2), match.group(3)
        present = name in env
        nonempty = present and env[name] != ""
        if operator == ":-":
            return env[name] if nonempty else argument
        if operator == "-":
            return env[name] if present else argument
        if operator == ":?":
            if not nonempty:
                raise Unset(f"{name}: {argument}")
            return env[name]
        if operator == "?":
            if not present:
                raise Unset(f"{name}: {argument}")
            return env[name]
        return env.get(name, "")

    return _TOKEN.sub(one, value)


def required_names(text: str) -> set[str]:
    return set(re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*):\?", "\n".join(code_lines(text))))


def render(text: str, env: dict[str, str] | None = None) -> str:
    """The compose file's code lines with every variable substituted. Every `${NAME:?...}` the file demands is given a
    placeholder unless the caller names it, so that what is under test is only what the caller varies."""
    environment = {name: "placeholder" for name in required_names(text)}
    environment.update(env or {})
    return "\n".join(interpolate(line, environment) for line in code_lines(text)) + "\n"


# Docker's own size grammar (`github.com/docker/go-units` `RAMInBytes`): digits, optional fraction, optional k m g t p,
# optional `i`, optional `b`.
_SIZE = re.compile(r"^(\d+(?:\.\d+)*) ?([kKmMgGtTpP])?[iI]?[bB]?$")


def size_bytes(value: str) -> int | None:
    match = _SIZE.match(value)
    if not match:
        return None
    exponent = "kmgtp".index(match.group(2).lower()) + 1 if match.group(2) else 0
    try:
        return int(float(match.group(1)) * 1024**exponent)
    except ValueError:  # "1.5.5": the grammar lets it through and the number parser does not, in Docker as here
        return None


# --- everything the file must satisfy -----------------------------------------------------------------------------


def problems(compose: str, example: str, env: dict[str, str] | None = None) -> list[str]:
    found: list[str] = []
    declared = services(compose)
    for name in declared:
        if name not in LONG_RUNNING and name not in ONE_SHOT:
            found.append(f"service {name!r} is neither long-running nor one-shot: decide its log and memory limits")
    for name in (*LONG_RUNNING, *ONE_SHOT):
        if name not in declared:
            found.append(f"service {name!r} is gone from the file")
    raw = declared
    rendered = services(render(compose, env))
    for name in LONG_RUNNING:
        if name not in raw:
            continue
        variable = VAR + name.upper().replace("-", "_")
        expected = "${" + variable + ":-0}"
        if raw[name].get("mem_limit") != expected:
            found.append(f"{name}: mem_limit must be exactly {expected!r}, it is {raw[name].get('mem_limit')!r}")
        shown = rendered[name].get("mem_limit")
        if not isinstance(shown, str) or size_bytes(shown) is None:
            found.append(f"{name}: mem_limit renders as {shown!r}, which Docker cannot read as a size")
        logging = raw[name].get("logging")
        if not isinstance(logging, dict):
            found.append(f"{name}: no logging block")
            continue
        if set(logging) != {"driver", "options"}:
            found.append(f"{name}: logging must be exactly a driver and options, it is {sorted(logging)}")
        if logging.get("driver") != "json-file":
            found.append(f"{name}: logging driver is {logging.get('driver')!r}, not json-file")
        options = logging.get("options")
        if not isinstance(options, dict) or set(options) != {"max-size", "max-file"}:
            found.append(f"{name}: logging options must be exactly max-size and max-file")
            continue
        if not re.fullmatch(r'"\d+[kmg]"', str(options["max-size"])):
            found.append(f"{name}: max-size {options['max-size']!r} is not a quoted number with a unit k, m or g")
        if not re.fullmatch(r'"[1-9]\d*"', str(options["max-file"])):
            found.append(f"{name}: max-file {options['max-file']!r} is not a quoted positive whole number")
    for name in ONE_SHOT:
        for key in ("mem_limit", "logging"):
            if name in raw and key in raw[name]:
                found.append(f"{name}: a one-shot service must not carry {key}")
    # The structural half of ADR-0021 row 8, on the file as written: every service that is not a one-shot declares both.
    # (Row 8 itself reads `docker compose config`; whether Compose prints a zero limit is Docker's and is not claimed here.)
    row_8 = sorted(
        name for name, body in raw.items()
        if name not in ONE_SHOT and not (body.get("mem_limit") and isinstance(body.get("logging"), dict)
                                         and body["logging"].get("options", {}).get("max-size"))  # type: ignore[union-attr]
    )
    if row_8:
        found.append(f"ADR-0021 row 8 would print {row_8}, not []")
    # The example: the variables the file reads, each shipped EMPTY.
    used = set(re.findall(rf"{VAR}[A-Z0-9_]+", "\n".join(code_lines(compose))))
    shipped = re.findall(rf"^({VAR}[A-Z0-9_]+)=(.*)$", example, re.MULTILINE)
    names = [name for name, _ in shipped]
    if sorted(names) != sorted(set(names)):
        found.append("alpha.env.example sets a memory-limit variable twice")
    if set(names) != used:
        found.append(f"alpha.env.example sets {sorted(names)}, compose reads {sorted(used)}")
    for name, value in shipped:
        if value != "":
            found.append(f"alpha.env.example ships {name}={value!r}: no memory number is invented before PROD-05a")
    return found


def _compose() -> str:
    return COMPOSE.read_text(encoding="utf-8")


def _example() -> str:
    return EXAMPLE.read_text(encoding="utf-8")


# --- the file as shipped ------------------------------------------------------------------------------------------


def test_the_file_as_shipped_satisfies_every_rule() -> None:
    assert problems(_compose(), _example()) == []


def test_the_long_running_services_are_the_six_the_adr_names() -> None:
    declared = set(services(_compose()))
    assert declared == set(LONG_RUNNING) | set(ONE_SHOT)
    restarts = {n: b.get("restart") for n, b in services(_compose()).items()}
    assert {n for n, r in restarts.items() if r == "unless-stopped"} == set(LONG_RUNNING), restarts
    assert {n for n, r in restarts.items() if r == '"no"'} == set(ONE_SHOT), restarts


def test_without_any_variable_every_service_renders_no_limit_and_a_rotated_log() -> None:
    shown = services(render(_compose()))
    for name in LONG_RUNNING:
        assert shown[name]["mem_limit"] == "0", (name, shown[name]["mem_limit"])
        assert size_bytes("0") == 0, "0 is Docker's 'no limit'"
        assert shown[name]["logging"] == {"driver": "json-file", "options": {"max-size": '"10m"', "max-file": '"5"'}}


def test_variables_set_to_the_empty_string_are_the_same_as_unset() -> None:
    """`alpha.env` ships the six lines empty, and compose reads `NAME=` as an empty string, not as unset."""
    env = {VAR + name.upper(): "" for name in LONG_RUNNING}
    shown = services(render(_compose(), env))
    assert {name: shown[name]["mem_limit"] for name in LONG_RUNNING} == {name: "0" for name in LONG_RUNNING}


def test_a_value_reaches_only_its_own_service() -> None:
    env = {VAR + "WORKER": "1536m", VAR + "API": "1g", VAR + "POSTGRES": "2147483648", VAR + "S3": "0.5g"}
    shown = services(render(_compose(), env))
    assert {name: shown[name]["mem_limit"] for name in LONG_RUNNING} == {
        "postgres": "2147483648", "s3": "0.5g", "api": "1g", "worker": "1536m", "web": "0", "proxy": "0"}
    assert [size_bytes(shown[n]["mem_limit"]) for n in ("worker", "api", "postgres", "s3")] == [  # type: ignore[arg-type]
        1536 * 1024**2, 1024**3, 2147483648, 512 * 1024**2]
    assert problems(_compose(), _example(), env) == []


@pytest.mark.parametrize("bad", ["lots", "1.5.5g", "-1g", "2 gigabytes", "1g!", "512mb x"])
def test_a_value_docker_cannot_read_is_seen_by_the_check(bad: str) -> None:
    found = problems(_compose(), _example(), {VAR + "WORKER": bad})
    assert any("worker: mem_limit renders as" in line for line in found), found


# --- the renderer is checked against the rules it claims to implement -------------------------------------------


@pytest.mark.parametrize(("template", "env", "expected"), (
    ("${V:-d}", {}, "d"), ("${V:-d}", {"V": ""}, "d"), ("${V:-d}", {"V": "x"}, "x"),
    ("${V-d}", {}, "d"), ("${V-d}", {"V": ""}, ""), ("${V-d}", {"V": "x"}, "x"),
    ("${V}", {}, ""), ("${V}", {"V": "x"}, "x"), ("$$HOME ${V:-0}", {}, "$HOME 0"),
    ("a${V:-0}b${W:-1}c", {"W": "z"}, "a0bzc"),
))
def test_the_interpolation_follows_the_documented_rules(template: str, env: dict[str, str], expected: str) -> None:
    assert interpolate(template, env) == expected


@pytest.mark.parametrize(("template", "env", "raises"), (
    ("${V:?no}", {}, True), ("${V:?no}", {"V": ""}, True), ("${V:?no}", {"V": "x"}, False),
    ("${V?no}", {}, True), ("${V?no}", {"V": ""}, False),
))
def test_the_required_forms_refuse_the_way_compose_does(template: str, env: dict[str, str], raises: bool) -> None:
    if raises:
        with pytest.raises(Unset):
            interpolate(template, env)
    else:
        interpolate(template, env)


@pytest.mark.parametrize(("value", "bytes_"), (
    ("0", 0), ("1", 1), ("512m", 512 * 1024**2), ("1536M", 1536 * 1024**2), ("2g", 2 * 1024**3), ("2GiB", 2 * 1024**3),
    ("1.5g", int(1.5 * 1024**3)), ("100k", 102400), ("64 m", 64 * 1024**2),
))
def test_the_size_grammar_reads_what_docker_reads(value: str, bytes_: int) -> None:
    assert size_bytes(value) == bytes_


@pytest.mark.parametrize("value", ["", "lots", "-1", "1x", "g", "1gg"])
def test_the_size_grammar_refuses_what_docker_refuses(value: str) -> None:
    assert size_bytes(value) is None


# --- every rule shown able to fail --------------------------------------------------------------------------------


def _slice(text: str, service: str) -> tuple[int, int]:
    start = text.index(f"\n  {service}:\n") + 1
    match = re.search(r"^  [a-z0-9-]+:\n", text[start + 1 :], re.MULTILINE)
    return start, len(text) if match is None else start + 1 + match.start()


def _edit_service(text: str, service: str, old: str, new: str) -> str:
    start, end = _slice(text, service)
    body = text[start:end]
    assert body.count(old) == 1, (service, old, body.count(old))
    return text[:start] + body.replace(old, new) + text[end:]


LOGGING = '    logging:\n      driver: json-file\n      options:\n        max-size: "10m"\n        max-file: "5"\n'


def test_a_service_without_a_logging_block_is_seen() -> None:
    mutated = _edit_service(_compose(), "worker", LOGGING, "")
    assert any(line == "worker: no logging block" for line in problems(mutated, _example()))


def test_a_service_without_a_memory_limit_is_seen() -> None:
    mutated = _edit_service(_compose(), "web", "    mem_limit: ${ALPHA_MEM_LIMIT_WEB:-0}\n", "")
    found = problems(mutated, _example())
    assert any(line.startswith("web: mem_limit must be exactly") for line in found), found
    assert any("ADR-0021 row 8 would print ['web']" in line for line in found), found


def test_a_default_that_is_not_no_limit_is_seen() -> None:
    """An empty default renders as nothing at all, which is not a size Docker can read from the file."""
    mutated = _edit_service(_compose(), "proxy", "${ALPHA_MEM_LIMIT_PROXY:-0}", "${ALPHA_MEM_LIMIT_PROXY:-}")
    found = problems(mutated, _example())
    assert any(line.startswith("proxy: mem_limit must be exactly") for line in found), found
    assert any(line.startswith("proxy: mem_limit renders as") for line in found), found


def test_an_invented_number_in_the_file_is_seen() -> None:
    for old, new in (("${ALPHA_MEM_LIMIT_API:-0}", "${ALPHA_MEM_LIMIT_API:-512m}"), ("${ALPHA_MEM_LIMIT_API:-0}", "512m")):
        mutated = _edit_service(_compose(), "api", old, new)
        assert any(line.startswith("api: mem_limit must be exactly") for line in problems(mutated, _example()))


def test_a_limit_read_from_another_services_variable_is_seen() -> None:
    mutated = _edit_service(_compose(), "web", "ALPHA_MEM_LIMIT_WEB", "ALPHA_MEM_LIMIT_API")
    assert any(line.startswith("web: mem_limit must be exactly") for line in problems(mutated, _example()))


def test_a_new_service_must_decide_its_limits() -> None:
    mutated = _compose().rstrip("\n") + "\n\n  sidecar:\n    image: x\n    restart: unless-stopped\n"
    found = problems(mutated, _example())
    assert any("'sidecar' is neither long-running nor one-shot" in line for line in found), found


def test_a_missing_service_is_seen() -> None:
    start, end = _slice(_compose(), "s3")
    mutated = _compose()[:start] + _compose()[end:]
    assert any("service 's3' is gone from the file" in line for line in problems(mutated, _example()))


@pytest.mark.parametrize(("old", "new", "says"), (
    ('driver: json-file', 'driver: local', "logging driver is 'local', not json-file"),
    ('        max-file: "5"\n', '', "logging options must be exactly max-size and max-file"),
    ('max-size: "10m"', 'max-size: "10"', "is not a quoted number with a unit"),
    ('max-size: "10m"', 'max-size: 10m', "is not a quoted number with a unit"),
    ('max-file: "5"', 'max-file: "0"', "is not a quoted positive whole number"),
    ('      options:\n', '      opts:\n', "logging must be exactly a driver and options"),
), ids=["driver", "no-max-file", "no-unit", "unquoted", "zero-files", "no-options-key"])
def test_a_malformed_logging_block_is_seen(old: str, new: str, says: str) -> None:
    mutated = _edit_service(_compose(), "s3", old, new)
    found = problems(mutated, _example())
    assert any(line.startswith("s3:") and says in line for line in found), found


@pytest.mark.parametrize("one_shot", ONE_SHOT)
def test_a_limit_on_a_one_shot_service_is_seen(one_shot: str) -> None:
    anchor = {"s3-init": '    restart: "no"\n', "migrate": '    restart: "no"\n', "release-notes": '    restart: "no"\n'}[one_shot]
    mutated = _edit_service(_compose(), one_shot, anchor, anchor + "    mem_limit: ${ALPHA_MEM_LIMIT_API:-0}\n")
    assert any(line == f"{one_shot}: a one-shot service must not carry mem_limit" for line in problems(mutated, _example()))


def test_a_number_shipped_in_the_example_is_seen() -> None:
    mutated = _example().replace("ALPHA_MEM_LIMIT_WORKER=\n", "ALPHA_MEM_LIMIT_WORKER=2g\n")
    assert mutated != _example()
    assert any("no memory number is invented before PROD-05a" in line for line in problems(_compose(), mutated))


def test_a_variable_missing_from_or_extra_in_the_example_is_seen() -> None:
    without = _example().replace("ALPHA_MEM_LIMIT_PROXY=\n", "")
    assert without != _example() and any("alpha.env.example sets" in line for line in problems(_compose(), without))
    extra = _example() + "ALPHA_MEM_LIMIT_SIDECAR=\n"
    assert any("alpha.env.example sets" in line for line in problems(_compose(), extra))
    twice = _example() + "ALPHA_MEM_LIMIT_API=\n"
    assert any("sets a memory-limit variable twice" in line for line in problems(_compose(), twice))


def test_the_example_still_parses_as_data_lines() -> None:
    """`deploy.sh` and its neighbours read `alpha.env` with `sed`, never source it: the shipped lines must be plain
    `NAME=` pairs with nothing after the equals sign."""
    lines = [line for line in _example().splitlines() if line.startswith(VAR)]
    assert len(lines) == 6 and all(re.fullmatch(rf"{VAR}[A-Z0-9_]+=", line) for line in lines), lines
