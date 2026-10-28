"""Plain-PDF admission for comparison (`CMP-INGEST-01`, ADR-0025 decisions 9, 10, 11 and 16).

A plain PDF -- no portal bundle -- is admitted for «Сравнение версий» as a ``comparison_pdf`` version: declared
before its first byte, sent in 16 MiB parts, verified whole against its declared SHA-256 and size, admitted under
the comparison envelope (:mod:`.envelope`), read for its title block in a ceilinged child (:mod:`.stamp_reader`),
grouped and ordered as a *proposal* (:mod:`.proposal`) and confirmed by an expert (:mod:`.service`). The order in
which a document's versions are compared is its own append-only history (:mod:`.orders`).

The package is reached from outside through :mod:`auditmanager.ingest.comparison_pdf.public` only. Its modules:

================== ====================================================================================
``limits``         the limits of decision 9 as typed refusals before the first part
``names``          what a file name hints at (a hint, never an identity)
``envelope``       the comparison envelope policy (the portal envelope is unchanged)
``child``          starting a ceilinged child over a descriptor
``stamp_reader``   the PDF half of the stamp reader: a program, not a function
``stamp``          the title block's text into facts (designation, «Изм.», date, stage, section)
``reading``        the envelope and the stamps of one PDF
``proposal``       grouping, order, labels and warnings
``repository``     the statements on the five tables of migration ``0038``
``service``        declare, part, complete, proposal, confirm
``orders``         the append-only order revisions
================== ====================================================================================
"""
