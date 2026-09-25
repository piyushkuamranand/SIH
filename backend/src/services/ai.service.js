/**
 * services/ai.service.js — NETRA-DR AI Inference Orchestration Service
 *
 * Implements the AI inference orchestration layer (Module 6):
 *   - Locates securely stored fundus images via ImageStorageService
 *   - Never exposes internal filesystem paths to public clients
 *   - Communicates with Python/Flask AI service via HTTP (multipart/form-data)
 *   - Configurable AI service URL and timeout
 *   - Controlled error handling: 503 for service unavailable, 504 for timeout,
 *     502 for malformed/upstream errors
 *   - Generates unique inference request IDs for end-to-end traceability
 *   - Preserves semantic AI service response without fabricating medical outputs
 */

'use strict';

const fs     = require('fs');
const path   = require('path');
const env    = require('../config/env');
const ImageStorageService = require('./image-storage.service');
const logger = require('../utils/logger');

/**
 * Custom Error: AI service error base class
 */
class AIServiceError extends Error {
  constructor(message, statusCode = 502, code = 'AI_SERVICE_ERROR', details = null) {
    super(message);
    this.name = 'AIServiceError';
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
  }
}

/**
 * Custom Error: AI service unavailable (connection refused, network error)
 */
class AIServiceUnavailableError extends AIServiceError {
  constructor(message = 'AI inference service is currently unavailable', details = null) {
    super(message, 503, 'AI_SERVICE_UNAVAILABLE', details);
    this.name = 'AIServiceUnavailableError';
  }
}

/**
 * Custom Error: AI service timeout (gateway timeout)
 */
class AIServiceTimeoutError extends AIServiceError {
  constructor(message = 'AI inference service request timed out', details = null) {
    super(message, 504, 'AI_SERVICE_TIMEOUT', details);
    this.name = 'AIServiceTimeoutError';
  }
}

/**
 * Custom Error: AI service malformed / unparseable response
 */
class AIServiceMalformedResponseError extends AIServiceError {
  constructor(message = 'AI inference service returned a malformed response', details = null) {
    super(message, 502, 'AI_SERVICE_MALFORMED_RESPONSE', details);
    this.name = 'AIServiceMalformedResponseError';
  }
}

