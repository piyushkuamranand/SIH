/**
 * tests/ai-inference.test.js — NETRA-DR Module 6 AI Inference Orchestration Test Suite
 *
 * Verifies the AI inference orchestration layer:
 *
 * Authentication & Authorization:
 *   1.  Unauthenticated request to POST /api/cases/:id/ai returns 401 Unauthorized.
 *   2.  Malformed/invalid token returns 401 Unauthorized.
 *   3.  Unauthorized role (doctor) returns 403 Forbidden.
 *   4.  Authorized role (technician) can invoke AI inference.
 *   5.  Authorized role (admin) can invoke AI inference.
 *
 * Case & Image Validation:
 *   6.  Invalid case ID format returns 400 Bad Request.
 *   7.  Path traversal attempt in case ID returns 400 Bad Request.
 *   8.  Nonexistent case returns 404 Not Found.
 *   9.  Case without uploaded fundus image returns 400 Bad Request.
 *  10.  Case whose stored image file is missing on disk returns 404 Not Found.
 *
 * AI Service Integration & Error Handling:
 *  11.  Successful inference returns 200 OK with structured AI output and trace ID.
 *  12.  Flask service 4xx error (e.g. 400 bad image) is handled cleanly without crashing.
 *  13.  Flask service 5xx error (e.g. 500 internal error) returns 502 Bad Gateway.
 *  14.  Flask service unavailable (connection refused) returns 503 with AI_SERVICE_UNAVAILABLE.
 *  15.  Flask service timeout returns 504 Gateway Timeout with AI_SERVICE_TIMEOUT.
 *  16.  Flask service malformed/non-JSON response returns 502 with AI_SERVICE_MALFORMED_RESPONSE.
 *
 * Security & Medical Safety:
 *  17.  Client cannot supply arbitrary filesystem path, URL, or model in request body.
 *  18.  Internal filesystem paths are never leaked to API clients.
 *  19.  Inference request ID is generated with 'inf_' and forwarded in request headers.
 *  20.  Real AI output is preserved without synthetic fabrication of predictions.
 */

'use strict';

const { test, describe, before, after, beforeEach } = require('node:test');
const assert = require('node:assert/strict');
const http   = require('http');
const fs     = require('fs');
const path   = require('path');
const app    = require('../src/app');
const UserModel = require('../src/models/user.model');
const CaseModel = require('../src/models/case.model');
const ImageStorageService = require('../src/services/image-storage.service');
const paths  = require('../src/config/paths');
const { ROLES } = require('../src/config/roles');
const { safeUnlink } = require('../src/utils/file.utils');

