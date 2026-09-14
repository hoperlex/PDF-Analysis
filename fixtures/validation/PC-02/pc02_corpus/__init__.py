"""Deterministic builder for the PC-02 field-validation corpus (task P4-QA-01).

PC-01 proved the machinery works on **one** document. PC-02 asks the question P04 exists
to answer - whether the findings are *professionally useful* - and that question is only
answerable against a corpus wide enough to spread a rate over and honest enough that the
rate measures the model rather than the ground truth.

Nothing here adds a dependency. `docs/program/P02_LOCK.json` pins `pdfplumber` and
`pypdf`, and the root lock is a single-writer hotspot this session does not own, so the
PDF writer, the TrueType subsetter and the reference extractor are reused read-only from
`tools/fixtures/ar_corpus/`, which session A4 wrote from the file-format specifications
for exactly this reason. This package adds layout, content and negatives for PC-02 and
reuses everything else.

Everything here is invented. Owner decision OD-17 rules the corpus synthetic-only: no
customer, production or real project bytes, and no real organisation, address, person or
project is named.
"""

__all__ = ["content", "layout", "negatives"]
