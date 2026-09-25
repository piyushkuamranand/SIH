/**
 * tests/image-upload.test.js — NETRA-DR Module 4 Fundus Image Upload Test Suite
 *
 * Verifies all required scenarios for Module 4 (Fundus Image Upload Only):
 *
 * Authentication:
 *   1.  Authenticated authorized user (technician) can upload.
 *   1b. Authenticated authorized user (admin) can upload.
 *   2.  Missing authentication returns 401 Unauthorized.
 *   3.  Unauthorized role (doctor) returns 403 Forbidden.
 *
 * Case Validation:
 *   4.  Upload to existing case succeeds.
 *   5.  Upload to nonexistent case returns 404 Not Found.
 *   6.  Invalid case ID is rejected with 400 Bad Request.
 *
 * File Validation:
 *   7.  Missing file returns 400 Bad Request.
 *   7b. Empty file (0 bytes) returns 400 Bad Request.
 *   8.  Supported JPEG/JPG upload succeeds.
 *   9.  Supported PNG upload succeeds.
 *  10.  Unsupported file type / extension is rejected with 400 Bad Request.
 *  11.  Oversized file is rejected with 413 Payload Too Large.
 *
 * Security:
 *  12.  Client cannot change case status directly.
 *  13.  Client cannot spoof uploadedBy.
 *  14.  Uploaded image is associated with authenticated user.
 *  15.  No JWT / password / secret / internal filesystem path is returned.
 *
 * Lifecycle & Re-upload:
 *  16.  Successful upload changes: created → image_uploaded.
 *  17.  Failed upload does NOT change the case status.
 *  18.  Re-upload to already uploaded case returns 409 Conflict.
 */

'use strict';

const { test, describe, before, after, beforeEach } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const app = require('../src/app');
const UserModel = require('../src/models/user.model');
const CaseModel = require('../src/models/case.model');
const paths = require('../src/config/paths');
const { ROLES } = require('../src/config/roles');
const { safeUnlink } = require('../src/utils/file.utils');

