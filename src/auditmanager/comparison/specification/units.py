"""Owner-approved 1:1 linear-metre identity; original values are never changed."""
from __future__ import annotations
import unicodedata


def unit_identity(value):
    original=str(value or '')
    normalized=' '.join(unicodedata.normalize('NFKC',original).split()).casefold()
    token=normalized.replace('.','').replace(' ','')
    return 'м' if token in {'м','пм','погм','мп'} else original
