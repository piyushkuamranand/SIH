/**
 * tests/image-storage.test.js — NETRA-DR Module 5 Image Storage & File Management Test Suite
 *
 * Verifies all required scenarios for Module 5:
 *
 * Storage:
 *   1.  Image is actually written to configured storage (storage/images/<caseId>/<imageId>.<ext>).
 *   2.  Server-generated filename is safe (alphanumeric UUID, no traversal).
 *   3.  Generated filename is unique across separate uploads.
 *   4.  Original filename is NOT used as storage filename (stored as metadata only).
 *   5.  Correct file extension (.jpg, .jpeg, .png) is preserved in storage filename.
 *   6.  Correct MIME metadata is stored.
 *   7.  Size metadata matches actual bytes written.
 *   8.  imageExists() returns true for stored image, false for nonexistent.
 *   9.  getImageStats() returns accurate file stats.
 *  10.  getImagePath() returns absolute path for existing image, null for nonexistent.
 *
 * Security:
 *  11.  Path traversal in caseId is rejected (../, ..\, ../../, encoded %2e).
 *  12.  Absolute filesystem paths in caseId or paths cannot be injected.
 *  13.  Malicious original filenames cannot control storage path or stored filename.
 *  14.  deleteImage() rejects path traversal attempts without deleting unrelated files.
 *  15.  getImagePath() rejects path traversal attempts.
 *  16.  imageExists() safely rejects path traversal attempts.
 *
 * Lifecycle:
 *  17.  Successful HTTP upload writes image to storage/images/<caseId>/ and updates case status.
 *  18.  Failed case association rolls back and cleans up the stored file.
 *  19.  Duplicate image upload attempt does not overwrite original stored file (returns 409).
 *
 * Cleanup:
 *  20.  deleteImage() removes only the intended image and cleans empty case directory.
 *  21.  Nonexistent image deletion is handled safely (returns false, no throw).
 *  22.  Cleanup does not delete unrelated case files or other case directories.
 */

'use strict';

const { test, describe, before, after, beforeEach } = require('node:test');
const assert = require('node:assert/strict');
const fs     = require('fs');
const path   = require('path');
const app    = require('../src/app');
const UserModel = require('../src/models/user.model');
const CaseModel = require('../src/models/case.model');
const ImageStorageService = require('../src/services/image-storage.service');
const paths  = require('../src/config/paths');
const { ROLES } = require('../src/config/roles');
const { safeUnlink } = require('../src/utils/file.utils');

