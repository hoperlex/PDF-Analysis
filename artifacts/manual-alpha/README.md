# Synthetic PDF pack for open-alpha acceptance

`alpha-test-pdfs.tar.gz` is a portable convenience bundle for
`docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md`. It contains five synthetic PDFs and no customer,
production or personal data:

- `fixtures/synthetic/ar/ar_baseline.pdf` — positive 8-page AR fixture;
- `fixtures/synthetic/ar/negative/encrypted.pdf`;
- `fixtures/synthetic/ar/negative/image_only.pdf`;
- `fixtures/synthetic/ar/negative/too_many_pages.pdf`;
- `fixtures/synthetic/ar/negative/oversize.pdf`.

The files under `fixtures/synthetic/ar/` are canonical. Verify them from the repository root:

```bash
sha256sum -c artifacts/manual-alpha/SHA256SUMS
```

Bundle SHA-256:
`a74038a5feac13116eba152a5238c061fa90b775743927985d71200edbfedb32`.

The archive deliberately keeps the canonical repository-relative paths. Extract it into an empty
directory; do not unpack it over a working tree. `oversize.pdf` expands to 26 MiB by design.
