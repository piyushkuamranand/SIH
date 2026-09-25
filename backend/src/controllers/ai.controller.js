/**
 * controllers/ai.controller.js — NETRA-DR AI Inference Controller
 *
 * Implements the AI inference orchestration endpoint (Module 6):
 *   - POST /api/cases/:id/ai (technician, admin)
 *
 * Responsibilities:
 *   - Authentication and authorization verification (technician, admin)
 *   - Case validation and verification that a fundus image has been uploaded
 *   - Security: prevents client-specified paths, URLs, models, or fabricated predictions
 *   - Resolves stored image strictly through ImageStorageService
 *   - Invokes AIService to send image to Python/Flask AI service
 *   - Handles AI service unavailability (503), timeout (504), malformed output (502)
 *   - Provides end-to-end request tracing via unique inferenceRequestId
 *   - Does NOT persist AI results to the database yet (deferred to Module 7)
 */

'use strict';

const crypto = require('crypto');
const CaseModel = require('../models/case.model');
const ImageStorageService = require('../services/image-storage.service');
const AIService = require('../services/ai.service');
const AIResultService = require('../services/ai-result.service');
const { isValidCaseId } = require('../utils/validation');
const logger = require('../utils/logger');

/**
 * Run AI inference on a screening case and persist the result.
 * POST /api/cases/:id/ai
 *
 * Allowed roles: technician, admin
 */
const runCaseInference = async (req, res, next) => {
  try {
    const { id } = req.params;

    // 1. Validate case ID parameter format
    if (!isValidCaseId(id)) {
      return res.status(400).json({
        status:  'error',
        success: false,
        code:    400,
        message: 'Invalid case ID parameter',
        error: {
          code:    'ERR_INVALID_CASE_ID',
          message: 'Invalid case ID parameter',
        },
      });
    }

    // 2. Verify case exists
    const caseRecord = await CaseModel.findById(id);
    if (!caseRecord) {
      return res.status(404).json({
        status:  'error',
        success: false,
        code:    404,
        message: `Screening case not found with ID: ${id}`,
        error: {
          code:    'ERR_CASE_NOT_FOUND',
          message: `Screening case not found with ID: ${id}`,
        },
      });
    }

    // 3. Confirm case has an uploaded fundus image
    if (!caseRecord.image || !caseRecord.image.imageId) {
      return res.status(400).json({
        status:  'error',
        success: false,
        code:    400,
        message: `Screening case ${id} has no uploaded fundus image. An image must be uploaded before running AI inference.`,
        error: {
          code:    'ERR_NO_IMAGE_UPLOADED',
          message: `Screening case ${id} has no uploaded fundus image. An image must be uploaded before running AI inference.`,
        },
      });
    }

    // 4. Verify that stored image is accessible on disk via ImageStorageService
    const imageExists = await ImageStorageService.imageExists(caseRecord.id, caseRecord.image.imageId);
    if (!imageExists) {
      return res.status(404).json({
        status:  'error',
        success: false,
        code:    404,
        message: `Stored fundus image not found on disk for screening case ${id}`,
        error: {
          code:    'ERR_STORED_IMAGE_NOT_FOUND',
          message: `Stored fundus image not found on disk for screening case ${id}`,
        },
      });
    }

    // 5. Generate request trace ID for correlation across frontend, Node.js, and Flask
    const inferenceRequestId = `inf_${crypto.randomUUID()}`;

    logger.info(`[Module 6/7] Initiating AI inference for case: ${caseRecord.id}, image: ${caseRecord.image.imageId} by user: ${req.user ? req.user.id : 'unknown'} (req: ${inferenceRequestId})`);

    // 6. Invoke AI pipeline orchestration layer (Module 6)
    // Strictly server-controlled; any client-provided filesystem path or URL is completely ignored
    const aiInference = await AIService.runInference({
      caseId:             caseRecord.id,
      imageId:            caseRecord.image.imageId,
      inferenceRequestId,
    });

    // 7. Persist AI result (Module 7)
    // Strictly server-controlled: generates resultId ('res_<uuid>'), associates with case, transitions case status to 'completed'
    const persistedResult = await AIResultService.saveResult({
      caseId:             caseRecord.id,
      inferenceRequestId: aiInference.inferenceRequestId,
      inference:          aiInference.inference,
    });

    // Retrieve updated case record reflecting 'completed' status
    const updatedCase = await CaseModel.findById(caseRecord.id);

    // 8. Return structured AI response envelope
    return res.status(200).json({
      status:             'success',
      success:            true,
      message:            'AI inference completed successfully',
      inferenceRequestId: persistedResult.inferenceRequestId,
      resultId:           persistedResult.resultId,
      caseId:             caseRecord.id,
      case: {
        id:        updatedCase ? updatedCase.id : caseRecord.id,
        status:    updatedCase ? updatedCase.status : CaseModel.CASE_STATUS.COMPLETED,
        patientId: updatedCase ? updatedCase.patientId : caseRecord.patientId,
      },
      inference:          persistedResult.inference,
      result:             persistedResult,
      data: {
        inferenceRequestId: persistedResult.inferenceRequestId,
        resultId:           persistedResult.resultId,
        caseId:             caseRecord.id,
        inference:          persistedResult.inference,
        result:             persistedResult,
      },
    });
  } catch (err) {
    logger.error(`[Module 6/7] AI inference failed for case ${req.params.id}: ${err.message}`, {
      code: err.code,
      statusCode: err.statusCode,
    });

    // Handle service timeout (504)
    if (err.name === 'AIServiceTimeoutError' || err.code === 'AI_SERVICE_TIMEOUT') {
      return res.status(504).json({
        status:  'error',
        success: false,
        code:    504,
        message: err.message,
        error: {
          code:    'AI_SERVICE_TIMEOUT',
          message: err.message,
        },
      });
    }

    // Handle service unavailable (503)
    if (err.name === 'AIServiceUnavailableError' || err.code === 'AI_SERVICE_UNAVAILABLE') {
      return res.status(503).json({
        status:  'error',
        success: false,
        code:    503,
        message: 'AI inference service is currently unavailable',
        error: {
          code:    'AI_SERVICE_UNAVAILABLE',
          message: 'AI inference service is currently unavailable',
        },
      });
    }

    // Handle malformed response from AI service (502)
    if (err.name === 'AIServiceMalformedResponseError' || err.code === 'AI_SERVICE_MALFORMED_RESPONSE') {
      return res.status(502).json({
        status:  'error',
        success: false,
        code:    502,
        message: 'AI inference service returned a malformed response',
        error: {
          code:    'AI_SERVICE_MALFORMED_RESPONSE',
          message: 'AI inference service returned a malformed response',
        },
      });
    }

    // Handle known HTTP error status from AI service
    if (err.statusCode && err.statusCode >= 400 && err.statusCode < 600) {
      return res.status(err.statusCode).json({
        status:  'error',
        success: false,
        code:    err.statusCode,
        message: err.message,
        error: {
          code:    err.code || 'AI_SERVICE_ERROR',
          message: err.message,
        },
      });
    }

    next(err);
  }
};

