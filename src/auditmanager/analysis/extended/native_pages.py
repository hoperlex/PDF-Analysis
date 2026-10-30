"""Real source-bound native PDF page crops for fresh v2/v3 review authority."""
from __future__ import annotations
from auditmanager.analysis.engine.result import ArtifactRef
from auditmanager.analysis.extended.core import digest
from auditmanager.analysis.geometry.crops import encode_png
from auditmanager.analysis.geometry.maths import plan_crop
from auditmanager.analysis.geometry.render import PdfiumDocument, renderer_name
from auditmanager.analysis.geometry.source_file import source_file
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import parse_blob_id, parse_blob_role
import hashlib


def prepare_native_page_sources(*, version_uid, source_ref, blob_store, max_pages=16, checkpoint=None,
                                window_offset=None, max_sources=None):
    """Publish genuine page PNGs, rendering at most16 pages in a v3 window."""
    if type(max_pages) is not int or not 1 <= max_pages <= 500:
        raise ValueError("native_page_limit_invalid")
    windowed=window_offset is not None
    if windowed and (max_pages > 16 or type(window_offset) is not int or not 0 <= window_offset < 1000
            or type(max_sources) is not int or not 1 <= max_sources <= 1000 or window_offset >= max_sources):
        raise ValueError("native_page_window_invalid")
    bid = parse_blob_id(source_ref.blob_id)
    recorded = blob_store.inspect(bid)
    if recorded.sha256 != source_ref.sha256 or recorded.size != source_ref.size_bytes:
        raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, role="source.document")
    sources, artifacts, skipped = [], [], []
    published_by_sha = {}
    with source_file(blob_store, bid, stage_id="text_analysis") as path:
        with PdfiumDocument(path, stage_id="text_analysis") as document:
            total = document.page_count
            first=1 if not windowed else window_offset+1
            last=min(total,max_pages) if not windowed else min(total,window_offset+max_pages,max_sources)
            for page in range(first,last+1):
                if checkpoint is not None:
                    checkpoint("extended_native_page_render")
                geometry = document.page_geometry(page)
                plan = plan_crop((0.,0.,1.,1.), geometry.width_pt, geometry.height_pt,
                    1600. / max(geometry.width_pt, geometry.height_pt))
                png = encode_png(document.render(page, plan))
                if len(png) > 4 * 1024 * 1024:
                    skipped.append({"page_number":page,"reason":"native_png_bytes_cap"})
                    continue
                sha = hashlib.sha256(png).hexdigest()
                ref = published_by_sha.get(sha)
                if ref is None:
                    published = blob_store.put_blob(png, declared_sha256=sha, declared_size=len(png),
                        role=parse_blob_role("analysis_extended_crop"), media_type="image/png")
                    ref = ArtifactRef("analysis.extended_crop", str(published.blob_id), published.sha256,
                        published.size, published.media_type)
                    artifacts.append(ref)
                    published_by_sha[sha] = ref
                identity = "native_"+digest({"version_uid":version_uid,"source_sha256":source_ref.sha256,
                    "page_number":page,"renderer":renderer_name(),"scale":plan.scale})[:32]
                sources.append({"source_id":identity,"kind":"image","source_type":"native_page",
                    "version_uid":version_uid,"page_number":page,"bbox_norm":[0.,0.,1.,1.],
                    "crop_sha256":sha,"blob_id":ref.blob_id,"size_bytes":len(png),"context":[],
                    "source_sha256":source_ref.sha256,"width_px":plan.width,"height_px":plan.height})
            if not windowed:
                skipped.extend({"page_number":page,"reason":"outside_approved_window"}
                    for page in range(max_pages+1,total+1))
    warnings = ["native_pdf_page_render_no_ocr"]
    if skipped:
        warnings.append("remaining_blocks_not_reviewed")
    return {"sources":sources,"artifacts":tuple(artifacts),"warnings":warnings,
        "coverage":{"blocks_total":total,"blocks_selected":len(sources),"blocks_processed":0,
            "blocks_remaining":total,"skipped":skipped},
        "source_sha256":digest({"version_uid":version_uid,"source_sha256":source_ref.sha256,
            "sources":sources,"max_pages":max_pages,"renderer":renderer_name()}),
        **({"source_window":{"offset":window_offset,"slots":max(0,last-first+1),
                "max_sources":max_sources,"source_total":total}} if windowed else {})}
