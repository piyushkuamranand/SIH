/**
 * controllers/auth.controller.js — NETRA-DR Authentication Controller
 *
 * Implements authentication endpoints:
 *   - POST /api/auth/register : Register a new user
 *   - POST /api/auth/login    : Authenticate credentials and issue JWT
 *   - GET  /api/auth/me       : Get authenticated user profile
 *   - POST /api/auth/logout   : Logout placeholder
 *   - POST /api/auth/refresh  : Token refresh placeholder
 *
 * Security:
 *   - Passwords are encrypted with bcrypt before saving
 *   - Passwords and password hashes are never returned in responses
 *   - Passwords, hashes, JWT secrets, and tokens are NEVER logged
 */

'use strict';

const bcrypt = require('bcryptjs');
const UserModel = require('../models/user.model');
const { generateToken } = require('../utils/jwt.utils');
const {
  validateRegistrationInput,
  validateLoginInput,
} = require('../utils/validation');
const logger = require('../utils/logger');

const BCRYPT_SALT_ROUNDS = 10;

/**
 * Register a new user.
 * POST /api/auth/register
 */
const register = async (req, res, next) => {
  try {
    const { name, email, password, role } = req.body || {};

    // 1. Input validation
    const validation = validateRegistrationInput({ name, email, password, role });
    if (!validation.valid) {
      return res.status(400).json({
        status:  'error',
        code:    400,
        message: validation.error,
      });
    }

    // 2. Uniqueness check
    const existingUser = await UserModel.findByEmail(email);
    if (existingUser) {
      return res.status(409).json({
        status:  'error',
        code:    409,
        message: 'A user with this email address already exists',
      });
    }

    // 3. Hash password (plaintext password is never stored)
    const passwordHash = await bcrypt.hash(password, BCRYPT_SALT_ROUNDS);

    // 4. Persist user via UserModel abstraction
    const user = await UserModel.create({
      name,
      email,
      passwordHash,
      role,
    });

    const safeUser = UserModel.toSafeUser(user);

    // Log event safely (never log password, hash, or token)
    logger.info(`User registered: ${safeUser.email} (id: ${safeUser.id}, role: ${safeUser.role})`);

    return res.status(201).json({
      status:  'success',
      success: true,
      message: 'User registered successfully',
      user:    safeUser,
    });
  } catch (err) {
    logger.error('Registration error', { error: err.message });
    next(err);
  }
};

/**
 * Authenticate user and issue JWT.
 * POST /api/auth/login
 */
const login = async (req, res, next) => {
  try {
    const { email, password } = req.body || {};

    // 1. Input validation
    const validation = validateLoginInput({ email, password });
    if (!validation.valid) {
      return res.status(400).json({
        status:  'error',
        code:    400,
        message: validation.error,
      });
    }

    // 2. User existence check
    const user = await UserModel.findByEmail(email);
    if (!user) {
      logger.warn(`Failed login attempt for email: ${email}`);
      return res.status(401).json({
        status:  'error',
        code:    401,
        message: 'Invalid email or password',
      });
    }

    // 3. Verify password hash
    const isPasswordValid = await bcrypt.compare(password, user.passwordHash);
    if (!isPasswordValid) {
      logger.warn(`Failed login attempt for email: ${email}`);
      return res.status(401).json({
        status:  'error',
        code:    401,
        message: 'Invalid email or password',
      });
    }

    // 4. Issue JWT
    const token = generateToken(user);
    const safeUser = UserModel.toSafeUser(user);

    logger.info(`User logged in: ${safeUser.email} (id: ${safeUser.id}, role: ${safeUser.role})`);

    // Return specified envelope
    return res.status(200).json({
      success: true,
      token,
      user: {
        id:    safeUser.id,
        name:  safeUser.name,
        email: safeUser.email,
        role:  safeUser.role,
      },
    });
  } catch (err) {
    logger.error('Login error', { error: err.message });
    next(err);
  }
};

/**
 * Retrieve current authenticated user profile.
 * GET /api/auth/me
 */
const getMe = async (req, res, next) => {
  try {
    // req.user is guaranteed to be attached by requireAuth middleware
    return res.status(200).json({
      success: true,
      user:    req.user,
    });
  } catch (err) {
    logger.error('Get profile error', { error: err.message });
    next(err);
  }
};

/**
 * Placeholder logout handler.
 * POST /api/auth/logout
 */
const logout = (_req, res) => {
  res.status(200).json({
    status:  'success',
    message: 'Logged out successfully',
  });
};

/**
 * Placeholder refresh handler.
 * POST /api/auth/refresh
 */
const refresh = (_req, res) => {
  res.status(501).json({
    status:  'not_implemented',
    message: 'Token refresh is not implemented yet.',
  });
};

/**
 * Generic stub handler (maintained for backwards compatibility).
 */
const stub = (_req, res) => {
  res.status(501).json({
    status:  'not_implemented',
    message: 'Authentication endpoint not implemented yet.',
  });
};

module.exports = {
  register,
  login,
  getMe,
  logout,
  refresh,
  stub,
};
