"""Deterministic builder for the synthetic comparison corpus (CMP-FIXTURES-01).

Three things live here, all pure standard library on top of `tools/fixtures/ar_corpus`:

*   VS-1, a set of five versions of one drawing set (`vs1.py`), each version a PDF whose
    sheets carry a title block;
*   SP-1, a stage pair: one П document and an assembly of three Р documents (`sp1.py`);
*   a "realistic A1" sheet generator (`realistic_a1.py`) used for measurements.

Each of the first two comes with an answer key: the facts a correct comparison must find,
authored next to the content that creates them. The corpus states expected results; it does
not compute them with a comparison engine. Nothing here reads customer, production or real
project bytes: every name, mark and number is invented (owner decision OD-17).
"""

__all__ = ["outlines", "realistic_a1", "scene", "sp1", "vs1"]
