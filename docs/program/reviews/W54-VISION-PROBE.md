# W54-VISION-PROBE — can a vision model read the АР drawings? (report only)

**Date:** 2026-10-13.
**Recorded by:** the integrator, `pdf-analysis-29`.
**Authority:** `R-120`. The owner authorised this one probe through the Codex VS Code extension
on the owner's subscription, instead of the product's proxy path. The integrator's session did
not launch Codex; the owner ran the task.

**Data handling (F-7):** the inputs and the raw model output are real client data. They stay
under `.local/probes/w54/vision/` and are never committed. This report carries only metrics and
conclusions.

## Inputs

- Eight IMAGE blocks, stamps excluded, cut locally with pypdfium2 from the owner's portal export of
  the АР document (pages 14, 15, 16, 18, 23, 27, 29, 30). These are the largest image block on each
  of eight pages.
- Each crop's long side is ≥ 800 px and its area ≤ 4 MP, the `W55B-FREEZE-01` crop budget. Sizes
  run from 1286×961 to 3369×904.
- `manifest.json` records each crop's SHA-256. The model verified all eight before describing them.

## Method

One Codex task. For each crop the model recorded:

- the drawing kind and printed title;
- grid axes and elevation marks;
- up to 15 dimensions, each with what it measures;
- element, room and section marks;
- legend entries;
- verbatim notes;
- possible issues, with evidence and confidence;
- unreadable parts;
- the seconds spent.

The integrator then checked crop 1 against the image.

## Results

| Measure | Value |
| --- | --- |
| model (self-reported) | `GPT-6` via Codex, subscription billing |
| crops processed / hash-verified | 8 / 8 |
| wall time | 134 s in total, 14–27 s per crop |
| printed title found | 6 / 8; the two colour-marked electrical overlays carry no title on the crop and were left empty, not invented |
| per crop | axes and elevations on every plan; 4–15 dimensions with what each measures; 3–22 element, room and section marks; Russian notes verbatim |
| legend | cut off at the crop edge on the plans, and reported as unreadable rather than guessed |
| possible issues raised | 0 on every crop; the model invents no findings |
| spot check, crop 1 | the title, all ten axes, the listed dimensions and the marks are correct; one minor misreading (`М/Л-1` for `МЛ-1`); an intermediate axis label is flagged as uncertain |

## Price on the product path: estimated, not measured

Anthropic's documented image rule is that an image with a long edge above 1568 px is
downscaled, and costs about `width × height / 750` input tokens. On that rule the eight crops
come to about **14 100 input tokens, 1 760 per crop** (880 to 2 240). The cost of a crop is
then about 1.76 k input tokens at the configured model's input price, plus its output tokens.
The proxy's model (`PROXY_LLM_MODEL`) is still not stated, so no dollar figure is given here. The
first paid W56b probe on the proxy path measures it, within `R-29`'s ceiling.

## Conclusions for W56b

1. **Reading.** A current vision model reads these АР drawings reliably for structural
   extraction: titles, axes, elevations, dimensions and marks. Drawing analysis is realistic.
2. **Context.** A crop cut exactly at the portal block's bounds loses the legend and the
   neighbouring annotations. W56b's region evidence should carry the sheet's legend, or a margin
   around the block, together with the crop.
3. **Findings.** The model raises no findings by itself. Consistency questions need explicit
   prompts and checklists, which matches W56a's profile v2 approach.
4. **Not covered:**
   - the product's own model and its price;
   - stamps;
   - raster or low-text pages;
   - rotated pages.
   These stay with the W56b plan and its probes.
