/**
 * routes/simulation.routes.js — NETRA-DR Simulation Routes
 *
 * Business logic: NOT implemented yet (stub handlers returning 501).
 *
 * RBAC applied (Module 2):
 *   All simulation endpoints require authentication.
 *   Role distribution per the permission model:
 *
 *   GET  /api/simulation/results   doctor, admin   — read simulation results (clinical/planning)
 *   POST /api/simulation/run       admin only      — trigger a simulation run (privileged action)
 *
 * Rationale:
 *   Simulation results are used for district-scale planning / clinical context.
 *   Running a simulation is an administrative / research action. Technicians are
 *   field-level users not involved in population-level simulation.
 *
 * NOTE: The existing MATLAB sweep_ratio.m is a standalone script (matlab/).
 * Node.js integration will allow triggering and reading its results.
 *
 * Planned endpoints:
 *   GET  /api/simulation/results        Read latest simulation results
 *   POST /api/simulation/run            Trigger a simulation run (future)
 */

'use strict';

const express = require('express');
const router  = express.Router();
const { stub } = require('../controllers/simulation.controller');
const { requireAuth, authorize } = require('../middleware/auth.middleware');
const { ROLES } = require('../config/roles');

// Reading results: doctors and admins (for clinical and planning use)
router.get('/results', requireAuth, authorize(ROLES.DOCTOR, ROLES.ADMIN), stub);

// Triggering runs: admin only (privileged system action)
router.post('/run',    requireAuth, authorize(ROLES.ADMIN), stub);

module.exports = router;
