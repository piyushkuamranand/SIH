/**
 * tests/auth.test.js — NETRA-DR Module 1 Authentication Test Suite
 *
 * Verifies all 7 required authentication scenarios + health check:
 *   1. Register new user
 *   2. Duplicate email registration rejected
 *   3. Login with correct password (receives JWT + user object)
 *   4. Login with incorrect password rejected (401)
 *   5. GET /api/auth/me without token rejected (401)
 *   6. GET /api/auth/me with invalid token rejected (401)
 *   7. GET /api/auth/me with valid token returns safe user profile (200)
 *   8. GET /api/health still returns 200
 */

'use strict';

const { test, describe, before, after } = require('node:test');
const assert = require('node:assert/strict');
const app = require('../src/app');
const UserModel = require('../src/models/user.model');

describe('NETRA-DR Module 1 — Authentication Tests', () => {
  let server;
  let baseUrl;
  let testUserToken;
  const testUser = {
    name: 'Dr. Jane Doe',
    email: 'jane.doe@netradr.org',
    password: 'SecurePassword123!',
    role: 'doctor',
  };

  before(async () => {
    // Clear user repository for fresh test state
    await UserModel.clear();

    // Start server on an ephemeral port
    await new Promise((resolve) => {
      server = app.listen(0, '127.0.0.1', () => {
        const port = server.address().port;
        baseUrl = `http://127.0.0.1:${port}`;
        resolve();
      });
    });
  });

  after(async () => {
    if (server) {
      await new Promise((resolve) => server.close(resolve));
    }
  });

  // 1. Health check verification
  test('Health check: GET /api/health returns 200 and status ok', async () => {
    const res = await fetch(`${baseUrl}/api/health`);
    assert.strictEqual(res.status, 200);

    const body = await res.json();
    assert.strictEqual(body.status, 'ok');
    assert.strictEqual(body.service, 'netra-dr-backend');
  });

  // 2. Register new user
  test('1. Register new user: POST /api/auth/register', async () => {
    const res = await fetch(`${baseUrl}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(testUser),
    });

    assert.strictEqual(res.status, 201);
    const body = await res.json();

    assert.strictEqual(body.success, true);
    assert.ok(body.user);
    assert.ok(body.user.id);
    assert.strictEqual(body.user.name, testUser.name);
    assert.strictEqual(body.user.email, testUser.email.toLowerCase());
    assert.strictEqual(body.user.role, testUser.role);
    assert.strictEqual(body.user.password, undefined, 'Password must never be returned');
    assert.strictEqual(body.user.passwordHash, undefined, 'Password hash must never be returned');
    assert.ok(body.user.createdAt);
  });

  // 3. Duplicate email
  test('2. Duplicate email: POST /api/auth/register returns 409 Conflict', async () => {
    const res = await fetch(`${baseUrl}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'Another User',
        email: testUser.email, // Same email
        password: 'AnotherPassword456!',
        role: 'technician',
      }),
    });

    assert.strictEqual(res.status, 409);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.strictEqual(body.code, 409);
    assert.match(body.message, /already exists/i);
  });

  // Validation: Missing fields or invalid role
  test('Register validation: invalid role returns 400 Bad Request', async () => {
    const res = await fetch(`${baseUrl}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'Bad Role User',
        email: 'badrole@netradr.org',
        password: 'SomePassword123!',
        role: 'superadmin', // Invalid role
      }),
    });

    assert.strictEqual(res.status, 400);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.strictEqual(body.code, 400);
  });

  // 4. Login with correct password
  test('3. Login with correct password: POST /api/auth/login returns 200 + token', async () => {
    const res = await fetch(`${baseUrl}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: testUser.email,
        password: testUser.password,
      }),
    });

    assert.strictEqual(res.status, 200);
    const body = await res.json();

    assert.strictEqual(body.success, true);
    assert.ok(typeof body.token === 'string' && body.token.length > 20);
    assert.ok(body.user);
    assert.ok(body.user.id);
    assert.strictEqual(body.user.name, testUser.name);
    assert.strictEqual(body.user.email, testUser.email.toLowerCase());
    assert.strictEqual(body.user.role, testUser.role);
    assert.strictEqual(body.user.password, undefined);
    assert.strictEqual(body.user.passwordHash, undefined);

    // Save token for subsequent /me test
    testUserToken = body.token;
  });

  // 5. Login with incorrect password
  test('4. Login with incorrect password: POST /api/auth/login returns 401 Unauthorized', async () => {
    const res = await fetch(`${baseUrl}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: testUser.email,
        password: 'WrongPassword999!',
      }),
    });

    assert.strictEqual(res.status, 401);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.strictEqual(body.code, 401);
    assert.strictEqual(body.token, undefined);
  });

  // Login with non-existent email
  test('Login with non-existent user returns 401 Unauthorized', async () => {
    const res = await fetch(`${baseUrl}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: 'nobody@netradr.org',
        password: 'SomePassword123!',
      }),
    });

    assert.strictEqual(res.status, 401);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.strictEqual(body.code, 401);
  });

  // 6. /me without token
  test('5. /me without token: GET /api/auth/me returns 401 Unauthorized', async () => {
    const res = await fetch(`${baseUrl}/api/auth/me`);

    assert.strictEqual(res.status, 401);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.strictEqual(body.code, 401);
    assert.match(body.message, /Authorization header is missing/i);
  });

  // 7. /me with invalid token
  test('6. /me with invalid token: GET /api/auth/me returns 401 Unauthorized', async () => {
    const res = await fetch(`${baseUrl}/api/auth/me`, {
      headers: {
        Authorization: 'Bearer invalid.token.signature',
      },
    });

    assert.strictEqual(res.status, 401);
    const body = await res.json();
    assert.strictEqual(body.status, 'error');
    assert.strictEqual(body.code, 401);
    assert.match(body.message, /Invalid or malformed/i);
  });

  // 8. /me with valid token
  test('7. /me with valid token: GET /api/auth/me returns 200 + safe user profile', async () => {
    assert.ok(testUserToken, 'Valid token from login test must exist');

    const res = await fetch(`${baseUrl}/api/auth/me`, {
      headers: {
        Authorization: `Bearer ${testUserToken}`,
      },
    });

    assert.strictEqual(res.status, 200);
    const body = await res.json();

    assert.strictEqual(body.success, true);
    assert.ok(body.user);
    assert.strictEqual(body.user.name, testUser.name);
    assert.strictEqual(body.user.email, testUser.email.toLowerCase());
    assert.strictEqual(body.user.role, testUser.role);
    assert.strictEqual(body.user.password, undefined);
    assert.strictEqual(body.user.passwordHash, undefined);
    assert.ok(body.user.createdAt);
    assert.ok(body.user.updatedAt);
  });
});
