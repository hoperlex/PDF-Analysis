"""Portal blocks and crops (`W55B-GEOMETRY-01`, plan section B3.7).

``page_geometry_extraction`` reads a portal bundle's stored ``_blocks.json`` through this
package, checks each page's box against the PDF, cuts a crop for every IMAGE block on a page
that passed, and publishes ``geometry.portal_blocks`` (``P02_SEAMS`` section 4.9), the crop
manifest ``geometry.page_crops`` under ``crop_policy: portal_image_blocks`` (section 4.5) and
the PNG blobs ``geometry.crop_image`` (section 4.10). Nothing here reaches analysis in W55b: no
model looks at a crop.

* :mod:`.maths` -- the page box, the page-box check and the crop's scale and clip: pure;
* :mod:`.portal` -- the block list normalised and ordered: pure;
* :mod:`.render` -- the only caller of PDFium, always under ``PDFIUM_LOCK``;
* :mod:`.crops` -- PNG encoding, the content-addressed blobs, the manifest records;
* :mod:`.source_file` -- the source PDF in a temporary file.
"""

from __future__ import annotations

from auditmanager.analysis.geometry.crops import (
    PNG_MEDIA_TYPE,
    PNG_SIGNATURE,
    CropPublisher,
    crop_record,
    encode_png,
)
from auditmanager.analysis.geometry.maths import (
    GEOMETRY_MISMATCH,
    GEOMETRY_OK,
    MAX_PIXELS,
    MIN_LONG_SIDE_PX,
    PAGE_BOX_TOLERANCE,
    CropPlan,
    DegenerateCrop,
    base_scale,
    check_page,
    plan_crop,
)
from auditmanager.analysis.geometry.portal import (
    IMAGE,
    PortalBlockGeometry,
    PortalLayout,
    image_blocks_to_crop,
    portal_blocks_body,
    read_layout,
)
from auditmanager.analysis.geometry.render import (
    PageGeometry,
    PdfiumDocument,
    pdfium_lock,
    renderer_name,
)
from auditmanager.analysis.geometry.source_file import source_file

__all__ = [
    "GEOMETRY_MISMATCH",
    "GEOMETRY_OK",
    "IMAGE",
    "MAX_PIXELS",
    "MIN_LONG_SIDE_PX",
    "PAGE_BOX_TOLERANCE",
    "PNG_MEDIA_TYPE",
    "PNG_SIGNATURE",
    "CropPlan",
    "CropPublisher",
    "DegenerateCrop",
    "PageGeometry",
    "PdfiumDocument",
    "PortalBlockGeometry",
    "PortalLayout",
    "base_scale",
    "check_page",
    "crop_record",
    "encode_png",
    "image_blocks_to_crop",
    "pdfium_lock",
    "plan_crop",
    "portal_blocks_body",
    "read_layout",
    "renderer_name",
    "source_file",
]
