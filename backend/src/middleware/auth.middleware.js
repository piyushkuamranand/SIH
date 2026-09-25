/**
 * middleware/auth.middleware.js — NETRA-DR Authentication & RBAC Middleware
 *
 * Module 1 — Authentication (requireAuth):
 *   1. Read Authorization header.
 *   2. Require 'Bearer <token>' format.
 *   3. Verify JWT against configured secret.
 *   4. Attach safe user object to req.user.
 *   5. Reject missing/invalid/expired tokens with 401 Unauthorized.
 *   6. Never expose JWT secret, token strings, or sensitive credentials.
 *
 * Module 2 — RBAC (authorize):
 *   7. Enforce role-based access control AFTER authentication.
 *   8. Return 403 Forbidden when authenticated but not authorized.
 *   9. Never combine auth + authz into a single function.
 */

'use strict';

const { verifyToken } = require('../utils/jwt.utils');
const UserModel       = require('../models/user.model');
const { VALID_ROLES } = require('../config/roles');
const logger          = require('../utils/logger');

/**
 * Authentication middleware.
 * Verifies Bearer JWT token and attaches user profile to req.user.
 *
 * @param {import('express').Request} req
 * @param {import('express').Response} res
 * @param {import('express').NextFunction} next
 */
const requireAuth = async (req, res, next) => {
  try {
    const authHeader = req.headers.authorization || req.headers.Authorization;

    if (!authHeader || typeof authHeader !== 'string') {
      return res.status(401).json({
        status:  'error',
        code:    401,
        message: "Authorization header is missing. Expected 'Bearer <token>'",
      });
    }

    const parts = authHeader.trim().split(/\s+/);
    if (parts.length !== 2 || parts[0] !== 'Bearer' || !parts[1]) {
      return res.status(401).json({
        status:  'error',
        code:    401,
        message: "Invalid authorization header format. Expected 'Bearer <token>'",
      });
    }

    const token = parts[1];

    let decoded;
    try {
      decoded = verifyToken(token);
    } catch (err) {
      if (err.name === 'TokenExpiredError') {
        return res.status(401).json({
          status:  'error',
          code:    401,
          message: 'Authentication token has expired. Please log in again',
        });
      }
      return res.status(401).json({
        status:  'error',
        code:    401,
        message: 'Invalid or malformed authentication token',
      });
    }

    if (!decoded || !decoded.userId) {
      return res.status(401).json({
        status:  'error',
        code:    401,
        message: 'Invalid token payload',
      });
    }

    // Look up the active user by ID
    const user = await UserModel.findById(decoded.userId);
    if (!user) {
      return res.status(401).json({
        status:  'error',
        code:    401,
        message: 'Authenticated user not found or inactive',
      });
    }

    // Attach safe user profile (without passwordHash) to req.user
    req.user = UserModel.toSafeUser(user);
    next();
  } catch (err) {
    logger.error('Unexpected error in requireAuth middleware', { error: err.message });
    next(err);
  }
};

/**
 * Role-based authorization middleware factory.
 *
 * MUST be used AFTER requireAuth in the middleware chain:
 *
 *   router.get('/protected', requireAuth, authorize('doctor', 'admin'), controller)
 *
 * Behavior:
 *   - Relies on req.user being set by requireAuth.
 *   - If req.user is absent         → 401 Unauthorized (auth did not run first).
 *   - If req.user.role not in roles → 403 Forbidden.
 *   - If req.user.role is in roles  → calls next().
 *   - Roles with unrecognized values are treated as forbidden (403).
 *
 * @param  {...string} roles  One or more allowed role strings
 * @returns {import('express').RequestHandler}
 */
const authorize = (...roles) => {
  // Validate role arguments at middleware registration time (startup safety check)
  const invalidRoles = roles.filter(r => !VALID_ROLES.includes(r));
  if (invalidRoles.length > 0) {
    throw new Error(
      `authorize() called with unrecognized roles: [${invalidRoles.join(', ')}]. ` +
      `Valid roles are: ${VALID_ROLES.join(', ')}`
    );
  }

  const allowed = new Set(roles);

  return (req, res, next) => {
    // Guard: requireAuth must have run first and populated req.user
    if (!req.user) {
      return res.status(401).json({
        status:  'error',
        code:    401,
        message: 'Authentication required',
      });
    }

    const userRole = req.user.role;

    // Reject unrecognized or missing role values
    if (!userRole || !VALID_ROLES.includes(userRole)) {
      logger.warn(
        `Authorization denied: user ${req.user.id} has unrecognized role '${userRole}'`
      );
      return res.status(403).json({
        status:  'error',
        code:    403,
        message: 'Access denied: your account role is not recognized',
      });
    }

    if (!allowed.has(userRole)) {
      logger.warn(
        `Authorization denied: user ${req.user.id} (role=${userRole}) ` +
        `attempted access requiring [${roles.join(', ')}]`
      );
      return res.status(403).json({
        status:  'error',
        code:    403,
        message: `Access denied: requires role [${roles.join(' | ')}], you have role [${userRole}]`,
      });
    }

    next();
  };
};

module.exports = {
  requireAuth,
  authenticate: requireAuth,  // backwards-compat alias
  authorize,
};
