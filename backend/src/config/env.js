/**
 * config/env.js — NETRA-DR Environment Configuration
 *
 * Single source of truth for all environment-derived settings.
 * All process.env reads happen here; the rest of the app imports from this file.
 */

'use strict';

const env = {
  NODE_ENV: process.env.NODE_ENV || 'development',
  HOST:     process.env.HOST     || '127.0.0.1',
  PORT:     parseInt(process.env.PORT || '3000', 10),

  // Python / Flask AI service (existing — do not modify that service)
  FLASK_HOST: process.env.FLASK_HOST || '127.0.0.1',
  FLASK_PORT: parseInt(process.env.FLASK_PORT || '5000', 10),

  // Storage
  STORAGE_ROOT: process.env.STORAGE_ROOT || 'storage',

  // Logging
  LOG_LEVEL: process.env.LOG_LEVEL || 'info',

  // JWT Authentication
  JWT_SECRET: process.env.JWT_SECRET || 'netra-dr-development-jwt-secret-key-32chars',
  JWT_EXPIRES_IN: process.env.JWT_EXPIRES_IN || '8h',
};

// Derived convenience helpers
env.FLASK_BASE_URL = `http://${env.FLASK_HOST}:${env.FLASK_PORT}`;
env.IS_PRODUCTION  = env.NODE_ENV === 'production';
env.IS_DEVELOPMENT = env.NODE_ENV === 'development';

module.exports = env;
