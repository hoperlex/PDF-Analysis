"""AR material shared by the АР v3 profile and the recognised-text readers.

``PROD-10`` moved it here from ``ar_v2`` so that neither ``ar_v3`` nor
``analysis.recognised`` imports the recorded v2 package, which ``PROD-11`` removes.
Nothing in this package imports ``ar_v2`` or ``ar_v3``; ``ar_v2`` may import it.
"""
