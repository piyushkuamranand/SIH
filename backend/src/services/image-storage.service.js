/**
 * services/image-storage.service.js — NETRA-DR Persistent Image Storage & File Management
 *
 * Implements the Image Storage & File Management abstraction layer (Module 5):
 *   - Local filesystem persistence organized by screening case:
 *       storage/
 *       └── images/
 *           └── <caseId>/
 *               └── <imageId>.<extension>
 *   - Server-generated safe unique filenames (UUID-based, never uses client filename)
 *   - Path traversal prevention across caseId, imageId, originalName, and storage paths
 *   - Case-level duplicate upload protection (prevents silent overwrite)
 *   - Safe lifecycle and failure cleanup (automatic rollback on failure)
 *   - Abstraction interface: saveImage(), deleteImage(), imageExists(), getImageStats(), getImagePath()
 *   - Pluggable design ready for future adapters (GridFS, Cloud Object Storage)
 */

'use strict';

const path   = require('path');
const fs     = require('fs');
const crypto = require('crypto');
const paths  = require('../config/paths');
const { ensureDir, safeUnlink, getFileStats } = require('../utils/file.utils');
const { isValidCaseId, ALLOWED_FUNDUS_EXTENSIONS, ALLOWED_FUNDUS_MIME_TYPES } = require('../utils/validation');

/**
 * Validates that candidatePath resolves strictly within baseDir.
 * Protects against ../, ..\, Windows drive injection, UNC paths, and encoded traversals.
 *
 * @param {string} candidatePath
 * @param {string} baseDir
 * @returns {string} Fully resolved safe absolute path
 * @throws {Error} If path traversal or illegal characters are detected
 */
const assertSafePath = (candidatePath, baseDir) => {
  if (!candidatePath || typeof candidatePath !== 'string') {
    const err = new Error('Invalid path: path must be a non-empty string');
    err.status = 400;
    err.code = 'ERR_INVALID_PATH';
    throw err;
  }

  // Reject null bytes, URL-encoded traversals, and raw traversal sequences
  if (
    candidatePath.includes('\0') ||
    /%2e|%2f|%5c|%00/i.test(candidatePath) ||
    candidatePath.includes('..')
  ) {
    const err = new Error(`Path traversal attempt detected in path: '${candidatePath}'`);
    err.status = 400;
    err.code = 'ERR_PATH_TRAVERSAL';
    throw err;
  }

  const resolvedBase = path.resolve(baseDir);
  const resolvedPath = path.resolve(baseDir, candidatePath);

  if (resolvedPath !== resolvedBase && !resolvedPath.startsWith(resolvedBase + path.sep)) {
    const err = new Error(`Path traversal detected: path '${candidatePath}' escapes storage root`);
    err.status = 400;
    err.code = 'ERR_PATH_TRAVERSAL';
    throw err;
  }

  return resolvedPath;
};

/**
 * Validates that caseId is a valid NETRA-DR case identifier and contains no path traversal.
 *
 * @param {string} caseId
 * @returns {string} Sanitized caseId
 * @throws {Error} If caseId is invalid or malicious
 */
const assertSafeCaseId = (caseId) => {
  if (!caseId || typeof caseId !== 'string') {
    const err = new Error('Invalid caseId: caseId must be a non-empty string');
    err.status = 400;
    err.code = 'ERR_INVALID_CASE_ID';
    throw err;
  }

  const trimmed = caseId.trim();

  // Check for traversal or path separators
  if (
    trimmed.includes('..') ||
    trimmed.includes('/') ||
    trimmed.includes('\\') ||
    trimmed.includes(':') ||
    trimmed.includes('\0') ||
    /%2e|%2f|%5c|%00/i.test(trimmed)
  ) {
    const err = new Error(`Path traversal attempt detected in caseId: '${caseId}'`);
    err.status = 400;
    err.code = 'ERR_PATH_TRAVERSAL';
    throw err;
  }

  if (!isValidCaseId(trimmed)) {
    const err = new Error(`Invalid case identifier format: '${caseId}'. Must begin with 'case_'`);
    err.status = 400;
    err.code = 'ERR_INVALID_CASE_ID';
    throw err;
  }

  return trimmed;
};