describe('NETRA-DR Module 6 — AI Inference Orchestration Tests', () => {
  let server;
  let baseUrl;

  // Mock Flask AI service
  let mockFlaskServer;
  let mockFlaskUrl;
  let mockFlaskHandler = null;
  let lastFlaskRequest = null;

  // Tokens
  let technicianToken;
  let technicianUser;
  let doctorToken;
  let doctorUser;
  let adminToken;
  let adminUser;

  // Minimal valid 1x1 JPEG buffer
  const validJpegBuffer = Buffer.from([
    0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01, 0x01,
    0x01, 0x00, 0x48, 0x00, 0x48, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43, 0x00, 0xFF, 0xD9,
  ]);

  const users = {
    technician: {
      name: 'Tech Orchestrator',
      email: 'tech.module6@netradr.org',
      password: 'TechPassword2026!',
      role: ROLES.TECHNICIAN,
    },
    doctor: {
      name: 'Dr. Evaluator',
      email: 'doctor.module6@netradr.org',
      password: 'DocPassword2026!',
      role: ROLES.DOCTOR,
    },
    admin: {
      name: 'Admin Orchestrator',
      email: 'admin.module6@netradr.org',
      password: 'AdminPassword2026!',
      role: ROLES.ADMIN,
    },
  };

  const registerAndLogin = async (userData) => {
    const regRes = await fetch(`${baseUrl}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(userData),
    });
    const regBody = await regRes.json();
    assert.strictEqual(regRes.status, 201, `Failed to register ${userData.email}`);

    const loginRes = await fetch(`${baseUrl}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: userData.email, password: userData.password }),
    });
    const loginBody = await loginRes.json();
    assert.strictEqual(loginRes.status, 200, `Failed to login ${userData.email}`);

    return { token: loginBody.token, user: regBody.user };
  };

  const createCase = async (token = technicianToken, patientId = 'PAT-M6-001') => {
    const res = await fetch(`${baseUrl}/api/cases`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ patientId }),
    });
    const body = await res.json();
    assert.strictEqual(res.status, 201, 'Failed to create test case');
    return body.case;
  };

  const attachTestImage = async (caseId, uploadedBy = technicianUser.id) => {
    const imageMetadata = await ImageStorageService.saveImage(
      {
        buffer: validJpegBuffer,
        originalName: 'fundus_test_sample.jpg',
        mimeType: 'image/jpeg',
      },
      {
        caseId,
        uploadedBy,
      }
    );
    const updatedCase = await CaseModel.attachImage(caseId, imageMetadata);
    return { imageMetadata, updatedCase };
  };

  const cleanImagesDir = () => {
    try {
      if (fs.existsSync(paths.IMAGES_DIR)) {
        const files = fs.readdirSync(paths.IMAGES_DIR);
        for (const file of files) {
          if (file !== '.gitkeep') {
            safeUnlink(path.join(paths.IMAGES_DIR, file));
          }
        }
      }
    } catch (_err) {}
  };

  before(async () => {
    await UserModel.clear();
    await CaseModel.clear();
    cleanImagesDir();

    // 1. Start mock Flask AI service
    mockFlaskServer = http.createServer((req, res) => {
      lastFlaskRequest = {
        method:  req.method,
        url:     req.url,
        headers: req.headers,
      };

      if (mockFlaskHandler) {
        return mockFlaskHandler(req, res);
      }

      // Default mock Flask behavior: successful Phase 1 / Quality assessment response
      let chunks = [];
      req.on('data', chunk => chunks.push(chunk));
      req.on('end', () => {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
          status:        'success',
          quality_label: 'GOOD',
          quality_score: 0.9654,
          confidence:    0.9654,
          action:        'PROCEED',
          recommendation: 'High-quality retinal photograph suitable for automated diagnostic screening.',
          guidance:      'All clarity, contrast, and field-of-view criteria are satisfied.',
          probabilities: {
            good:       0.9654,
            borderline: 0.0246,
            reject:     0.0100,
          },
          model_info: {
            name:            'EyeQ-EfficientNetB4',
            ensemble_size:   8,
            input_size:      [520, 520],
            decision_policy: 'argmax',
          },
        }));
      });
    });

    await new Promise((resolve) => {
      mockFlaskServer.listen(0, '127.0.0.1', () => {
        const port = mockFlaskServer.address().port;
        mockFlaskUrl = `http://127.0.0.1:${port}`;
        process.env.AI_SERVICE_URL = mockFlaskUrl;
        process.env.AI_SERVICE_ENDPOINT = '/api/quality';
        process.env.AI_SERVICE_TIMEOUT_MS = '2000';
        resolve();
      });
    });

    // 2. Start Express app server
    await new Promise((resolve) => {
      server = app.listen(0, '127.0.0.1', () => {
        const port = server.address().port;
        baseUrl = `http://127.0.0.1:${port}`;
        resolve();
      });
    });

    // 3. Register and obtain tokens
    const techAuth   = await registerAndLogin(users.technician);
    technicianToken  = techAuth.token;
    technicianUser   = techAuth.user;

    const docAuth    = await registerAndLogin(users.doctor);
    doctorToken      = docAuth.token;
    doctorUser       = docAuth.user;

    const admAuth    = await registerAndLogin(users.admin);
    adminToken       = admAuth.token;
    adminUser        = admAuth.user;
  });

  beforeEach(() => {
    mockFlaskHandler = null;
    lastFlaskRequest = null;
    process.env.AI_SERVICE_URL = mockFlaskUrl;
    process.env.AI_SERVICE_ENDPOINT = '/api/quality';
    process.env.AI_SERVICE_TIMEOUT_MS = '2000';
  });

  after(async () => {
    if (server) {
      await new Promise((resolve) => server.close(resolve));
    }
    if (mockFlaskServer) {
      await new Promise((resolve) => mockFlaskServer.close(resolve));
    }
    await UserModel.clear();
    await CaseModel.clear();
    cleanImagesDir();
  });

  // --------------------------------------------------------------------------
  // AUTHENTICATION & AUTHORIZATION
  // --------------------------------------------------------------------------

  test('1. Unauthenticated request to POST /api/cases/:id/ai returns 401 Unauthorized', async () => {
    const testCase = await createCase();
    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method: 'POST',
    });
    assert.strictEqual(res.status, 401);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.ok(body.message.toLowerCase().includes('token') || body.message.toLowerCase().includes('auth'));
  });

  test('2. Malformed / invalid token returns 401 Unauthorized', async () => {
    const testCase = await createCase();
    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method: 'POST',
      headers: { Authorization: 'Bearer this.is.an.invalid.token' },
    });
    assert.strictEqual(res.status, 401);
  });

  test('3. Unauthorized role (doctor) returns 403 Forbidden', async () => {
    const testCase = await createCase();
    await attachTestImage(testCase.id);

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${doctorToken}` },
    });
    assert.strictEqual(res.status, 403);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.ok(body.message.toLowerCase().includes('denied') || body.message.toLowerCase().includes('role') || body.message.toLowerCase().includes('forbidden'));
  });

  test('4. Authorized role (technician) can invoke AI inference', async () => {
    const testCase = await createCase();
    await attachTestImage(testCase.id);

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    assert.strictEqual(res.status, 200);
    const body = await res.json();
    assert.strictEqual(body.status, 'success');
  });

  test('5. Authorized role (admin) can invoke AI inference', async () => {
    const testCase = await createCase(adminToken, 'PAT-ADM-001');
    await attachTestImage(testCase.id, adminUser.id);

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${adminToken}` },
    });
    assert.strictEqual(res.status, 200);
    const body = await res.json();
    assert.strictEqual(body.status, 'success');
  });

  // --------------------------------------------------------------------------
  // CASE & IMAGE VALIDATION
  // --------------------------------------------------------------------------

  test('6. Invalid case ID format returns 400 Bad Request', async () => {
    const res = await fetch(`${baseUrl}/api/cases/invalid-case-id/ai`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    assert.strictEqual(res.status, 400);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.ok(body.message.toLowerCase().includes('invalid case id'));
  });

  test('7. Path traversal attempt in case ID returns 400 Bad Request', async () => {
    const res = await fetch(`${baseUrl}/api/cases/case_..%2F..%2Fetc/ai`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    assert.strictEqual(res.status, 400);
  });

  test('8. Nonexistent case returns 404 Not Found', async () => {
    const nonexistentId = 'case_00000000-0000-0000-0000-000000000000';
    const res = await fetch(`${baseUrl}/api/cases/${nonexistentId}/ai`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    assert.strictEqual(res.status, 404);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.ok(body.message.includes(nonexistentId));
  });

  test('9. Case without uploaded fundus image returns 400 Bad Request', async () => {
    // Create case in 'created' status without image
    const testCase = await createCase(technicianToken, 'PAT-NO-IMG');
    assert.strictEqual(testCase.status, 'created');

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    assert.strictEqual(res.status, 400);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.ok(body.message.toLowerCase().includes('no uploaded fundus image'));
  });

  test('10. Case whose stored image file is missing on disk returns 404 Not Found', async () => {
    const testCase = await createCase(technicianToken, 'PAT-MISSING-DISK');
    const { imageMetadata } = await attachTestImage(testCase.id);

    // Intentionally delete image file from filesystem to simulate disk loss
    const imagePath = await ImageStorageService.getImagePath(testCase.id, imageMetadata.imageId);
    if (imagePath && fs.existsSync(imagePath)) {
      fs.unlinkSync(imagePath);
    }

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    assert.strictEqual(res.status, 404);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.ok(body.message.toLowerCase().includes('stored fundus image not found'));
  });

  // --------------------------------------------------------------------------
  // AI SERVICE INTEGRATION & ERROR HANDLING
  // --------------------------------------------------------------------------

  test('11. Successful inference returns 200 OK with structured AI output and trace ID', async () => {
    const testCase = await createCase(technicianToken, 'PAT-SUCCESS-001');
    const { imageMetadata } = await attachTestImage(testCase.id);

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });

    assert.strictEqual(res.status, 200);
    const body = await res.json();

    assert.strictEqual(body.status, 'success');
    assert.strictEqual(body.success, true);
    assert.strictEqual(body.caseId, testCase.id);
    assert.ok(body.inferenceRequestId && body.inferenceRequestId.startsWith('inf_'));
    assert.ok(body.inference, 'Response must contain inference data');
    assert.strictEqual(body.inference.status, 'success');
    assert.strictEqual(body.inference.quality_label, 'GOOD');
    assert.strictEqual(typeof body.inference.quality_score, 'number');

    // Confirm mock Flask received request
    assert.ok(lastFlaskRequest);
    assert.strictEqual(lastFlaskRequest.method, 'POST');
    assert.strictEqual(lastFlaskRequest.headers['x-inference-request-id'], body.inferenceRequestId);
  });

  test('12. Flask service 4xx error (e.g. 400 bad image) is handled cleanly without crashing', async () => {
    const testCase = await createCase(technicianToken, 'PAT-FLASK-400');
    await attachTestImage(testCase.id);

    mockFlaskHandler = (_req, res) => {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        status: 'error',
        error: 'Corrupted fundus image file rejected by quality gate',
      }));
    };

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });

    assert.strictEqual(res.status, 400);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.strictEqual(body.success, false);
    assert.ok(body.message.includes('Corrupted fundus image file'));
  });

  test('13. Flask service 5xx error (e.g. 500 internal error) returns 502 Bad Gateway', async () => {
    const testCase = await createCase(technicianToken, 'PAT-FLASK-500');
    await attachTestImage(testCase.id);

    mockFlaskHandler = (_req, res) => {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        status: 'error',
        error: 'CUDA Out of Memory during inference execution',
      }));
    };

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });

    assert.strictEqual(res.status, 502);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.strictEqual(body.success, false);
    assert.ok(body.message.includes('CUDA Out of Memory'));
  });

  test('14. Flask service unavailable (connection refused) returns 503 with AI_SERVICE_UNAVAILABLE', async () => {
    const testCase = await createCase(technicianToken, 'PAT-FLASK-DOWN');
    await attachTestImage(testCase.id);

    // Target a dead port where nothing is listening
    process.env.AI_SERVICE_URL = 'http://127.0.0.1:59997';

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });

    assert.strictEqual(res.status, 503);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.strictEqual(body.success, false);
    assert.strictEqual(body.error.code, 'AI_SERVICE_UNAVAILABLE');
    assert.ok(body.message.includes('unavailable'));
  });

  test('15. Flask service timeout returns 504 Gateway Timeout with AI_SERVICE_TIMEOUT', async () => {
    const testCase = await createCase(technicianToken, 'PAT-TIMEOUT');
    await attachTestImage(testCase.id);

    // Configure 150ms timeout; mock server delays 500ms
    process.env.AI_SERVICE_TIMEOUT_MS = '150';

    mockFlaskHandler = (_req, res) => {
      setTimeout(() => {
        try {
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ status: 'success' }));
        } catch (_e) {}
      }, 500);
    };

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });

    assert.strictEqual(res.status, 504);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.strictEqual(body.success, false);
    assert.strictEqual(body.error.code, 'AI_SERVICE_TIMEOUT');
    assert.ok(body.message.toLowerCase().includes('timed out'));
  });

  test('16. Flask service malformed/non-JSON response returns 502 with AI_SERVICE_MALFORMED_RESPONSE', async () => {
    const testCase = await createCase(technicianToken, 'PAT-MALFORMED');
    await attachTestImage(testCase.id);

    mockFlaskHandler = (_req, res) => {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end('<html><head><title>Nginx 502</title></head><body>Bad Gateway</body></html>');
    };

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });

    assert.strictEqual(res.status, 502);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.strictEqual(body.success, false);
    assert.strictEqual(body.error.code, 'AI_SERVICE_MALFORMED_RESPONSE');
  });

  // --------------------------------------------------------------------------
  // SECURITY & MEDICAL SAFETY
  // --------------------------------------------------------------------------

  test('17. Client cannot supply arbitrary filesystem path, URL, or model in request body', async () => {
    const testCase = await createCase(technicianToken, 'PAT-SECURITY-001');
    const { imageMetadata } = await attachTestImage(testCase.id);

    let receivedUrl = null;
    mockFlaskHandler = (req, res) => {
      receivedUrl = req.url;
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'success', quality_label: 'GOOD', quality_score: 0.95 }));
    };

    // Malicious client tries to inject path traversal, fake URL, arbitrary model and fake prediction
    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method: 'POST',
      headers: {
        Authorization:  `Bearer ${technicianToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        path:         'C:\\Windows\\System32\\cmd.exe',
        storagePath:  '../../etc/shadow',
        aiServiceUrl: 'http://malicious-external-server.com',
        model:        'custom-hacked-model',
        prediction:   'Severe DR (fabricated)',
        confidence:   0.9999,
      }),
    });

    assert.strictEqual(res.status, 200);
    const body = await res.json();

    // Verify injected predictions were NOT accepted or returned
    assert.notStrictEqual(body.inference.prediction, 'Severe DR (fabricated)');
    assert.strictEqual(body.inference.quality_label, 'GOOD');
    assert.strictEqual(body.inference.quality_score, 0.95);

    // Verify request went to the server-configured Flask endpoint, not injected URL
    assert.ok(lastFlaskRequest);
    assert.ok(!lastFlaskRequest.headers.host.includes('malicious-external-server.com'));
  });

  test('18. Internal filesystem paths are never leaked to API clients', async () => {
    const testCase = await createCase(technicianToken, 'PAT-LEAK-TEST');
    await attachTestImage(testCase.id);

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });

    assert.strictEqual(res.status, 200);
    const bodyStr = await res.text();

    assert.ok(!bodyStr.includes('storage\\images'), 'Response must not leak storage\\images path');
    assert.ok(!bodyStr.includes('storage/images'), 'Response must not leak storage/images path');
    assert.ok(!bodyStr.includes('storagePath'), 'Response must not contain storagePath property');
  });

  test('19. Inference request ID is generated with inf_ prefix and forwarded in request headers', async () => {
    const testCase = await createCase(technicianToken, 'PAT-TRACE-001');
    await attachTestImage(testCase.id);

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });

    assert.strictEqual(res.status, 200);
    const body = await res.json();

    assert.ok(body.inferenceRequestId);
    assert.ok(body.inferenceRequestId.startsWith('inf_'));
    assert.strictEqual(lastFlaskRequest.headers['x-inference-request-id'], body.inferenceRequestId);
  });

  test('20. Real AI output is preserved without synthetic fabrication of predictions', async () => {
    const testCase = await createCase(technicianToken, 'PAT-SAFETY-001');
    await attachTestImage(testCase.id);

    const flaskPayload = {
      status:        'success',
      quality_label: 'BORDERLINE',
      quality_score: 0.724,
      confidence:    0.724,
      action:        'PROCEED_WITH_CAUTION',
      recommendation: 'The image is usable but sub-optimal.',
      probabilities: {
        good:       0.25,
        borderline: 0.724,
        reject:     0.026,
      },
      model_info: {
        name: 'EyeQ-EfficientNetB4',
        ensemble_size: 8,
      },
    };

    mockFlaskHandler = (_req, res) => {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(flaskPayload));
    };

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });

    assert.strictEqual(res.status, 200);
    const body = await res.json();

    // Verify faithful propagation of the exact quality label and score from the model
    assert.strictEqual(body.inference.quality_label, 'BORDERLINE');
    assert.strictEqual(body.inference.quality_score, 0.724);
    assert.strictEqual(body.inference.action, 'PROCEED_WITH_CAUTION');
    assert.strictEqual(body.inference.model_info.name, 'EyeQ-EfficientNetB4');
  });
});
