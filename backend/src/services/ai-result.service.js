/**
 * services/ai-result.service.js — NETRA-DR AI Results Persistence Service
 *
 * Implements AI Results Persistence & Management (Module 7):
 *   - Persists structured AI inference results associated with screening cases
 *   - Strictly validates upstream AI responses — never trusts client-supplied AI results
 *   - Ensures server-controlled resultId ('res_<uuid>'), preserving upstream inferenceRequestId ('inf_<uuid>')
 *   - Idempotent: duplicate calls with the same inferenceRequestId do not create duplicate records
 *   - Lifecycle ownership: transitions screening case status from 'image_uploaded' -> 'completed'
 *   - Security: prevents path leakage, secrets leakage, and client-side result/ID injection
 *   - Pluggable design ready for future persistent stores (MongoDB/Mongoose)
 */

'use strict';

const AIResultModel = require('../models/ai-result.model');
const CaseModel     = require('../models/case.model');
const {
  isValidCaseId,
  isValidResultId,
  isValidInferenceRequestId,
} = require('../utils/validation');
const logger        = require('../utils/logger');

/**
 * Sanitize AI inference payload to prevent internal path or credential leakage.
 * Preserves genuine Flask output semantics.
 *
 * @param {object} inference
 * @returns {object} Clean cloned inference object
 */
const sanitizeInference = (inference) => {
  if (!inference || typeof inference !== 'object' || Array.isArray(inference)) {
    throw new Error('Inference output must be a valid non-empty object');
  }

  const clone = JSON.parse(JSON.stringify(inference));

  // Recursively remove any keys that might contain filesystem paths or credentials
  const forbiddenPatterns = ['storagepath', 'filepath', 'absolutepath', 'token', 'secret', 'password'];

  const cleanNode = (obj) => {
    if (!obj || typeof obj !== 'object') return;
    for (const key of Object.keys(obj)) {
      const lowerKey = key.toLowerCase();
      if (forbiddenPatterns.some(p => lowerKey.includes(p))) {
        delete obj[key];
      } else if (typeof obj[key] === 'object' && obj[key] !== null) {
        cleanNode(obj[key]);
      }
    }
  };

  cleanNode(clone);
  return clone;
};

