# W58-INT-STORAGE-BOUNDARY-DOC-01 — storage boundary descriptions

The storage package and private layout docstrings now name the recovery-only
resolver added by `W58-INT-STORAGE-KEY-RESOLVER-01`. They continue to require
opaque Blob IDs in product code and identify object keys as transport locators.

Changed files: `src/auditmanager/storage/__init__.py`,
`src/auditmanager/storage/_object_layout.py`, this report and its task file.
Only docstrings changed in the two Python modules; function bodies, imports,
exports and constants are untouched. Contracts, migrations, root files,
composition root, global styles, corpus, recovery scripts and Git refs are
unchanged.

Checks: direct task governance, exact-path/docstring-only diff and
`git diff --check` passed. Runtime tests and full gate were not run for this
prose-only correction. Real DB/S3 recovery remains unverified.

Integrate only these four paths. No tag or remote publication.
