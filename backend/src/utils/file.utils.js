/**
 * utils/file.utils.js — NETRA-DR File System Utilities (Placeholder)
 *
 * Will provide helpers for file creation, deletion, and path resolution
 * within the backend storage/ directory.
 * Not implemented yet — stub only.
 */

'use strict';

const path = require('path');
const fs   = require('fs');

/**
 * Ensure a directory exists, creating it recursively if necessary.
 * @param {string} dirPath  Absolute path to directory
 */
const ensureDir = (dirPath) => {
  fs.mkdirSync(dirPath, { recursive: true });
};

/**
 * Delete a file safely (no error if it doesn't exist).
 * @param {string} filePath  Absolute path to file
 */
const safeUnlink = (filePath) => {
  try {
    fs.unlinkSync(filePath);
  } catch (_err) {
    // ignore ENOENT
  }
};

module.exports = { ensureDir, safeUnlink };
