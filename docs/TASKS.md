# NETRA-DR TASK TRACKER

Read `HANDOFF.md` and `IMPLEMENTATION_SCHEMA.md` before touching this file. This tracker only records state — it does not contain task detail.

## CURRENT TASK

TASK-002 | Define and implement the model contract

## NEXT TASK

TASK-003 | Preprocessing function (no model)

## COMPLETED TASKS

- [x] TASK-001 — Create repository structure (done 2026-09-25)

- [ ] TASK-002 — Define and implement the model contract
- [ ] TASK-003 — Preprocessing function (no model)
- [ ] TASK-004 — Integrate the IQA (quality) model
- [ ] TASK-005 — PHASE 1 CHECKPOINT
- [ ] TASK-006 — Integrate vessel segmentation model
- [ ] TASK-007 — Integrate lesion segmentation models (HE/EX/SE)
- [ ] TASK-008 — Integrate MA (microaneurysm) detector
- [ ] TASK-009 — PHASE 2 CHECKPOINT
- [ ] TASK-010 — Integrate DR grading model
- [ ] TASK-011 — Add calibration (temperature scaling)
- [ ] TASK-012 — Decision fusion (referral decision)
- [ ] TASK-013 — PHASE 3 CHECKPOINT
- [ ] TASK-014 — Grad-CAM explainability
- [ ] TASK-015 — Final report assembly
- [ ] TASK-016 — PHASE 4 CHECKPOINT
- [ ] TASK-017 — Single-page website skeleton
- [ ] TASK-018 — End-to-end demo wiring with the full demo set
- [ ] TASK-019 — One-command launch hardening
- [ ] TASK-020 — Final demo hardening / dry run checkpoint
- [ ] TASK-021 — Simulink workflow simulation (separate track, no ordering dependency)

## BLOCKED TASKS

None

## NOTES & DECISIONS LOG

- Control files (HANDOFF.md, IMPLEMENTATION_SCHEMA.md, TASKS.md) generated from the SIH26038 PRD, the NETRA-DR Final Model Stack, and the NETRA-DR Master Build Prompt. No architecture component was dropped; Stage 10 (ensemble) and Stage 6 (NV) are marked OPTIONAL per the source documents' own framing, and Simulink (Stage 12) is kept as an independent, non-blocking track — see "KNOWN CONFLICTS / DECISIONS RECORDED" in HANDOFF.md for the full reasoning.
- TASK-001: Initialized Git repository and created complete repository skeleton with directory structure and placeholder .gitkeep / __init__.py files.

## LAST VALIDATED RESULT

TASK-001 validated: Complete directory tree verified with all placeholder files, empty requirements.txt, and single-paragraph README.md pointing to docs/HANDOFF.md.

---

### Update procedure (for whichever Claude context completes a task)

1. Move the completed task from the checklist above into a new dated line under a "Completed" sub-list, e.g. `- [x] TASK-001 — Create repository structure (done <date>)`.
2. Update **CURRENT TASK** to the task that was previously **NEXT TASK**.
3. Update **NEXT TASK** to the task after that, per the Phase-to-Task Map in `IMPLEMENTATION_SCHEMA.md`.
4. Add one line to **NOTES & DECISIONS LOG** if any decision was made (e.g. "used EfficientNet-B0 fallback instead of ResNet-50 because...").
5. Update **LAST VALIDATED RESULT** with a one-line summary of what the task's Validation step confirmed.
6. Stop. Do not start the next task in the same session.
