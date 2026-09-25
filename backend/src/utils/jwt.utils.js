/**
 * utils/jwt.utils.js — NETRA-DR JWT Token Service
 *
 * Provides cryptographic token generation and verification.
 * Adheres strictly to security specifications:
 *   - Only identity claims are encoded (userId, role, email)
 *   - Medical, patient, and screening data are NEVER included in tokens
 *   - JWT secret is loaded securely from configuration/environment
 *   - Secrets and tokens are NEVER logged
 */

'use strict';

const jwt = require('jsonwebtoken');
const env = require('../config/env');

/**
 * Generate a signed JWT for an authenticated user.
 *
 * @param {object} user - User record or safe user object
 * @param {string} user.id - User unique identifier
 * @param {string} user.role - User role ('technician' | 'doctor' | 'admin')
 * @param {string} user.email - User email address
 * @returns {string} Signed JWT token string
 */
const generateToken = (user) => {
  if (!user || !user.id || !user.role) {
    throw new Error('User id and role are required to issue a JWT');
  }

  const payload = {
    userId: user.id,
    role:   user.role,
    email:  user.email,
  };

  return jwt.sign(payload, env.JWT_SECRET, {
    expiresIn: env.JWT_EXPIRES_IN || '8h',
  });
};

/**
 * Verify a JWT string against the configured secret.
 *
 * @param {string} token - Raw JWT token string
 * @returns {object} Decoded token payload
 * @throws {jwt.JsonWebTokenError|jwt.TokenExpiredError}
 */
const verifyToken = (token) => {
  return jwt.verify(token, env.JWT_SECRET);
};

module.exports = {
  generateToken,
  verifyToken,
};
