# CFB-INT-DEV-PUBLISH-36 — W57a set custody on dev

The completed W57a source `5ab5512eecbb90a6c89298bea4e9d93ede22c9e9`
is based on published dev34. It was applied to published dev35
`75c558871535f456674af6fb70e3c0459ff8e8dd` as `00bf1c82`; source and
integrated binary patch streams both hash to
`2f56aae5b494b1d1c80ce69630a915c9a7e0af472e28ea9423f64e1f0487bc59`.
Its four task-owned paths are unchanged.

The unserved reader checks a current Run/Attempt, verified set pin, confirmed
set and catalogue custody, available Blob metadata and exact set bytes under
a 10 MB ceiling. It independently hashes the full stream and rechecks Attempt
and SQL pin after reading. It does not call a model, publish a finding or
authorize a route. A later caller must bind its candidate to the recorded
model response and rerun the transaction publication gate.

Integrated W57a custody/citation, W56b TEXT and programme suites: **91
passed**. Python compilation, direct governance, frozen-hash, path,
whitespace, clean-tree and fresh remote fast-forward/readback checks are
recorded at publication. No service, provider or paid call was used.

No contract, migration, existing writer/reader/job/storage adapter, root
dependency/lock, composition root, API/UI, global style, production DB/S3,
`origin/main`, tag or deployment input changed. Real PostgreSQL/S3 readback,
registered v3 profile, served CITE integration, W54 qualified corpus and the
complete beta gate remain open.
