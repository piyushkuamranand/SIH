/**
 * routes/cases.routes.js — NETRA-DR Cases Routes
 *
 * Implemented in Module 3 (Screening Case Creation):
 *   POST   /api/cases         technician, admin         — create case
 *   GET    /api/cases         technician, doctor, admin — list cases
 *   GET    /api/cases/:id     technician, doctor, admin — get single case
 *   PATCH  /api/cases/:id     technician, doctor, admin — update case metadata
 *   DELETE /api/cases/:id     admin only                — delete case (stub)
 *
 * IMPORTANT OWNERSHIP NOTE:
 *   Role-level authorization here grants category-level access.
 *   Per-resource ownership (e.g. "can this specific technician access
 *   this specific case?") will be implemented after persistent case storage
 *   (MongoDB) is integrated.
 */

'use strict';

const express = require('express');
const router  = express.Router();
const {
  createCase,
  listCases,
  getCaseById,
  updateCase,
  validateCaseForUpload,
  uploadCaseImage,
  runCaseInference,
  getCaseAiResult,
  stub,
} = require('../controllers/cases.controller');
const { requireAuth, authorize } = require('../middleware/auth.middleware');
const { handleImageUpload }      = require('../middleware/upload.middleware');
const { ROLES }                  = require('../config/roles');

// List cases: technician, doctor, admin
router.get('/',       requireAuth, authorize(ROLES.TECHNICIAN, ROLES.DOCTOR, ROLES.ADMIN), listCases);

// Get single case: technician, doctor, admin
router.get('/:id',    requireAuth, authorize(ROLES.TECHNICIAN, ROLES.DOCTOR, ROLES.ADMIN), getCaseById);

// Retrieve persisted AI inference result (Module 7): technician, doctor, admin
router.get('/:id/ai-result', requireAuth, authorize(ROLES.TECHNICIAN, ROLES.DOCTOR, ROLES.ADMIN), getCaseAiResult);
router.get('/:id/ai',        requireAuth, authorize(ROLES.TECHNICIAN, ROLES.DOCTOR, ROLES.ADMIN), getCaseAiResult);

// Create screening case: technician and admin only (doctors cannot create screening cases)
router.post('/',      requireAuth, authorize(ROLES.TECHNICIAN, ROLES.ADMIN), createCase);

// Upload fundus image to screening case (Module 4): technician and admin only
router.post(
  '/:id/image',
  requireAuth,
  authorize(ROLES.TECHNICIAN, ROLES.ADMIN),
  validateCaseForUpload,
  handleImageUpload('image'),
  uploadCaseImage
);

// Run AI inference on screening case (Module 6): technician and admin only
router.post(
  '/:id/ai',
  requireAuth,
  authorize(ROLES.TECHNICIAN, ROLES.ADMIN),
  runCaseInference
);

// Update case metadata: technician, doctor, admin
router.patch('/:id',  requireAuth, authorize(ROLES.TECHNICIAN, ROLES.DOCTOR, ROLES.ADMIN), updateCase);

// Delete case: admin-only destructive operation (stub)
router.delete('/:id', requireAuth, authorize(ROLES.ADMIN), stub);

module.exports = router;
