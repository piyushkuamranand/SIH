/**
 * routes/cases.routes.js — NETRA-DR Cases Routes
 *
 * Business logic: NOT implemented yet (stub handlers returning 501).
 *
 * RBAC applied (Module 2):
 *   All case endpoints require authentication.
 *   Role distribution per the permission model:
 *
 *   GET    /api/cases         technician, doctor, admin — list cases
 *   GET    /api/cases/:id     technician, doctor, admin — get single case
 *   POST   /api/cases         technician, admin         — create case
 *   PATCH  /api/cases/:id     technician, doctor, admin — update case
 *   DELETE /api/cases/:id     admin only                — delete case
 *
 * IMPORTANT OWNERSHIP NOTE:
 *   Role-level authorization here grants category-level access.
 *   Per-resource ownership (e.g. "can this specific technician access
 *   this specific case?") MUST be implemented inside the case controller
 *   once the case data model is persisted.
 *   TODO: Implement ownership/access-level checks in cases.controller.js
 *
 * Doctor review preparation (Module 3 ready):
 *   PATCH /api/cases/:id is available to doctor for review updates.
 *   A dedicated POST /api/cases/:id/review endpoint will be added in
 *   the doctor-review module and should use: authorize('doctor', 'admin')
 *
 * Planned endpoints:
 *   GET    /api/cases           List all cases
 *   GET    /api/cases/:id       Get single case
 *   POST   /api/cases           Create case (linked to screening result)
 *   PATCH  /api/cases/:id       Update case
 *   DELETE /api/cases/:id       Delete case
 */

'use strict';

const express = require('express');
const router  = express.Router();
const { stub } = require('../controllers/cases.controller');
const { requireAuth, authorize } = require('../middleware/auth.middleware');
const { ROLES } = require('../config/roles');

// List and read: all roles may view cases (ownership enforced in controller)
router.get('/',       requireAuth, authorize(ROLES.TECHNICIAN, ROLES.DOCTOR, ROLES.ADMIN), stub);
router.get('/:id',    requireAuth, authorize(ROLES.TECHNICIAN, ROLES.DOCTOR, ROLES.ADMIN), stub);

// Create: technicians create cases; admins can too
router.post('/',      requireAuth, authorize(ROLES.TECHNICIAN, ROLES.ADMIN), stub);

// Update: technicians update case data; doctors update for review; admins always
router.patch('/:id',  requireAuth, authorize(ROLES.TECHNICIAN, ROLES.DOCTOR, ROLES.ADMIN), stub);

// Delete: admin-only destructive operation
router.delete('/:id', requireAuth, authorize(ROLES.ADMIN), stub);

module.exports = router;
