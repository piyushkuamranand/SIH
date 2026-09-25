/**
 * controllers/cases.controller.js — NETRA-DR Cases Controller (Placeholder)
 *
 * All handlers are stubs returning 501 Not Implemented.
 * Business logic (DB CRUD) will be added in the database integration task.
 */

'use strict';

const stub = (_req, res) => {
  res.status(501).json({
    status:  'not_implemented',
    message: 'Case management is not implemented yet.',
  });
};

module.exports = { stub };
