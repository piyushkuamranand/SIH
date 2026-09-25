/**
 * services/segmentation.service.js — NETRA-DR Segmentation Service (Placeholder)
 *
 * Will call Flask Phase 2 endpoints (vessel + lesion + MA detection).
 * Not implemented yet — stub only.
 */

'use strict';

const runVesselSegmentation  = async (_preprocessedImagePath) => {
  throw new Error('Vessel segmentation service not implemented yet.');
};

const runLesionSegmentation = async (_preprocessedImagePath) => {
  throw new Error('Lesion segmentation service not implemented yet.');
};

const runMADetection = async (_preprocessedImagePath) => {
  throw new Error('MA detection service not implemented yet.');
};

module.exports = { runVesselSegmentation, runLesionSegmentation, runMADetection };
