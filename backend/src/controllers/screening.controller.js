/**
 * controllers/screening.controller.js — NETRA-DR Screening Controller (Placeholder)
 *
 * All handlers are stubs returning 501 Not Implemented.
 * Business logic (Flask proxy, image pipeline) will be added in the
 * Flask integration task.
 */

'use strict';

const stub = (_req, res) => {
  res.status(501).json({
    status:  'not_implemented',
    message: 'Screening pipeline integration is not implemented yet.',
  });
};

module.exports = { stub };
