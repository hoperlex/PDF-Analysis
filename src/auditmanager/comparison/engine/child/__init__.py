"""The modules that run inside the engine's child process (`CMP-ENGINE-01`).

The child is a program (:mod:`.program`) started with ``python -I -B``; it loads this directory as a package under a
private name and imports **nothing from the product**, so that a crash of PDFium here is the crash of this process
only and the interpreter pays for ``numpy`` and ``cv2`` and nothing else. The modules that need neither
(``settings``, ``status``, ``textdiff``, ``words``, ``annotations``, ``result``) are also imported by the worker's
side of the engine; this file imports nothing so that doing so costs nothing.
"""