/**
 * Retrieve persisted AI inference result for a screening case.
 * GET /api/cases/:id/ai-result
 *
 * Allowed roles: technician, doctor, admin
 */
const getCaseAiResult = async (req, res, next) => {
  try {
    const { id } = req.params;

    // 1. Validate case ID parameter format
    if (!isValidCaseId(id)) {
      return res.status(400).json({
        status:  'error',
        success: false,
        code:    400,
        message: 'Invalid case ID parameter',
        error: {
          code:    'ERR_INVALID_CASE_ID',
          message: 'Invalid case ID parameter',
        },
      });
    }

    // 2. Verify case exists
    const caseRecord = await CaseModel.findById(id);
    if (!caseRecord) {
      return res.status(404).json({
        status:  'error',
        success: false,
        code:    404,
        message: `Screening case not found with ID: ${id}`,
        error: {
          code:    'ERR_CASE_NOT_FOUND',
          message: `Screening case not found with ID: ${id}`,
        },
      });
    }

    // 3. Retrieve persisted AI result via AIResultService
    const aiResult = await AIResultService.getResultByCaseId(caseRecord.id);
    if (!aiResult) {
      return res.status(404).json({
        status:  'error',
        success: false,
        code:    404,
        message: `No AI inference result found for screening case: ${id}`,
        error: {
          code:    'ERR_AI_RESULT_NOT_FOUND',
          message: `No AI inference result found for screening case: ${id}`,
        },
      });
    }

    // 4. Return safe result envelope (Section 17 contract)
    return res.status(200).json({
      status:   'success',
      success:  true,
      caseId:   caseRecord.id,
      result:   aiResult,
      data:     aiResult,
    });
  } catch (err) {
    logger.error(`[Module 7] Error retrieving AI result for case ${req.params.id}: ${err.message}`);
    next(err);
  }
};

module.exports = {
  runCaseInference,
  getCaseAiResult,
};
