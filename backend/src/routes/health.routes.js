/**
 * routes/health.routes.js — NETRA-DR Health Check Endpoint
 *
 * GET /api/health
 *   Returns server liveness, version, environment, and uptime.
 *   Used by Node.js backend itself and can proxy Flask status in a future task.
 */

'use strict';

const express = require('express');
const router  = express.Router();

const { getHealth } = require('../controllers/health.controller');

router.get('/', getHealth);

module.exports = router;
