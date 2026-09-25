/**
 * config/roles.js — NETRA-DR Centralized Role Definitions
 *
 * Single source of truth for all role strings used across the application.
 * Import this file wherever roles must be referenced — never hardcode
 * role strings in routes, middleware, or controllers directly.
 *
 * Roles:
 *   TECHNICIAN  — field technician who operates the screening device
 *   DOCTOR      — ophthalmologist who reviews AI-generated screening results
 *   ADMIN       — system administrator with full application access
 *
 * Permission model (high-level; enforced at route / controller level):
 *
 *   TECHNICIAN can:
 *     - create screening cases
 *     - view cases they are authorized to access
 *     - upload fundus images
 *     - submit screening jobs
 *     - view pipeline processing status
 *     - view AI results for authorized cases
 *
 *   TECHNICIAN cannot:
 *     - perform or update doctor review
 *     - administer users
 *     - access administrative routes
 *     - modify another user's role
 *
 *   DOCTOR can:
 *     - view screening cases
 *     - view AI results and evidence artifacts
 *     - perform and update doctor review
 *     - generate and view clinical reports
 *
 *   DOCTOR cannot:
 *     - administer users
 *     - modify system configuration
 *     - modify another user's role
 *
 *   ADMIN can:
 *     - access administrative functions
 *     - manage users (when those routes are implemented)
 *     - view all application records
 *     - access audit functionality (when implemented)
 *
 * NOTE: Role-level authorization is a coarse guard. Per-resource ownership
 * (e.g. "can this technician access THIS case?") must be enforced inside
 * the relevant controller, not here.
 */

'use strict';

const ROLES = Object.freeze({
  TECHNICIAN: 'technician',
  DOCTOR:     'doctor',
  ADMIN:      'admin',
});

const VALID_ROLES = Object.freeze(Object.values(ROLES));

module.exports = { ROLES, VALID_ROLES };
