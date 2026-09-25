/**
 * routes/screening.routes.js — NETRA-DR Screening Routes
 *
 * Business logic: NOT implemented yet (stub handlers returning 501).
 *
 * RBAC applied (Module 2):
 *   All screening endpoints require authentication.
 *   Role distribution per the permission model:
 *
 *   POST /api/screening/         technician, doctor, admin  — upload + run pipeline
 *   POST /api/screening/quality  technician, doctor, admin  — Phase 1 quality check only
 *   GET  /api/screening/:id/status technician, doctor, admin — poll pipeline status
 *   GET  /api/screening/:id/result technician, doctor, admin — retrieve full result
 *
 * NOTE: Resource-ownership checks (can THIS user access THIS screening job?)
 * are a TODO for the screening controller implementation — role-level guards
 * here are a necessary but not sufficient access control layer.
 *
 * Planned endpoints:
 *   POST /api/screening/upload          Upload + full pipeline
 *   POST /api/screening/quality         Phase 1 quality check only
 *   GET  /api/screening/:id/status      Poll pipeline status
 *   GET  /api/screening/:id/result      Retrieve full pipeline result
 */

'use strict';

const express = require('express');
const router  = express.Router();
const { stub } = require('../controllers/screening.controller');
const { requireAuth, authorize } = require('../middleware/auth.middleware');
const { ROLES } = require('../config/roles');

// All authenticated roles may interact with screening endpoints.
// (Technician initiates screening; doctors and admins can also view results.)
const screeningRoles = [ROLES.TECHNICIAN, ROLES.DOCTOR, ROLES.ADMIN];

router.post('/',             requireAuth, authorize(...screeningRoles), stub); // upload + run full pipeline
router.post('/quality',      requireAuth, authorize(...screeningRoles), stub); // Phase 1 only
router.get('/:id/status',   requireAuth, authorize(...screeningRoles), stub);
router.get('/:id/result',   requireAuth, authorize(...screeningRoles), stub);

module.exports = router;
