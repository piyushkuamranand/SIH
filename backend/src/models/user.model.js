/**
 * models/user.model.js — NETRA-DR User Model & Data Access Abstraction
 *
 * Implements the user data model and repository abstraction for authentication.
 * Designed so that the database implementation (e.g. MongoDB/Mongoose) can later
 * be connected cleanly without modifying controllers or middleware.
 *
 * Fields supported:
 *   - id:           unique user ID string
 *   - name:         user's full name
 *   - email:        normalized unique email address (lowercase, trimmed)
 *   - passwordHash: bcrypt-hashed password (NEVER plaintext)
 *   - role:         technician | doctor | admin
 *   - createdAt:    ISO 8601 UTC timestamp string
 *   - updatedAt:    ISO 8601 UTC timestamp string
 */

'use strict';

const crypto = require('crypto');

// Role constants sourced from the centralized definition — never duplicated
const { ROLES, VALID_ROLES } = require('../config/roles');

// In-memory data store for the authentication abstraction
const usersById = new Map();
const usersByEmail = new Map();

const UserModel = {
  ROLES,
  VALID_ROLES,

  /**
   * Return a safe representation of a user object.
   * NEVER returns password or passwordHash.
   *
   * @param {object} user
   * @returns {object|null}
   */
  toSafeUser(user) {
    if (!user) return null;
    const { passwordHash: _hash, ...safeUser } = user;
    return safeUser;
  },

  /**
   * Find a user by email address (case-insensitive, trimmed).
   *
   * @param {string} email
   * @returns {Promise<object|null>}
   */
  async findByEmail(email) {
    if (!email || typeof email !== 'string') return null;
    const normalized = email.trim().toLowerCase();
    const user = usersByEmail.get(normalized);
    return user ? { ...user } : null;
  },

  /**
   * Find a user by unique ID.
   *
   * @param {string} id
   * @returns {Promise<object|null>}
   */
  async findById(id) {
    if (!id || typeof id !== 'string') return null;
    const user = usersById.get(id);
    return user ? { ...user } : null;
  },

  /**
   * Create and persist a new user record.
   *
   * @param {object} data
   * @param {string} data.name
   * @param {string} data.email
   * @param {string} data.passwordHash
   * @param {string} data.role
   * @returns {Promise<object>} Created user record (including internal fields)
   */
  async create({ name, email, passwordHash, role }) {
    const normalizedEmail = email.trim().toLowerCase();
    const now = new Date().toISOString();
    const id = `usr_${crypto.randomUUID()}`;

    const record = {
      id,
      name: name.trim(),
      email: normalizedEmail,
      passwordHash,
      role: role.toLowerCase(),
      createdAt: now,
      updatedAt: now,
    };

    usersById.set(id, record);
    usersByEmail.set(normalizedEmail, record);

    return { ...record };
  },

  /**
   * Return all users as safe records.
   *
   * @returns {Promise<Array<object>>}
   */
  async findAll() {
    return Array.from(usersById.values()).map(u => UserModel.toSafeUser(u));
  },

  /**
   * Clear all records (useful for testing).
   */
  async clear() {
    usersById.clear();
    usersByEmail.clear();
  },
};

module.exports = UserModel;
