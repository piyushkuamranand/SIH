/**
 * middleware/upload.middleware.js — NETRA-DR Multer File Upload Middleware
 *
 * Configures multer for fundus image uploads (Module 4):
 *   - Destination: backend/storage/images/
 *   - Accepted MIME types: image/jpeg, image/png
 *   - Accepted extensions: .jpg, .jpeg, .png
 *   - Configurable max file size (MAX_IMAGE_UPLOAD_MB, default 32MB)
 *   - Single image upload ('image')
 *   - Returns 400 Bad Request for unsupported file types / extensions
 *   - Returns 413 Payload Too Large for oversized uploads
 */

'use strict';

const path   = require('path');
const multer = require('multer');
const paths  = require('../config/paths');
const env    = require('../config/env');
const { ensureDir } = require('../utils/file.utils');

const ALLOWED_MIME_TYPES = Object.freeze(['image/jpeg', 'image/png']);
const ALLOWED_EXTENSIONS = Object.freeze(['.jpg', '.jpeg', '.png']);

// ---------------------------------------------------------------------------
// Storage — stage in backend/storage/temp/upload_<timestamp>_<random><ext>
// The Image Storage Service moves the file to storage/images/<caseId>/ on persistence.
// ---------------------------------------------------------------------------
const getStagingDir = () => paths.TEMP_DIR || path.join(paths.STORAGE_ROOT, 'temp');

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => {
    const dest = getStagingDir();
    ensureDir(dest);
    cb(null, dest);
  },
  filename: (_req, file, cb) => {
    const unique = `upload_${Date.now()}_${Math.round(Math.random() * 1e8)}`;
    const ext    = path.extname(file.originalname).toLowerCase();
    cb(null, `${unique}${ext}`);
  },
});

// ---------------------------------------------------------------------------
// File filter — only JPEG and PNG allowed (MIME type + extension check)
// ---------------------------------------------------------------------------
const fileFilter = (_req, file, cb) => {
  const mime = (file.mimetype || '').toLowerCase();
  const ext  = path.extname(file.originalname || '').toLowerCase();

  if (!ALLOWED_MIME_TYPES.includes(mime)) {
    const err = new Error(
      `Unsupported file type: '${mime || 'unknown'}'. Only JPEG and PNG image files are accepted.`,
    );
    err.status = 400;
    return cb(err, false);
  }

  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    const err = new Error(
      `Unsupported file extension: '${ext || 'none'}'. Only .jpg, .jpeg, and .png are accepted.`,
    );
    err.status = 400;
    return cb(err, false);
  }

  cb(null, true);
};

// ---------------------------------------------------------------------------
// Multer instance factory
// ---------------------------------------------------------------------------
const getMaxUploadBytes = () => {
  const mb = parseInt(process.env.MAX_IMAGE_UPLOAD_MB || env.MAX_IMAGE_UPLOAD_MB || '32', 10);
  return (isNaN(mb) || mb <= 0 ? 32 : mb) * 1024 * 1024;
};

const createUploadInstance = () => {
  return multer({
    storage,
    fileFilter,
    limits: {
      fileSize: getMaxUploadBytes(),
      files:    1,
    },
  });
};

const upload = createUploadInstance();

/**
 * Express middleware wrapper for single fundus image upload.
 * Intercepts MulterError and fileFilter errors, formatting clean JSON responses.
 *
 * @param {string} [fieldName='image']
 * @returns {import('express').RequestHandler}
 */
const handleImageUpload = (fieldName = 'image') => {
  return (req, res, next) => {
    const maxMb = parseInt(process.env.MAX_IMAGE_UPLOAD_MB || env.MAX_IMAGE_UPLOAD_MB || '32', 10);
    const uploader = multer({
      storage,
      fileFilter,
      limits: {
        fileSize: (isNaN(maxMb) || maxMb <= 0 ? 32 : maxMb) * 1024 * 1024,
        files: 1,
      },
    }).single(fieldName);

    uploader(req, res, (err) => {
      if (err) {
        if (err.code === 'LIMIT_FILE_SIZE' || (err instanceof multer.MulterError && err.code === 'LIMIT_FILE_SIZE')) {
          return res.status(413).json({
            status:  'error',
            code:    413,
            message: `File size exceeds the configured maximum limit of ${maxMb}MB`,
          });
        }
        if (err instanceof multer.MulterError) {
          return res.status(400).json({
            status:  'error',
            code:    400,
            message: `File upload error: ${err.message}`,
          });
        }
        const statusCode = err.status || err.statusCode || 400;
        return res.status(statusCode).json({
          status:  'error',
          code:    statusCode,
          message: err.message,
        });
      }
      next();
    });
  };
};

module.exports = {
  upload,
  handleImageUpload,
  ALLOWED_MIME_TYPES,
  ALLOWED_EXTENSIONS,
};
