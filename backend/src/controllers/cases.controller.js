/**
 * controllers/cases.controller.js — NETRA-DR Cases Controller
 *
 * Implements screening case management endpoints (Module 3):
 *   - POST  /api/cases     : Create a new screening case (technician, admin)
 *   - GET   /api/cases     : List screening cases (technician, doctor, admin)
 *   - GET   /api/cases/:id : Get single screening case by ID (technician, doctor, admin)
 *   - PATCH /api/cases/:id : Update case metadata (technician, doctor, admin)
 *   - DELETE /api/cases/:id : Admin only stub (501)
 *
 * Architecture Notes:
 *   - Case represents the screening workflow lifecycle.
 *   - AI inference results, Grad-CAM artifacts, doctor reviews, and clinical
 *     reports are separate entities handled in later modules.
 *   - Per-resource ownership filtering is intentionally deferred until persistent
 *     case storage (MongoDB) is integrated.
 *   - createdBy is strictly bound to req.user.id and cannot be forged by clients.
 */

'use strict';

const crypto = require('crypto');
const CaseModel = require('../models/case.model');
const {
  isValidCaseId,
  validateCreateCaseInput,
  validateUpdateCaseInput,
  validateFundusImage,
} = require('../utils/validation');
const { safeUnlink } = require('../utils/file.utils');
const ImageStorageService = require('../services/image-storage.service');
const logger = require('../utils/logger');

/**
 * Create a new screening case.
 * POST /api/cases
 *
 * Allowed roles: technician, admin
 */
const createCase = async (req, res, next) => {
  try {
    // 1. Input validation
    const validation = validateCreateCaseInput(req.body);
    if (!validation.valid) {
      return res.status(400).json({
        status:  'error',
        code:    400,
        message: validation.error,
      });
    }

    const { patientId, notes } = req.body;

    // 2. Associate with authenticated user (never trust createdBy from request)
    const creatorId = req.user && req.user.id;
    if (!creatorId) {
      return res.status(401).json({
        status:  'error',
        code:    401,
        message: 'Authentication required: missing user context',
      });
    }

    // 3. Persist via CaseModel abstraction (lifecycle status defaults to 'created')
    const newCase = await CaseModel.create({
      patientId,
      createdBy: creatorId,
      notes,
    });

    logger.info(`Screening case created: ${newCase.id} for patient: ${newCase.patientId} by user: ${creatorId}`);

    return res.status(201).json({
      status:  'success',
      success: true,
      message: 'Screening case created successfully',
      case:    newCase,
      data:    newCase,
    });
  } catch (err) {
    logger.error('Error creating screening case', { error: err.message });
    next(err);
  }
};

/**
 * List screening cases.
 * GET /api/cases
 *
 * Allowed roles: technician, doctor, admin
 * Note: Resource-level ownership filtering will be implemented after persistent case storage is integrated.
 */
const listCases = async (_req, res, next) => {
  try {
    const cases = await CaseModel.findAll();

    return res.status(200).json({
      status:  'success',
      success: true,
      count:   cases.length,
      cases,
      data:    cases,
    });
  } catch (err) {
    logger.error('Error listing screening cases', { error: err.message });
    next(err);
  }
};

/**
 * Get a single screening case by ID.
 * GET /api/cases/:id
 *
 * Allowed roles: technician, doctor, admin
 */
const getCaseById = async (req, res, next) => {
  try {
    const { id } = req.params;

    if (!isValidCaseId(id)) {
      return res.status(400).json({
        status:  'error',
        code:    400,
        message: 'Invalid case ID parameter',
      });
    }

    const caseRecord = await CaseModel.findById(id);
    if (!caseRecord) {
      return res.status(404).json({
        status:  'error',
        code:    404,
        message: `Screening case not found with ID: ${id}`,
      });
    }

    return res.status(200).json({
      status:  'success',
      success: true,
      case:    caseRecord,
      data:    caseRecord,
    });
  } catch (err) {
    logger.error(`Error retrieving case ${req.params.id}`, { error: err.message });
    next(err);
  }
};

/**
 * Update screening case metadata.
 * PATCH /api/cases/:id
 *
 * Allowed roles: technician, doctor, admin
 * Protected fields: id, caseId, createdBy, createdAt, updatedAt, status
 */
const updateCase = async (req, res, next) => {
  try {
    const { id } = req.params;

    if (!isValidCaseId(id)) {
      return res.status(400).json({
        status:  'error',
        code:    400,
        message: 'Invalid case ID parameter',
      });
    }

    // 1. Validate update payload
    const validation = validateUpdateCaseInput(req.body);
    if (!validation.valid) {
      return res.status(400).json({
        status:  'error',
        code:    400,
        message: validation.error,
      });
    }

    // 2. Verify case existence
    const existing = await CaseModel.findById(id);
    if (!existing) {
      return res.status(404).json({
        status:  'error',
        code:    404,
        message: `Screening case not found with ID: ${id}`,
      });
    }

    // 3. Apply updates to allowed fields
    const updatedCase = await CaseModel.update(id, req.body);

    logger.info(`Screening case updated: ${id} by user: ${req.user ? req.user.id : 'unknown'}`);

    return res.status(200).json({
      status:  'success',
      success: true,
      message: 'Screening case updated successfully',
      case:    updatedCase,
      data:    updatedCase,
    });
  } catch (err) {
    logger.error(`Error updating case ${req.params.id}`, { error: err.message });
    next(err);
  }
};

