"""Bounded graphical plans; registration and crop rendering stay with their owner."""

from dataclasses import asdict, replace
from hashlib import sha256

from auditmanager.executors.public import CropImage, attach_images

from .classifier import CLASSIFICATION_SCHEMA, SYSTEM_PROMPT, evidence_source, parse_classification
from .loop import final_document, with_loop
from .model import AtomicEvidence, ClassifiedCard, EvidenceGroup, ReviewGroup, SynthesisGroup
from .requests import make_plan
from .source import SourceGroup
from .synthesis import build_synthesis_request
from .validation import StageAiValidationError, digest

VERSION = "stage-graphic-ai/1"
REGIONS_PER_REQUEST = 4
MAX_IMAGES = 8
MAX_IMAGE_BYTES = 2 * 1024 * 1024
PROMPT = """Это GRAPHIC evidence: анализируй только приложенные П/Р изображения с проверенной регистрацией.
Пары изображений подписаны evidence_id/region_key/side. Геометрические координаты не инженерные размеры.
Не придумывай числа, марки или назначение по пикселям; при нехватке данных выбирай REVIEW/uncertain/unknown.
Скан не TEXT evidence, не делай SAME и не доказывай появление/исчезновение объекта отсутствием графики.
Классификация предварительная: эксперт должен проверить изображение. Контекстные запросы ищут только исходный текст."""


def eligible_links(snapshot):
    paired = [row for row in snapshot["links"] if row["relation"] == "paired"]
    return tuple(row for row in paired if sum(other["left_profile_id"] == row["left_profile_id"] for other in paired) == 1
                 and sum(other["right_profile_id"] == row["right_profile_id"] for other in paired) == 1)


def group_id(evidence_id):
    return "graphic:" + digest(evidence_id)[:24]


def bundles(provider, *, run_id, snapshot, phase, model, classes, unchecked=()):
    if phase == "review":
        return []
    permitted = {(row["left_profile_id"], row["right_profile_id"]) for row in eligible_links(snapshot)}
    result = []
    for raw in provider.evidence(run_id):
        if raw["status"] != "reliable" or (raw["left_profile_id"], raw["right_profile_id"]) not in permitted:
            continue
        regions = sorted(raw["regions"], key=lambda row: row["region_key"])
        if not regions:
            continue
        if len(regions) > 2000 or len({row["region_key"] for row in regions}) != len(regions):
            raise StageAiValidationError("stage_ai_graphic_regions_invalid")
        gid = group_id(raw["evidence_id"])
        if gid in unchecked:
            continue
        evidence = AtomicEvidence(raw["evidence_id"], raw["content_key"], "CHANGED", (), (),
            "Графический участок исходного листа П.", "Графический участок исходного листа Р.",
            "Зарегистрированы графические различия; изображения требуют интерпретации.", "UNCLASSIFIED", "GRAPHIC")
        source = EvidenceGroup(gid, (evidence,))
        group = SourceGroup(ReviewGroup(gid, (), (), (raw["left_profile_id"],), (raw["right_profile_id"],)), source)
        full_sha = digest(raw)
        if phase == "synthesize":
            classified = classes.get(gid)
            if classified is None or classified["source_sha256"] != full_sha:
                raise StageAiValidationError("stage_ai_graphic_classification_missing")
            cards = tuple(ClassifiedCard(**(dict(card) | {"evidence_ids": tuple(card["evidence_ids"]),
                "policy_reasons": tuple(card.get("policy_reasons", ())) })) for card in classified["cards"])
            plans = (with_loop(build_synthesis_request(SynthesisGroup(gid, (evidence,), cards), model=model)),)
        else:
            plans = []
            for offset in range(0, len(regions), REGIONS_PER_REQUEST):
                selected = regions[offset:offset + REGIONS_PER_REQUEST]
                following = selected[-1]["region_key"] if offset + REGIONS_PER_REQUEST < len(regions) else None
                document = evidence_source(source) | {"graphic": {
                    "evidence_id": raw["evidence_id"], "content_key": raw["content_key"],
                    "left_profile_id": raw["left_profile_id"], "right_profile_id": raw["right_profile_id"],
                    "regions": selected, "page_no": len(plans) + 1, "next_region_key": following,
                    "after_region_key": None if offset == 0 else regions[offset - 1]["region_key"],
                    "total_regions": len(regions), "total_pages": (len(regions) + REGIONS_PER_REQUEST - 1) // REGIONS_PER_REQUEST,
                }}
                plans.append(with_loop(make_plan(phase="classify", group_id=gid, unit_key=f"{gid}:page:{len(plans) + 1}",
                    source=document, payload=document, schema=CLASSIFICATION_SCHEMA,
                    instructions=SYSTEM_PROMPT + "\n" + PROMPT, version=VERSION, model=model, output_tokens=12_000)))
            plans = tuple(plans)
        key = digest({"phase": phase, "source_sha256": full_sha, "plans": [plan.content_key for plan in plans]})
        result.append((group, plans, full_sha, key))
    return result


def attach(provider, *, run_id, plan, request):
    source = plan.payload.get("graphic")
    if source is None:
        return request, ()
    selected, following = provider.crop_plan(run_id, source["evidence_id"],
        after=source["after_region_key"], limit=REGIONS_PER_REQUEST)
    if ([row["region_key"] for row in selected] != [row["region_key"] for row in source["regions"]]
            or following != source["next_region_key"]):
        raise StageAiValidationError("stage_ai_graphic_regions_incomplete")
    crops, receipts = [], []
    for region in source["regions"]:
        for side in ("left", "right"):
            crop = provider.crop(run_id, source["evidence_id"], region["region_key"], side, long_side_px=1400)
            expected = tuple(float(value) for value in region[side + "_box"])
            if (crop.evidence_id != source["evidence_id"] or crop.region_key != region["region_key"] or crop.side != side
                    or crop.profile_id != source[side + "_profile_id"] or tuple(crop.box) != expected
                    or len(crop.data) > MAX_IMAGE_BYTES or sha256(crop.data).hexdigest() != crop.sha256):
                raise StageAiValidationError("stage_ai_graphic_crop_mismatch")
            label = "sgcrop:" + digest([source["evidence_id"], region["region_key"], side])[:48]
            crops.append(CropImage(crop_id=label, data=crop.data))
            receipts.append({"crop_id": label, "profile_id": crop.profile_id, "box": list(crop.box),
                             "sha256": crop.sha256, "bytes": len(crop.data)})
    if not 1 <= len(crops) <= MAX_IMAGES:
        raise StageAiValidationError("stage_ai_graphic_image_budget")
    return attach_images(request, crops), tuple(receipts)


def aggregate(plans, responses):
    cards = [parse_classification(plan, final_document(plan, responses[plan.content_key])[0]).cards[0] for plan in plans]
    first = cards[0]
    if any((card.class_name, card.category, card.system, card.title) !=
           (first.class_name, first.category, first.system, first.title) for card in cards[1:]):
        first = replace(first, class_name="REVIEW", category="uncertain", system="unknown",
                        title="Графические различия требуют проверки", model_class="REVIEW",
                        card_key=digest({"class": "REVIEW", "evidence_ids": first.evidence_ids}),
                        policy_reasons=("graphic_page_interpretations_differ",))
    return [asdict(first)]