describe('NETRA-DR Module 5 — Image Storage & File Management Tests', () => {
  let server;
  let baseUrl;
  let technicianToken;
  let technicianUser;

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

  /**
   * Helper: Clean all files and directories in storage/images/ except .gitkeep
   */
  const cleanStorage = () => {
    try {
      if (fs.existsSync(paths.IMAGES_DIR)) {
        const entries = fs.readdirSync(paths.IMAGES_DIR);
        for (const entry of entries) {
          if (entry !== '.gitkeep') {
            safeUnlink(path.join(paths.IMAGES_DIR, entry));
          }
        }
      }
      if (paths.TEMP_DIR && fs.existsSync(paths.TEMP_DIR)) {
        const tempEntries = fs.readdirSync(paths.TEMP_DIR);
        for (const entry of tempEntries) {
          if (entry !== '.gitkeep') {
            safeUnlink(path.join(paths.TEMP_DIR, entry));
          }
        }
      }
    } catch (_err) {}
  };

  before(async () => {
    await UserModel.clear();
    await CaseModel.clear();
    cleanStorage();

    await new Promise((resolve) => {
      server = app.listen(0, '127.0.0.1', () => {
        baseUrl = `http://127.0.0.1:${server.address().port}`;
        resolve();
      });
    });

    // Register technician
    const regRes = await fetch(`${baseUrl}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'Storage Tech',
        email: 'storage.tech@netradr.org',
        password: 'TechPassword2026!',
        role: ROLES.TECHNICIAN,
      }),
    });
    const regBody = await regRes.json();
    technicianUser = regBody.user;

    const loginRes = await fetch(`${baseUrl}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: 'storage.tech@netradr.org',
        password: 'TechPassword2026!',
      }),
    });
    const loginBody = await loginRes.json();
    technicianToken = loginBody.token;
  });

  after(async () => {
    if (server) {
      await new Promise((resolve) => server.close(resolve));
    }
    cleanStorage();
  });

  beforeEach(async () => {
    await CaseModel.clear();
    cleanStorage();
  });

  // ==========================================================================
  // 1. Storage Operations
  // ==========================================================================
  describe('1. Storage Operations', () => {
    test('1. Image is actually written to storage/images/<caseId>/<imageId>.<ext>', async () => {
      const caseId = 'case_11111111-1111-4111-8111-111111111111';
      const result = await ImageStorageService.saveImage({
        buffer: validJpegBuffer,
        originalName: 'patient_retina_left.jpg',
        mimeType: 'image/jpeg',
        caseId,
        uploadedBy: technicianUser.id,
      });

      assert.ok(result.imageId);
      assert.strictEqual(result.caseId, caseId);
      assert.strictEqual(result.originalName, 'patient_retina_left.jpg');
      assert.strictEqual(result.mimeType, 'image/jpeg');
      assert.strictEqual(result.extension, '.jpg');
      assert.strictEqual(result.sizeBytes, validJpegBuffer.length);
      assert.strictEqual(result.storedFilename, `${result.imageId}.jpg`);

      // Verify the file physically exists on the disk in case subdirectory
      const expectedDir = path.join(paths.IMAGES_DIR, caseId);
      const expectedPath = path.join(expectedDir, result.storedFilename);
      assert.ok(fs.existsSync(expectedDir), 'Case directory should exist');
      assert.ok(fs.existsSync(expectedPath), 'Image file should physically exist in case directory');

      const fileContent = fs.readFileSync(expectedPath);
      assert.deepStrictEqual(fileContent, validJpegBuffer);
    });

    test('2. Server-generated stored filename is safe (UUID-based, no path separators)', async () => {
      const caseId = 'case_22222222-2222-4222-8222-222222222222';
      const result = await ImageStorageService.saveImage({
        buffer: validPngBuffer,
        originalName: '../../etc/passwd.png',
        mimeType: 'image/png',
        caseId,
        uploadedBy: technicianUser.id,
      });

      assert.match(result.storedFilename, /^img_[0-9a-f-]{36}\.png$/i);
      assert.strictEqual(result.storedFilename.includes('/'), false);
      assert.strictEqual(result.storedFilename.includes('\\'), false);
      assert.strictEqual(result.storedFilename.includes('..'), false);
    });

    test('3. Generated filename is unique across separate uploads', async () => {
      const case1 = 'case_33333333-3333-4333-8333-333333333331';
      const case2 = 'case_33333333-3333-4333-8333-333333333332';

      const res1 = await ImageStorageService.saveImage({
        buffer: validJpegBuffer,
        originalName: 'same_name.jpg',
        mimeType: 'image/jpeg',
        caseId: case1,
        uploadedBy: technicianUser.id,
      });

      const res2 = await ImageStorageService.saveImage({
        buffer: validJpegBuffer,
        originalName: 'same_name.jpg',
        mimeType: 'image/jpeg',
        caseId: case2,
        uploadedBy: technicianUser.id,
      });

      assert.notStrictEqual(res1.imageId, res2.imageId);
      assert.notStrictEqual(res1.storedFilename, res2.storedFilename);
    });

    test('4. Original client filename is not used as storage filename', async () => {
      const caseId = 'case_44444444-4444-4444-8444-444444444444';
      const clientName = 'custom_fundus_photo_2026.jpg';

      const result = await ImageStorageService.saveImage({
        buffer: validJpegBuffer,
        originalName: clientName,
        mimeType: 'image/jpeg',
        caseId,
        uploadedBy: technicianUser.id,
      });

      assert.notStrictEqual(result.storedFilename, clientName);
      assert.strictEqual(result.originalName, clientName);

      const caseDir = path.join(paths.IMAGES_DIR, caseId);
      assert.strictEqual(fs.existsSync(path.join(caseDir, clientName)), false);
      assert.strictEqual(fs.existsSync(path.join(caseDir, result.storedFilename)), true);
    });

    test('5. Correct extension is preserved (.jpg, .jpeg, .png)', async () => {
      const cases = [
        { id: 'case_55555555-5555-4555-8555-555555555551', name: 'img1.jpg', mime: 'image/jpeg', ext: '.jpg', buf: validJpegBuffer },
        { id: 'case_55555555-5555-4555-8555-555555555552', name: 'img2.jpeg', mime: 'image/jpeg', ext: '.jpeg', buf: validJpegBuffer },
        { id: 'case_55555555-5555-4555-8555-555555555553', name: 'img3.png', mime: 'image/png', ext: '.png', buf: validPngBuffer },
      ];

      for (const item of cases) {
        const res = await ImageStorageService.saveImage({
          buffer: item.buf,
          originalName: item.name,
          mimeType: item.mime,
          caseId: item.id,
          uploadedBy: technicianUser.id,
        });
        assert.strictEqual(res.extension, item.ext);
        assert.ok(res.storedFilename.endsWith(item.ext));
      }
    });

    test('6. Correct MIME metadata is stored and validated', async () => {
      const caseId = 'case_66666666-6666-4666-8666-666666666666';
      const result = await ImageStorageService.saveImage({
        buffer: validJpegBuffer,
        originalName: 'retina.jpg',
        mimeType: 'image/jpeg',
        caseId,
        uploadedBy: technicianUser.id,
      });

      assert.strictEqual(result.mimeType, 'image/jpeg');

      // Attempt unsupported MIME
      await assert.rejects(
        () => ImageStorageService.saveImage({
          buffer: Buffer.from('bad'),
          originalName: 'bad.txt',
          mimeType: 'text/plain',
          caseId: 'case_66666666-6666-4666-8666-666666666667',
          uploadedBy: technicianUser.id,
        }),
        /unsupported mime type/i
      );
    });

    test('7. Size metadata matches actual bytes written', async () => {
      const caseId = 'case_77777777-7777-4777-8777-777777777777';
      const result = await ImageStorageService.saveImage({
        buffer: validJpegBuffer,
        originalName: 'retina.jpg',
        mimeType: 'image/jpeg',
        caseId,
        uploadedBy: technicianUser.id,
      });

      assert.strictEqual(result.sizeBytes, validJpegBuffer.length);
      const stats = fs.statSync(result.storagePath);
      assert.strictEqual(stats.size, result.sizeBytes);
    });

    test('8. imageExists() accurately reports image existence', async () => {
      const caseId = 'case_88888888-8888-4888-8888-888888888888';
      const res = await ImageStorageService.saveImage({
        buffer: validJpegBuffer,
        originalName: 'retina.jpg',
        mimeType: 'image/jpeg',
        caseId,
        uploadedBy: technicianUser.id,
      });

      const exists = await ImageStorageService.imageExists(caseId, res.imageId);
      assert.strictEqual(exists, true);

      const nonexistent = await ImageStorageService.imageExists(caseId, 'img_00000000-0000-0000-0000-000000000000');
      assert.strictEqual(nonexistent, false);

      const nonexistentCase = await ImageStorageService.imageExists('case_00000000-0000-0000-0000-000000000000', res.imageId);
      assert.strictEqual(nonexistentCase, false);
    });

    test('9. getImageStats() returns accurate file stats', async () => {
      const caseId = 'case_99999999-9999-4999-8999-999999999999';
      const res = await ImageStorageService.saveImage({
        buffer: validPngBuffer,
        originalName: 'retina.png',
        mimeType: 'image/png',
        caseId,
        uploadedBy: technicianUser.id,
      });

      const stats = await ImageStorageService.getImageStats(caseId, res.imageId);
      assert.ok(stats);
      assert.strictEqual(stats.size, validPngBuffer.length);
      assert.ok(stats.birthtime instanceof Date || typeof stats.birthtimeMs === 'number');

      const nonStats = await ImageStorageService.getImageStats(caseId, 'img_00000000-0000-0000-0000-000000000000');
      assert.strictEqual(nonStats, null);
    });

    test('10. getImagePath() returns absolute path for existing image, null for nonexistent', async () => {
      const caseId = 'case_aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
      const res = await ImageStorageService.saveImage({
        buffer: validJpegBuffer,
        originalName: 'retina.jpg',
        mimeType: 'image/jpeg',
        caseId,
        uploadedBy: technicianUser.id,
      });

      const foundPath = await ImageStorageService.getImagePath(caseId, res.imageId);
      assert.ok(foundPath);
      assert.strictEqual(path.isAbsolute(foundPath), true);
      assert.strictEqual(fs.existsSync(foundPath), true);

      const notFound = await ImageStorageService.getImagePath(caseId, 'img_00000000-0000-0000-0000-000000000000');
      assert.strictEqual(notFound, null);
    });
  });

  // ==========================================================================
  // 2. Security & Traversal Protection
  // ==========================================================================
  describe('2. Security & Traversal Protection', () => {
    test('11. Path traversal in caseId is rejected', async () => {
      const maliciousCases = [
        '../evil',
        '..\\evil',
        '../../etc/passwd',
        'case_123/../../escape',
        'case_123\\..\\..\\escape',
        'case_123%2e%2e%2fescape',
        'case_123\0nullbyte',
      ];

      for (const badCase of maliciousCases) {
        await assert.rejects(
          () => ImageStorageService.saveImage({
            buffer: validJpegBuffer,
            originalName: 'test.jpg',
            mimeType: 'image/jpeg',
            caseId: badCase,
            uploadedBy: technicianUser.id,
          }),
          /traversal|invalid.*case/i
        );
      }
    });

    test('12. Absolute filesystem paths and Windows drive paths cannot be injected as caseId', async () => {
      const badPaths = [
        'C:\\Windows\\System32',
        'D:\\storage',
        '/etc/shadow',
        '\\\\server\\share',
      ];

      for (const badPath of badPaths) {
        await assert.rejects(
          () => ImageStorageService.saveImage({
            buffer: validJpegBuffer,
            originalName: 'test.jpg',
            mimeType: 'image/jpeg',
            caseId: badPath,
            uploadedBy: technicianUser.id,
          }),
          /invalid.*case|traversal/i
        );
      }
    });

    test('13. Malicious original filenames cannot control storage path or stored filename', async () => {
      const caseId = 'case_bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
      const maliciousNames = [
        '../../../boot.ini.jpg',
        '..\\..\\windows\\system.ini.jpg',
        'shell.php.jpg',
        'foo/bar/baz.png',
      ];

      for (const name of maliciousNames) {
        const uniqueCase = `case_${crypto.randomUUID()}`;
        const res = await ImageStorageService.saveImage({
          buffer: validJpegBuffer,
          originalName: name,
          mimeType: 'image/jpeg',
          caseId: uniqueCase,
          uploadedBy: technicianUser.id,
        });

        // Destination must strictly be inside storage/images/<uniqueCase>/
        const expectedDir = path.resolve(paths.IMAGES_DIR, uniqueCase);
        assert.strictEqual(path.dirname(res.storagePath), expectedDir);
        assert.match(res.storedFilename, /^img_[0-9a-f-]{36}\.(jpg|jpeg|png)$/i);
        assert.strictEqual(res.storedFilename.includes('..'), false);
      }
    });

    test('14. deleteImage() rejects path traversal attempts without deleting unrelated files', async () => {
      // First write a legitimate image
      const safeCase = 'case_cccccccc-cccc-4ccc-8ccc-cccccccccccc';
      const res = await ImageStorageService.saveImage({
        buffer: validJpegBuffer,
        originalName: 'retina.jpg',
        mimeType: 'image/jpeg',
        caseId: safeCase,
        uploadedBy: technicianUser.id,
      });

      // Attempt traversal deletion
      await assert.rejects(
        () => ImageStorageService.deleteImage('../../images', res.imageId),
        /traversal|invalid/i
      );

      await assert.rejects(
        () => ImageStorageService.deleteImage(safeCase, '../../evil'),
        /traversal|invalid/i
      );

      // Verify legitimate file was NOT deleted by the attack
      const stillExists = await ImageStorageService.imageExists(safeCase, res.imageId);
      assert.strictEqual(stillExists, true);
    });

    test('15. getImagePath() rejects path traversal attempts', async () => {
      await assert.rejects(
        () => ImageStorageService.getImagePath('../escaped', 'img_12345'),
        /traversal|invalid/i
      );

      await assert.rejects(
        () => ImageStorageService.getImagePath('case_12345', '../../evil'),
        /traversal|invalid/i
      );
    });

    test('16. imageExists() safely returns false on traversal attempts without throwing or escaping', async () => {
      const res1 = await ImageStorageService.imageExists('../../../etc', 'img_test');
      assert.strictEqual(res1, false);

      const res2 = await ImageStorageService.imageExists('case_valid', '../../test');
      assert.strictEqual(res2, false);
    });
  });

  // ==========================================================================
  // 3. Lifecycle & Failure Rollback
  // ==========================================================================
  describe('3. Lifecycle & Failure Rollback', () => {
    test('17. Successful HTTP upload writes image to storage/images/<caseId>/ and updates case status', async () => {
      // 1. Create a case
      const createRes = await fetch(`${baseUrl}/api/cases`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${technicianToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ patientId: 'PAT-STOR-001' }),
      });
      const createBody = await createRes.json();
      const testCase = createBody.case;

      // 2. Upload image via HTTP
      const form = new FormData();
      form.append('image', new Blob([validJpegBuffer], { type: 'image/jpeg' }), 'left_eye.jpg');

      const uploadRes = await fetch(`${baseUrl}/api/cases/${testCase.id}/image`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${technicianToken}` },
        body: form,
      });

      assert.strictEqual(uploadRes.status, 200);
      const uploadBody = await uploadRes.json();
      assert.strictEqual(uploadBody.success, true);
      assert.strictEqual(uploadBody.case.status, 'image_uploaded');
      assert.ok(uploadBody.image.imageId);
      assert.strictEqual(uploadBody.image.storedFilename, `${uploadBody.image.imageId}.jpg`);
      assert.strictEqual(uploadBody.image.extension, '.jpg');

      // Verify the image file was written to disk in storage/images/<caseId>/<imageId>.jpg
      const caseDir = path.join(paths.IMAGES_DIR, testCase.id);
      const storedPath = path.join(caseDir, uploadBody.image.storedFilename);
      assert.strictEqual(fs.existsSync(storedPath), true);

      // Verify raw model association
      const rawCase = await CaseModel.getRawById(testCase.id);
      assert.strictEqual(rawCase.status, 'image_uploaded');
      assert.strictEqual(rawCase.image.imageId, uploadBody.image.imageId);
      assert.strictEqual(rawCase.image.storedFilename, uploadBody.image.storedFilename);
      assert.strictEqual(rawCase.image.storagePath, storedPath);
    });

    test('18. Failed case association rolls back and cleans up the stored file', async () => {
      // 1. Create case in model
      const createdCase = await CaseModel.create({ patientId: 'PAT-FAIL-TEST', createdBy: technicianUser.id });
      const caseId = createdCase.id;

      // 2. Simulate a failure in attaching image metadata
      const originalAttach = CaseModel.attachImage;
      CaseModel.attachImage = async () => {
        throw new Error('Simulated database write failure during image attachment');
      };

      try {
        const form = new FormData();
        form.append('image', new Blob([validJpegBuffer], { type: 'image/jpeg' }), 'retina_fail.jpg');

        const res = await fetch(`${baseUrl}/api/cases/${caseId}/image`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${technicianToken}` },
          body: form,
        });

        assert.strictEqual(res.status, 500);

        // Verify the file was cleaned up and does not linger in storage/images/<caseId>/
        const caseDir = path.join(paths.IMAGES_DIR, caseId);
        if (fs.existsSync(caseDir)) {
          const files = fs.readdirSync(caseDir).filter(f => !f.startsWith('.'));
          assert.strictEqual(files.length, 0, 'No orphaned file should remain in case directory after rollback');
        }
      } finally {
        CaseModel.attachImage = originalAttach;
      }
    });

    test('19. Duplicate image upload attempt does not overwrite original stored file (returns 409)', async () => {
      // 1. Create case
      const createRes = await fetch(`${baseUrl}/api/cases`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${technicianToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ patientId: 'PAT-DUP-TEST' }),
      });
      const createBody = await createRes.json();
      const testCase = createBody.case;

      // 2. First upload succeeds
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
      const initialStoredFile = path.join(paths.IMAGES_DIR, testCase.id, body1.image.storedFilename);
      assert.strictEqual(fs.existsSync(initialStoredFile), true);

      // 3. Second upload attempt to same case is rejected with 409 Conflict
      const form2 = new FormData();
      form2.append('image', new Blob([validPngBuffer], { type: 'image/png' }), 'attempt2.png');
      const res2 = await fetch(`${baseUrl}/api/cases/${testCase.id}/image`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${technicianToken}` },
        body: form2,
      });
      assert.strictEqual(res2.status, 409);

      // 4. Verify initial image was preserved unmodified
      assert.strictEqual(fs.existsSync(initialStoredFile), true);
      const caseFiles = fs.readdirSync(path.join(paths.IMAGES_DIR, testCase.id)).filter(f => !f.startsWith('.'));
      assert.strictEqual(caseFiles.length, 1);
      assert.strictEqual(caseFiles[0], body1.image.storedFilename);
    });
  });

  // ==========================================================================
  // 4. Cleanup & File Deletion
  // ==========================================================================
  describe('4. Cleanup & File Deletion', () => {
    test('20. deleteImage() removes only the intended image and cleans empty case directory', async () => {
      const caseId = 'case_eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee';
      const res = await ImageStorageService.saveImage({
        buffer: validJpegBuffer,
        originalName: 'to_delete.jpg',
        mimeType: 'image/jpeg',
        caseId,
        uploadedBy: technicianUser.id,
      });

      const caseDir = path.join(paths.IMAGES_DIR, caseId);
      assert.strictEqual(fs.existsSync(res.storagePath), true);

      // Delete image
      const deleted = await ImageStorageService.deleteImage(caseId, res.imageId);
      assert.strictEqual(deleted, true);

      // Verify file is gone
      assert.strictEqual(fs.existsSync(res.storagePath), false);

      // Verify empty case directory was pruned
      assert.strictEqual(fs.existsSync(caseDir), false);
    });

    test('21. Nonexistent image deletion is handled safely (returns false, no throw)', async () => {
      const deleted1 = await ImageStorageService.deleteImage(
        'case_ffffffff-ffff-4fff-8fff-ffffffffffff',
        'img_00000000-0000-0000-0000-000000000000'
      );
      assert.strictEqual(deleted1, false);

      // Existing case directory but non-existent imageId
      const caseId = 'case_12121212-1212-4212-8212-121212121212';
      await ImageStorageService.saveImage({
        buffer: validJpegBuffer,
        originalName: 'sample.jpg',
        mimeType: 'image/jpeg',
        caseId,
        uploadedBy: technicianUser.id,
      });

      const deleted2 = await ImageStorageService.deleteImage(caseId, 'img_99999999-9999-4999-8999-999999999999');
      assert.strictEqual(deleted2, false);
    });

    test('22. Cleanup does not delete unrelated case files or other case directories', async () => {
      const caseA = 'case_aaaaaaaa-1111-4aaa-8aaa-aaaaaaaaaaaa';
      const caseB = 'case_bbbbbbbb-2222-4bbb-8bbb-bbbbbbbbbbbb';

      const resA = await ImageStorageService.saveImage({
        buffer: validJpegBuffer,
        originalName: 'retina_a.jpg',
        mimeType: 'image/jpeg',
        caseId: caseA,
        uploadedBy: technicianUser.id,
      });

      const resB = await ImageStorageService.saveImage({
        buffer: validPngBuffer,
        originalName: 'retina_b.png',
        mimeType: 'image/png',
        caseId: caseB,
        uploadedBy: technicianUser.id,
      });

      // Delete only image for caseA
      const deletedA = await ImageStorageService.deleteImage(caseA, resA.imageId);
      assert.strictEqual(deletedA, true);

      // Verify caseA file is gone
      assert.strictEqual(fs.existsSync(resA.storagePath), false);

      // Verify caseB file remains intact!
      assert.strictEqual(fs.existsSync(resB.storagePath), true);
      const existsB = await ImageStorageService.imageExists(caseB, resB.imageId);
      assert.strictEqual(existsB, true);
    });
  });
});
