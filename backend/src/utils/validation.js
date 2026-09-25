/**
 * utils/validation.js — NETRA-DR Input Validation Helpers
 *
 * Provides reusable validation functions for request bodies and params.
 */

'use strict';

const { VALID_ROLES } = require('../models/user.model');

// RFC 5322 compliant simplified email regex
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Check if a string is a valid email address.
 *
 * @param {string} email
 * @returns {boolean}
 */
const isValidEmail = (email) => {
  return typeof email === 'string' && EMAIL_REGEX.test(email.trim());
};

/**
 * Check if a password meets minimum criteria.
 * Minimum 6 characters.
 *
 * @param {string} password
 * @returns {boolean}
 */
const isValidPassword = (password) => {
  return typeof password === 'string' && password.length >= 6;
};

/**
 * Check if a role is supported.
 *
 * @param {string} role
 * @returns {boolean}
 */
const isValidRole = (role) => {
  return typeof role === 'string' && VALID_ROLES.includes(role.toLowerCase());
};

/**
 * Validate user registration payload.
 *
 * @param {object} body
 * @returns {{ valid: boolean, error?: string }}
 */
const validateRegistrationInput = (body = {}) => {
  const { name, email, password, role } = body;

  if (!name || typeof name !== 'string' || name.trim().length === 0) {
    return { valid: false, error: 'Name is required' };
  }

  if (!email || !isValidEmail(email)) {
    return { valid: false, error: 'A valid email address is required' };
  }

  if (!password || typeof password !== 'string') {
    return { valid: false, error: 'Password is required' };
  }

  if (!isValidPassword(password)) {
    return { valid: false, error: 'Password must be at least 6 characters long' };
  }

  if (!role || !isValidRole(role)) {
    return {
      valid: false,
      error: `Role must be one of: ${VALID_ROLES.join(', ')}`,
    };
  }

  return { valid: true };
};

/**
 * Validate user login payload.
 *
 * @param {object} body
 * @returns {{ valid: boolean, error?: string }}
 */
const validateLoginInput = (body = {}) => {
  const { email, password } = body;

  if (!email || typeof email !== 'string' || email.trim().length === 0) {
    return { valid: false, error: 'Email is required' };
  }

  if (!password || typeof password !== 'string' || password.length === 0) {
    return { valid: false, error: 'Password is required' };
  }

  return { valid: true };
};

/**
 * Validate that an uploaded file is an acceptable fundus image.
 * @param {object} _file  Multer file object
 * @returns {{ valid: boolean, error: string|null }}
 */
const validateFundusImage = (_file) => {
  // TODO: Implement in validation task
  return { valid: true, error: null };
};

module.exports = {
  isValidEmail,
  isValidPassword,
  isValidRole,
  validateRegistrationInput,
  validateLoginInput,
  validateFundusImage,
};
