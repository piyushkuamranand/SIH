/**
 * services/screening.service.js — NETRA-DR Screening Service (Placeholder)
 *
 * Will orchestrate the full pipeline by calling the Flask AI service.
 * Not implemented yet — stub only.
 *
 * Planned responsibilities:
 *   - Accept uploaded image path
 *   - Call Flask POST /api/pipeline
 *   - Persist result to database
 *   - Return structured result to controller
 */

'use strict';

const runFullPipeline = async (_imagePath) => {
  throw new Error('Screening service not implemented yet.');
};

module.exports = { runFullPipeline };
