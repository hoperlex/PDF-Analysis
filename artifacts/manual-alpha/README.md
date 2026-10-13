# Synthetic file pack for open-alpha acceptance

`alpha-test-files.tar.gz` is a portable convenience bundle for
`docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md`. It contains synthetic files only and no customer,
production or personal data. Since `W55B-INGEST-01` an upload is a **portal bundle** (a ZIP), so the
pack carries bundles:

- `fixtures/synthetic/ar/bundles/ar_baseline.zip` — the valid bundle (eight pages, portal blocks);
- `fixtures/synthetic/ar/bundles/encrypted.zip` — a bundle whose PDF is password-protected;
- `fixtures/synthetic/ar/bundles/image_only.zip` — a bundle whose two pages have neither a text layer nor a block;
- `fixtures/synthetic/ar/ar_baseline.pdf` — a bare PDF, which the application no longer accepts;
- `fixtures/synthetic/ar/negative/not_a_pdf.txt` — a text file;
- `generated/bundle_501_pages.zip` — a bundle around a 501-page PDF, one page past the limit. It is
  **generated** by `tools/fixtures/build_journey_inputs.py` when the pack is built, so its bytes depend on the
  compressor that built it and its digest is not pinned.

The file over the 250 MiB limit is not in the pack (it would be 251 MiB of nothing). Make a sparse stand-in
with `truncate -s 251M oversize_bundle.zip`: it costs a few kilobytes of disk, and the browser refuses it before
any byte is sent. From a checkout, `python3 tools/fixtures/build_journey_inputs.py <empty-dir>` writes both
generated inputs.

The files under `fixtures/synthetic/ar/` are canonical. Verify the five of them from the repository root:

```bash
sha256sum -c artifacts/manual-alpha/SHA256SUMS
```

Bundle SHA-256:
`89809d4e64a6faf6d4e672da986bd86b2ac35be7052f65bb32bcb977360a2910`.

The archive deliberately keeps the canonical repository-relative paths. Extract it into an empty
directory; do not unpack it over a working tree.
