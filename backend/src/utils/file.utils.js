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
 * Delete a file or directory safely (no error if it doesn't exist).
 * Recursively deletes directories if a directory path is passed.
 * @param {string} targetPath  Absolute path to file or directory
 */
const safeUnlink = (targetPath) => {
  try {
    if (!targetPath || typeof targetPath !== 'string') return;
    if (fs.existsSync(targetPath)) {
      const stat = fs.statSync(targetPath);
      if (stat.isDirectory()) {
        fs.rmSync(targetPath, { recursive: true, force: true });
      } else {
        fs.unlinkSync(targetPath);
      }
    }
  } catch (_err) {
    // ignore ENOENT and deletion errors
  }
};

/**
 * Check if a file exists synchronously.
 * @param {string} filePath  Absolute path to file
 * @returns {boolean}
 */
const fileExists = (filePath) => {
  try {
    return fs.existsSync(filePath);
  } catch (_err) {
    return false;
  }
};

/**
 * Get file stats safely.
 * @param {string} filePath  Absolute path to file
 * @returns {fs.Stats|null}
 */
const getFileStats = (filePath) => {
  try {
    return fs.statSync(filePath);
  } catch (_err) {
    return null;
  }
};

module.exports = { ensureDir, safeUnlink, fileExists, getFileStats };