/**
 * Validates that imageId is a valid server-generated identifier.
 *
 * @param {string} imageId
 * @returns {string} Sanitized imageId
 * @throws {Error} If imageId is invalid or malicious
 */
const assertSafeImageId = (imageId) => {
  if (!imageId || typeof imageId !== 'string') {
    const err = new Error('Invalid imageId: imageId must be a non-empty string');
    err.status = 400;
    err.code = 'ERR_INVALID_IMAGE_ID';
    throw err;
  }

  const trimmed = imageId.trim();

  if (
    trimmed.includes('..') ||
    trimmed.includes('/') ||
    trimmed.includes('\\') ||
    trimmed.includes(':') ||
    trimmed.includes('\0') ||
    /%2e|%2f|%5c|%00/i.test(trimmed)
  ) {
    const err = new Error(`Path traversal attempt detected in imageId: '${imageId}'`);
    err.status = 400;
    err.code = 'ERR_PATH_TRAVERSAL';
    throw err;
  }

  // Must match img_<uuid> or safe alphanumeric identifier
  if (!/^img_[0-9a-fA-F-]{1,64}$/.test(trimmed)) {
    const err = new Error(`Invalid imageId format: '${imageId}'. Must begin with 'img_' followed by alphanumeric/hyphen characters`);
    err.status = 400;
    err.code = 'ERR_INVALID_IMAGE_ID';
    throw err;
  }

  return trimmed;
};

/**
 * Normalizes and validates the file extension.
 *
 * @param {string} filenameOrExt
 * @returns {string} Allowed extension (.jpg, .jpeg, .png)
 * @throws {Error} If extension is unsupported
 */
const validateFileExtension = (filenameOrExt) => {
  let ext = path.extname(filenameOrExt || '').toLowerCase();
  if (!ext && typeof filenameOrExt === 'string' && filenameOrExt.startsWith('.')) {
    ext = filenameOrExt.toLowerCase();
  }

  if (!ALLOWED_FUNDUS_EXTENSIONS.includes(ext)) {
    const err = new Error(
      `Unsupported file extension: '${ext || 'none'}'. Only ${ALLOWED_FUNDUS_EXTENSIONS.join(', ')} are supported`
    );
    err.status = 400;
    err.code = 'ERR_UNSUPPORTED_EXTENSION';
    throw err;
  }

  return ext;
};

