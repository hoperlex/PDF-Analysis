# CFB-INT-DEV-PUBLISH-37 — W54 CPU-window preflight on dev

The completed W54 source `a0eff1a321878f4156636fa6640351c9e3c9539b`
is an exact child of published dev36
`cf9b64a0c99042cdfe207de776f0296d6857b930`. Its four task-owned paths
are integrated without editing their bytes. The source and integrated binary
patch streams both hash to
`0355182ded3faa993d63dbe07264ab37a39241696793389b6026d42b093798b8`.

The offline W54 preflight now exposes 1-minute load and refuses load at or
above 8 or invalid measurement. This threshold reflects the recorded
promotion window on this eight-CPU host; W54 §3.9 separately sets disk/RAM
floors and one heavy lane. Existing CLI choices and 0/2 exits remain.

The source's read-only repair-sample metadata preflight refused on this host:
disk 5,774,962,688 < 6,442,450,944 required bytes and available RAM
6,385,348,608 < 6,442,450,944, while load 2.084 was under 8. This is a
point-in-time reading, not a resource reservation or corpus verification.
The proxy credential remains absent; no paid sample, repaired snapshot,
embedding build, qualified bundle or DB/S3 publication exists.

Integrated W54 preflight and programme suites: **48 passed**. Direct
governance, compilation, frozen hashes, patch/path equality, whitespace, clean tree and remote
fast-forward/readback are recorded at publication. The source's mutation
probe made three new boundary tests fail when the load guard was disabled.
No Docker, DB/S3, provider or paid call was used in this integration.

No contract, migration, root dependency/lock, composition root, global style,
source corpus/sums/dump, production DB/S3, `origin/main`, tag or deployment
input changed. R-135 defers the complete W56–W63 beta gate.
