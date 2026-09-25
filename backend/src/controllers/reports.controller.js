/**
 * controllers/reports.controller.js — NETRA-DR Reports Controller (Placeholder)
 *
 * All handlers are stubs returning 501 Not Implemented.
 * Business logic (PDF generation) will be added in the report task.
 */

'use strict';

const stub = (_req, res) => {
  res.status(501).json({
    status:  'not_implemented',
    message: 'Report generation is not implemented yet.',
  });
};

module.exports = { stub };
