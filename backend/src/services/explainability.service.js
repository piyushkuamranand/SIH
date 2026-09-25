/**
 * services/explainability.service.js — NETRA-DR Grad-CAM Service (Placeholder)
 *
 * Will call Flask Phase 4 Grad-CAM endpoint.
 * Mandatory label convention: output must be labeled "model attention" —
 * NEVER "clinical proof" or "clinical evidence" (per HANDOFF.md).
 * Not implemented yet — stub only.
 */

'use strict';

const runGradCAM = async (_preprocessedImagePath, _severityClass) => {
  throw new Error('Grad-CAM explainability service not implemented yet.');
};

module.exports = { runGradCAM };
