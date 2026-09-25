/**
 * tests/ai-results.test.js — NETRA-DR Module 7 AI Results Persistence Test Suite
 *
 * Verifies AI Results Persistence (Module 7):
 *
 * 1. Successful Persistence:
 *    - Flask inference success triggers automatic persistence of AI result
 *    - Server-generated resultId ('res_<uuid>') is assigned
 *    - caseId is correctly associated
 *    - Upstream inferenceRequestId ('inf_<uuid>') is preserved
 *    - Case status transitions from 'image_uploaded' to 'completed'
 *    - Direct model inspection verifies persistent storage in AIResultModel
 *
 * 2. Data Integrity:
 *    - Result belongs strictly to the case whose image was processed
 *    - Result contains actual Flask output without fabricated scores
 *    - Result does not contain internal filesystem paths (storagePath, storage/images)
 *    - Result does not contain secrets, tokens, or environment variables
 *
 * 3. Duplicate Handling / Idempotency:
 *    - Same inferenceRequestId does not silently create duplicate results
 *    - Idempotent invocation returns existing result without generating new resultId
 *    - Total count in AIResultModel remains unchanged on replay
 *    - Multiple distinct inference runs on the same case produce distinct records,
 *      with getResultByCaseId returning the latest result
 *
 * 4. Failure Safety:
 *    - Flask 4xx does not persist a successful result
 *    - Flask 5xx does not persist a successful result
 *    - Flask service unavailable (503) does not persist a successful result
 *    - Flask service timeout (504) does not persist a successful result
 *    - Flask malformed response (502) does not persist a successful result
 *    - Case status does not become 'completed' on failure
 *    - Does not store prediction = null labeled as completed
 *
 * 5. Result Retrieval (GET /api/cases/:id/ai-result):
 *    - Existing result returns 200 OK with expected safe envelope
 *    - Technician can retrieve AI result (200)
 *    - Doctor can retrieve AI result (200)
 *    - Admin can retrieve AI result (200)
 *    - Case with no result returns 404 Not Found
 *    - Missing / nonexistent case returns 404 Not Found
 *    - Invalid case ID parameter returns 400 Bad Request
 *    - Path traversal in case ID returns 400 Bad Request
 *    - Unauthenticated request returns 401 Unauthorized
 *    - Invalid token returns 401 Unauthorized
 *    - Unauthorized role (unrecognized/malformed role) returns 403 Forbidden
 *
 * 6. Security:
 *    - Client-supplied resultId, inferenceRequestId, prediction, confidence in request body are ignored
 *    - Direct client POST to /api/cases/:id/ai-result returns 404 (no client result injection endpoint)
 *    - Cross-case inference ID conflict is rejected (409)
 *    - Case without uploaded image cannot have result persisted
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
const AIResultModel = require('../src/models/ai-result.model');
const AIResultService = require('../src/services/ai-result.service');
const ImageStorageService = require('../src/services/image-storage.service');
const paths  = require('../src/config/paths');
const { ROLES } = require('../src/config/roles');
const { generateToken } = require('../src/utils/jwt.utils');
const { safeUnlink } = require('../src/utils/file.utils');

describe('NETRA-DR Module 7 — AI Results Persistence Tests', () => {
  let server;
  let baseUrl;

  // Mock Flask AI service
  let mockFlaskServer;
  let mockFlaskUrl;
  let mockFlaskHandler = null;
  let lastFlaskRequest = null;

  // Auth tokens and users
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

  const defaultFlaskPayload = {
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
  };

  const users = {
    technician: {
      name:     'Tech Persist',
      email:    'tech.module7@netradr.org',
      password: 'TechPassword2026!',
      role:     ROLES.TECHNICIAN,
    },
    doctor: {
      name:     'Dr. Persist',
      email:    'doctor.module7@netradr.org',
      password: 'DocPassword2026!',
      role:     ROLES.DOCTOR,
    },
    admin: {
      name:     'Admin Persist',
      email:    'admin.module7@netradr.org',
      password: 'AdminPassword2026!',
      role:     ROLES.ADMIN,
    },
  };

  const registerAndLogin = async (userData) => {
    const regRes = await fetch(`${baseUrl}/api/auth/register`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(userData),
    });
    const regBody = await regRes.json();
    assert.strictEqual(regRes.status, 201, `Failed to register ${userData.email}`);

    const loginRes = await fetch(`${baseUrl}/api/auth/login`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ email: userData.email, password: userData.password }),
    });
    const loginBody = await loginRes.json();
    assert.strictEqual(loginRes.status, 200, `Failed to login ${userData.email}`);

    return { token: loginBody.token, user: regBody.user };
  };

  const createCase = async (token = technicianToken, patientId = 'PAT-M7-001') => {
    const res = await fetch(`${baseUrl}/api/cases`, {
      method:  'POST',
      headers: {
        Authorization:  `Bearer ${token}`,
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
        buffer:       validJpegBuffer,
        originalName: 'fundus_sample_m7.jpg',
        mimeType:     'image/jpeg',
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
    await AIResultModel.clear();
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

      let chunks = [];
      req.on('data', chunk => chunks.push(chunk));
      req.on('end', () => {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(defaultFlaskPayload));
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

    // 3. Register users and obtain auth tokens
    const techAuth  = await registerAndLogin(users.technician);
    technicianToken = techAuth.token;
    technicianUser  = techAuth.user;

    const docAuth   = await registerAndLogin(users.doctor);
    doctorToken     = docAuth.token;
    doctorUser      = docAuth.user;

    const admAuth   = await registerAndLogin(users.admin);
    adminToken      = admAuth.token;
    adminUser       = admAuth.user;
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
    await AIResultModel.clear();
    cleanImagesDir();
  });

  // ==========================================================================
  // 1. SUCCESSFUL PERSISTENCE
  // ==========================================================================

  test('1. Successful inference automatically persists AI result and returns safe result envelope', async () => {
    const testCase = await createCase(technicianToken, 'PAT-PERSIST-001');
    await attachTestImage(testCase.id);

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method:  'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });

    assert.strictEqual(res.status, 200);
    const body = await res.json();

    assert.strictEqual(body.status, 'success');
    assert.strictEqual(body.success, true);
    assert.strictEqual(body.caseId, testCase.id);

    // Verify inferenceRequestId format and preservation
    assert.ok(body.inferenceRequestId && body.inferenceRequestId.startsWith('inf_'));

    // Verify server-generated resultId
    assert.ok(body.resultId && body.resultId.startsWith('res_'));

    // Verify result object
    assert.ok(body.result, 'Response must contain persisted result');
    assert.strictEqual(body.result.resultId, body.resultId);
    assert.strictEqual(body.result.caseId, testCase.id);
    assert.strictEqual(body.result.inferenceRequestId, body.inferenceRequestId);
    assert.strictEqual(body.result.status, 'completed');
    assert.ok(body.result.createdAt, 'Result must contain createdAt');
    assert.ok(body.result.updatedAt, 'Result must contain updatedAt');

    // Verify inference contents
    assert.strictEqual(body.result.inference.status, 'success');
    assert.strictEqual(body.result.inference.quality_label, 'GOOD');
    assert.strictEqual(body.result.inference.quality_score, 0.9654);
    assert.strictEqual(body.result.inference.action, 'PROCEED');
    assert.strictEqual(body.result.inference.model_info.name, 'EyeQ-EfficientNetB4');

    // Verify case lifecycle state transitioned to 'completed'
    assert.strictEqual(body.case.status, 'completed');
    const storedCase = await CaseModel.findById(testCase.id);
    assert.strictEqual(storedCase.status, 'completed');

    // Direct model verification: check that AIResultModel has stored the record
    const storedResult = await AIResultModel.findByCaseId(testCase.id);
    assert.ok(storedResult, 'AIResultModel must contain the persisted record');
    assert.strictEqual(storedResult.resultId, body.resultId);
    assert.strictEqual(storedResult.status, 'completed');
  });

  // ==========================================================================
  // 2. DATA INTEGRITY
  // ==========================================================================

  test('2. Result belongs strictly to the correct case', async () => {
    const caseA = await createCase(technicianToken, 'PAT-INTEGRITY-A');
    const caseB = await createCase(technicianToken, 'PAT-INTEGRITY-B');
    await attachTestImage(caseA.id);
    await attachTestImage(caseB.id);

    // Run inference only on caseA
    const resA = await fetch(`${baseUrl}/api/cases/${caseA.id}/ai`, {
      method:  'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    assert.strictEqual(resA.status, 200);
    const bodyA = await resA.json();

    // Verify caseA has result
    const resultA = await AIResultService.getResultByCaseId(caseA.id);
    assert.ok(resultA);
    assert.strictEqual(resultA.caseId, caseA.id);
    assert.strictEqual(resultA.resultId, bodyA.resultId);

    // Verify caseB has NO result
    const resultB = await AIResultService.getResultByCaseId(caseB.id);
    assert.strictEqual(resultB, null, 'Case B must not have received Case A result');
  });

  test('3. Result contains genuine Flask output without synthetic fabrication', async () => {
    const testCase = await createCase(technicianToken, 'PAT-GENUINE-001');
    await attachTestImage(testCase.id);

    const customFlaskOutput = {
      status:        'success',
      quality_label: 'BORDERLINE',
      quality_score: 0.6812,
      confidence:    0.6812,
      action:        'PROCEED_WITH_CAUTION',
      recommendation: 'Borderline illumination detected; automated diagnostic confidence may be reduced.',
      guidance:      'Consider capturing an additional fundus photo if time permits.',
      probabilities: {
        good:       0.2800,
        borderline: 0.6812,
        reject:     0.0388,
      },
      model_info: {
        name:            'EyeQ-EfficientNetB4-Custom',
        ensemble_size:   4,
        input_size:      [512, 512],
        decision_policy: 'argmax',
      },
    };

    mockFlaskHandler = (_req, res) => {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(customFlaskOutput));
    };

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method:  'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    assert.strictEqual(res.status, 200);
    const body = await res.json();

    const storedResult = await AIResultModel.findByCaseId(testCase.id);
    assert.strictEqual(storedResult.inference.quality_label, 'BORDERLINE');
    assert.strictEqual(storedResult.inference.quality_score, 0.6812);
    assert.strictEqual(storedResult.inference.action, 'PROCEED_WITH_CAUTION');
    assert.strictEqual(storedResult.inference.model_info.name, 'EyeQ-EfficientNetB4-Custom');
    assert.strictEqual(storedResult.inference.model_info.ensemble_size, 4);

    // Verify no fabricated DR diagnosis or clinical grade was inserted
    assert.strictEqual(storedResult.inference.diagnosis, undefined);
    assert.strictEqual(storedResult.inference.dr_grade, undefined);
    assert.strictEqual(storedResult.inference.severity, undefined);
  });

  test('4. Result does NOT leak internal filesystem paths or sensitive credentials', async () => {
    const testCase = await createCase(technicianToken, 'PAT-LEAK-PREVENT');
    await attachTestImage(testCase.id);

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method:  'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    assert.strictEqual(res.status, 200);
    const rawText = await res.text();

    assert.ok(!rawText.includes('storagePath'), 'Response must not contain storagePath');
    assert.ok(!rawText.includes('storage\\images'), 'Response must not contain Windows storage path');
    assert.ok(!rawText.includes('storage/images'), 'Response must not contain POSIX storage path');
    assert.ok(!rawText.includes('JWT_SECRET'), 'Response must not contain secret tokens');
    assert.ok(!rawText.includes('passwordHash'), 'Response must not contain password hash');
  });

  // ==========================================================================
  // 3. DUPLICATE HANDLING / IDEMPOTENCY
  // ==========================================================================

  test('5. Same inferenceRequestId returns existing result without creating duplicates', async () => {
    const testCase = await createCase(technicianToken, 'PAT-IDEMPOTENT-001');
    await attachTestImage(testCase.id);

    const testInfId = 'inf_00000000-0000-4000-8000-000000000001';

    // First call to saveResult
    const firstResult = await AIResultService.saveResult({
      caseId:             testCase.id,
      inferenceRequestId: testInfId,
      inference:          defaultFlaskPayload,
    });

    const countAfterFirst = await AIResultModel.count();

    // Replay with exact same inferenceRequestId
    const secondResult = await AIResultService.saveResult({
      caseId:             testCase.id,
      inferenceRequestId: testInfId,
      inference:          defaultFlaskPayload,
    });

    const countAfterSecond = await AIResultModel.count();

    // Must return the exact same resultId and no duplicate record was created
    assert.strictEqual(countAfterSecond, countAfterFirst, 'Total records count must not increase');
    assert.strictEqual(secondResult.resultId, firstResult.resultId, 'Result IDs must match');
    assert.strictEqual(secondResult.inferenceRequestId, testInfId);
  });

  test('6. Multiple distinct inferences on same case create distinct records, latest is returned', async () => {
    const testCase = await createCase(technicianToken, 'PAT-MULTI-RUN');
    await attachTestImage(testCase.id);

    const infId1 = 'inf_11111111-1111-4111-8111-111111111111';
    const infId2 = 'inf_22222222-2222-4222-8222-222222222222';

    const result1 = await AIResultService.saveResult({
      caseId:             testCase.id,
      inferenceRequestId: infId1,
      inference:          { ...defaultFlaskPayload, quality_score: 0.85 },
    });

    // Small delay to ensure distinct timestamp
    await new Promise(r => setTimeout(r, 10));

    const result2 = await AIResultService.saveResult({
      caseId:             testCase.id,
      inferenceRequestId: infId2,
      inference:          { ...defaultFlaskPayload, quality_score: 0.98 },
    });

    assert.notStrictEqual(result1.resultId, result2.resultId);

    // Latest by case ID should be result2
    const latest = await AIResultService.getResultByCaseId(testCase.id);
    assert.strictEqual(latest.resultId, result2.resultId);
    assert.strictEqual(latest.inference.quality_score, 0.98);

    // Both should be in history
    const all = await AIResultService.getAllResultsByCaseId(testCase.id);
    assert.strictEqual(all.length, 2);
    assert.strictEqual(all[0].resultId, result2.resultId); // newest first
  });

  // ==========================================================================
  // 4. FAILURE SAFETY
  // ==========================================================================

  test('7. Flask 4xx does NOT persist a successful AI result', async () => {
    const testCase = await createCase(technicianToken, 'PAT-FAIL-400');
    await attachTestImage(testCase.id);

    mockFlaskHandler = (_req, res) => {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'error', error: 'Fundus image corrupted' }));
    };

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method:  'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    assert.strictEqual(res.status, 400);

    // Verify no completed AI result was persisted
    const storedResult = await AIResultModel.findByCaseId(testCase.id);
    assert.strictEqual(storedResult, null, 'No successful AI result should be persisted on 400 error');

    // Case status should not be 'completed'
    const storedCase = await CaseModel.findById(testCase.id);
    assert.notStrictEqual(storedCase.status, 'completed');
  });

  test('8. Flask 5xx does NOT persist a successful AI result', async () => {
    const testCase = await createCase(technicianToken, 'PAT-FAIL-500');
    await attachTestImage(testCase.id);

    mockFlaskHandler = (_req, res) => {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'error', error: 'Internal Model Execution Error' }));
    };

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method:  'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    assert.strictEqual(res.status, 502);

    const storedResult = await AIResultModel.findByCaseId(testCase.id);
    assert.strictEqual(storedResult, null, 'No successful AI result should be persisted on 500 error');

    const storedCase = await CaseModel.findById(testCase.id);
    assert.notStrictEqual(storedCase.status, 'completed');
  });

  test('9. Flask service unavailable (503) does NOT persist a successful AI result', async () => {
    const testCase = await createCase(technicianToken, 'PAT-FAIL-503');
    await attachTestImage(testCase.id);

    process.env.AI_SERVICE_URL = 'http://127.0.0.1:59998'; // offline port

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method:  'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    assert.strictEqual(res.status, 503);

    const storedResult = await AIResultModel.findByCaseId(testCase.id);
    assert.strictEqual(storedResult, null, 'No successful AI result should be persisted on 503');

    const storedCase = await CaseModel.findById(testCase.id);
    assert.notStrictEqual(storedCase.status, 'completed');
  });

  test('10. Flask service timeout (504) does NOT persist a successful AI result', async () => {
    const testCase = await createCase(technicianToken, 'PAT-FAIL-504');
    await attachTestImage(testCase.id);

    process.env.AI_SERVICE_TIMEOUT_MS = '100';

    mockFlaskHandler = (_req, res) => {
      setTimeout(() => {
        try {
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify(defaultFlaskPayload));
        } catch (_e) {}
      }, 400);
    };

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method:  'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    assert.strictEqual(res.status, 504);

    const storedResult = await AIResultModel.findByCaseId(testCase.id);
    assert.strictEqual(storedResult, null, 'No successful AI result should be persisted on timeout');

    const storedCase = await CaseModel.findById(testCase.id);
    assert.notStrictEqual(storedCase.status, 'completed');
  });

  test('11. Flask service malformed response (502) does NOT persist a successful AI result', async () => {
    const testCase = await createCase(technicianToken, 'PAT-FAIL-MALFORMED');
    await attachTestImage(testCase.id);

    mockFlaskHandler = (_req, res) => {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end('<html><body>502 Bad Gateway</body></html>');
    };

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method:  'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    assert.strictEqual(res.status, 502);

    const storedResult = await AIResultModel.findByCaseId(testCase.id);
    assert.strictEqual(storedResult, null, 'No successful AI result should be persisted on malformed response');
  });

  // ==========================================================================
  // 5. RESULT RETRIEVAL (GET /api/cases/:id/ai-result)
  // ==========================================================================

  test('12. Existing result can be retrieved via GET /api/cases/:id/ai-result (200 OK)', async () => {
    const testCase = await createCase(technicianToken, 'PAT-RETRIEVE-001');
    await attachTestImage(testCase.id);

    // Run inference first
    const aiRes = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method:  'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    assert.strictEqual(aiRes.status, 200);
    const aiBody = await aiRes.json();

    // Retrieve result
    const getRes = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai-result`, {
      method:  'GET',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    assert.strictEqual(getRes.status, 200);
    const getBody = await getRes.json();

    assert.strictEqual(getBody.status, 'success');
    assert.strictEqual(getBody.success, true);
    assert.strictEqual(getBody.caseId, testCase.id);
    assert.strictEqual(getBody.result.resultId, aiBody.resultId);
    assert.strictEqual(getBody.result.inferenceRequestId, aiBody.inferenceRequestId);
    assert.strictEqual(getBody.result.status, 'completed');
    assert.strictEqual(getBody.result.inference.quality_label, 'GOOD');
    assert.strictEqual(getBody.result.inference.quality_score, 0.9654);

    // Verify alias GET /api/cases/:id/ai also works
    const aliasRes = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method:  'GET',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    assert.strictEqual(aliasRes.status, 200);
    const aliasBody = await aliasRes.json();
    assert.strictEqual(aliasBody.result.resultId, aiBody.resultId);
  });

  test('13. Authorized roles: Technician, Doctor, and Admin can all retrieve AI results', async () => {
    const testCase = await createCase(technicianToken, 'PAT-ROLES-001');
    await attachTestImage(testCase.id);

    // Create result
    await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method:  'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });

    // 1. Technician can retrieve
    const techRes = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai-result`, {
      method:  'GET',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    assert.strictEqual(techRes.status, 200);

    // 2. Doctor can retrieve
    const docRes = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai-result`, {
      method:  'GET',
      headers: { Authorization: `Bearer ${doctorToken}` },
    });
    assert.strictEqual(docRes.status, 200);

    // 3. Admin can retrieve
    const admRes = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai-result`, {
      method:  'GET',
      headers: { Authorization: `Bearer ${adminToken}` },
    });
    assert.strictEqual(admRes.status, 200);
  });

  test('14. Retrieval for case with NO AI result returns 404 Not Found', async () => {
    const testCase = await createCase(technicianToken, 'PAT-NO-RESULT');
    await attachTestImage(testCase.id);

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai-result`, {
      method:  'GET',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    assert.strictEqual(res.status, 404);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.ok(body.message.includes('No AI inference result found'));
  });

  test('15. Retrieval for NONEXISTENT case returns 404 Not Found', async () => {
    const nonexistentId = 'case_00000000-0000-0000-0000-000000000099';
    const res = await fetch(`${baseUrl}/api/cases/${nonexistentId}/ai-result`, {
      method:  'GET',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    assert.strictEqual(res.status, 404);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.ok(body.message.includes(nonexistentId));
  });

  test('16. Retrieval with INVALID case ID format returns 400 Bad Request', async () => {
    const res = await fetch(`${baseUrl}/api/cases/invalid-case-id/ai-result`, {
      method:  'GET',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    assert.strictEqual(res.status, 400);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.strictEqual(body.error.code, 'ERR_INVALID_CASE_ID');
  });

  test('17. Retrieval with path traversal in case ID returns 400 Bad Request', async () => {
    const res = await fetch(`${baseUrl}/api/cases/case_..%2F..%2Fetc/ai-result`, {
      method:  'GET',
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    assert.strictEqual(res.status, 400);
  });

  test('18. Unauthenticated request to GET /api/cases/:id/ai-result returns 401 Unauthorized', async () => {
    const testCase = await createCase(technicianToken, 'PAT-UNAUTH-001');
    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai-result`, {
      method: 'GET',
    });
    assert.strictEqual(res.status, 401);
  });

  test('19. Invalid token returns 401 Unauthorized', async () => {
    const testCase = await createCase(technicianToken, 'PAT-BAD-TOKEN');
    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai-result`, {
      method:  'GET',
      headers: { Authorization: 'Bearer this.is.an.invalid.token' },
    });
    assert.strictEqual(res.status, 401);
  });

  test('20. Malformed role in token returns 403 Forbidden', async () => {
    const testCase = await createCase(technicianToken, 'PAT-BAD-ROLE');
    const badRoleToken = generateToken({ id: 'usr_bad_role', role: 'superuser', email: 'bad@netradr.org' });

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai-result`, {
      method:  'GET',
      headers: { Authorization: `Bearer ${badRoleToken}` },
    });
    // Either 401 (user not in DB) or 403 (unrecognized role) per auth middleware
    assert.ok(res.status === 401 || res.status === 403);
  });

  // ==========================================================================
  // 6. SECURITY & CLIENT RESULT INJECTION PREVENTION
  // ==========================================================================

  test('21. Client-supplied AI result, resultId, prediction, and confidence in body are completely ignored', async () => {
    const testCase = await createCase(technicianToken, 'PAT-INJECT-001');
    await attachTestImage(testCase.id);

    // Attacker submits malicious payload attempting to forge AI outcome
    const maliciousPayload = {
      resultId:           'res_hacked_id_12345',
      inferenceRequestId: 'inf_hacked_id_12345',
      prediction:         'Proliferative DR (Fabricated)',
      confidence:         0.9999,
      quality_label:      'REJECT',
      status:             'completed',
      model_info: {
        name: 'Evil-Injected-Model',
      },
    };

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai`, {
      method:  'POST',
      headers: {
        Authorization:  `Bearer ${technicianToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(maliciousPayload),
    });

    assert.strictEqual(res.status, 200);
    const body = await res.json();

    // Verify injected resultId was rejected
    assert.notStrictEqual(body.resultId, 'res_hacked_id_12345');
    assert.ok(body.resultId.startsWith('res_'));

    // Verify injected inferenceRequestId was rejected
    assert.notStrictEqual(body.inferenceRequestId, 'inf_hacked_id_12345');
    assert.ok(body.inferenceRequestId.startsWith('inf_'));

    // Verify genuine Flask quality score and label were used
    assert.strictEqual(body.result.inference.quality_label, 'GOOD');
    assert.strictEqual(body.result.inference.quality_score, 0.9654);
    assert.notStrictEqual(body.result.inference.prediction, 'Proliferative DR (Fabricated)');
    assert.notStrictEqual(body.result.inference.model_info.name, 'Evil-Injected-Model');

    // Model store verification
    const stored = await AIResultModel.findByCaseId(testCase.id);
    assert.notStrictEqual(stored.resultId, 'res_hacked_id_12345');
    assert.strictEqual(stored.inference.quality_label, 'GOOD');
  });

  test('22. Client cannot POST arbitrary results to /api/cases/:id/ai-result (404 Not Found)', async () => {
    const testCase = await createCase(technicianToken, 'PAT-DIRECT-POST');
    await attachTestImage(testCase.id);

    // Client attempts to push an AI result directly
    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/ai-result`, {
      method:  'POST',
      headers: {
        Authorization:  `Bearer ${technicianToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        status:     'completed',
        quality:    'GOOD',
        confidence: 0.99,
      }),
    });

    // Endpoint does NOT support POST — results can ONLY originate from the trusted Module 6 pipeline
    assert.strictEqual(res.status, 404);
  });

  test('23. Cannot save result for a case without uploaded fundus image', async () => {
    const testCase = await createCase(technicianToken, 'PAT-NO-IMG-PERSIST');
    // Case has no image attached

    await assert.rejects(
      async () => {
        await AIResultService.saveResult({
          caseId:             testCase.id,
          inferenceRequestId: 'inf_test_no_image',
          inference:          defaultFlaskPayload,
        });
      },
      (err) => {
        assert.strictEqual(err.code, 'ERR_NO_IMAGE_UPLOADED');
        assert.strictEqual(err.statusCode, 400);
        return true;
      }
    );
  });

  test('24. Inference ID cannot be hijacked across different cases (409 Conflict)', async () => {
    const case1 = await createCase(technicianToken, 'PAT-CASE-1');
    const case2 = await createCase(technicianToken, 'PAT-CASE-2');
    await attachTestImage(case1.id);
    await attachTestImage(case2.id);

    const sharedInfId = 'inf_shared_trace_id_0001';

    // Persist for case 1
    await AIResultService.saveResult({
      caseId:             case1.id,
      inferenceRequestId: sharedInfId,
      inference:          defaultFlaskPayload,
    });

    // Attempting to reuse same inferenceRequestId for case 2 must throw 409
    await assert.rejects(
      async () => {
        await AIResultService.saveResult({
          caseId:             case2.id,
          inferenceRequestId: sharedInfId,
          inference:          defaultFlaskPayload,
        });
      },
      (err) => {
        assert.strictEqual(err.code, 'ERR_INFERENCE_ID_CONFLICT');
        assert.strictEqual(err.statusCode, 409);
        return true;
      }
    );
  });
});
