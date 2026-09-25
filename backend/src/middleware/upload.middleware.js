/**
 * middleware/upload.middleware.js — NETRA-DR Multer File Upload Middleware
 *
 * Configures multer for fundus image uploads.
 * Accepted MIME types: image/jpeg, image/png
 * Max file size: 32 MB (matches Flask MAX_CONTENT_LENGTH)
 *
 * Business logic (virus scan, metadata extraction, etc.) is NOT added yet.
 */

'use strict';

const path   = require('path');
const multer = require('multer');
const paths  = require('../config/paths');

// ---------------------------------------------------------------------------
// Storage — save to backend/storage/images/<timestamp>-<originalname>
// ---------------------------------------------------------------------------
const storage = multer.diskStorage({
  destination: (_req, _file, cb) => {
    cb(null, paths.IMAGES_DIR);
  },
  filename: (_req, file, cb) => {
    const unique = `${Date.now()}-${Math.round(Math.random() * 1e6)}`;
    const ext    = path.extname(file.originalname).toLowerCase();
    cb(null, `${unique}${ext}`);
  },
});

// ---------------------------------------------------------------------------
// File filter — only JPEG and PNG allowed
// ---------------------------------------------------------------------------
const fileFilter = (_req, file, cb) => {
  const ALLOWED_TYPES = ['image/jpeg', 'image/png'];
  if (ALLOWED_TYPES.includes(file.mimetype)) {
    cb(null, true);
  } else {
    const err = new Error(
      `Unsupported file type: ${file.mimetype}. Only JPEG and PNG are accepted.`,
    );
    err.status = 415;
    cb(err, false);
  }
};

// ---------------------------------------------------------------------------
// Multer instance
// ---------------------------------------------------------------------------
const upload = multer({
  storage,
  fileFilter,
  limits: {
    fileSize: 32 * 1024 * 1024, // 32 MB
    files:    1,                  // single image per request
  },
});

// Named export: use as  upload.single('image')  in routes
module.exports = { upload };
