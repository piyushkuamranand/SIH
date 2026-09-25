/**
 * utils/validation.js — NETRA-DR Input Validation Helpers
 *
 * Provides reusable validation functions for request bodies and params.
 */

'use strict';

const path = require('path');
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

const ALLOWED_FUNDUS_MIME_TYPES = Object.freeze(['image/jpeg', 'image/png']);
const ALLOWED_FUNDUS_EXTENSIONS = Object.freeze(['.jpg', '.jpeg', '.png']);

/**
 * Validate that an uploaded file is an acceptable fundus image.
 *
 * Checks:
 *   1. File exists
 *   2. File size is greater than 0
 *   3. MIME type is image/jpeg or image/png
 *   4. File extension is .jpg, .jpeg, or .png
 *
 * @param {object} file  Multer file object
 * @returns {{ valid: boolean, error: string|null }}
 */
const validateFundusImage = (file) => {
  if (!file) {
    return { valid: false, error: 'No image file provided' };
  }

  if (typeof file.size === 'number' && file.size === 0) {
    return { valid: false, error: 'Uploaded file is empty (0 bytes)' };
  }

  const mime = (file.mimetype || '').toLowerCase();
  if (!ALLOWED_FUNDUS_MIME_TYPES.includes(mime)) {
    return {
      valid: false,
      error: `Unsupported file type: '${mime || 'unknown'}'. Only JPEG and PNG images are accepted`,
    };
  }

  const ext = path.extname(file.originalname || '').toLowerCase();
  if (!ALLOWED_FUNDUS_EXTENSIONS.includes(ext)) {
    return {
      valid: false,
      error: `Unsupported file extension: '${ext || 'none'}'. Only .jpg, .jpeg, and .png are accepted`,
    };
  }

  return { valid: true, error: null };
};

/**
 * Validate case ID parameter.
 * Must be a non-empty string starting with 'case_' without forbidden characters.
 *
 * @param {string} id
 * @returns {boolean}
 */
const isValidCaseId = (id) => {
  if (!id || typeof id !== 'string') return false;
  const trimmed = id.trim();
  if (trimmed.length === 0) return false;
  if (/[\s/\\<>:;"'|?*]/.test(trimmed)) return false;
  if (!trimmed.startsWith('case_')) return false;
  return true;
};

/**
 * Validate screening case creation payload.
 *
 * Requirements:
 *   - patientId: required non-empty string
 *   - status: cannot be arbitrarily set by client (always starts in 'created')
 *   - notes: optional string
 *   - rejected on unrecognized fields to prevent arbitrary medical injection
 *
 * @param {object} body
 * @returns {{ valid: boolean, error?: string }}
 */
const validateCreateCaseInput = (body = {}) => {
  if (!body || typeof body !== 'object' || Array.isArray(body)) {
    return { valid: false, error: 'Request body must be a valid JSON object' };
  }

  const { patientId, notes, status } = body;

  if (!patientId || typeof patientId !== 'string' || patientId.trim().length === 0) {
    return { valid: false, error: 'Patient reference (patientId) is required and must be a non-empty string' };
  }

  // Reject attempts to set workflow state during creation
  if (status !== undefined && status !== 'created') {
    return {
      valid: false,
      error: "Case status cannot be set during creation. All new cases start in 'created' status",
    };
  }

  if (notes !== undefined && notes !== null && typeof notes !== 'string') {
    return { valid: false, error: 'Notes must be a string' };
  }

  // Check for disallowed / unexpected fields to prevent arbitrary medical injection
  const allowedKeys = ['patientId', 'notes', 'status', 'id', 'caseId', 'createdBy'];
  for (const key of Object.keys(body)) {
    if (!allowedKeys.includes(key)) {
      return { valid: false, error: `Unrecognized field: '${key}'. Case creation only accepts patient reference and optional notes` };
    }
  }

  return { valid: true };
};

/**
 * Validate screening case update (PATCH) payload.
 *
 * Requirements:
 *   - Protected fields (id, caseId, createdBy, createdAt, updatedAt, status) cannot be modified.
 *   - Body cannot be empty.
 *   - Only allowed metadata fields can be updated (patientId, notes).
 *
 * @param {object} body
 * @returns {{ valid: boolean, error?: string }}
 */
const validateUpdateCaseInput = (body = {}) => {
  if (!body || typeof body !== 'object' || Array.isArray(body)) {
    return { valid: false, error: 'Request body must be a valid JSON object' };
  }

  const keys = Object.keys(body);
  if (keys.length === 0) {
    return { valid: false, error: 'Request body cannot be empty' };
  }

  const protectedFields = ['id', 'caseId', 'createdBy', 'createdAt', 'updatedAt', 'status'];
  for (const key of keys) {
    if (protectedFields.includes(key)) {
      return { valid: false, error: `Field '${key}' is protected and cannot be modified` };
    }
  }

  const allowedUpdateFields = ['patientId', 'notes'];
  for (const key of keys) {
    if (!allowedUpdateFields.includes(key)) {
      return { valid: false, error: `Field '${key}' is not allowed for update. Allowed fields: ${allowedUpdateFields.join(', ')}` };
    }
  }

  if (body.patientId !== undefined) {
    if (typeof body.patientId !== 'string' || body.patientId.trim().length === 0) {
      return { valid: false, error: 'patientId must be a non-empty string' };
    }
  }

  if (body.notes !== undefined && body.notes !== null) {
    if (typeof body.notes !== 'string') {
      return { valid: false, error: 'notes must be a string or null' };
    }
  }

  return { valid: true };
};

/**
 * Validate AI result ID parameter.
 * Must be a non-empty string starting with 'res_' without forbidden characters.
 *
 * @param {string} id
 * @returns {boolean}
 */
const isValidResultId = (id) => {
  if (!id || typeof id !== 'string') return false;
  const trimmed = id.trim();
  if (trimmed.length === 0) return false;
  if (/[\s/\\<>:;"'|?*]/.test(trimmed)) return false;
  if (!trimmed.startsWith('res_')) return false;
  return true;
};

/**
 * Validate AI inference request ID parameter.
 * Must be a non-empty string starting with 'inf_' without forbidden characters.
 *
 * @param {string} id
 * @returns {boolean}
 */
const isValidInferenceRequestId = (id) => {
  if (!id || typeof id !== 'string') return false;
  const trimmed = id.trim();
  if (trimmed.length === 0) return false;
  if (/[\s/\\<>:;"'|?*]/.test(trimmed)) return false;
  if (!trimmed.startsWith('inf_')) return false;
  return true;
};

module.exports = {
  isValidEmail,
  isValidPassword,
  isValidRole,
  validateRegistrationInput,
  validateLoginInput,
  validateFundusImage,
  isValidCaseId,
  isValidResultId,
  isValidInferenceRequestId,
  validateCreateCaseInput,
  validateUpdateCaseInput,
  ALLOWED_FUNDUS_MIME_TYPES,
  ALLOWED_FUNDUS_EXTENSIONS,
};

