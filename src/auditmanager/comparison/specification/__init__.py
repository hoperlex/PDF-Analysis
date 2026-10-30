"""Specifications of a version comparison: positions by GOST 21.110 (part A) and the whole-specification comparison (part B).

`CMP-VC-SPEC-01`. This package is split in two kinds of module.

**Pure modules** -- :mod:`.table` (the page parser and the stream of positions across pages) and :mod:`.diff` (the
order-independent comparison of two streams) -- import the standard library only and nothing of the product. The engine's
child program loads them by path under the name ``_amc_spec`` (it imports nothing from the product, ADR-0025 decision 8), so
this ``__init__`` must stay free of imports: loading the package must never pull a database, a model or a blob store in.

The other modules (the reader of a version's positions, the views of the contract, the part-B prompt, checks and repository)
may import the product; the child never loads them.
"""
