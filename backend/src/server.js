/**
 * server.js — NETRA-DR HTTP Server Entry Point
 *
 * Loads environment variables, imports the Express app,
 * and binds it to the configured port.
 *
 * Usage:
 *   node src/server.js        (production)
 *   npm run dev               (development — nodemon)
 */

'use strict';

require('dotenv').config();

const app    = require('./app');
const env    = require('./config/env');
const logger = require('./utils/logger');

const PORT = env.PORT;
const HOST = env.HOST;

// ---------------------------------------------------------------------------
// Start HTTP server
// ---------------------------------------------------------------------------
const server = app.listen(PORT, HOST, () => {
  logger.info(`NETRA-DR backend running  →  http://${HOST}:${PORT}`);
  logger.info(`Environment : ${env.NODE_ENV}`);
  logger.info(`Health check: http://${HOST}:${PORT}/api/health`);
});

// ---------------------------------------------------------------------------
// Graceful shutdown
// ---------------------------------------------------------------------------
const shutdown = (signal) => {
  logger.info(`${signal} received — shutting down gracefully…`);
  server.close(() => {
    logger.info('HTTP server closed.');
    process.exit(0);
  });
  // Force exit if graceful close takes too long
  setTimeout(() => {
    logger.error('Could not close connections in time — forcing exit.');
    process.exit(1);
  }, 10_000);
};

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT',  () => shutdown('SIGINT'));

// ---------------------------------------------------------------------------
// Unhandled rejection / exception guards
// ---------------------------------------------------------------------------
process.on('unhandledRejection', (reason) => {
  logger.error('Unhandled promise rejection:', reason);
});

process.on('uncaughtException', (err) => {
  logger.error('Uncaught exception:', err);
  process.exit(1);
});

module.exports = server;
