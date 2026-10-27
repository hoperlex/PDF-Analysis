# CMP-INGEST-ZIP-01 — a safe reader for ZIP sets of whole stages

Task: [CMP-INGEST-ZIP-01](tasks/CMP-INGEST-ZIP-01.md). Lane branch `agent/cmp-ingest-zip-01`, base `cc3dd36b` on
`integration/compare-modules`. Plan `COMPARE-MODULES-PLAN.md` §3.2 `R3-17`; ADR-0025 decision 12 (and decision 9's batch
limits, decision 25: «a new reason under an existing code is the default»). Written 2026-10-28.

## 1. Result

`bundle_archive.extract_bundle` takes a **policy parameter**. The default, `PORTAL_POLICY`, is every rule the module had
before; a differential over 558 archives gives the same outcomes on the base commit and on this tree, byte for byte
(§8). The **set policy** is written in the new package `auditmanager.ingest.comparison_zip` and reads a ZIP of many PDFs:

- at most **N = 1 000 entries** and **2 GiB** uncompressed, each counted **over every level together**;
- **one nesting level** (an archive inside the archive, none inside that); a nested archive is read in the budget the
  first level left and its file is removed once read;
- a PDF member is any `.pdf` (any case), judged by the **existing PDF envelope** (`inspect_pdf`), which is a parameter;
- **names are hints, never identity**: a member is its ordinal, its SHA-256 and its size; every file is named by key in a
  private temporary directory; the hint is scrubbed and cut;
- thirteen refusal reasons `comparison_zip_*` under the existing `validation_failed`, `field: "file"`;
- adversarial tests for every class the brief names, **183 tests, 57 mutations, every one turns a test red** (§10).

No contract, migration, root lock, composition root or wiring file is touched; nothing calls the reader yet.

## 2. Premise (task file P-01, P-02)

Contract `1.9.0`, 115 paths / 130 operations / 351 schemas, 27 error codes, migration head `0038_comparison_foundation`,
base `cc3dd36b`: as the wave brief says, no STOP. The portal reader's `tests/integration/ingest/test_bundle_archive.py`
gave `269 passed` on the base without any container.

## 3. What was built

### `src/auditmanager/ingest/bundle_archive.py` (+77 / −3, the only edit of an existing source file)

| addition | what it is |
| --- | --- |
| `ArchivePolicy` (frozen dataclass) | `judge(entries) -> {key: entry}` (which entries the kind accepts), `translate(DomainError) -> DomainError` or `None` (how refusals are named), `max_directory_bytes` or `None` (how large a central directory it will read) |
| `PORTAL_POLICY` | `ArchivePolicy(judge=_judge_entries)`, nothing else: the default |
| `extract_bundle(handle, *, limits=..., policy=PORTAL_POLICY)` | the body became `_extract(handle, limits, policy)`; `policy.judge` replaces the call of `_judge_entries`; one directory-size check before `load_entries` when the policy carries a bound; the renaming wraps the call only when the policy has one |
| `ArchiveEntry`, `ACCEPTED_METHODS`, `is_unsafe_name`, `duplicate_key` (+ `decode_display_name`, already public, now in `__all__`) | public names for what a policy's judge reuses, so that a set applies the **same** name, duplicate and method rules as the bundle, not a copy of them |

