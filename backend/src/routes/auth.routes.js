/**
 * routes/auth.routes.js — NETRA-DR Authentication Routes
 *
 * Endpoints:
 *   POST /api/auth/register - Register new technician/doctor/admin
 *   POST /api/auth/login    - Authenticate user credentials & receive JWT
 *   GET  /api/auth/me       - Protected: get authenticated user profile
 *   POST /api/auth/logout   - Logout (token invalidation / session clear)
 *   POST /api/auth/refresh  - Refresh token (placeholder)
 */

'use strict';

const express = require('express');
const router  = express.Router();
const {
  register,
  login,
  getMe,
  logout,
  refresh,
} = require('../controllers/auth.controller');
const { requireAuth } = require('../middleware/auth.middleware');

router.post('/register', register);
router.post('/login',    login);
router.get('/me',        requireAuth, getMe);
router.post('/logout',   logout);
router.post('/refresh',  refresh);

module.exports = router;
