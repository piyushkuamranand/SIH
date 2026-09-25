/**
 * controllers/simulation.controller.js — NETRA-DR Simulation Controller (Placeholder)
 *
 * All handlers are stubs returning 501 Not Implemented.
 * Integration with MATLAB sweep_ratio.m results will be added in the
 * simulation task. The MATLAB script itself is at matlab/sweep_ratio.m
 * in the Python project root and must NOT be modified by this backend.
 */

'use strict';

const stub = (_req, res) => {
  res.status(501).json({
    status:  'not_implemented',
    message: 'Simulink workflow simulation integration is not implemented yet.',
  });
};

module.exports = { stub };
