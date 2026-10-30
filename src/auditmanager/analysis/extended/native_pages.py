"""Real source-bound native PDF page crops for the fresh v2 review authority."""
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


def prepare_native_page_sources(*, version_uid, source_ref, blob_store, max_pages=16, checkpoint=None):
    """Publish at most16 genuine whole-page PNGs; never mint portal block identities."""
    if type(max_pages) is not int or not 1 <= max_pages <= 16:
        raise ValueError("native_page_limit_invalid")
    bid = parse_blob_id(source_ref.blob_id)
    recorded = blob_store.inspect(bid)
    if recorded.sha256 != source_ref.sha256 or recorded.size != source_ref.size_bytes:
        raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, role="source.document")
    sources, artifacts, skipped = [], [], []
    published_by_sha = {}
    with source_file(blob_store, bid, stage_id="text_analysis") as path:
        with PdfiumDocument(path, stage_id="text_analysis") as document:
            total = document.page_count
            for page in range(1, min(total, max_pages)+1):
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
            skipped.extend({"page_number":page,"reason":"outside_approved_window"}
                for page in range(max_pages+1,total+1))
    warnings = ["native_pdf_page_render_no_ocr"]
    if skipped:
        warnings.append("remaining_blocks_not_reviewed")
    return {"sources":sources,"artifacts":tuple(artifacts),"warnings":warnings,
        "coverage":{"blocks_total":total,"blocks_selected":len(sources),"blocks_processed":0,
            "blocks_remaining":total,"skipped":skipped},
        "source_sha256":digest({"version_uid":version_uid,"source_sha256":source_ref.sha256,
            "sources":sources,"max_pages":max_pages,"renderer":renderer_name()})}