/**
 * Pre-upload validation middleware.
 * Verifies case ID validity, case existence, and lifecycle status before multer runs.
 * Prevents unwanted disk I/O when target case is invalid or already has an image.
 */
const validateCaseForUpload = async (req, res, next) => {
  try {
    const { id } = req.params;

    if (!isValidCaseId(id)) {
      return res.status(400).json({
        status:  'error',
        code:    400,
        message: 'Invalid case ID parameter',
      });
    }

    const caseRecord = await CaseModel.findById(id);
    if (!caseRecord) {
      return res.status(404).json({
        status:  'error',
        code:    404,
        message: `Screening case not found with ID: ${id}`,
      });
    }

    // Only cases in 'created' status without an existing image can receive an image upload
    if (caseRecord.status !== CaseModel.CASE_STATUS.CREATED || caseRecord.image) {
      return res.status(409).json({
        status:  'error',
        code:    409,
        message: `Screening case ${id} already has a fundus image (status: '${caseRecord.status}'). Re-upload is not permitted.`,
      });
    }

    req.case = caseRecord;
    next();
  } catch (err) {
    logger.error(`Error validating case before upload: ${req.params.id}`, { error: err.message });
    next(err);
  }
};

/**
 * Upload fundus image for an existing screening case.
 * POST /api/cases/:id/image
 *
 * Allowed roles: technician, admin
 */
const uploadCaseImage = async (req, res, next) => {
  try {
    const { id } = req.params;

    // 1. Guard against missing file
    if (!req.file) {
      return res.status(400).json({
        status:  'error',
        code:    400,
        message: 'Fundus image file is required. Please upload an image using multipart/form-data with field name "image"',
      });
    }

    // 2. Validate file (MIME type, extension, non-empty)
    const fileValidation = validateFundusImage(req.file);
    if (!fileValidation.valid) {
      safeUnlink(req.file.path);
      return res.status(400).json({
        status:  'error',
        code:    400,
        message: fileValidation.error,
      });
    }

    // 3. Fallback verification if pre-upload middleware was bypassed
    const targetCase = req.case || await CaseModel.findById(id);
    if (!targetCase) {
      safeUnlink(req.file.path);
      return res.status(404).json({
        status:  'error',
        code:    404,
        message: `Screening case not found with ID: ${id}`,
      });
    }

    if (targetCase.status !== CaseModel.CASE_STATUS.CREATED || targetCase.image) {
      safeUnlink(req.file.path);
      return res.status(409).json({
        status:  'error',
        code:    409,
        message: `Screening case ${id} already has a fundus image (status: '${targetCase.status}'). Re-upload is not permitted.`,
      });
    }

    // 4. Persist image via Image Storage Service (Module 5)
    // Server generates safe storage filename and organizes inside storage/images/<caseId>/<imageId>.<ext>
    const imageMetadata = await ImageStorageService.saveImage(req.file, {
      caseId:     targetCase.id,
      uploadedBy: req.user.id,
    });

    // 5. Associate image metadata with case and transition status to 'image_uploaded'
    let updatedCase;
    try {
      updatedCase = await CaseModel.attachImage(targetCase.id, imageMetadata);
    } catch (attachErr) {
      // Failure cleanup: remove persisted image if case association fails
      await ImageStorageService.deleteImage(targetCase.id, imageMetadata.imageId);
      throw attachErr;
    }

    logger.info(`Fundus image ${imageMetadata.imageId} uploaded for case: ${targetCase.id} by user: ${req.user.id}`);

    // 6. Return safe response envelope (Step 11 contract, internal paths hidden)
    return res.status(200).json({
      status:  'success',
      success: true,
      message: 'Fundus image uploaded successfully',
      case: {
        id:        updatedCase.id,
        status:    updatedCase.status,
        patientId: updatedCase.patientId,
        createdBy: updatedCase.createdBy,
        createdAt: updatedCase.createdAt,
        updatedAt: updatedCase.updatedAt,
      },
      image: {
        imageId:        imageMetadata.imageId,
        originalName:   imageMetadata.originalName,
        storedFilename: imageMetadata.storedFilename,
        mimeType:       imageMetadata.mimeType,
        extension:      imageMetadata.extension,
        sizeBytes:      imageMetadata.sizeBytes,
        uploadedBy:     imageMetadata.uploadedBy,
        uploadedAt:     imageMetadata.uploadedAt,
      },
    });
  } catch (err) {
    if (req.file && req.file.path) {
      safeUnlink(req.file.path);
    }
    logger.error(`Error uploading image for case ${req.params.id}`, { error: err.message });
    next(err);
  }
};

/**
 * Stub handler for endpoints not yet implemented (e.g. DELETE /api/cases/:id).
 */
const stub = (_req, res) => {
  res.status(501).json({
    status:  'not_implemented',
    message: 'Endpoint not implemented yet.',
  });
};

module.exports = {
  createCase,
  listCases,
  getCaseById,
  updateCase,
  validateCaseForUpload,
  uploadCaseImage,
  uploadImage: uploadCaseImage,
  runCaseInference: require('./ai.controller').runCaseInference,
  getCaseAiResult:  require('./ai.controller').getCaseAiResult,
  stub,
};
