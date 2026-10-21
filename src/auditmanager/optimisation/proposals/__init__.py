"""«Оптимизация проекта» proposals: deterministic cheaper analogs with expert decisions.

`W60-OPT-PROPOSALS-01`. An expert starts an optimisation pass for the current AR version of
a document set; the pass pins the version, its newest published run, the project's current
price-list revision and the effective AR vendor-list revision, and persists immutable
proposals of one deterministic kind, ``cheaper_analog``. Experts append accept / reject /
revise decisions per proposal. Proposals are a separate entity beside findings, with their
own decisions, counts and CSV export (``ROADMAP-TO-BETA.md`` §10.1 A-2).

The surface is :mod:`auditmanager.optimisation.proposals.public`; the context's cross-context
surface (:mod:`auditmanager.optimisation.public`) re-exports it when the operations arrive.
"""