const AIService = {
  // Error classes exposed for controller and testing
  AIServiceError,
  AIServiceUnavailableError,
  AIServiceTimeoutError,
  AIServiceMalformedResponseError,

  /**
   * Resolve active AI service base URL.
   * Checks process.env dynamically for test overrides.
   *
   * @returns {string}
   */
  getBaseUrl() {
    return (process.env.AI_SERVICE_URL || env.AI_SERVICE_URL || env.FLASK_BASE_URL || 'http://127.0.0.1:5000').replace(/\/+$/, '');
  },

  /**
   * Resolve active AI service endpoint path.
   *
   * @returns {string}
   */
  getEndpoint() {
    const ep = process.env.AI_SERVICE_ENDPOINT || env.AI_SERVICE_ENDPOINT || '/api/quality';
    return ep.startsWith('/') ? ep : `/${ep}`;
  },

  /**
   * Resolve active AI service timeout in milliseconds.
   *
   * @returns {number}
   */
  getTimeoutMs() {
    const raw = process.env.AI_SERVICE_TIMEOUT_MS || env.AI_SERVICE_TIMEOUT_MS || '60000';
    const parsed = parseInt(raw, 10);
    return isNaN(parsed) || parsed <= 0 ? 60000 : parsed;
  },

  /**
   * Check if Python/Flask AI service is reachable and operational.
   *
   * @returns {Promise<{ operational: boolean, details?: object, error?: string }>}
   */
  async checkHealth() {
    const targetUrl = `${this.getBaseUrl()}/api/status`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    try {
      const res = await fetch(targetUrl, { signal: controller.signal });
      if (!res.ok) {
        return { operational: false, error: `Health check returned HTTP ${res.status}` };
      }
      const data = await res.json();
      return { operational: true, details: data };
    } catch (err) {
      return { operational: false, error: err.message };
    } finally {
      clearTimeout(timeoutId);
    }
  },

  /**
   * Orchestrate AI inference for a screening case.
   *
   * Flow:
   *   1. Resolve securely stored image path via ImageStorageService
   *   2. Validate file presence on disk
   *   3. Read image binary and prepare multipart/form-data
   *   4. Dispatch request to Flask service with configurable timeout
   *   5. Parse structured response and handle errors
   *   6. Return structured result to caller
   *
   * @param {object} params
   * @param {string} params.caseId             - Unique case identifier
   * @param {string} params.imageId            - Stored image identifier
   * @param {string} params.inferenceRequestId - Unique request trace ID
   * @returns {Promise<object>} Structured AI inference result
   */
  async runInference({ caseId, imageId, inferenceRequestId }) {
    if (!caseId || typeof caseId !== 'string') {
      throw new Error('caseId is required for AI inference');
    }
    if (!imageId || typeof imageId !== 'string') {
      throw new Error('imageId is required for AI inference');
    }
    if (!inferenceRequestId || typeof inferenceRequestId !== 'string') {
      throw new Error('inferenceRequestId is required for AI inference tracing');
    }

    // 1. Resolve stored image path via ImageStorageService (server-controlled, path traversal safe)
    const imagePath = await ImageStorageService.getImagePath(caseId, imageId);
    if (!imagePath || !fs.existsSync(imagePath)) {
      const err = new Error(`Stored fundus image file not found on disk for case: ${caseId}, image: ${imageId}`);
      err.statusCode = 404;
      err.code = 'ERR_IMAGE_NOT_FOUND';
      throw err;
    }

    // 2. Read image buffer and prepare multipart payload
    const imageBuffer = fs.readFileSync(imagePath);
    if (imageBuffer.length === 0) {
      const err = new Error(`Stored fundus image file is empty (0 bytes): ${caseId}`);
      err.statusCode = 400;
      err.code = 'ERR_EMPTY_IMAGE';
      throw err;
    }

    const ext = path.extname(imagePath).toLowerCase();
    const mimeType = ext === '.png' ? 'image/png' : 'image/jpeg';
    const filename = path.basename(imagePath);

    const formData = new FormData();
    const blob = new Blob([imageBuffer], { type: mimeType });
    formData.append('image', blob, filename);

    // 3. Build target URL and configure timeout
    const targetUrl = `${this.getBaseUrl()}${this.getEndpoint()}`;
    const timeoutMs = this.getTimeoutMs();

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    logger.info(`[Module 6] Sending image ${imageId} for case ${caseId} to AI service at ${targetUrl} (req: ${inferenceRequestId}, timeout: ${timeoutMs}ms)`);

    let response;
    try {
      response = await fetch(targetUrl, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
        headers: {
          'X-Inference-Request-ID': inferenceRequestId,
        },
      });
    } catch (netErr) {
      clearTimeout(timeoutId);

      // Handle timeout
      if (controller.signal.aborted || netErr.name === 'AbortError') {
        logger.error(`[Module 6] AI inference service timed out after ${timeoutMs}ms for case ${caseId} (req: ${inferenceRequestId})`);
        throw new AIServiceTimeoutError(`AI inference service timed out after ${timeoutMs}ms`, {
          caseId,
          inferenceRequestId,
          timeoutMs,
        });
      }

      // Handle network / connectivity failure (offline, connection refused, DNS failure)
      logger.error(`[Module 6] AI inference service connection failed for case ${caseId}: ${netErr.message} (req: ${inferenceRequestId})`);
      throw new AIServiceUnavailableError('AI inference service is currently unavailable', {
        cause: netErr.message,
        code: netErr.code,
        targetUrl,
      });
    } finally {
      clearTimeout(timeoutId);
    }

    // 4. Read response text
    let rawBodyText = '';
    try {
      rawBodyText = await response.text();
    } catch (readErr) {
      throw new AIServiceError(`Failed to read response from AI service: ${readErr.message}`);
    }

    // 5. Parse JSON response
    let parsedJson = null;
    try {
      parsedJson = JSON.parse(rawBodyText);
    } catch (_jsonErr) {
      logger.error(`[Module 6] AI service returned malformed non-JSON response (HTTP ${response.status}) (req: ${inferenceRequestId})`);
      throw new AIServiceMalformedResponseError('AI inference service returned a malformed response', {
        httpStatus: response.status,
        rawSnippet: rawBodyText.slice(0, 300),
      });
    }

    // 6. Handle HTTP error status codes from Flask
    if (!response.ok) {
      const errorMsg = (parsedJson && (parsedJson.error || parsedJson.message))
        ? (typeof parsedJson.error === 'string' ? parsedJson.error : JSON.stringify(parsedJson.error))
        : `AI service returned error status ${response.status}`;

      logger.warn(`[Module 6] AI service error response HTTP ${response.status} for case ${caseId}: ${errorMsg} (req: ${inferenceRequestId})`);

      if (response.status >= 400 && response.status < 500) {
        throw new AIServiceError(errorMsg, response.status, 'AI_SERVICE_REJECTED', parsedJson);
      }

      throw new AIServiceError(errorMsg, 502, 'AI_SERVICE_EXECUTION_ERROR', parsedJson);
    }

    // 7. Verify JSON structure
    if (!parsedJson || typeof parsedJson !== 'object') {
      throw new AIServiceMalformedResponseError('AI inference service returned invalid data structure');
    }

    logger.info(`[Module 6] AI inference completed successfully for case ${caseId} (req: ${inferenceRequestId})`);

    return {
      inferenceRequestId,
      caseId,
      imageId,
      inference: parsedJson,
    };
  },
};

module.exports = AIService;
