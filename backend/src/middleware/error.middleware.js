/**
 * middleware/error.middleware.js — NETRA-DR Centralised Error Handler
 *
 * Must be registered LAST in the Express middleware chain (after all routes).
 * Catches any error forwarded via next(err) and returns a consistent JSON envelope.
 */

'use strict';

const logger = require('../utils/logger');

/**
 * Express 4-argument error handler.
 * Express identifies it as an error handler because it has exactly 4 params.
 *
 * @param {Error}           err
 * @param {import('express').Request}  req
 * @param {import('express').Response} res
 * @param {import('express').NextFunction} _next  (must be declared even if unused)
 */
const errorHandler = (err, req, res, _next) => {
  const status  = err.status || err.statusCode || 500;
  const message = err.message || 'Internal Server Error';

  // Log the full stack in development; just the message in production
  if (process.env.NODE_ENV !== 'production') {
    logger.error(`[${status}] ${req.method} ${req.originalUrl} — ${message}`, {
      stack: err.stack,
    });
  } else {
    logger.error(`[${status}] ${req.method} ${req.originalUrl} — ${message}`);
  }

  res.status(status).json({
    status:  'error',
    code:    status,
    message,
    // Only expose stack trace in non-production
    ...(process.env.NODE_ENV !== 'production' && { stack: err.stack }),
  });
};

module.exports = { errorHandler };