const AIResultService = {
  /**
   * Persist a successful AI inference result for a screening case.
   *
   * Flow:
   *   1. Validate caseId format and verify case existence in CaseModel
   *   2. Verify case has an uploaded fundus image
   *   3. Validate inferenceRequestId format ('inf_<uuid>')
   *   4. Check idempotency: if inferenceRequestId already persisted, return existing result
   *   5. Sanitize genuine inference output (preserves Flask semantics, removes internal paths)
   *   6. Persist via AIResultModel abstraction with status 'completed'
   *   7. Transition screening case lifecycle to 'completed'
   *   8. Return safe result representation
   *
   * @param {object} params
   * @param {string} params.caseId             - Unique screening case identifier
   * @param {string} params.inferenceRequestId - Upstream trace ID
   * @param {object} params.inference          - Genuine Flask AI output
   * @returns {Promise<object>} Persisted safe AI result
   */
  async saveResult({ caseId, inferenceRequestId, inference }) {
    // 1. Validate caseId format
    if (!isValidCaseId(caseId)) {
      const err = new Error(`Invalid case ID format: '${caseId}'`);
      err.statusCode = 400;
      err.code = 'ERR_INVALID_CASE_ID';
      throw err;
    }

    // Verify case exists in repository
    const caseRecord = await CaseModel.findById(caseId);
    if (!caseRecord) {
      const err = new Error(`Screening case not found with ID: ${caseId}`);
      err.statusCode = 404;
      err.code = 'ERR_CASE_NOT_FOUND';
      throw err;
    }

    // 2. Verify case has an uploaded fundus image
    if (!caseRecord.image || !caseRecord.image.imageId) {
      const err = new Error(`Screening case ${caseId} has no uploaded fundus image. An image must be uploaded before persisting an AI result.`);
      err.statusCode = 400;
      err.code = 'ERR_NO_IMAGE_UPLOADED';
      throw err;
    }

    // 3. Validate inferenceRequestId format
    if (!isValidInferenceRequestId(inferenceRequestId)) {
      const err = new Error(`Invalid inferenceRequestId format: '${inferenceRequestId}'. Must begin with 'inf_'`);
      err.statusCode = 400;
      err.code = 'ERR_INVALID_INFERENCE_REQUEST_ID';
      throw err;
    }

    // 4. Idempotency check: prevent duplicate results for the same inference request
    const existing = await AIResultModel.findByInferenceRequestId(inferenceRequestId);
    if (existing) {
      if (existing.caseId !== caseRecord.id) {
        const err = new Error(`Inference request ID ${inferenceRequestId} is already associated with a different case (${existing.caseId})`);
        err.statusCode = 409;
        err.code = 'ERR_INFERENCE_ID_CONFLICT';
        throw err;
      }
      logger.info(`[Module 7] Idempotent AI result return: request ${inferenceRequestId} already persisted for case ${caseId}`);
      return existing;
    }

    // 5. Sanitize genuine Flask inference output (do NOT fabricate any medical predictions or thresholds)
    const cleanInference = sanitizeInference(inference);

    // 6. Persist result record
    const persisted = await AIResultModel.create({
      caseId:             caseRecord.id,
      inferenceRequestId: inferenceRequestId.trim(),
      inference:          cleanInference,
      status:             AIResultModel.RESULT_STATUS.COMPLETED,
    });

    // 7. Transition screening case lifecycle to 'completed'
    try {
      await CaseModel.updateStatus(caseRecord.id, CaseModel.CASE_STATUS.COMPLETED);
    } catch (statusErr) {
      logger.warn(`[Module 7] Failed to update case status for ${caseRecord.id}: ${statusErr.message}`);
    }

    logger.info(`[Module 7] AI result persisted: ${persisted.resultId} for case: ${caseRecord.id} (req: ${inferenceRequestId})`);

    return persisted;
  },

  /**
   * Persist a failed AI inference record (failure auditing / traceability).
   * Safe: never stores null prediction as completed.
   *
   * @param {object} params
   * @param {string} params.caseId
   * @param {string} params.inferenceRequestId
   * @param {object} params.error
   * @returns {Promise<object>}
   */
  async saveFailedResult({ caseId, inferenceRequestId, error }) {
    if (!isValidCaseId(caseId)) {
      const err = new Error(`Invalid case ID format: '${caseId}'`);
      err.statusCode = 400;
      err.code = 'ERR_INVALID_CASE_ID';
      throw err;
    }

    if (!isValidInferenceRequestId(inferenceRequestId)) {
      const err = new Error(`Invalid inferenceRequestId format: '${inferenceRequestId}'. Must begin with 'inf_'`);
      err.statusCode = 400;
      err.code = 'ERR_INVALID_INFERENCE_REQUEST_ID';
      throw err;
    }

    const existing = await AIResultModel.findByInferenceRequestId(inferenceRequestId);
    if (existing) {
      return existing;
    }

    const safeError = {
      code:    error && error.code ? error.code : 'AI_SERVICE_ERROR',
      message: error && error.message ? error.message : 'AI inference execution failed',
    };

    const persisted = await AIResultModel.create({
      caseId:             caseId.trim(),
      inferenceRequestId: inferenceRequestId.trim(),
      status:             AIResultModel.RESULT_STATUS.FAILED,
      error:              safeError,
    });

    logger.warn(`[Module 7] AI failure persisted: ${persisted.resultId} for case: ${caseId} (req: ${inferenceRequestId})`);
    return persisted;
  },

  /**
   * Retrieve the latest AI result for a screening case.
   *
   * @param {string} caseId
   * @returns {Promise<object|null>} Safe AI result or null if not found
   */
  async getResultByCaseId(caseId) {
    if (!isValidCaseId(caseId)) {
      const err = new Error(`Invalid case ID format: '${caseId}'`);
      err.statusCode = 400;
      err.code = 'ERR_INVALID_CASE_ID';
      throw err;
    }

    // Verify case exists
    const caseRecord = await CaseModel.findById(caseId);
    if (!caseRecord) {
      const err = new Error(`Screening case not found with ID: ${caseId}`);
      err.statusCode = 404;
      err.code = 'ERR_CASE_NOT_FOUND';
      throw err;
    }

    return AIResultModel.findByCaseId(caseId);
  },

  /**
   * Retrieve an AI result by its unique resultId.
   *
   * @param {string} resultId
   * @returns {Promise<object|null>} Safe AI result or null if not found
   */
  async getResultById(resultId) {
    if (!isValidResultId(resultId)) {
      const err = new Error(`Invalid result ID format: '${resultId}'`);
      err.statusCode = 400;
      err.code = 'ERR_INVALID_RESULT_ID';
      throw err;
    }

    return AIResultModel.findById(resultId);
  },

  /**
   * Retrieve all historical AI results for a screening case.
   *
   * @param {string} caseId
   * @returns {Promise<Array<object>>}
   */
  async getAllResultsByCaseId(caseId) {
    if (!isValidCaseId(caseId)) {
      const err = new Error(`Invalid case ID format: '${caseId}'`);
      err.statusCode = 400;
      err.code = 'ERR_INVALID_CASE_ID';
      throw err;
    }

    return AIResultModel.findAllByCaseId(caseId);
  },

  /**
   * Clear all results (for test suite isolation).
   */
  async clear() {
    await AIResultModel.clear();
  },
};

module.exports = AIResultService;
