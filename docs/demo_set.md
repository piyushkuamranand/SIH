## NETRA-DR Demo Set — Image Selection Documentation
## TASK-018 | End-to-end demo wiring with the full demo set

This document describes every image in `data/demo/` and the reasoning behind
each selection, so a presenter knows exactly what to expect from each one.

---

### Selection criteria (per HANDOFF.md Data Flow section)

The demo set must include:
- One Good-quality image
- One Borderline or Reject-quality image
- Coverage across different DR severity grades where available
- At least one visually "hard" case to motivate the heatmap explainability

Dataset source constraint: training/validation/test data must NEVER be copied
into `data/demo/`. Only individual images hand-selected for demonstration
purposes are permitted here.

---

### Current demo set

#### 1. `good_sample.jpg`

| Field          | Value                                               |
|----------------|-----------------------------------------------------|
| File           | data/demo/good_sample.jpg                           |
| Size           | 664 KB                                              |
| Source         | Public-domain fundus image (not from training set)  |
| Quality class  | Expected: Good                                      |
| DR grade       | Expected: Grade 0 or Grade 1 (mild / no DR)         |
| Resolution     | 1024 x 1024 px (preprocessed to 512 x 512 for model)|

**Why selected:**
Demonstrates the "all-clear" path of the pipeline end-to-end. Shows the
quality gate passing, all Phase 2 structure overlays rendering, Phase 3
returning a NO REFER decision (assuming Grade 0-1), and the Phase 4 model
attention heatmap producing a sensible, low-activation map. Gives the
presenter a clean baseline narrative before showing a pathological case.

**What to narrate:**
> "This is a well-captured fundus image. The quality gate passes it
> immediately. Phase 2 identifies the major vessel arcades. The grading
> model gives us Grade 0 — no diabetic retinopathy — with high confidence.
> The model attention heatmap highlights the optic disc region, which is
> where the network learned to anchor its grade-0 representation."

---

#### 2. `reject_sample.jpg`

| Field          | Value                                                       |
|----------------|-------------------------------------------------------------|
| File           | data/demo/reject_sample.jpg                                 |
| Size           | ~19 KB (compressed after synthetic degradation)             |
| Source         | Synthetically degraded version of good_sample.jpg           |
| Degradation    | Underexposed (x0.08 brightness), heavy Gaussian blur (s=20),|
|                | recompressed at JPEG quality 40                             |
| Quality class  | Expected: Reject                                            |
| DR grade       | N/A — pipeline stops at Phase 1                             |

**Why selected:**
Demonstrates the Reject gate and the clinical safety principle that the
system never grades an ungradable image. Shows `stopped_at_phase1=True`
rendering in the website and the "image rejected, please recapture" message.

**IMPORTANT NOTE:** This image is synthetically degraded for demo purposes.
It should be replaced with a real DDR ungradable image before the final
presentation if one becomes available from the dataset, so the rejection
narrative is grounded in a genuinely poor-quality clinical capture rather
than an artificial one. Replace the file at `data/demo/reject_sample.jpg`
and re-run the pipeline to verify.

**What to narrate:**
> "This is a severely out-of-focus, underexposed fundus image. Our quality
> gate catches it immediately and stops the pipeline — we display a clear
> message asking the technician to recapture the image. This is by design:
> it is safer to ask for a retake than to grade an ungradable image."

---

### Expected result per image (for presenter reference)

| Image              | Quality | Stopped? | Grade   | Decision  | Heatmap  |
|--------------------|---------|----------|---------|-----------|----------|
| good_sample.jpg    | Good    | No       | 0-1*    | NO REFER* | Present* |
| reject_sample.jpg  | Reject  | YES      | N/A     | N/A       | N/A      |

*Exact values depend on the grading model ONNX artifact being present.
Until the MATLAB team delivers the ONNX exports, all ML phases show
"unavailable" — the structural plumbing is verified but live inference
is blocked. The presenter should acknowledge this and show the system's
honest error handling as a feature, not a bug.

---

### To expand the demo set (recommended before final presentation)

Add 3-5 more images covering:
1. A Grade 2-3 (Moderate/Severe NPDR) case — to demonstrate the REFER path
2. A Borderline-quality image — to demonstrate the stricter referral threshold
3. A Grade 4 (PDR) case with visible neovascularization — heatmap will show
   high peripheral activation
4. A "hard" case where grade-alone and fused decision disagree — shows the
   value of decision fusion

Place each image in `data/demo/`, add a row to this table, and update the
narration notes above. Never include sealed test-set images.
