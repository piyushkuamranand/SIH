/**
 * config/paths.js — NETRA-DR Project Path Resolution
 *
 * Centralises all filesystem paths used by the backend.
 *
 * IMPORTANT:
 *   - All Python/Flask code lives in ../  (the SIH/ project root).
 *   - This backend must NEVER modify or move files in the Python project.
 *   - Paths that reference the Python project are READ-ONLY from Node's perspective.
 */

'use strict';

const path = require('path');

// Resolve absolute paths relative to this file's location
// backend/src/config/paths.js  →  backend/ is two levels up
const BACKEND_ROOT  = path.resolve(__dirname, '..', '..');
const PROJECT_ROOT  = path.resolve(BACKEND_ROOT, '..');     // SIH/ project root

const paths = {
  // ── Node.js backend ────────────────────────────────────────────────────────
  BACKEND_ROOT,
  STORAGE_ROOT:   path.join(BACKEND_ROOT, 'storage'),
  IMAGES_DIR:     path.join(BACKEND_ROOT, 'storage', 'images'),
  MASKS_DIR:      path.join(BACKEND_ROOT, 'storage', 'masks'),
  HEATMAPS_DIR:   path.join(BACKEND_ROOT, 'storage', 'heatmaps'),
  REPORTS_DIR:    path.join(BACKEND_ROOT, 'storage', 'reports'),

  // ── Python/Flask project (READ-ONLY references — never write here) ─────────
  PROJECT_ROOT,
  FLASK_APP:      path.join(PROJECT_ROOT, 'app', 'app.py'),
  PIPELINE_DIR:   path.join(PROJECT_ROOT, 'pipeline'),
  MODELS_DIR:     path.join(PROJECT_ROOT, 'models'),
  CONFIGS_DIR:    path.join(PROJECT_ROOT, 'configs'),
  DEMO_DATA_DIR:  path.join(PROJECT_ROOT, 'data', 'demo'),
};

module.exports = paths;
