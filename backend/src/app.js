/**
 * app.js — NETRA-DR Express Application Factory
 *
 * Creates and configures the Express application instance.
 * server.js imports this and binds it to a port.
 *
 * Middleware stack (in order):
 *   1. HTTP request logging (morgan)
 *   2. CORS
 *   3. JSON + URL-encoded body parsing
 *   4. Application routes
 *   5. 404 catch-all
 *   6. Centralised error handler
 */

'use strict';

const express = require('express');
const cors    = require('cors');
const morgan  = require('morgan');

const { errorHandler } = require('./middleware/error.middleware');

const healthRouter     = require('./routes/health.routes');
const authRouter       = require('./routes/auth.routes');
const screeningRouter  = require('./routes/screening.routes');
const casesRouter      = require('./routes/cases.routes');
const reportsRouter    = require('./routes/reports.routes');
const simulationRouter = require('./routes/simulation.routes');

const app = express();

// ---------------------------------------------------------------------------
// Request logging
// ---------------------------------------------------------------------------
app.use(morgan('combined'));

// ---------------------------------------------------------------------------
// CORS — allow all origins in development; restrict in production via config
// ---------------------------------------------------------------------------
app.use(cors());

// ---------------------------------------------------------------------------
// Body parsing
// ---------------------------------------------------------------------------
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------
app.use('/api/health',     healthRouter);
app.use('/api/auth',       authRouter);
app.use('/api/screening',  screeningRouter);
app.use('/api/cases',      casesRouter);
app.use('/api/reports',    reportsRouter);
app.use('/api/simulation', simulationRouter);

// ---------------------------------------------------------------------------
// 404 catch-all — must come after all routes
// ---------------------------------------------------------------------------
app.use((req, res, _next) => {
  res.status(404).json({
    status:  'error',
    code:    404,
    message: `Route not found: ${req.method} ${req.originalUrl}`,
  });
});

// ---------------------------------------------------------------------------
// Centralised error handler — must be last and have 4 parameters
// ---------------------------------------------------------------------------
app.use(errorHandler);

module.exports = app;