`_judge_declared` and `_unpack` — the declared sizes, the counted bytes, the ratio on the bytes the stream really used, the
CRC — are not touched and are shared by both policies. The `looks_like_zip` check, the temporary-directory prefix
(`auditmanager-bundle-`, so `jobs.temporaries` sweeps a set's directories when stale — tested) and the cleanup on refusal
are the portal's.

### `src/auditmanager/ingest/comparison_zip/`

| module | content |
| --- | --- |
| `refusals.py` | the 13 `CONSTRAINTS`, one fixed sentence each, `refuse_set`, and `translate` (renames the shared reader's `bundle_*` reasons; an unnamed one is a `RuntimeError`, not a refusal) |
| `policy.py` | the bounds (`SET_*`), `SetPolicy` (validated: no negative bound, nesting 0 or 1 only), `DEFAULT_SET_POLICY`, `LevelJudge` (the judge of one archive; counts the entries it saw) |
| `reader.py` | `extract_pdf_set`, `ExtractedSet`, `SetMember`, `SetMemberRefused`, `inspect_pdf_member`, the hint scrub |
| `__init__.py` | the names below; also re-exports `looks_like_zip` |

## 4. The rules, in the order they are applied

Cheapest first, as the portal reader does; each refusal answers `field: "file"` and carries no name, size or byte.

| # | rule | reason (`comparison_zip_…`) | where |
| --- | --- | --- | --- |
| 0 | the upload is a ZIP (magic); the end records are found; not multi-disk; ZIP64 consistent | `unreadable` | shared (`looks_like_zip`, `_Archive`) |
| 0 | more than N entries — also when the end record only *claims* more | `entry_count` | shared (`declared_count`) |
| 0 | a central directory larger than `directory_bytes` (4 MiB), refused before it is loaded | `unreadable` | the policy parameter |
| 1 | an absolute, drive-letter, backslash or `..` name — in the header **and** in the name a reader would show (Unicode Path field); also for a directory entry | `member_name` | `LevelJudge`, `is_unsafe_name` |
| 1 | a symbolic link (Unix mode bit, Unix entries only) | `symlink` | `LevelJudge` |
| 1 | an encrypted member (flag 0 or 6; AES is method 99 *with* the flag: reported as encrypted) | `encrypted_member` | `LevelJudge` |
| 1 | a method other than stored or deflate | `compression_method` | `LevelJudge` |
| 1 | a `__MACOSX/` entry; a directory entry that holds bytes | `member_kind` | `LevelJudge` |
| 2 | a name that repeats, also after case folding and NFC (of the shown name) | `duplicate_member` | `LevelJudge`, `duplicate_key` |
| 3 | a member that is not `.pdf` or (first level) `.zip` | `member_kind` | `LevelJudge` |
| 3 | a `.zip` at the second level | `nested_depth` | `LevelJudge` (`archives_allowed=False`) |
| 4 | a member declared over 250 MiB; the declared total over 2 GiB; a declared ratio over 100 (member and archive) — before a byte is unpacked | `member_size`, `total_size`, `compression_ratio` | shared (`_judge_declared`) |
| 5 | the bytes that come out, counted: over the member bound, the total, **or the member's own declaration** (a header that lies small); fewer than declared, a CRC mismatch, a stream that does not end, a local header that names another member | `member_size`, `total_size`, `unreadable` | shared (`_unpack`, `data_offset`) |
| 5 | the ratio of what came out to the compressed bytes the stream really used (a header may pad) | `compression_ratio` | shared (`_unpack`) |
| 6 | a nested archive: rules 0–5 again, in the entries and bytes the first level left; its file is then removed | the same | `reader.py` |
| 7 | no PDF in the set at all | `empty` | `reader.py` |
| 8 | each PDF, in set order, by the envelope — a refusal is `SetMemberRefused` with the envelope's own `field`/`constraint` | the envelope's (`pdf_magic_bytes`, `parseable_pdf`, `not_encrypted`, …) | `reader.py` |

A directory entry (name ends `/`, declared size 0) is structure: judged for its name, counted, never unpacked. The portal
refuses it; a ZIP of a folder has them (Windows Explorer and 7-Zip write them).

## 5. The figures

| bound | value | basis |
| --- | --- | --- |
| entries `N` (all levels together) | **1 000** — decided by this slice (the ADR left it to it) | the batch holds ≤ 10 000 files and ≤ 100 sets (decision 9), so a set averages 100 files and one archive may hold ten times that; each PDF costs two child processes (§13), so `N` is also a bound on time. The original's guard was 20 000 members per archive (`ORIGINAL-STAGE-COMPARISON-INVENTORY.md` §3.1, `stage_upload.py:40–58`) — a DoS limit, not a use case |
| total uncompressed (all levels) | **2 GiB** | ADR decision 12. The original: archive ≤ 2 GiB, unpacked ≤ 10 GiB |
| one member | **250 MiB** | the existing envelope's `MAX_BYTES` |
| ratio | **100** | the portal reader's `MAX_RATIO` |
| central directory | **4 MiB** | the reader's own bound is `entries × 196 KiB` (`_MAX_ENTRY_BYTES`): 8 entries made it 1.5 MiB, **1 000 would let one upload make the API read 196 MiB**; 4 MiB is 4 KiB an entry |
| nesting | **1** | ADR decision 12 |

A nested archive's own bytes count against the total (they are written to disk before they are read), and so do the bytes
inside it: a megabyte of PDF inside a ZIP beside a megabyte of PDF costs three. The disk a set can use is the total, never
more, whatever the nesting. A nested archive is a member like any other, so it is at most 250 MiB.

## 6. The API for `CMP-INGEST-01` and `CMP-INGEST-02`

All names are in `auditmanager.ingest.comparison_zip` (inside the one `ingest` context; `ingest/public.py` and
`ingest/__init__.py` are not edited).

```python
from auditmanager.ingest.comparison_zip import (
    extract_pdf_set, ExtractedSet, SetMember, SetMemberRefused, SetPolicy, DEFAULT_SET_POLICY,
    inspect_pdf_member, looks_like_zip, CONSTRAINTS, FIELD, MAX_HINT,
    SET_MAX_ENTRIES, SET_TOTAL_BYTES, SET_MEMBER_BYTES, SET_MAX_RATIO, SET_DIRECTORY_BYTES, SET_MAX_NESTING,
)

extract_pdf_set(
    handle: BinaryIO,                      # seekable, the whole ZIP; left open by the reader
    *,
    policy: SetPolicy = DEFAULT_SET_POLICY,    # entries, total_bytes, member_bytes, ratio, directory_bytes, nesting_levels
    envelope: Callable[[BinaryIO], PdfFacts] | None = inspect_pdf_member,
) -> ExtractedSet                          # a context manager; close() removes every temporary directory

ExtractedSet.members        # tuple[SetMember, ...] in set order
ExtractedSet.entries_seen   # entries of every archive of the set, directory entries included
ExtractedSet.bytes_seen     # uncompressed bytes of every member of every level, archives included
ExtractedSet.open(member)   # BinaryIO on the temporary file

SetMember.ordinal           # 0.. in the order the archives list their PDFs (a nested archive's at its own place): the handle
SetMember.sha256, .size     # identity, with the ordinal
SetMember.level             # 0 the archive itself, 1 an archive inside it
SetMember.display_name      # a HINT (scrubbed, at most MAX_HINT = 1024 characters; a nested archive counts as a folder)
SetMember.base_name, .folder   # derived from the hint; base_name is never blank ("document.pdf" at worst)
SetMember.path              # the temporary file (valid until close)
SetMember.facts             # PdfFacts from the envelope, or None when envelope=None
```

Errors: `DomainError(VALIDATION_FAILED, field="file", constraint=<one of CONSTRAINTS>)` for the archive;
`SetMemberRefused` (a `DomainError` with `.member_ordinal`) for a PDF that fails `envelope`, keeping the envelope's code,
`field` (`content`), `constraint` and sentence. Any other exception is the server's and propagates unchanged; in every case
the temporary directories are already removed.

What the consumer must do about three things:

1. **Pass its comparison envelope.** The default is the *existing* envelope, whose `PAGE_ELEMENTS_MAX` = 400 000 refuses
   the real A1 sheet of the measured set (536 426 elements, ADR-0025 addendum item 3). `CMP-INGEST-01` owns the comparison
   envelope; it passes it as `envelope=`.
2. **Decide whether the envelope runs inline.** It costs two child processes a PDF: **361 ms a PDF measured** (five
   six-page PDFs of `fixtures/comparison/vs1`, best of three, 1.81 s against 0.01 s without; command in §12) — about six
   minutes for 1 000 small PDFs, and up to 60 s CPU a hostile one. A set of that size is not one unit of work under the
   900 s attempt watchdog. `envelope=None` runs none and leaves `facts = None`; the caller then calls
   `inspect_pdf_member` (or its own) on `ExtractedSet.open(member)` one member at a time, as separate work. **A member
   whose check has not run must not be stored.**
3. **Check the disk before the call.** A set can use up to 2 GiB of temporary space at once (the peak is the total). The
   reader does not look at free space (decision 9's `comparison-disk` readiness is the caller's).

The stage of a set (the original's `VALID_STAGES` check, «wrong stage») is the batch's declared role of the upload, not a
property of an archive: the reader has no stage parameter and checks none. (The id `CP-01` named in the brief is not in
`ORIGINAL-STAGE-COMPARISON-INVENTORY.md`; the original's rules were taken from its §3.1.)

## 7. The refusal reasons, and the registration they need

The thirteen reasons are new `constraint` values under the existing code, `field: "file"`:
`comparison_zip_unreadable`, `_entry_count`, `_member_name`, `_symlink`, `_encrypted_member`, `_compression_method`,
`_duplicate_member`, `_member_kind`, `_nested_depth`, `_member_size`, `_total_size`, `_compression_ratio`, `_empty`.
`contracts/domain/v1/error-codes.json` lists registered constraints in the prose notes of `validation_failed`; **adding
the note is a contract slot's edit and is outside this lane** (rule 5 of the brief). No test fails without it (the tests
that read those notes cover the portal's and the comparison upload's values only); a client that shows a Russian sentence
per constraint needs it. Proposed text for the slot that owns the note:

> constraint, comparison ZIP set (CMP-INGEST-ZIP-01, ADR-0025 decision 12): the reader of a ZIP that holds the PDFs of a
> whole stage refuses with field file and one of these registered values: comparison_zip_unreadable (not a ZIP, or its
> directory cannot be read within its bounds), comparison_zip_entry_count (more than 1 000 entries over the archive and
> the archive inside it together), comparison_zip_member_name (an absolute, drive-letter, backslash or .. name, in the
> header or in the name a reader would show), comparison_zip_symlink, comparison_zip_encrypted_member,
> comparison_zip_compression_method (a method other than stored or deflate), comparison_zip_duplicate_member (a name that
> repeats, also after case folding and NFC), comparison_zip_member_kind (a member that is neither a PDF nor, at the first
> level, a ZIP: another format, a __MACOSX/ entry, a directory entry that holds bytes), comparison_zip_nested_depth (an
> archive inside an archive that is itself inside the archive), comparison_zip_member_size (one member over 250 MiB,
> declared or actual), comparison_zip_total_size (more than 2 GiB uncompressed over every level), comparison_zip_compression_ratio
> (a member or an archive compressed more than 100 to one) and comparison_zip_empty (no PDF document in it). A PDF member
> that fails the existing envelope is refused with the envelope's own constraint under field content. No name is echoed.

The shared reader's own `bundle_*` reasons never leave the set reader (test `no_portal_constraint_name_ever_leaves…`,
mutations M20, M32, M33), and a test reads `bundle_archive.py` with `ast` to prove that every reason its shared functions
can raise has a name in the table (M21).

## 8. The portal policy is unchanged — three layers

1. **The existing suite, unedited**, on this tree (`PYTHONPATH=$PWD/src AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent
   .venv/bin/python -m pytest -q tests/integration/ingest/<file>.py -p no:cacheprovider`; no container needed):
   `test_bundle_archive` **269 passed** (the same count as on the base), `test_bundle_envelope` 99, `test_uncuttable_image_block`
   60, `test_block_ceilings` 11, `test_display_name_scrub` 12; and `tests/unit/jobs/test_stale_temporaries.py` (it reads
   `bundle_archive`'s source for the temporary prefix) green.
2. **A differential over a corpus**, run against the unmodified base (`git archive cc3dd36b src contracts`) and against
   this tree with the same script: 558 outcomes — the seven committed bundles, the 70 small negatives (68 distinct names; the
   outcome is keyed by name) of `tools/fixtures/portal_bundle/archive_negatives.py` (each at the production bounds and at lowered ones), the
   positives (ZIP64 among them), the size-driven families at lowered bounds (member size stored and deflated, at the bound,
   the total, the ratio, a header that lies small and one that lies large) and 400 seeded byte-level mutations of a
   committed bundle (flips, truncations, appended bytes, flips inside the directory and the end record). For each the
   outcome is the members it kept (role, shown name, size, SHA-256, the file's own digest, the file's name) or the
   refusal's field, constraint and **full message**; the JSON of the two runs is identical
   (`cmp`, SHA-256 `e0a8f5820e51…c010`; 167 accepted, 391 refused). The script is not committed (it needs the base commit
   unpacked beside this tree); the command is
   `python -I portal_diff.py SRC TOOLS_FIXTURES REPO OUT.json` for `SRC` in `{base/src, $PWD/src}` followed by `cmp`.
3. **`test_portal_policy_unchanged.py`** (22 tests): the default is `PORTAL_POLICY`, which has `judge is _judge_entries`, no
   `translate`, no directory bound; the portal's bounds are the ruled figures (8, 300 MiB, 100, 250 MiB, 16 MiB, 4 MiB);
   the committed bundles read the same with the default and with the policy named; nine refusals keep their `bundle_*`
   name and their exact sentence; the portal accepts no set and the set accepts no bundle; the portal has no directory
   bound; the set package is imported by no module of the portal path. Mutations M27 and M27b turn it red.

## 9. Tests (`tests/unit/ingest/comparison_zip/`, no container, 5–8 s)

| file | tests | what |
| --- | --- | --- |
| `test_adversarial_archives.py` | 100 | bombs by ratio (declared, hidden by padding behind the stream, nested) and by absolute size (production figures with lying headers, no gigabyte written; lowered figures with real bytes; the inclusive boundary to the byte; a header that declares less than the member holds, stored and deflated, refused within one piece of the declaration); traversal (6 shapes), absolute / drive-letter / backslash (8), a hostile Unicode Path field and its mirror image; symbolic links (4), encrypted members (5, AES included), 7 compression methods; duplicates (6 shapes, nested); the shared local header of a quine bomb; nesting (accepted at 1, refused at 2, a chain of 6 opens exactly two archives, a policy cannot allow 2); 17 non-PDF names, `__MACOSX/`, a directory with bytes, an empty set, garbage and truncated input; 1 001 entries against 1 000, entries over both levels, the end record that lies, the directory bound; no `bundle_*` reason ever leaves |
| `test_set_reader.py` | 47 | what the standard library reads (stored, deflated, ZIP64 local, ZIP64 directory and end record, data descriptors); determinism; names are hints (renaming changes nothing but the hint, no name reaches a path, files are named by key, the container is removed); the hint scrub equals the portal's for 19 code points; cut; `base_name`/`folder`; cleanup, double close; the sweep recognises the directories; the policy validates; every sentence passes the error screen; the table of reasons is total |
| `test_member_envelope.py` | 14 | the real envelope (a child process each): facts kept; five bad PDFs (text, empty, a ZIP named `.pdf`, truncated, encrypted) refuse the set with the envelope's refusal, the ordinal of the member, nothing else added; a nested member's ordinal; no PDF is read for a refused archive; a caller's envelope; `None` runs none; a server fault propagates and leaves nothing |
| `test_portal_policy_unchanged.py` | 22 | §8 layer 3 |
| `zip_builders.py` | — | header-level archives with the repository's own writer (`tools/fixtures/portal_bundle/zipwrite.py`, loaded by path), and an autouse fixture that makes the reader's temporary directories in a directory of the test and fails the test if any is left |

Every refusal test goes through one helper that also requires `field: "file"`, a registered constraint, the error
envelope's screen, and (by the fixture) an empty temporary directory afterwards.

## 10. Mutation proofs

Each row: the mutation (a textual replacement in the named file), the number of tests it turned red on this tree, and one
of them. Run by `mutate.py` (scratchpad, not committed): apply, run `tests/unit/ingest/comparison_zip`, check that the tests
named for the guard are among the red ones, restore from a copy, and finally run the directory on the restored tree
(**`183 passed`**, `git diff` empty). 57 mutations; the table is the complete run **after** the repairs of §11, on commit
`2c3e3f30` (the source files of the lane are unchanged since; the later commits are documents).

| id | guard | file | mutation | red | first red test |
| --- | --- | --- | --- | --- | --- |
| M01 | declared ratio rule (a member or the archive compressed too much) | bundle_archive.py | `return size > ratio * compressed` -> `return False` | 5 | `test_a_bomb_inside_a_nested_archive_is_refused_by_the_same_rule` |
| M02 | ratio is judged on the bytes the stream used, not on the header's claim | bundle_archive.py | `if _ratio_exceeded(actual, archive.consumed, limits.ratio):` -> `if _ratio_exceeded(actual, entry.compressed_size, limits.ratio):` | 1 | `test_the_ratio_is_judged_on_the_bytes_the_stream_used_not_on_what_the_header_claims` |
| M03 | a member is held to its own declaration while it is counted | bundle_archive.py | `if actual > entry.size:` -> `if False:` | 2 | `test_a_header_that_declares_less_than_the_member_holds_is_refused_as_soon_as_it_is_pass...` |
| M04 | the member bound (declared and counted) | bundle_archive.py | `if entry.size > limits.member_bytes: raise refuse("bundle_member_si...` -> `if False: raise refuse("bundle_member_size") if role in _TEXT_ROLES`; `if actual > limits.member_bytes:` -> `if False:` | 4 | `test_a_member_declared_over_the_production_member_bound_is_refused_without_unpacking_it` |
| M05 | the total bound (declared and counted) | bundle_archive.py | `if declared_total > limits.total_bytes:` -> `if False:`; `if total > limits.total_bytes:` -> `if False:` | 4 | `test_members_declared_over_two_gib_together_are_refused_at_the_production_figure` |
| M06 | the entry count | bundle_archive.py | `if archive.declared_count > limits.entries:` -> `if False:` | 6 | `test_an_end_record_that_claims_more_entries_than_the_limit_is_refused_before_the_direct...` |
| M07 | the entry budget is shared by the levels | comparison_zip/reader.py | `entries=policy.entries - entries_seen,` -> `entries=policy.entries,` | 1 | `test_the_limit_is_over_every_level_together` |
| M08 | the byte budget is shared by the levels | comparison_zip/reader.py | `total_bytes=policy.total_bytes - bytes_seen,` -> `total_bytes=policy.total_bytes,` | 1 | `test_the_total_is_over_every_level_together_and_counts_the_container` |
| M09 | a nested archive's own bytes come out of the budget | comparison_zip/reader.py | `bytes_seen = sum(member.size for member in outer.members.values())` -> `bytes_seen = sum(m.size for k, m in outer.members.items() if not k....` | 1 | `test_the_total_is_over_every_level_together_and_counts_the_container` |
| M10 | the central directory bound | bundle_archive.py | `policy.max_directory_bytes is not None and archive._directory_size ...` -> `False` | 2 | `test_a_central_directory_over_the_policy_bound_is_refused_before_it_is_read` |
| M11 | the name rule of the set (traversal, absolute, backslash, drive letter) | comparison_zip/policy.py | `if is_unsafe_name(name): raise refuse_set("comparison_zip_member_na...` -> `if False: raise refuse_set("comparison_zip_member_name")` | 1 | `test_a_header_name_that_is_hostile_is_refused_whatever_the_unicode_path_field_shows` |
| M11a | the absolute-name clause of the shared name rule | bundle_archive.py | `name.startswith(b"/") or b"\\" in name` -> `False or b"\\" in name` | 3 | `test_a_name_that_only_the_unicode_path_field_makes_hostile_is_refused` |
| M11b | the backslash clause of the shared name rule | bundle_archive.py | `or b"\\" in name` -> `or False` | 3 | `test_an_absolute_drive_letter_or_backslash_name_is_refused[\\\\server\\share\\evil.pdf]` |
| M11c | the drive-letter clause of the shared name rule | bundle_archive.py | `or (len(name) >= 2 and name[1:2] == b":" and name[:1].isalpha())` -> `or False` | 2 | `test_an_absolute_drive_letter_or_backslash_name_is_refused[Z:/evil.pdf]` |
| M11d | the dot-dot clause of the shared name rule | bundle_archive.py | `or b".." in name.split(b"/")` -> `or False` | 12 | `test_a_header_name_that_is_hostile_is_refused_whatever_the_unicode_path_field_shows` |
| M12 | the name a reader would show (Unicode Path field) is held to the name rule | comparison_zip/policy.py | `if is_unsafe_name(shown.encode("utf-8")):` -> `if False:` | 1 | `test_a_name_that_only_the_unicode_path_field_makes_hostile_is_refused` |
| M13 | symbolic links | comparison_zip/policy.py | `if entry.is_symlink:` -> `if False:` | 6 | `test_a_symbolic_link_member_is_refused[folder/]` |
| M13b | a symbolic link is a Unix mode bit, and only on a Unix entry | bundle_archive.py | `return self.create_system == _UNIX and (mode & _MODE_TYPE_MASK) == ...` -> `return (mode & _MODE_TYPE_MASK) == _MODE_SYMLINK` | 1 | `test_a_member_made_by_another_system_is_not_taken_for_a_link` |
| M14 | encrypted members | comparison_zip/policy.py | `if entry.is_encrypted:` -> `if False:` | 7 | `test_an_encrypted_member_is_refused[strong-flag-alone]` |
| M14b | strong (flag 6) encryption | bundle_archive.py | `return bool(self.flags & _FLAG_ENCRYPTED) or bool(self.flags & _FLA...` -> `return bool(self.flags & _FLAG_ENCRYPTED)` | 1 | `test_an_encrypted_member_is_refused[strong-flag-alone]` |
| M15 | compression methods other than stored and deflate | comparison_zip/policy.py | `if entry.method not in ACCEPTED_METHODS:` -> `if False:` | 8 | `test_a_method_other_than_stored_or_deflate_is_refused[12]` |
| M16 | names that repeat | comparison_zip/policy.py | `if key in seen:` -> `if False:` | 9 | `test_a_name_that_repeats_inside_a_nested_archive_is_refused` |
| M16b | case folding in the repeat rule | bundle_archive.py | `folded = unicodedata.normalize("NFC", shown).casefold()` -> `folded = unicodedata.normalize("NFC", shown)` | 6 | `test_a_name_that_repeats_inside_a_nested_archive_is_refused` |
| M16c | NFC in the repeat rule | bundle_archive.py | `folded = unicodedata.normalize("NFC", shown).casefold()` -> `folded = shown.casefold()`; `return unicodedata.normalize("NFC", folded)` -> `return folded` | 2 | `test_a_name_that_repeats_is_refused_also_after_case_folding_and_nfc[nfc-cyrillic]` |
| M17 | no archive inside the second-level archive | comparison_zip/reader.py | `second = LevelJudge(archives_allowed=False)` -> `second = LevelJudge(archives_allowed=True)` | 2 | `test_a_chain_of_archives_is_stopped_at_the_second_level_and_never_unpacked_further` |
| M17b | a policy that allows no nesting | comparison_zip/reader.py | `first = LevelJudge(archives_allowed=policy.nesting_levels >= 1)` -> `first = LevelJudge(archives_allowed=True)` | 1 | `test_a_policy_that_allows_no_nesting_refuses_the_first` |
| M17c | a policy cannot be made to allow a second level | comparison_zip/policy.py | `if not 0 <= self.nesting_levels <= SET_MAX_NESTING:` -> `if False:` | 3 | `test_a_policy_cannot_allow_more_than_one_level` |
| M18 | members that are not PDFs | comparison_zip/policy.py | `else: raise refuse_set("comparison_zip_member_kind") return chosen` -> `else: chosen[f"{KEY_PDF}{entry.index:05d}"] = entry return chosen` | 19 | `test_a_member_that_is_not_a_pdf_is_refused[.DS_Store]` |
| M18b | __MACOSX/ entries | comparison_zip/policy.py | `if name.startswith(b"__MACOSX/"):` -> `if False:` | 1 | `test_macos_resource_forks_are_refused_not_skipped` |
| M18c | a directory entry that holds bytes | comparison_zip/policy.py | `if entry.size != 0:` -> `if False:` | 1 | `test_a_directory_entry_that_holds_bytes_is_refused` |
| M18e | an archive whose only members hold no PDF (the reader) | comparison_zip/reader.py | `if not drafts:` -> `if False:` | 2 | `test_an_archive_that_holds_no_pdf_is_refused` |
| M18f | the suffix is judged case-blind | comparison_zip/policy.py | `lowered = name.lower()` -> `lowered = name` | 6 | `test_directory_entries_are_structure_and_the_suffix_is_case_blind` |
| M19 | directory entries are skipped as structure | comparison_zip/policy.py | `continue files.append(entry)` -> `pass files.append(entry)` | 9 | `test_an_archive_that_holds_no_pdf_is_refused` |
| M20 | the set's refusals are renamed (the portal's names never leave) | comparison_zip/reader.py | `judge=judge, translate=translate, max_directory_bytes=policy.direct...` -> `judge=judge, translate=None, max_directory_bytes=policy.directory_b...` | 27 | `test_a_bomb_inside_a_nested_archive_is_refused_by_the_same_rule` |
| M21 | the table of renamed refusals is total | comparison_zip/refusals.py | `"bundle_total_size": "comparison_zip_total_size",` -> `` | 5 | `test_members_declared_over_two_gib_together_are_refused_at_the_production_figure` |
| M22 | a refused set keeps no temporary directory | comparison_zip/reader.py | `stack.callback(bundle.close) return bundle` -> `return bundle` | 13 + 8 errors | `test_a_caller_envelope_that_refuses_names_the_member` |
| M23 | a nested archive's own file is removed once read | comparison_zip/reader.py | `container.unlink()` -> `pass` | 2 | `test_no_name_reaches_a_path` |
| M24 | every member is handed to the envelope | comparison_zip/reader.py | `facts = envelope(pdf)` -> `facts = None` | 12 | `test_a_caller_envelope_that_refuses_names_the_member` |
| M24b | the refusal names the member by ordinal | comparison_zip/reader.py | `raise SetMemberRefused(refused, ordinal) from None` -> `raise SetMemberRefused(refused, 0) from None` | 8 | `test_a_caller_envelope_that_refuses_names_the_member` |
| M24c | the archive rules come before any PDF is read | comparison_zip/reader.py | `drafts: list[_Draft] = [] for key, member in outer.members.items():` -> `drafts: list[_Draft] = [] if envelope is not None: for _key, _membe...` | 10 | `test_a_caller_envelope_that_refuses_names_the_member` |
| M24d | the envelope's refusal keeps its message | comparison_zip/reader.py | `refused.code, message=refused.custom_message, **dict(refused.detail...` -> `refused.code, message=None, **dict(refused.detail_fields)` | 5 | `test_a_pdf_that_fails_the_envelope_refuses_the_set_with_the_envelopes_own_refusal[a-zip...` |
| M24e | a deferred envelope (None) runs none | comparison_zip/reader.py | `if envelope is not None: try:` -> `if True: try:` | 54 | `test_a_benign_unicode_path_is_shown_and_accepted` |
| M25 | the hint is scrubbed of control and format characters | comparison_zip/reader.py | `"_" if unicodedata.category(ch) in _UNSHOWABLE or ch in _INVISIBLE_...` -> `ch` | 19 | `test_a_hint_never_carries_a_character_a_screen_or_a_log_would_act_on[U+0000]` |
| M25b | the hint is cut | comparison_zip/reader.py | `return cleaned.strip()[:MAX_HINT]` -> `return cleaned.strip()` | 1 | `test_a_hint_is_cut_and_a_base_name_never_blank` |
| M25c | a base name is never blank | comparison_zip/reader.py | `[:_MAX_BASE_NAME] or "document.pdf"` -> `[:_MAX_BASE_NAME]` | 1 | `test_a_hint_is_cut_and_a_base_name_never_blank` |
| M26 | a name never becomes a path (a member's file is named by key) | comparison_zip/policy.py | `chosen[f"{KEY_PDF}{entry.index:05d}"] = entry elif kind == "zip":` -> `chosen[f"{KEY_PDF}{entry.name.decode('latin-1').replace('/', '_')}"...` | 2 | `test_a_hint_never_carries_a_character_a_screen_or_a_log_would_act_on[U+0000]` |
| M27 | the portal policy is the default and carries no extra bound | bundle_archive.py | `PORTAL_POLICY: Final[ArchivePolicy] = ArchivePolicy(judge=_judge_en...` -> `PORTAL_POLICY: Final[ArchivePolicy] = ArchivePolicy(judge=_judge_en...` | 2 | `test_the_default_policy_is_the_portal_policy_and_it_is_nothing_but_the_portal_rules` |
| M27b | the portal's refusals are never renamed | bundle_archive.py | `PORTAL_POLICY: Final[ArchivePolicy] = ArchivePolicy(judge=_judge_en...` -> `PORTAL_POLICY: Final[ArchivePolicy] = ArchivePolicy(judge=_judge_en...` | 1 | `test_the_default_policy_is_the_portal_policy_and_it_is_nothing_but_the_portal_rules` |
| M28 | the production total is 2 GiB | comparison_zip/policy.py | `SET_TOTAL_BYTES: Final[int] = 2 * GiB` -> `SET_TOTAL_BYTES: Final[int] = 3 * GiB` | 3 | `test_members_declared_over_two_gib_together_are_refused_at_the_production_figure` |
| M28b | the production entry limit | comparison_zip/policy.py | `SET_MAX_ENTRIES: Final[int] = 1_000` -> `SET_MAX_ENTRIES: Final[int] = 10_000` | 3 | `test_an_end_record_that_claims_more_entries_than_the_limit_is_refused_before_the_direct...` |
| M28c | the production member bound is the envelope's 250 MiB | comparison_zip/policy.py | `SET_MEMBER_BYTES: Final[int] = MAX_BYTES` -> `SET_MEMBER_BYTES: Final[int] = 2 * MAX_BYTES` | 3 | `test_a_member_declared_over_the_production_member_bound_is_refused_without_unpacking_it` |
| M29 | the local header must name the member the directory names | bundle_archive.py | `if self._read(entry.header_offset + 30, name_length) != entry.name:` -> `if False:` | 1 | `test_two_entries_that_share_one_local_header_are_refused` |
| M30 | ZIP64 sizes are read | bundle_archive.py | `if usize == 0xFFFFFFFF: usize = take()` -> `if False: usize = take()` | 2 | `test_zip64_directory_entries_and_the_zip64_end_record_are_read[zip64-entries-and-end-re...` |
| M30b | ZIP64 compressed sizes are read | bundle_archive.py | `if csize == 0xFFFFFFFF: csize = take()` -> `if False: csize = take()` | 2 | `test_zip64_directory_entries_and_the_zip64_end_record_are_read[zip64-entries-and-end-re...` |
| M30c | the ZIP64 end record is consulted | bundle_archive.py | `if total == 0xFFFF or directory_size == 0xFFFFFFFF or directory_off...` -> `if False:` | 1 | `test_zip64_directory_entries_and_the_zip64_end_record_are_read[zip64-entries-and-end-re...` |
| M32 | the policy's judge is the one that judges | bundle_archive.py | `chosen = policy.judge(entries)` -> `chosen = _judge_entries(entries)` | 108 | `test_a_benign_unicode_path_is_shown_and_accepted` |
| M33 | the policy's renaming of refusals is applied | bundle_archive.py | `raise policy.translate(refused) from None` -> `raise refused from None` | 27 | `test_a_bomb_inside_a_nested_archive_is_refused_by_the_same_rule` |

M22 (the cleanup of a refused set) is the only one that turns tests into *errors*: the autouse fixture's teardown assertion
is what fails (13 failed, 8 errors). M11 alone is shown by one test: the raw header name and the shown name are each held
to the rule, so removing either is masked by the other for every name that is the same in both — which is why the mirror
image test exists (§11).

## 11. What the first mutation run found

The first complete run had **four guards no test turned red for** (and three expectations of the harness that named a test
wrongly); none was a missing check, every one a test that did not prove its guard:

1. the raw-name rule (`M11`): masked by the shown-name rule, because the tests used names that are the same in both —
   added a test whose header name is `../evil.pdf` and whose Unicode Path field is harmless;
2. the empty-archive check of the judge (`M18d`): **repeated by the reader's final check**, so not a guard — removed from
   `LevelJudge` (and its `files_required` parameter), one check remains (`M18e`);
3. the ZIP64 fields of the central directory (`M30`): `zipfile` writes ZIP64 only in a local header, so the "equals the
   standard library" tests never reached `_zip64_values` — added a test with the repository writer's central-directory
   ZIP64 entries and end record (`M30`, `M30b`, `M30c`);
4. the entry-limit test read the limit from the constant it guards (`M28b`): a constant raised by mistake moved the test
   with it — now written out as 1 000 and 1 001.

The wrong expectations (a test-name substring in `M16b`, `M16c`, `M27`) were corrected in the harness, not in the tests. After
the repairs the whole run was repeated from the first mutation (an anchor of `M17` named a parameter that item 2 had
removed; the anchors are now checked before a run).

## 12. Checks run (light acceptance, `AGENTS.md` §8 and `R-135`; every command with its result)

All from the lane's worktree root with `PYTHONPATH=$PWD/src AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent`, the shared
`.venv`, on the tree of the commit before this report.

| command | result |
| --- | --- |
| `.venv/bin/python -m pytest -q tests/unit/ingest/comparison_zip -p no:cacheprovider` | `183 passed` (also with the bare `.venv/bin/pytest`) |
| `… pytest -q tests/unit/ingest tests/unit/jobs/test_stale_temporaries.py` | `211 passed` |
| `… pytest -q tests/integration/ingest/test_bundle_archive.py` (and `test_bundle_envelope`, `test_uncuttable_image_block`, `test_block_ceilings`, `test_display_name_scrub`) | `269`, `99`, `60`, `11`, `12 passed` |
| `… pytest -q tests/contract --ignore=…test_cp00_candidate.py --ignore=…test_validate_bootstrap.py --ignore=…test_cp00_final_state.py` (the three files of `D-220`) | `1306 passed, 19283 subtests` after the task file was repaired (below); the architecture boundary test (`test_alr05_boundaries`) is among them |
| the differential (§8) | identical, 558 outcomes |
| the mutation run (§10) | 57 of 57 red, restored tree `183 passed` |
| `git diff --check` | exit 0 |
| `df -h /` before the runs | 2.6–3.3 GiB free; the lane writes at most a few MiB (lowered bounds); no container started |
| cost of the envelope: `python -I` script: five `vs1` PDFs zipped, `extract_pdf_set(...)` three times, best | 1.81 s with the envelope, 0.01 s with `envelope=None` (361 ms a PDF) |

**One red the contract battery found in this lane's own file**: `tests/contract/program/test_wave_governance.py` refused the
task file (`PREMISE_DECLARATION_REQUIRED`: the section needs a `- premise:` line before the `### P-01` block). Repaired in a
follow-up commit; the file passes (16 passed) and the battery was re-run after it. No `make gate` was run (`R-135`: the
complete gate moves to the end of the CMP code series; `AGENTS.md` §8 case 3 does not apply — no contract, migration,
lock, composition root, `Makefile` or `conftest.py` is touched).

## 13. Limits and risks

- **The security judge ADR-0025 decision 12 asks for has not been held.** This lane wrote the reader and the tests; an
  independent read-only judge should be dispatched by the integrator. Places worth its time: the shared `_unpack` loop under
  a set's larger counts; `LevelJudge` against `_judge_entries` (the two now differ in directories, `__MACOSX/` and roles);
  the Unicode Path display rule; the hint scrub; the budget arithmetic of the second level (`reader.py`); `translate`.
- **The thirteen reasons are not yet registered** in the contract notes (§7). Until they are, a client has no sentence for them.
- **The default envelope is the portal's** (element ceilings; §6 item 1), and **running it inline does not scale to `N`** (§6
  item 2). Both are the consumer's decisions; the parameter makes each one a line.
- **`__MACOSX/` is refused, not skipped**, as the portal refuses it: a ZIP made by Finder is refused with
  `comparison_zip_member_kind` and the user is not told which member. Skipping the tree is one condition in `policy.py` if
  the owner prefers it; it is not done because a skipped entry is a silent acceptance.
- **A refusal does not say which archive member is wrong** (names are never echoed); only a PDF member's envelope refusal
  carries the ordinal. A user who gets `member_kind` has to look through the archive.
- **The nested archive's bytes are counted twice** (as a container, then as what is inside it) and a nested archive is at
  most 250 MiB: a stage of eight 200 MiB project archives is refused. Raising either is a figure in `SetPolicy`.
- **A member's kind is its suffix.** A ZIP named `.pdf` is carried as a PDF and refused by the envelope (`pdf_magic_bytes`,
  tested); with `envelope=None` nothing judges it until the caller's check runs.
- **Not covered**: multi-disk and split archives and an end-record comment over 64 KiB (refused as unreadable); archive formats
  other than ZIP (refused as unreadable or `member_kind`); time — the archive part is I/O bound and bounded by the 2 GiB, it
  has no wall clock; free disk (the caller's); the `VALID_STAGES` check of the original (the batch's).
- The stale-temporaries sweep walks at most 10 000 entries of a directory (`_MAX_ENTRIES_WALKED`); a set holds at most 1 000.
- Commit trailers use the brief's literal line (`Co-Authored-By: Claude Sonnet 4.6 …`, wave brief §1 item 8); the session
  that wrote them is a different model version than that line names.

## 14. Instructions for the integrator

1. Merge `agent/cmp-ingest-zip-01` after `CMP-EXEC-IMAGES-01` and before `CMP-INGEST-01` (brief §3). It touches no wiring
   file (`bootstrap/adapters.py`, `ports.py`, `public.py` of comparison, the enumerators): there are no overlapping hunks.
2. Dispatch the security judge of decision 12 (§13) before `CMP-INGEST-01` builds on the reader, or accept the risk in a ruling.
3. Have the contract slot that next owns `contracts/domain/v1/error-codes.json` add the note of §7 (a prose note; no
   schema or version change is implied by it, but the shared-version rule is the integrator's).
4. Brief `CMP-INGEST-01` with §6: its comparison envelope as `envelope=`; the identity of a member is `(ordinal, sha256,
   size)`; the name only proposes; check the free disk first. Brief `CMP-INGEST-02` with item 2 of §6 (deferred checks,
   per-item work).
5. `docs/program/CURRENT_STATE.md`, `DEBT_REGISTER.md` and the rulings are not edited by this lane.

## 15. Forbidden hotspots

`git diff --name-only cc3dd36b..HEAD` lists only: `docs/program/tasks/CMP-INGEST-ZIP-01.md`,
`docs/program/CMP-INGEST-ZIP-01.md`, `src/auditmanager/ingest/bundle_archive.py`, the four modules and `__init__.py` of
`src/auditmanager/ingest/comparison_zip/`, and the five files of `tests/unit/ingest/comparison_zip/`. No file under
`contracts/`, `db/migrations/`, `infra/`, `web/`, `bootstrap/`, `tests/integration/`, `tests/support/`, no `conftest.py`,
no `pyproject.toml`, no lock file, no `envelope.py` and no other module of `ingest`.
