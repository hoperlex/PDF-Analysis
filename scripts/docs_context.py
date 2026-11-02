#!/usr/bin/env python3
"""Build a live, line-addressable index of repository Markdown without copying it."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_LINES = 100
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
UPDATE = re.compile(r"^\*\*Updated (\d{4}-\d{2}-\d{2}) by `([^`]+)`")
RANGE = re.compile(r"^(docs/[^:]+\.md):(\d+)-(\d+)$")


@dataclass(frozen=True)
class Crop:
    path: str
    start: int
    end: int
    title: str
    kind: str
    chars: int

    @property
    def address(self) -> str:
        return f"{self.path}:{self.start}-{self.end}"


def kind_of(path: str) -> str:
    if path == "docs/program/CURRENT_STATE.md":
        return "current-state"
    for prefix, kind in (
        ("docs/context/", "guide"),
        ("docs/architecture/adr/", "decision"),
        ("docs/architecture/", "architecture"),
        ("docs/program/tasks/", "task"),
        ("docs/program/reviews/", "review"),
        ("docs/program/dispatch/", "dispatch"),
        ("docs/program/history/", "history"),
        ("docs/program/", "program"),
        ("docs/manual-tests/", "runbook"),
        ("docs/stages/", "stage"),
    ):
        if path.startswith(prefix):
            return kind
    return "general"


def markdown_paths(prefix: str = "docs/") -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", "docs"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    paths = {p.decode() for p in result.stdout.split(b"\0") if p}
    return sorted(p for p in paths if p.endswith(".md") and p.startswith(prefix))


def crop_lines(path: str, lines: list[str], max_lines: int = MAX_LINES) -> list[Crop]:
    if not lines:
        return []
    if max_lines < 1:
        raise ValueError("max_lines must be positive")
    chunks: list[Crop] = []
    stack: list[str] = []
    title = Path(path).name
    start = 1
    fence: str | None = None

    def append_segment(first: int, last: int, label: str) -> None:
        while first <= last:
            stop = min(first + max_lines - 1, last)
            if stop < last:
                # Prefer a paragraph boundary, but always keep the crop bounded.
                for candidate in range(stop, first + max_lines // 2, -1):
                    if not lines[candidate - 1].strip():
                        stop = candidate
                        break
            chunks.append(Crop(path, first, stop, label, kind_of(path),
                               sum(len(line) for line in lines[first - 1:stop])))
            first = stop + 1

    for number, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            fence = None if fence == marker else marker if fence is None else fence
            continue
        if fence:
            continue
        match = HEADING.match(line)
        update = UPDATE.match(line) if path == "docs/program/CURRENT_STATE.md" else None
        if not match and not update:
            continue
        if number > start:
            append_segment(start, number - 1, title)
        if match:
            level = len(match.group(1))
            stack = stack[:level - 1]
            stack.append(match.group(2).strip())
            title = " / ".join(stack)
        else:
            title = f"Current state / {update.group(1)} / {update.group(2)}"
        start = number
    append_segment(start, len(lines), title)
    return chunks


def load_crops(prefix: str = "docs/") -> tuple[list[Crop], dict[str, list[str]]]:
    crops: list[Crop] = []
    documents: dict[str, list[str]] = {}
    for path in markdown_paths(prefix):
        full = (ROOT / path).resolve()
        if not full.is_relative_to(ROOT / "docs") or not full.is_file():
            raise ValueError(f"invalid documentation path: {path}")
        lines = full.read_text(encoding="utf-8").splitlines(keepends=True)
        documents[path] = lines
        crops.extend(crop_lines(path, lines))
    return crops, documents


def cmd_search(args: argparse.Namespace) -> None:
    crops, documents = load_crops(args.path)
    query = args.query.casefold()
    priority = {"current-state": 0, "guide": 1, "decision": 2,
                "architecture": 3, "program": 4, "dispatch": 5,
                "task": 6, "runbook": 7, "review": 8, "history": 9}
    matches = []
    for crop in crops:
        body = "".join(documents[crop.path][crop.start - 1:crop.end])
        if query not in body.casefold() and query not in crop.title.casefold():
            continue
        excerpt = next((line.strip() for line in body.splitlines()
                        if query in line.casefold()), crop.title)
        matches.append((priority.get(crop.kind, 5), crop.path, crop.start, crop, excerpt))
    matches.sort(key=lambda row: row[:3])
    for _, _, _, crop, excerpt in matches[:args.limit]:
        print(f"{crop.address} [{crop.kind}] {crop.title[:100]}")
        print(f"  {excerpt[:180]}")
    print(f"Matches: {len(matches)}; shown: {min(len(matches), args.limit)}")


def cmd_index(args: argparse.Namespace) -> None:
    crops, _ = load_crops(args.path)
    payload = "".join(json.dumps(asdict(crop), ensure_ascii=False, sort_keys=True) + "\n"
                      for crop in crops)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
        print(f"Indexed {len(crops)} crops from {len(set(c.path for c in crops))} files: {output}")
    else:
        print(payload, end="")


def cmd_show(args: argparse.Namespace) -> None:
    match = RANGE.fullmatch(args.address)
    if not match:
        raise ValueError("expected docs/path.md:start-end")
    path, start, end = match.group(1), int(match.group(2)), int(match.group(3))
    if path not in markdown_paths() or start < 1 or end < start or end - start >= MAX_LINES:
        raise ValueError("address is outside a tracked Markdown file or exceeds 100 lines")
    lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
    if end > len(lines):
        raise ValueError("address exceeds the current file")
    print(f"# {path}:{start}-{end}")
    for number in range(start, end + 1):
        print(f"{number:>5} {lines[number - 1]}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    search = commands.add_parser("search", help="find live source crops by text")
    search.add_argument("query")
    search.add_argument("--path", default="docs/", help="repository-relative path prefix")
    search.add_argument("--limit", type=int, default=20)
    search.set_defaults(func=cmd_search)
    index = commands.add_parser("index", help="export the current crop metadata as JSONL")
    index.add_argument("--path", default="docs/", help="repository-relative path prefix")
    index.add_argument("--output", help="write an ignored local index, e.g. .local/docs-context.jsonl")
    index.set_defaults(func=cmd_index)
    show = commands.add_parser("show", help="read exact source lines from an index address")
    show.add_argument("address")
    show.set_defaults(func=cmd_show)
    args = parser.parse_args()
    if args.command == "search" and (args.limit < 1 or not args.path.startswith("docs/")):
        parser.error("--limit must be positive and --path must start with docs/")
    if args.command == "index" and not args.path.startswith("docs/"):
        parser.error("--path must start with docs/")
    try:
        args.func(args)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"docs_context: {exc}\n")


if __name__ == "__main__":
    main()
