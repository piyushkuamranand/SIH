/**
 * routes/reports.routes.js — NETRA-DR Report Routes
 *
 * Business logic: NOT implemented yet (stub handlers returning 501).
 *
 * RBAC applied (Module 2):
 *   All report endpoints require authentication.
 *   Role distribution per the permission model:
 *
 *   GET  /api/reports/:caseId           doctor, admin        — view clinical report
 *   POST /api/reports/:caseId/generate  doctor, admin        — generate / regenerate PDF
 *   GET  /api/reports/:caseId/download  doctor, admin        — download PDF
 *
 * Rationale:
 *   Report generation and access is a clinical activity reserved for doctors
 *   and administrators. Technicians do not generate or download clinical reports.
 *
 * Planned endpoints:
 *   GET  /api/reports/:caseId          Get report for a case
 *   POST /api/reports/:caseId/generate Generate / regenerate PDF report
 *   GET  /api/reports/:caseId/download Download PDF report
 */

'use strict';

const express = require('express');
const router  = express.Router();
const { stub } = require('../controllers/reports.controller');
const { requireAuth, authorize } = require('../middleware/auth.middleware');
const { ROLES } = require('../config/roles');

// Clinical report access: doctor and admin only
router.get('/:caseId',             requireAuth, authorize(ROLES.DOCTOR, ROLES.ADMIN), stub);
router.post('/:caseId/generate',   requireAuth, authorize(ROLES.DOCTOR, ROLES.ADMIN), stub);
router.get('/:caseId/download',    requireAuth, authorize(ROLES.DOCTOR, ROLES.ADMIN), stub);

module.exports = router;
