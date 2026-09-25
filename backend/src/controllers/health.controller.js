/**
 * controllers/health.controller.js — NETRA-DR Health Check Controller
 *
 * Handles GET /api/health.
 * Returns a JSON payload with:
 *   - status:      "ok"
 *   - service:     service name
 *   - version:     from package.json
 *   - environment: NODE_ENV
 *   - uptime:      process uptime in seconds
 *   - timestamp:   ISO 8601 UTC
 *
 * Flask / AI pipeline status is NOT checked here yet — that will be added
 * when the Flask integration task is implemented.
 */

'use strict';

const env     = require('../config/env');
const pkg     = require('../../package.json');

const getHealth = (req, res) => {
  res.status(200).json({
    status:      'ok',
    service:     pkg.name,
    version:     pkg.version,
    environment: env.NODE_ENV,
    uptime_s:    Math.floor(process.uptime()),
    timestamp:   new Date().toISOString(),
    ai_service: {
      note: 'Flask AI pipeline status not yet proxied — add in integration task',
      flask_url: env.FLASK_BASE_URL,
    },
  });
};

module.exports = { getHealth };