const ImageStorageService = {
  /**
   * Save an uploaded image into persistent case-organized storage:
   *   storage/images/<caseId>/<imageId>.<extension>
   *
   * Accepts either:
   *   - A Multer file object: { path, originalname, mimetype, size, buffer }
   *   - An options object: { buffer, sourcePath, originalName, mimeType, sizeBytes, caseId, uploadedBy, imageId }
   *
   * @param {object} fileOrInput
   * @param {object} [options={}]
   * @returns {Promise<object>} Stored image metadata
   */
  async saveImage(fileOrInput, options = {}) {
    if (!fileOrInput || typeof fileOrInput !== 'object') {
      const err = new Error('No image file or input provided for storage');
      err.status = 400;
      throw err;
    }

    // Merge options
    const caseId       = options.caseId || fileOrInput.caseId;
    const uploadedBy   = options.uploadedBy || fileOrInput.uploadedBy;
    const originalName = options.originalName || fileOrInput.originalname || fileOrInput.originalName || 'fundus.jpg';
    const mimeType     = (options.mimeType || fileOrInput.mimetype || fileOrInput.mimeType || '').toLowerCase();
    const sourcePath   = fileOrInput.path || options.sourcePath;
    const buffer       = fileOrInput.buffer || options.buffer;
    const explicitId   = options.imageId || fileOrInput.imageId;

    // 1. Validate caseId and prevent traversal
    const safeCaseId = assertSafeCaseId(caseId);

    // 2. Validate user identity
    if (!uploadedBy || typeof uploadedBy !== 'string' || uploadedBy.trim().length === 0) {
      const err = new Error('User context (uploadedBy) is required for image storage');
      err.status = 401;
      throw err;
    }

    // 3. Validate MIME type
    if (!ALLOWED_FUNDUS_MIME_TYPES.includes(mimeType)) {
      const err = new Error(
        `Unsupported MIME type: '${mimeType}'. Only JPEG and PNG image files are accepted`
      );
      err.status = 400;
      err.code = 'ERR_UNSUPPORTED_MIME';
      throw err;
    }

    // 4. Validate extension
    const ext = validateFileExtension(originalName);

    // 5. Generate safe server-controlled image ID and filename
    const imageId = explicitId ? assertSafeImageId(explicitId) : `img_${crypto.randomUUID()}`;
    const storedFilename = `${imageId}${ext}`;

    // 6. Resolve destination directory: storage/images/<caseId>/
    const targetDir = assertSafePath(safeCaseId, paths.IMAGES_DIR);
    ensureDir(targetDir);

    // 7. Prevent silent duplicate overwrite for this case
    if (!options.allowOverwrite) {
      const existingEntries = fs.readdirSync(targetDir).filter(f => !f.startsWith('.'));
      if (existingEntries.length > 0) {
        const err = new Error(`Screening case ${safeCaseId} already has a stored fundus image. Re-upload or overwrite is not permitted.`);
        err.status = 409;
        err.statusCode = 409;
        err.code = 'ERR_IMAGE_ALREADY_EXISTS';
        throw err;
      }
    }

    // 8. Resolve destination file path: storage/images/<caseId>/<storedFilename>
    const targetFilePath = path.join(targetDir, storedFilename);
    assertSafePath(targetFilePath, targetDir);

    let createdFilePath = null;
    try {
      if (buffer && Buffer.isBuffer(buffer)) {
        if (buffer.length === 0) {
          const err = new Error('Uploaded file buffer is empty (0 bytes)');
          err.status = 400;
          throw err;
        }
        fs.writeFileSync(targetFilePath, buffer);
        createdFilePath = targetFilePath;
      } else if (sourcePath && typeof sourcePath === 'string') {
        if (!fs.existsSync(sourcePath)) {
          const err = new Error(`Source upload file not found: ${sourcePath}`);
          err.status = 400;
          throw err;
        }
        const srcStat = fs.statSync(sourcePath);
        if (srcStat.size === 0) {
          const err = new Error('Uploaded file is empty (0 bytes)');
          err.status = 400;
          throw err;
        }

        // Move source to target path (cross-device safe)
        try {
          fs.renameSync(sourcePath, targetFilePath);
        } catch (renameErr) {
          if (renameErr.code === 'EXDEV') {
            fs.copyFileSync(sourcePath, targetFilePath);
            safeUnlink(sourcePath);
          } else {
            throw renameErr;
          }
        }
        createdFilePath = targetFilePath;
      } else {
        const err = new Error('No valid file source (buffer or sourcePath) provided for storage');
        err.status = 400;
        throw err;
      }

      // Verify written file
      const finalStat = fs.statSync(targetFilePath);
      if (finalStat.size === 0) {
        throw new Error('Stored file is empty (0 bytes)');
      }

      const uploadedAt = new Date().toISOString();

      return {
        imageId,
        caseId:         safeCaseId,
        originalName:   path.basename(originalName),
        storedFilename,
        mimeType,
        extension:      ext,
        sizeBytes:      finalStat.size,
        uploadedBy:     uploadedBy.trim(),
        uploadedAt,
        storagePath:    targetFilePath, // for internal service/model use only
      };
    } catch (writeErr) {
      if (createdFilePath) {
        safeUnlink(createdFilePath);
      }
      // Clean up empty directory if needed
      try {
        const remaining = fs.readdirSync(targetDir).filter(f => !f.startsWith('.'));
        if (remaining.length === 0) {
          safeUnlink(targetDir);
        }
      } catch (_e) {}
      throw writeErr;
    }
  },

  /**
   * Delete an image from storage.
   * Safe and idempotent: returns false if the file/case does not exist.
   * Cleans up empty case directory upon file deletion.
   *
   * @param {string} caseId
   * @param {string} [imageId] Optional imageId. If omitted, deletes all images for the case.
   * @returns {Promise<boolean>} True if file was deleted, false if not found
   */
  async deleteImage(caseId, imageId) {
    const safeCaseId = assertSafeCaseId(caseId);
    const caseDir = assertSafePath(safeCaseId, paths.IMAGES_DIR);

    if (!fs.existsSync(caseDir)) {
      return false;
    }

    if (imageId) {
      const safeImgId = assertSafeImageId(imageId);
      const files = fs.readdirSync(caseDir);
      const targetFile = files.find(f => f.startsWith(safeImgId));

      if (!targetFile) {
        return false;
      }

      const targetPath = path.join(caseDir, targetFile);
      assertSafePath(targetPath, caseDir);
      safeUnlink(targetPath);
    } else {
      // Delete all files in case directory
      const files = fs.readdirSync(caseDir);
      for (const file of files) {
        if (!file.startsWith('.')) {
          safeUnlink(path.join(caseDir, file));
        }
      }
    }

    // Clean up empty case directory
    try {
      const remaining = fs.readdirSync(caseDir).filter(f => !f.startsWith('.'));
      if (remaining.length === 0) {
        safeUnlink(caseDir);
      }
    } catch (_e) {}

    return true;
  },

  /**
   * Check if a stored image exists for a given case and imageId.
   *
   * @param {string} caseId
   * @param {string} imageId
   * @returns {Promise<boolean>}
   */
  async imageExists(caseId, imageId) {
    try {
      const safeCaseId = assertSafeCaseId(caseId);
      const safeImgId  = assertSafeImageId(imageId);
      const caseDir    = assertSafePath(safeCaseId, paths.IMAGES_DIR);

      if (!fs.existsSync(caseDir)) return false;

      const files = fs.readdirSync(caseDir);
      return files.some(f => f.startsWith(safeImgId));
    } catch (_err) {
      return false;
    }
  },

  /**
   * Retrieve file stats for a stored image.
   *
   * @param {string} caseId
   * @param {string} imageId
   * @returns {Promise<fs.Stats|null>}
   */
  async getImageStats(caseId, imageId) {
    try {
      const safeCaseId = assertSafeCaseId(caseId);
      const safeImgId  = assertSafeImageId(imageId);
      const caseDir    = assertSafePath(safeCaseId, paths.IMAGES_DIR);

      if (!fs.existsSync(caseDir)) return null;

      const files = fs.readdirSync(caseDir);
      const targetFile = files.find(f => f.startsWith(safeImgId));
      if (!targetFile) return null;

      const targetPath = path.join(caseDir, targetFile);
      assertSafePath(targetPath, caseDir);

      return getFileStats(targetPath);
    } catch (_err) {
      return null;
    }
  },

  /**
   * Get safe absolute file path for a stored image (internal retrieval foundation).
   *
   * @param {string} caseId
   * @param {string} imageId
   * @returns {Promise<string|null>} Absolute filesystem path or null if not found
   * @throws {Error} If path traversal is attempted
   */
  async getImagePath(caseId, imageId) {
    const safeCaseId = assertSafeCaseId(caseId);
    const safeImgId  = assertSafeImageId(imageId);
    const caseDir    = assertSafePath(safeCaseId, paths.IMAGES_DIR);

    if (!fs.existsSync(caseDir)) return null;

    const files = fs.readdirSync(caseDir);
    const targetFile = files.find(f => f.startsWith(safeImgId));
    if (!targetFile) return null;

    const targetPath = path.join(caseDir, targetFile);
    assertSafePath(targetPath, caseDir);

    return fs.existsSync(targetPath) ? targetPath : null;
  },

  /**
   * List all stored image files for a case.
   *
   * @param {string} caseId
   * @returns {Promise<Array<string>>} List of stored filenames
   */
  async listImagesByCase(caseId) {
    const safeCaseId = assertSafeCaseId(caseId);
    const caseDir    = assertSafePath(safeCaseId, paths.IMAGES_DIR);

    if (!fs.existsSync(caseDir)) return [];

    const files = fs.readdirSync(caseDir);
    return files.filter(f => !f.startsWith('.'));
  },

  // Export helpers for testing and security validation
  assertSafePath,
  assertSafeCaseId,
  assertSafeImageId,
  validateFileExtension,
};

module.exports = ImageStorageService;
