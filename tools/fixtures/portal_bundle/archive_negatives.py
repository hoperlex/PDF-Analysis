"""One archive per bundle rule, each a valid minimal bundle broken in exactly one way.

Attributable failure is the design constraint, as for the PDF negatives: if an archive
broke two rules, a lane that refused it would have proved nothing about which rule fired.
Each builder starts from the same small valid bundle (a two-page PDF, a block list with a
TEXT block per page, the matching markdown) and changes one thing. They are keyed by the
constraint name `W55B-SEAL-01` registered, and the tests ask the validator to refuse each
for exactly that name and no other.

The small archives are returned as bytes. The size-driven ones take their sizes as
arguments -- the freeze fixes the ratio, the total and the entry count, but INGEST chooses
the per-member bound -- and write to a path in chunks, so an archive that unpacks to
hundreds of MiB never exists in memory (deflated zeros are a few hundred KiB on disk).
These are built at test time and never committed.
"""

from __future__ import annotations

import copy
import gzip
import hashlib
import json
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from . import blocklist, generated, portal_format as fmt, zipscan, zipwrite
from .blocklist import Block
from .bundle import PortalFiles, make_files, pack
from .pdffacts import PageFacts, read_pages
from .zipwrite import Member

STEM = "bundle"
CYRILLIC_STEM = "Тайга"          # contains `й`, which has two Unicode spellings


@lru_cache(maxsize=None)
def base_files(stem: str = STEM) -> PortalFiles:
    """The valid bundle every negative starts from: two text pages, a block each."""
    return make_files(generated.pdf_with_n_pages(2), stem)


def members(stem: str = STEM, **options) -> list[Member]:
    """Fresh archive members of the base bundle (they are mutable; never share them)."""
    return pack(base_files(stem), **options)


def _build(items: list[Member], **options) -> bytes:
    return zipwrite.build_zip(items, **options)


# ------------------------------------------------------------ portal_bundle_required


def bare_pdf() -> bytes:
    """A PDF presented as the upload: the old input, now refused with a way forward."""
    return base_files().pdf


def plain_text() -> bytes:
    return "Это не архив и не PDF.\n".encode("utf-8")


def gzip_stream() -> bytes:
    """Another archive format: a ZIP's bytes gzipped (mtime fixed, so the bytes repeat)."""
    return gzip.compress(_build(members()), mtime=0)


def seven_zip_magic() -> bytes:
    return b"7z\xbc\xaf\x27\x1c" + bytes(64)


def empty_upload() -> bytes:
    return b""


# ---------------------------------------------------------------- bundle_unreadable