describe('NETRA-DR Module 4 — Fundus Image Upload Tests', () => {
  let server;
  let baseUrl;

  let technicianToken;
  let technicianUser;
  let doctorToken;
  let doctorUser;
  let adminToken;
  let adminUser;

  // Minimal valid image buffers
  const validJpegBuffer = Buffer.from([
    0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01, 0x01,
    0x01, 0x00, 0x48, 0x00, 0x48, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43, 0x00, 0xFF, 0xD9,
  ]);

  const validPngBuffer = Buffer.from([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D, 0x49,
    0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, 0x08, 0x06,
    0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4, 0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44,
    0x41, 0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00, 0x05, 0x00, 0x01, 0x0D,
    0x0A, 0x2D, 0xB4, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE, 0x42,
    0x60, 0x82,
  ]);

  const users = {
    technician: {
      name: 'Tech Alpha',
      email: 'tech.module4@netradr.org',
      password: 'TechPassword2026!',
      role: ROLES.TECHNICIAN,
    },
    doctor: {
      name: 'Dr. Retina',
      email: 'doctor.module4@netradr.org',
      password: 'DocPassword2026!',
      role: ROLES.DOCTOR,
    },
    admin: {
      name: 'Admin Boss',
      email: 'admin.module4@netradr.org',
      password: 'AdminPassword2026!',
      role: ROLES.ADMIN,
    },
  };

  /**
   * Helper: Register user and return login token + user object
   */
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

  /**
   * Helper: Create a screening case and return its ID
   */
  const createCase = async (token = technicianToken, patientId = 'PAT-M4-001') => {
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

  /**
   * Helper: Clean test files in storage/images/ directory
   */
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

    await new Promise((resolve) => {
      server = app.listen(0, '127.0.0.1', () => {
        const port = server.address().port;
        baseUrl = `http://127.0.0.1:${port}`;
        resolve();
      });
    });

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

  after(async () => {
    if (server) {
      await new Promise((resolve) => server.close(resolve));
    }
    cleanImagesDir();
  });

  beforeEach(async () => {
    await CaseModel.clear();
    cleanImagesDir();
  });

  // --------------------------------------------------------------------------
  // 1. Authentication
  // --------------------------------------------------------------------------
  test('1. Authenticated authorized user (technician) can upload fundus image', async () => {
    const testCase = await createCase();

    const form = new FormData();
    form.append('image', new Blob([validJpegBuffer], { type: 'image/jpeg' }), 'fundus_left.jpg');

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
      body: form,
    });

    assert.strictEqual(res.status, 200);
    const body = await res.json();
    assert.strictEqual(body.success, true);
    assert.strictEqual(body.message, 'Fundus image uploaded successfully');
    assert.strictEqual(body.case.id, testCase.id);
    assert.strictEqual(body.case.status, 'image_uploaded');
    assert.ok(body.image.imageId);
    assert.match(body.image.imageId, /^img_[0-9a-f-]{36}$/i);
    assert.strictEqual(body.image.originalName, 'fundus_left.jpg');
    assert.strictEqual(body.image.mimeType, 'image/jpeg');
    assert.strictEqual(body.image.sizeBytes, validJpegBuffer.length);
  });

  test('1b. Authenticated authorized user (admin) can upload fundus image', async () => {
    const testCase = await createCase(adminToken, 'PAT-ADM-IMG');

    const form = new FormData();
    form.append('image', new Blob([validPngBuffer], { type: 'image/png' }), 'fundus_admin.png');

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${adminToken}` },
      body: form,
    });

    assert.strictEqual(res.status, 200);
    const body = await res.json();
    assert.strictEqual(body.success, true);
    assert.strictEqual(body.case.status, 'image_uploaded');
    assert.strictEqual(body.image.uploadedBy, adminUser.id);
  });

  test('2. Missing authentication returns 401 Unauthorized', async () => {
    const testCase = await createCase();

    const form = new FormData();
    form.append('image', new Blob([validJpegBuffer], { type: 'image/jpeg' }), 'fundus.jpg');

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/image`, {
      method: 'POST',
      body: form,
    });

    assert.strictEqual(res.status, 401);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.strictEqual(body.code, 401);
    assert.match(body.message, /authorization header is missing/i);
  });

  test('3. Unauthorized role (doctor) returns 403 Forbidden', async () => {
    const testCase = await createCase();

    const form = new FormData();
    form.append('image', new Blob([validJpegBuffer], { type: 'image/jpeg' }), 'fundus.jpg');

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${doctorToken}` },
      body: form,
    });

    assert.strictEqual(res.status, 403);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.strictEqual(body.code, 403);
    assert.match(body.message, /access denied/i);
  });

  // --------------------------------------------------------------------------
  // 2. Case Validation
  // --------------------------------------------------------------------------
  test('4. Upload to existing case succeeds and persists association', async () => {
    const testCase = await createCase(technicianToken, 'PAT-PERSIST');

    const form = new FormData();
    form.append('image', new Blob([validJpegBuffer], { type: 'image/jpeg' }), 'macula.jpg');

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
      body: form,
    });

    assert.strictEqual(res.status, 200);

    // Retrieve via GET /api/cases/:id to verify persistent association in case model
    const getRes = await fetch(`${baseUrl}/api/cases/${testCase.id}`, {
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    assert.strictEqual(getRes.status, 200);
    const getBody = await getRes.json();
    assert.strictEqual(getBody.case.status, 'image_uploaded');
    assert.ok(getBody.case.image);
    assert.strictEqual(getBody.case.image.originalName, 'macula.jpg');
    assert.strictEqual(getBody.case.image.mimeType, 'image/jpeg');
    assert.strictEqual(getBody.case.image.uploadedBy, technicianUser.id);
  });

  test('5. Upload to nonexistent case returns 404 Not Found', async () => {
    const form = new FormData();
    form.append('image', new Blob([validJpegBuffer], { type: 'image/jpeg' }), 'fundus.jpg');

    const nonexistentId = 'case_00000000-0000-0000-0000-000000000000';
    const res = await fetch(`${baseUrl}/api/cases/${nonexistentId}/image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
      body: form,
    });

    assert.strictEqual(res.status, 404);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.strictEqual(body.code, 404);
    assert.match(body.message, /not found/i);
  });

  test('6. Invalid case ID parameter is rejected with 400 Bad Request', async () => {
    const form = new FormData();
    form.append('image', new Blob([validJpegBuffer], { type: 'image/jpeg' }), 'fundus.jpg');

    // Invalid ID: does not start with 'case_'
    const res = await fetch(`${baseUrl}/api/cases/invalid_id_format/image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
      body: form,
    });

    assert.strictEqual(res.status, 400);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.strictEqual(body.code, 400);
    assert.match(body.message, /invalid case id/i);
  });

  // --------------------------------------------------------------------------
  // 3. File Validation
  // --------------------------------------------------------------------------
  test('7. Missing file returns 400 Bad Request', async () => {
    const testCase = await createCase();

    // Multipart request with empty form (no image file)
    const emptyForm = new FormData();
    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
      body: emptyForm,
    });

    assert.strictEqual(res.status, 400);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.strictEqual(body.code, 400);
    assert.match(body.message, /image.*required/i);
  });

  test('7b. Empty file (0 bytes) returns 400 Bad Request', async () => {
    const testCase = await createCase();

    const emptyBuffer = Buffer.alloc(0);
    const form = new FormData();
    form.append('image', new Blob([emptyBuffer], { type: 'image/jpeg' }), 'empty.jpg');

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
      body: form,
    });

    assert.strictEqual(res.status, 400);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.match(body.message, /empty/i);
  });

  test('8. Supported JPEG (.jpg and .jpeg) upload succeeds', async () => {
    const case1 = await createCase(technicianToken, 'PAT-JPG');
    const case2 = await createCase(technicianToken, 'PAT-JPEG');

    const form1 = new FormData();
    form1.append('image', new Blob([validJpegBuffer], { type: 'image/jpeg' }), 'retina.jpg');

    const res1 = await fetch(`${baseUrl}/api/cases/${case1.id}/image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
      body: form1,
    });
    assert.strictEqual(res1.status, 200);

    const form2 = new FormData();
    form2.append('image', new Blob([validJpegBuffer], { type: 'image/jpeg' }), 'retina.jpeg');

    const res2 = await fetch(`${baseUrl}/api/cases/${case2.id}/image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
      body: form2,
    });
    assert.strictEqual(res2.status, 200);
  });

  test('9. Supported PNG (.png) upload succeeds', async () => {
    const testCase = await createCase();

    const form = new FormData();
    form.append('image', new Blob([validPngBuffer], { type: 'image/png' }), 'fundus.png');

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
      body: form,
    });

    assert.strictEqual(res.status, 200);
    const body = await res.json();
    assert.strictEqual(body.image.mimeType, 'image/png');
    assert.strictEqual(body.image.originalName, 'fundus.png');
  });

  test('10. Unsupported file type is rejected with 400 Bad Request', async () => {
    const testCase = await createCase();

    // 1. Text file
    const textBuffer = Buffer.from('console.log("malicious code");');
    const form1 = new FormData();
    form1.append('image', new Blob([textBuffer], { type: 'text/plain' }), 'notes.txt');

    const res1 = await fetch(`${baseUrl}/api/cases/${testCase.id}/image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
      body: form1,
    });
    assert.strictEqual(res1.status, 400);
    const body1 = await res1.json();
    assert.strictEqual(body1.status, 'error');
    assert.match(body1.message, /unsupported/i);

    // 2. PDF file
    const pdfBuffer = Buffer.from('%PDF-1.4 sample content');
    const form2 = new FormData();
    form2.append('image', new Blob([pdfBuffer], { type: 'application/pdf' }), 'report.pdf');

    const res2 = await fetch(`${baseUrl}/api/cases/${testCase.id}/image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
      body: form2,
    });
    assert.strictEqual(res2.status, 400);

    // 3. Spoofed MIME with bad extension (.exe disguised as jpeg)
    const form3 = new FormData();
    form3.append('image', new Blob([validJpegBuffer], { type: 'image/jpeg' }), 'program.exe');

    const res3 = await fetch(`${baseUrl}/api/cases/${testCase.id}/image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
      body: form3,
    });
    assert.strictEqual(res3.status, 400);
  });

  test('11. Oversized file is rejected with 413 Payload Too Large', async () => {
    const testCase = await createCase();

    // Temporarily configure a small upload limit for testing
    const previousLimit = process.env.MAX_IMAGE_UPLOAD_MB;
    process.env.MAX_IMAGE_UPLOAD_MB = '1'; // 1 MB limit

    try {
      // Create a 1.5 MB buffer
      const oversizedBuffer = Buffer.alloc(1.5 * 1024 * 1024);
      const form = new FormData();
      form.append('image', new Blob([oversizedBuffer], { type: 'image/jpeg' }), 'oversized.jpg');

      const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/image`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${technicianToken}` },
        body: form,
      });

      assert.strictEqual(res.status, 413);
      const body = await res.json();
      assert.strictEqual(body.status, 'error');
      assert.strictEqual(body.code, 413);
      assert.match(body.message, /exceeds.*limit/i);
    } finally {
      if (previousLimit !== undefined) {
        process.env.MAX_IMAGE_UPLOAD_MB = previousLimit;
      } else {
        delete process.env.MAX_IMAGE_UPLOAD_MB;
      }
    }
  });

  // --------------------------------------------------------------------------
  // 4. Security
  // --------------------------------------------------------------------------
  test('12. Client cannot change case status directly via upload or patch', async () => {
    const testCase = await createCase();

    // 1. Client supplies status in multipart upload body
    const form = new FormData();
    form.append('image', new Blob([validJpegBuffer], { type: 'image/jpeg' }), 'fundus.jpg');
    form.append('status', 'completed'); // malicious attempt to jump lifecycle

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
      body: form,
    });

    assert.strictEqual(res.status, 200);
    const body = await res.json();
    // Server enforces lifecycle: status MUST become 'image_uploaded', NOT 'completed'
    assert.strictEqual(body.case.status, 'image_uploaded');

    // 2. Client attempts to mutate status via PATCH /api/cases/:id
    const patchRes = await fetch(`${baseUrl}/api/cases/${testCase.id}`, {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${technicianToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ status: 'completed' }),
    });
    assert.strictEqual(patchRes.status, 400);
  });

  test('13. Client cannot spoof uploadedBy in request body', async () => {
    const testCase = await createCase();

    const form = new FormData();
    form.append('image', new Blob([validJpegBuffer], { type: 'image/jpeg' }), 'fundus.jpg');
    form.append('uploadedBy', 'usr_fake_attacker_admin_id');

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
      body: form,
    });

    assert.strictEqual(res.status, 200);
    const body = await res.json();
    assert.notStrictEqual(body.image.uploadedBy, 'usr_fake_attacker_admin_id');
    assert.strictEqual(body.image.uploadedBy, technicianUser.id);
  });

  test('14. Uploaded image is bound strictly to req.user context', async () => {
    const testCase = await createCase(adminToken, 'PAT-ADM-BOUND');

    const form = new FormData();
    form.append('image', new Blob([validJpegBuffer], { type: 'image/jpeg' }), 'fundus.jpg');

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${adminToken}` },
      body: form,
    });

    assert.strictEqual(res.status, 200);
    const body = await res.json();
    assert.strictEqual(body.image.uploadedBy, adminUser.id);
  });

  test('15. Safe upload response never exposes secrets, tokens, or internal filesystem paths', async () => {
    const testCase = await createCase();

    const form = new FormData();
    form.append('image', new Blob([validJpegBuffer], { type: 'image/jpeg' }), 'fundus.jpg');

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
      body: form,
    });

    assert.strictEqual(res.status, 200);
    const body = await res.json();

    // Verify allowed fields exist
    assert.ok(body.case.id);
    assert.strictEqual(body.case.status, 'image_uploaded');
    assert.ok(body.image.imageId);
    assert.strictEqual(body.image.originalName, 'fundus.jpg');
    assert.strictEqual(body.image.mimeType, 'image/jpeg');
    assert.strictEqual(body.image.sizeBytes, validJpegBuffer.length);

    // Verify sensitive and internal fields are NOT exposed
    assert.strictEqual(body.token, undefined);
    assert.strictEqual(body.jwt, undefined);
    assert.strictEqual(body.password, undefined);
    assert.strictEqual(body.passwordHash, undefined);
    assert.strictEqual(body.image.storagePath, undefined);
    assert.strictEqual(body.image.filePath, undefined);
    assert.strictEqual(body.image.path, undefined);
    assert.strictEqual(body.image.destination, undefined);

    // Verify no fabricated AI fields
    assert.strictEqual(body.aiResult, undefined);
    assert.strictEqual(body.gradcam, undefined);
    assert.strictEqual(body.uncertainty, undefined);
    assert.strictEqual(body.diagnosis, undefined);
    assert.strictEqual(body.qualityScore, undefined);
  });

  // --------------------------------------------------------------------------
  // 5. Lifecycle & Re-upload
  // --------------------------------------------------------------------------
  test('16. Successful upload changes case status from "created" to "image_uploaded"', async () => {
    const testCase = await createCase();
    assert.strictEqual(testCase.status, 'created');

    const form = new FormData();
    form.append('image', new Blob([validJpegBuffer], { type: 'image/jpeg' }), 'fundus.jpg');

    const res = await fetch(`${baseUrl}/api/cases/${testCase.id}/image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
      body: form,
    });

    assert.strictEqual(res.status, 200);
    const body = await res.json();
    assert.strictEqual(body.case.status, 'image_uploaded');

    // Confirm via GET /api/cases/:id
    const verifyRes = await fetch(`${baseUrl}/api/cases/${testCase.id}`, {
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    const verifyBody = await verifyRes.json();
    assert.strictEqual(verifyBody.case.status, 'image_uploaded');
    assert.ok(verifyBody.case.image);
    assert.ok(verifyBody.case.updatedAt >= verifyBody.case.createdAt);
  });

  test('17. Failed upload does NOT change the case status', async () => {
    const testCase = await createCase();
    assert.strictEqual(testCase.status, 'created');

    // Attempt 1: Upload unsupported file type
    const form1 = new FormData();
    form1.append('image', new Blob([Buffer.from('not an image')], { type: 'text/plain' }), 'bad.txt');

    const res1 = await fetch(`${baseUrl}/api/cases/${testCase.id}/image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
      body: form1,
    });
    assert.strictEqual(res1.status, 400);

    // Verify case status has NOT transitioned
    let checkRes = await fetch(`${baseUrl}/api/cases/${testCase.id}`, {
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    let checkBody = await checkRes.json();
    assert.strictEqual(checkBody.case.status, 'created');
    assert.strictEqual(checkBody.case.image, undefined);

    // Attempt 2: Upload without file
    const form2 = new FormData();
    const res2 = await fetch(`${baseUrl}/api/cases/${testCase.id}/image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
      body: form2,
    });
    assert.strictEqual(res2.status, 400);

    // Verify case status STILL has NOT transitioned
    checkRes = await fetch(`${baseUrl}/api/cases/${testCase.id}`, {
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    checkBody = await checkRes.json();
    assert.strictEqual(checkBody.case.status, 'created');
    assert.strictEqual(checkBody.case.image, undefined);
  });

  test('18. Re-upload to already uploaded case returns 409 Conflict', async () => {
    const testCase = await createCase();

    // First upload succeeds
    const form1 = new FormData();
    form1.append('image', new Blob([validJpegBuffer], { type: 'image/jpeg' }), 'initial.jpg');

    const res1 = await fetch(`${baseUrl}/api/cases/${testCase.id}/image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
      body: form1,
    });
    assert.strictEqual(res1.status, 200);
    const body1 = await res1.json();
    const initialImageId = body1.image.imageId;

    // Second upload attempt to same case
    const form2 = new FormData();
    form2.append('image', new Blob([validPngBuffer], { type: 'image/png' }), 'second_attempt.png');

    const res2 = await fetch(`${baseUrl}/api/cases/${testCase.id}/image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${technicianToken}` },
      body: form2,
    });

    assert.strictEqual(res2.status, 409);
    const body2 = await res2.json();
    assert.strictEqual(body2.status, 'error');
    assert.strictEqual(body2.code, 409);
    assert.match(body2.message, /already has a fundus image/i);

    // Verify original image was preserved
    const checkRes = await fetch(`${baseUrl}/api/cases/${testCase.id}`, {
      headers: { Authorization: `Bearer ${technicianToken}` },
    });
    const checkBody = await checkRes.json();
    assert.strictEqual(checkBody.case.status, 'image_uploaded');
    assert.strictEqual(checkBody.case.image.imageId, initialImageId);
    assert.strictEqual(checkBody.case.image.originalName, 'initial.jpg');
  });
});
