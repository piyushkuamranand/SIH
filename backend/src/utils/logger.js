/**
 * utils/logger.js — NETRA-DR Winston Logger
 *
 * Provides a shared logger instance used across the entire backend.
 * Console transport in development; file transport in production.
 */

'use strict';

const { createLogger, format, transports } = require('winston');

const { combine, timestamp, colorize, printf, json } = format;

const isDev = (process.env.NODE_ENV || 'development') === 'development';

// Human-readable format for development
const devFormat = combine(
  colorize(),
  timestamp({ format: 'HH:mm:ss' }),
  printf(({ level, message, timestamp: ts, ...meta }) => {
    const metaStr = Object.keys(meta).length ? ` ${JSON.stringify(meta)}` : '';
    return `${ts} [${level}] ${message}${metaStr}`;
  }),
);

// JSON format for production (machine-parseable)
const prodFormat = combine(timestamp(), json());

const logger = createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: isDev ? devFormat : prodFormat,
  transports: [
    new transports.Console(),
  ],
});

module.exports = logger;