def truncated() -> bytes:
    data = _build(members())
    return data[: len(data) * 3 // 5]


def garbage() -> bytes:
    """A ZIP's local-header magic followed by bytes that are nothing (a fixed digest chain)."""
    out = bytearray(b"PK\x03\x04")
    block = b"garbage"
    while len(out) < 4096:
        block = hashlib.sha256(block).digest()
        out += block
    return bytes(out)


def no_end_record() -> bytes:
    """Every entry intact and the central directory present, but no end record."""
    data = _build(members())
    return data[:-22]


def entry_count_lies() -> bytes:
    """The end record says three entries; the central directory holds four."""
    items = members()
    items.append(Member(b"extra.txt", b"x"))
    data = bytearray(_build(items))
    end = data.rfind(b"PK\x05\x06")
    data[end + 8:end + 12] = (3).to_bytes(2, "little") * 2
    return bytes(data)


def local_header_names_another_member() -> bytes:
    """The local header's name differs from the directory's: the classic mix-up."""
    data = bytearray(_build(members()))
    assert data[30:30 + len(STEM)] == STEM.encode("ascii")
    data[30] ^= 0x20                      # `b` becomes `B` in the local header only
    return bytes(data)


def crc_mismatch() -> bytes:
    items = members()
    items[2].crc = 0xDEADBEEF
    return _build(items)


def corrupt_deflate_data() -> bytes:
    """A method-8 member whose first deflate block header is damaged."""
    data = bytearray(_build(members()))
    with zipscan.Archive.from_bytes(bytes(data)) as archive:
        entry = archive.load_entries()[2]
        start = archive.data_offset(entry)
    data[start + 1] ^= 0xFF               # the stored block's length no longer matches NLEN
    return bytes(data)


def sizes_disagree_within_bounds() -> bytes:
    """The header declares one byte more than the member holds, well inside every bound."""
    items = members()
    items[2].declared_size = len(items[2].payload) + 1
    return _build(items)


# --------------------------------------------------------------- bundle_entry_count


def entry_count(entries: int = 9) -> bytes:
    """A valid bundle plus unknown members, `entries` in all. Nine is one over the bound."""
    items = members()
    for number in range(entries - len(items)):
        items.append(Member(f"{STEM}_extra{number}.txt".encode(), b"x"))
    return _build(items)


# -------------------------------------------------------- bundle_directory_entry


def directory_entry() -> bytes:
    items = members()
    items.append(Member(b"docs/", b"", external_attr=zipwrite.DIRECTORY))
    return _build(items)


def macosx_directory() -> bytes:
    items = members()
    items.append(Member(b"__MACOSX/", b"", external_attr=zipwrite.DIRECTORY))
    return _build(items)


def macosx_file() -> bytes:
    """The resource-fork file a Finder-made archive carries beside every member."""
    items = members()
    items.append(Member(f"__MACOSX/._{STEM}.pdf".encode(), b"\x00\x05\x16\x07"))
    return _build(items)


# ------------------------------------------------------------ bundle_member_name


def _prefixed(prefix: bytes) -> bytes:
    """All three members under one prefix, so the stem still agrees and only the name is wrong."""
    items = members()
    for item in items:
        item.name = prefix + item.name
    return _build(items)


def absolute_name() -> bytes:
    return _prefixed(b"/")


def drive_letter_name() -> bytes:
    return _prefixed(b"C:")


def backslash_name() -> bytes:
    return _prefixed(b"docs\\")


def dotdot_name() -> bytes:
    return _prefixed(b"../")


# ----------------------------------------------------------------- bundle_symlink


def symlink() -> bytes:
    """The markdown is an entry marked as a symbolic link (its bytes are the target path)."""
    items = members()
    items[2].external_attr = zipwrite.SYMLINK
    return _build(items)


# -------------------------------------------------------- bundle_encrypted_member


def encrypted_member() -> bytes:
    items = members()
    items[0].flags |= zipwrite.FLAG_ENCRYPTED
    return _build(items)


# ---------------------------------------------------- bundle_compression_method


def compression_method(method: int = 12) -> bytes:
    """A member labelled with a method other than stored or deflate.

    12 is bzip2, 14 LZMA, 99 the WinZip AES marker. The data is written as it is; the
    envelope must refuse on the label, before any attempt to unpack.
    """
    items = members()
    items[1].method = method
    return _build(items)


# ------------------------------------------------------ bundle_duplicate_member


def duplicate_exact() -> bytes:
    items = members()
    items.append(Member(items[2].name, items[2].payload, method=items[2].method))
    return _build(items)


def duplicate_casefolded() -> bytes:
    items = members()
    items.append(Member(items[2].name.upper().replace(b"MD", b"md"), items[2].payload))
    return _build(items)


def duplicate_nfc_cyrillic() -> bytes:
    """The same Cyrillic name spelled with `й` precomposed and as `и` plus a breve."""
    items = members(CYRILLIC_STEM)
    decomposed = unicodedata.normalize("NFD", items[2].name.decode("utf-8")).encode("utf-8")
    assert decomposed != items[2].name
    items.append(Member(decomposed, items[2].payload, flags=items[2].flags))
    return _build(items)


# ------------------------------------------------------- bundle_stem_mismatch


def stem_mismatch_name() -> bytes:
    items = members()
    items[1].name = b"other_blocks.json"
    return _build(items)


def stem_mismatch_case() -> bytes:
    """`Bundle.pdf` beside `bundle_blocks.json`: names that differ only by case."""
    items = members()
    items[0].name = b"Bundle.pdf"
    return _build(items)


def stem_mismatch_normalisation() -> bytes:
    """Cyrillic stems that look alike and differ in raw bytes: NFC in two, NFD in one."""
    items = members(CYRILLIC_STEM)
    items[2].name = unicodedata.normalize("NFD", items[2].name.decode("utf-8")).encode("utf-8")
    assert items[2].name != members(CYRILLIC_STEM)[2].name
    return _build(items)


# ----------------------------------------------------------- bundle_member_set


def missing_pdf() -> bytes:
    return _build(members(roles=(fmt.ROLE_BLOCKS, fmt.ROLE_RESULTS_MD)))


def missing_blocks() -> bytes:
    return _build(members(roles=(fmt.ROLE_PDF, fmt.ROLE_RESULTS_MD)))


def missing_results() -> bytes:
    return _build(members(roles=(fmt.ROLE_PDF, fmt.ROLE_BLOCKS)))


def unknown_member() -> bytes:
    items = members()
    items.append(Member(f"{STEM}_notes.txt".encode(), b"not a bundle member"))
    return _build(items)


def repeated_suffix() -> bytes:
    """Two PDFs. Distinct names, so this is a repeated suffix and not a duplicate."""
    items = members()
    items.append(Member(b"second.pdf", items[0].payload))
    return _build(items)


def ordinary_zip() -> bytes:
    """A ZIP of ordinary files. It is a ZIP, so it is refused for its members, not as a
    non-ZIP: `portal_bundle_required` is for a part that is not an archive at all."""
    return _build([
        Member(b"readme.txt", b"just some files"), Member(b"table.csv", b"a,b\n1,2\n"),
        Member(b"picture.png", b"\x89PNG\r\n\x1a\n"),
    ])


# -------------------------------------------------------------- blocks_json_invalid


def _with_blocks(mutate: Callable[[dict], None] | None = None, *, raw: bytes | None = None,
                 stem: str = STEM) -> bytes:
    items = members(stem)
    if raw is None:
        document = json.loads(base_files(stem).blocks_json)
        if mutate is not None:
            mutate(document)
        raw = blocklist.dump(document)
    items[1].payload = raw
    return _build(items)


def _set_first(key: str, value: object) -> Callable[[dict], None]:
    def mutate(document: dict) -> None:
        document["blocks"][0][key] = value
    return mutate


def _delete(key: str) -> Callable[[dict], None]:
    def mutate(document: dict) -> None:
        del document[key]
    return mutate


def _second_block_repeats_the_first(document: dict) -> None:
    document["blocks"][1] = copy.deepcopy(document["blocks"][0])


def _page_gap(document: dict) -> None:
    document["pages"][1]["page_index"] = 2


def _unknown_page(document: dict) -> None:
    document["blocks"][0]["page_index"] = 7


def _two_point_polygon(document: dict) -> None:
    document["blocks"][0]["polygon_points"] = [[0.1, 0.1], [0.2, 0.2]]


def _polygon_without_points(document: dict) -> None:
    """A block that says it is a polygon and carries no vertices (the key is there, `null`)."""
    document["blocks"][0].update(shape_type="polygon", polygon_points=None)


def _unknown_shape_type(document: dict) -> None:
    """A shape the portal's set {rectangle, polygon} does not hold."""
    document["blocks"][0]["shape_type"] = "circle"


def _set_page(key: str, value: object) -> Callable[[dict], None]:
    def mutate(document: dict) -> None:
        document["pages"][0][key] = value
    return mutate


BLOCKS_INVALID: dict[str, Callable[[], bytes]] = {
    "not_json": lambda: _with_blocks(raw=b"{ this is not JSON"),
    "not_utf8": lambda: _with_blocks(raw=b'{"schema_version": 1}\xff\xfe'),
    "not_an_object": lambda: _with_blocks(raw=b"[1, 2, 3]"),
    "wrong_schema_version": lambda: _with_blocks(lambda d: d.update(schema_version=2)),
    "wrong_coordinate_space": lambda: _with_blocks(
        lambda d: d.update(coordinate_space="pixels_top_left")),
    "missing_blocks_key": lambda: _with_blocks(_delete("blocks")),
    "no_pages": lambda: _with_blocks(lambda d: d.update(pages=[])),
    "bad_block_id": lambda: _with_blocks(_set_first("block_id", "blk_NOT-HEX")),
    "bad_block_type": lambda: _with_blocks(_set_first("block_type", "table")),
    "bad_status": lambda: _with_blocks(_set_first("status", "Recognized!")),
    "coords_out_of_range": lambda: _with_blocks(_set_first("coords_norm", [0.1, 0.1, 1.4, 0.9])),
    "coords_inverted": lambda: _with_blocks(_set_first("coords_norm", [0.9, 0.1, 0.1, 0.9])),
    "coords_wrong_length": lambda: _with_blocks(_set_first("coords_norm", [0.1, 0.1, 0.9])),
    "duplicate_block_id": lambda: _with_blocks(_second_block_repeats_the_first),
    "page_index_gap": lambda: _with_blocks(_page_gap),
    "block_on_unknown_page": lambda: _with_blocks(_unknown_page),
    "bad_rotation": lambda: _with_blocks(_set_page("rotation", 45)),
    "zero_width": lambda: _with_blocks(_set_page("width_px", 0)),
    "polygon_with_two_points": lambda: _with_blocks(_two_point_polygon),
    "polygon_without_points": lambda: _with_blocks(_polygon_without_points),
    "unknown_shape_type": lambda: _with_blocks(_unknown_shape_type),
    "ordinal_a_string": lambda: _with_blocks(_set_first("ordinal", "1")),
}


def blocks_json_invalid(kind: str = "not_json") -> bytes:
    return BLOCKS_INVALID[kind]()


# ------------------------------------------------------------- blocks_page_count


def _bundle_with_pages(pages: tuple[PageFacts, ...]) -> bytes:
    """The base PDF with a block list and markdown built for a different page list."""
    files = make_files(base_files().pdf, STEM, pages=pages)
    return _build(pack(files))


def blocks_fewer_pages() -> bytes:
    """The list describes one page of a two-page PDF, and the markdown agrees with it."""
    return _bundle_with_pages(read_pages(base_files().pdf)[:1])


def blocks_more_pages() -> bytes:
    """The list describes three pages of a two-page PDF."""
    pages = read_pages(base_files().pdf)
    return _bundle_with_pages(pages + pages[:1])


# ------------------------------------------------------------------- blocks_count


def _with_stamps(count: int, *, page_index: int = 0) -> bytes:
    """The base bundle with ``count`` STAMP blocks added on one page. A stamp has no header in
    the markdown, so the list and the markdown still agree and only the ceiling is broken."""
    stamps = [Block(fmt.KIND_STAMP, page_index, (0.5, 0.86, 0.9, 0.95)) for _ in range(count)]
    return _build(pack(make_files(base_files().pdf, STEM, extra_blocks=stamps)))


def blocks_over_the_page_ceiling() -> bytes:
    """One page holds one block more than ``MAX_BLOCKS_PER_PAGE`` (`W55B-FIX`, X-4)."""
    return _with_stamps(fmt.MAX_BLOCKS_PER_PAGE)


# ----------------------------------------------------- results_blocks_mismatch

_SECTION = re.compile(r"(?=^### BLOCK #)", re.MULTILINE)


def _with_markdown(edit: Callable[[str], str], files: PortalFiles | None = None) -> bytes:
    files = files or base_files()
    items = pack(files)
    items[2].payload = edit(files.results_md.decode("utf-8")).encode("utf-8")
    return _build(items)


def markdown_missing_a_header() -> bytes:
    """A TEXT block of the list with no section in the markdown."""
    def edit(text: str) -> str:
        parts = _SECTION.split(text)
        return "".join(parts[:-1])
    return _with_markdown(edit)


def markdown_extra_header() -> bytes:
    """A section for a block the list does not hold."""
    extra = ("### BLOCK #9 [TEXT]: blk_" + "0" * 32 + "\n\n> **Created:** x\n\ntext\n")
    return _with_markdown(lambda text: text + "\n" + extra)


def markdown_type_differs() -> bytes:
    return _with_markdown(lambda text: text.replace("[TEXT]", "[IMAGE]", 1))


def markdown_duplicate_header() -> bytes:
    def edit(text: str) -> str:
        parts = _SECTION.split(text)
        return "".join(parts) + parts[1]
    return _with_markdown(edit)


def markdown_header_for_a_stamp() -> bytes:
    """The list holds a STAMP block; the markdown, which must never mention one, has a header."""
    stamp = Block(fmt.KIND_STAMP, 0, (0.5, 0.86, 0.9, 0.95),
                  fields=(("code", "СП-7-АР"),))
    files = make_files(base_files().pdf, STEM, extra_blocks=[stamp])
    stamp_id = next(b.block_id for b in files.blocks if b.kind == fmt.KIND_STAMP)
    return _with_markdown(
        lambda text: text + f"\n### BLOCK #99 [STAMP]: {stamp_id}\n\n> **Created:** x\n\nstamp\n",
        files)


def markdown_not_utf8() -> bytes:
    items = members()
    items[2].payload = b"# Document\n\xff\xfe\n"
    return _build(items)


MARKDOWN_MISMATCH: dict[str, Callable[[], bytes]] = {
    "missing_header": markdown_missing_a_header,
    "extra_header": markdown_extra_header,
    "type_differs": markdown_type_differs,
    "duplicate_header": markdown_duplicate_header,
    "header_for_a_stamp": markdown_header_for_a_stamp,
    "not_utf8": markdown_not_utf8,
}


# ------------------------------------------------------------ stamp_audit_invalid


def stamp_audit_not_json() -> bytes:
    items = members()
    items.append(Member(f"{STEM}_stamp_audit.json".encode(), b"{ not json", method=8))
    return _build(items)


def stamp_audit_over_cap(cap: int) -> bytes:
    """Valid JSON of `cap + 1` bytes: only the cap is wrong with it."""
    shell = b'{"schema_version": 1, "pad": ""}'
    padded = shell[:-2] + b"x" * (cap + 1 - len(shell)) + shell[-2:]
    assert len(padded) == cap + 1
    items = members()
    items.append(Member(f"{STEM}_stamp_audit.json".encode(), padded, method=8))
    return _build(items)


# --------------------------------------------------------------- size-driven ones


def _big_member(name: bytes, size: int, compress: str, *, declared: int | None = None,
                prefix: bytes = b"") -> Member:
    """A member of `size` actual bytes, stored or deflated (zlib: zeros are tiny)."""
    method = zipwrite.STORED if compress == "stored" else zipwrite.DEFLATED
    return Member(name, zipwrite.Fill(size, 0, prefix), method=method, deflate="zlib",
                  declared_size=declared)


def _archive_with_big_pdf(big: Member) -> list[Member]:
    items = members()
    items[0] = big
    return items


def member_size(path: Path, *, member_bytes: int, compress: str = "deflate") -> Path:
    """A PDF member one byte over `member_bytes`; the header says so truthfully."""
    big = _big_member(f"{STEM}.pdf".encode(), member_bytes + 1, compress, prefix=b"%PDF-1.7\n")
    zipwrite.write_zip(path, _archive_with_big_pdf(big))
    return path


def total_size(path: Path, *, member_bytes: int, total_bytes: int,
               compress: str = "deflate") -> Path:
    """Two large members, each inside `member_bytes`, that together pass `total_bytes`."""
    each = total_bytes // 2 + 1
    if each > member_bytes:
        raise ValueError("the member bound must be at least half the total bound")
    items = members()
    items[0] = _big_member(f"{STEM}.pdf".encode(), each, compress, prefix=b"%PDF-1.7\n")
    items.append(_big_member(f"{STEM}_results.html".encode(), each, compress))
    zipwrite.write_zip(path, items)
    return path


def compression_ratio(path: Path, *, size: int, ratio: int = fmt.MAX_COMPRESSION_RATIO) -> Path:
    """A deflated member of `size` zero bytes whose ratio is above `ratio` (checked)."""
    big = _big_member(f"{STEM}.pdf".encode(), size, "deflate", prefix=b"%PDF-1.7\n")
    zipwrite.write_zip(path, _archive_with_big_pdf(big))
    with zipscan.Archive.from_path(path) as archive:
        entry = archive.load_entries()[0]
        if entry.size <= ratio * entry.compressed_size:
            raise ValueError(f"{size} zero bytes deflate to {entry.compressed_size}: "
                             f"ratio {entry.size / entry.compressed_size:.0f}, not above {ratio}")
    return path


def size_lie_declared_small(path: Path, *, actual_bytes: int, declared_bytes: int = 1,
                            compress: str = "deflate") -> Path:
    """The header declares fewer bytes than the member unpacks to (a zip bomb's disguise)."""
    if declared_bytes >= actual_bytes:
        raise ValueError("a small lie declares fewer bytes than the member holds")
    big = _big_member(f"{STEM}.pdf".encode(), actual_bytes, compress, declared=declared_bytes,
                      prefix=b"%PDF-1.7\n")
    zipwrite.write_zip(path, _archive_with_big_pdf(big))
    return path


def size_lie_declared_large(path: Path, *, actual_bytes: int, declared_bytes: int,
                            compress: str = "stored") -> Path:
    """The header declares more bytes than the member holds; the member itself is small."""
    if declared_bytes <= actual_bytes:
        raise ValueError("a large lie declares more bytes than the member holds")
    big = _big_member(f"{STEM}.pdf".encode(), actual_bytes, compress, declared=declared_bytes,
                      prefix=b"%PDF-1.7\n")
    big.zip64 = declared_bytes > 0xFFFFFFFF       # a 4-byte header field cannot say it
    zipwrite.write_zip(path, _archive_with_big_pdf(big))
    return path


# ------------------------------------------------------------------- the registry


@dataclass(frozen=True)
class Negative:
    name: str
    constraint: str
    build: Callable[[], bytes]


def _keyed(constraint: str, builders: dict[str, Callable[[], bytes]]) -> list[Negative]:
    return [Negative(name, constraint, build) for name, build in builders.items()]


def small_negatives() -> list[Negative]:
    """Every negative that is small enough to be returned as bytes, with its rule."""
    found: list[Negative] = []
    found += _keyed("portal_bundle_required", {
        "bare_pdf": bare_pdf, "plain_text": plain_text, "gzip_stream": gzip_stream,
        "seven_zip_magic": seven_zip_magic, "empty_upload": empty_upload,
    })
    found += _keyed("bundle_unreadable", {
        "truncated": truncated, "garbage": garbage, "no_end_record": no_end_record,
        "entry_count_lies": entry_count_lies,
        "local_header_names_another_member": local_header_names_another_member,
        "crc_mismatch": crc_mismatch, "corrupt_deflate_data": corrupt_deflate_data,
        "sizes_disagree_within_bounds": sizes_disagree_within_bounds,
    })
    found += _keyed("bundle_entry_count", {"nine_entries": entry_count})
    found += _keyed("bundle_directory_entry", {
        "directory_entry": directory_entry, "macosx_directory": macosx_directory,
        "macosx_file": macosx_file,
    })
    found += _keyed("bundle_member_name", {
        "absolute_name": absolute_name, "drive_letter_name": drive_letter_name,
        "backslash_name": backslash_name, "dotdot_name": dotdot_name,
    })
    found += _keyed("bundle_symlink", {"symlink": symlink})
    found += _keyed("bundle_encrypted_member", {"encrypted_member": encrypted_member})
    found += _keyed("bundle_compression_method", {
        "bzip2": lambda: compression_method(12), "lzma": lambda: compression_method(14),
        "winzip_aes": lambda: compression_method(99),
    })
    found += _keyed("bundle_duplicate_member", {
        "duplicate_exact": duplicate_exact, "duplicate_casefolded": duplicate_casefolded,
        "duplicate_nfc_cyrillic": duplicate_nfc_cyrillic,
    })
    found += _keyed("bundle_stem_mismatch", {
        "stem_mismatch_name": stem_mismatch_name, "stem_mismatch_case": stem_mismatch_case,
        "stem_mismatch_normalisation": stem_mismatch_normalisation,
    })
    found += _keyed("bundle_member_set", {
        "missing_pdf": missing_pdf, "missing_blocks": missing_blocks,
        "missing_results": missing_results, "unknown_member": unknown_member,
        "repeated_suffix": repeated_suffix, "ordinary_zip": ordinary_zip,
    })
    found += _keyed("blocks_json_invalid", {
        name: (lambda kind=name: blocks_json_invalid(kind)) for name in BLOCKS_INVALID
    })
    found += _keyed("blocks_page_count", {
        "fewer_pages": blocks_fewer_pages, "more_pages": blocks_more_pages,
    })
    found += _keyed("blocks_count", {"over_the_page_ceiling": blocks_over_the_page_ceiling})
    found += _keyed("results_blocks_mismatch", MARKDOWN_MISMATCH)
    found += _keyed("stamp_audit_invalid", {"not_json": stamp_audit_not_json})
    return found


# Archives too large to hold as bytes, by the rule they break. Each takes the sizes it
# needs, writes to a path and returns it; `member_size` has two disguises beside the plain
# case, because a header's declared size is the first thing a zip bomb lies about.
SIZE_DRIVEN: dict[str, tuple[Callable[..., Path], ...]] = {
    "bundle_member_size": (member_size, size_lie_declared_small, size_lie_declared_large),
    "bundle_total_size": (total_size,),
    "bundle_compression_ratio": (compression_ratio,),
}


def by_constraint() -> dict[str, list[Negative]]:
    """The small negatives grouped under the constraint each is refused with."""
    grouped: dict[str, list[Negative]] = {}
    for negative in small_negatives():
        grouped.setdefault(negative.constraint, []).append(negative)
    return grouped
