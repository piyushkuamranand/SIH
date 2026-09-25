# NETRA-DR Backend Integration PRD: AI/ML Pipeline & EyeQ Service Boundary

**Document Version:** 1.0.0  
**Date:** September 2026  
**Project:** NETRA-DR (SIH Problem Statement: 26038)  
**Target Audience:** AI/ML Engineers, Python Pipeline Developers, EyeQ Integration Specialists, Backend Engineers  
**Target Repository Directory:** `SIH/backend/`  
**Referenced AI Implementation:** `SIH/app/app.py`, `SIH/pipeline/quality_service.py`, `SIH/external/EyeQ/`  

---

## 1. Executive Summary

This Product Requirements Document (PRD) provides an exhaustive, code-level architectural audit and integration specification for connecting external AI/ML services (specifically the EyeQ retinal fundus quality assessment model and subsequent diagnostic pipelines) to the NETRA-DR Node.js/Express backend.

Modules 1 through 7 of the NETRA-DR backend are **fully implemented, passing 100% of integration and unit tests (137 tests across 11 test suites), and must NOT be redesigned, refactored, or broken**.

### The Golden Rule for AI/ML Integration
> [!IMPORTANT]
> **"You do NOT need to modify the Node.js backend unless the existing contract is technically impossible to satisfy."**
> 
> The Node.js backend acts as a strict, secure HTTP client and orchestration supervisor. It handles user authentication, role-based access control (RBAC), fundus image ingestion, safe filesystem storage, request tracing, and database persistence. It delegates inference to an independent Python/Flask microservice via standard HTTP multipart requests and expects a predictable JSON response envelope.

---

## 2. Scope

### In Scope
1. **Architectural Audit:** Full recursive audit of `SIH/backend/` source code, configuration, models, middleware, and tests.
2. **Lifecycle Trace:** End-to-end tracing of fundus image upload, validation, physical persistence, AI orchestration, result sanitization, and database persistence.
3. **Module 6 Contract:** Exact network and payload specifications for Node.js `AIService` dispatching inference to Flask.
4. **Module 7 Contract:** Persistence schemas, idempotency indexes, and retrieval envelopes for `AIResultService` and `AIResultModel`.
5. **AI/ML Developer Handoff:** Step-by-step instructions for implementing or adapting the Flask AI adapter to satisfy Node.js expectations.
6. **EyeQ-Specific Integration:** Detailed boundary definitions between PyTorch/EyeQ model execution and Flask HTTP serialization.
7. **Portability & Test Plan:** Complete setup instructions and 5-level test protocol to verify cross-computer deployment.

### Explicit Non-Goals (Out of Scope)
- Modifying or refactoring any existing JavaScript code in `SIH/backend/`.
- Creating Module 8 (Report Generation) or Module 10 (Doctor Review Override).
- Expanding the Node.js Module 6 inference orchestration beyond the current Phase 1 Quality Gate contract without explicit authorization.
- Committing secrets, mock credentials, or internal file paths into version control.

---

## 3. Existing Backend Architecture

The NETRA-DR backend adopts a layered MVC/Service-Repository architecture built on Node.js (>=18.0.0) and Express (4.19.2).

```
Client (Web / Mobile / Device)
      │
      │ HTTP (Bearer JWT)
      ▼
Backend Entrypoint (`backend/src/server.js` → `backend/src/app.js`)
      │
      ├─ Middleware: morgan (logging) → cors → express.json({ limit: '50mb' }) → express.urlencoded()
      ▼
Route Registration Layer (`backend/src/routes/*.routes.js`)
      │
      ├─ Auth Middleware (`backend/src/middleware/auth.middleware.js` → requireAuth)
      ├─ RBAC Middleware (`backend/src/middleware/auth.middleware.js` → authorize(...))
      ├─ Upload Middleware (`backend/src/middleware/upload.middleware.js` → handleImageUpload)
      ▼
Controller Layer (`backend/src/controllers/*.controller.js`)
      │
      ├─ Input Validation (`backend/src/utils/validation.js`)
      ▼
Service Layer (`backend/src/services/*.service.js`)
      ├─ Image Storage (`backend/src/services/image-storage.service.js`)
      │       └── Writes to `backend/storage/images/<caseId>/<imageId>.<ext>`
      ├─ AI Orchestration (`backend/src/services/ai.service.js`)
      │       └── Dispatches HTTP POST multipart/form-data via native fetch
      └─ AI Results Persistence (`backend/src/services/ai-result.service.js`)
              └── Sanitizes inference payload and orchestrates state transition
      ▼
Model / Repository Abstraction (`backend/src/models/*.model.js`)
      ├─ `user.model.js`      (User accounts, bcrypt password hashes, roles)
      ├─ `case.model.js`      (Screening case workflows, image metadata, lifecycle state)
      └─ `ai-result.model.js` (Inference results indexed by resultId, caseId, inferenceRequestId)
      ▼
External AI Service Boundary
      Node.js `AIService` ──[HTTP POST multipart/form-data]──► Python/Flask AI Service (`/api/quality`)
```

### Component Inventory & Responsibilities

| Component | Exact File Path | Exported Symbols | Responsibilities | Upstream Caller | Downstream Dependency |
|---|---|---|---|---|---|
| **Server Entrypoint** | `backend/src/server.js` | `server` (HTTP Server) | Loads `.env`, binds Express to HOST:PORT, manages graceful shutdown (SIGINT/SIGTERM). | Node runtime | `backend/src/app.js`, `backend/src/config/env.js`, `backend/src/utils/logger.js` |
| **Express App Factory** | `backend/src/app.js` | `app` (Express App) | Configures logging, CORS, body parsers, registers all routers, 404 handler, and error handler. | `backend/src/server.js`, Test suites | `backend/src/routes/*`, `backend/src/middleware/error.middleware.js` |
| **Environment Config** | `backend/src/config/env.js` | `env` object | Centralized configuration for ports, AI URLs, timeouts, JWT secrets, upload limits. | All services and controllers | `process.env` |
| **Path Resolution** | `backend/src/config/paths.js` | `paths` object | Resolves absolute paths for backend roots, storage folders, and read-only Python paths. | Services, storage | Node `path` |
| **Role Definitions** | `backend/src/config/roles.js` | `ROLES`, `VALID_ROLES` | Freezes valid role strings (`technician`, `doctor`, `admin`). | Routes, middleware, controllers | None |
| **Auth Middleware** | `backend/src/middleware/auth.middleware.js` | `requireAuth`, `authorize` | Validates JWT tokens, extracts claims, attaches `req.user`, enforces RBAC permissions. | All protected routes | `backend/src/utils/jwt.utils.js`, `backend/src/models/user.model.js` |
| **Upload Middleware** | `backend/src/middleware/upload.middleware.js` | `handleImageUpload`, `upload` | Multer staging in `storage/temp/`, verifies MIME types and 32MB file size limits. | `cases.routes.js` | `multer`, `backend/src/config/paths.js` |
| **Error Middleware** | `backend/src/middleware/error.middleware.js` | `errorHandler` | Catches `next(err)` across all controllers; formats clean JSON responses; hides stack traces in prod. | `backend/src/app.js` | `backend/src/utils/logger.js` |
| **Cases Controller** | `backend/src/controllers/cases.controller.js` | `createCase`, `listCases`, `getCaseById`, `updateCase`, `validateCaseForUpload`, `uploadCaseImage`, `runCaseInference`, `getCaseAiResult` | HTTP handlers for screening case workflows, validation, and lifecycle coordination. | `cases.routes.js` | `case.model.js`, `image-storage.service.js`, `ai.controller.js` |
| **AI Controller** | `backend/src/controllers/ai.controller.js` | `runCaseInference`, `getCaseAiResult` | Coordinates Module 6 inference execution and Module 7 persistence; maps AI HTTP errors to 502/503/504. | `cases.controller.js`, `cases.routes.js` | `ai.service.js`, `ai-result.service.js`, `case.model.js`, `image-storage.service.js` |
| **Image Storage Service** | `backend/src/services/image-storage.service.js` | `ImageStorageService` | Moves staged uploads into `storage/images/<caseId>/<imageId>.<ext>`, asserts path safety, handles deletion. | `cases.controller.js`, `ai.service.js` | Node `fs`, Node `crypto`, `paths.js` |
| **AI Orchestration Service** | `backend/src/services/ai.service.js` | `AIService`, Error classes | Reads binary image from disk, creates `FormData`, executes HTTP fetch to Flask, handles timeouts. | `ai.controller.js` | Node `fs`, Node `fetch`, `image-storage.service.js`, `config/env.js` |
| **AI Result Service** | `backend/src/services/ai-result.service.js` | `AIResultService` | Validates IDs, checks idempotency, sanitizes inference payload (removes paths/secrets), updates case status. | `ai.controller.js` | `ai-result.model.js`, `case.model.js`, `validation.js` |
| **Case Model / Repo** | `backend/src/models/case.model.js` | `CaseModel`, `CASE_STATUS` | In-memory repository abstraction for screening cases and attached image metadata. | Controllers, services | Node `crypto` |
| **AI Result Model / Repo** | `backend/src/models/ai-result.model.js` | `AIResultModel`, `RESULT_STATUS` | In-memory repository abstraction for AI results indexed by `resultId`, `caseId`, and `inferenceRequestId`. | `ai-result.service.js` | Node `crypto` |

---

## 4. Repository Structure

```text
SIH/backend/
├── .env                              # Active local environment configuration (git-ignored)
├── .env.example                      # Template defining required environment variables
├── .gitignore                        # Git ignore rules for node_modules, storage, logs, .env
├── package.json                      # Node.js project manifest, dependencies, test scripts
├── package-lock.json                 # Pinned dependency tree
├── README.md                         # Backend service overview and quick start guide
├── storage/                          # Persistent server storage directory
│   ├── heatmaps/                     # Destination for future explainability Grad-CAM heatmaps
│   ├── images/                       # Case-partitioned fundus storage: storage/images/<caseId>/<imageId>.<ext>
│   ├── masks/                        # Destination for future vessel/lesion segmentation masks
│   ├── reports/                      # Destination for future generated clinical PDF reports
│   └── temp/                         # Staging directory for Multer in-flight uploads
├── src/
│   ├── app.js                        # Express app initialization, middleware, router mount points
│   ├── server.js                     # HTTP server startup, port binding, graceful shutdown
│   ├── config/
│   │   ├── env.js                    # Parsed environment settings with sensible fallbacks
│   │   ├── paths.js                  # Absolute filesystem path resolution (backend & python roots)
│   │   └── roles.js                  # Centralized user role definitions (technician, doctor, admin)
│   ├── controllers/
│   │   ├── ai.controller.js          # POST /api/cases/:id/ai, GET /api/cases/:id/ai-result
│   │   ├── auth.controller.js        # POST /api/auth/register, POST /api/auth/login, GET /api/auth/me
│   │   ├── cases.controller.js       # CRUD operations for screening cases and image uploads
│   │   ├── health.controller.js      # GET /api/health system liveness endpoint
│   │   ├── reports.controller.js     # Stub handlers (501) for PDF clinical reports
│   │   ├── screening.controller.js   # Stub handlers (501) for legacy screening routes
│   │   └── simulation.controller.js  # Stub handlers (501) for MATLAB sweep simulation routes
│   ├── db/
│   │   ├── connection.js             # Database connection stub (prepared for future MongoDB/SQLite)
│   │   └── schema.js                 # Database schema placeholder
│   ├── middleware/
│   │   ├── auth.middleware.js        # requireAuth (JWT token verification) & authorize (RBAC guard)
│   │   ├── error.middleware.js       # Centralized 4-argument Express error handler
│   │   └── upload.middleware.js      # Multer multipart/form-data upload middleware
│   ├── models/
│   │   ├── ai-result.model.js        # AI inference persistence repository and safe projection
│   │   ├── case.model.js             # Screening case repository and lifecycle status transitions
│   │   ├── review.model.js           # Stub placeholder for doctor review entity
│   │   └── user.model.js             # User account repository and password hashing abstractions
│   ├── routes/
│   │   ├── auth.routes.js            # /api/auth/* endpoints
│   │   ├── cases.routes.js           # /api/cases/* endpoints (creation, upload, AI inference, results)
│   │   ├── health.routes.js          # /api/health endpoint
│   │   ├── reports.routes.js         # /api/reports/* stubs
│   │   ├── screening.routes.js       # /api/screening/* stubs
│   │   └── simulation.routes.js      # /api/simulation/* stubs
│   ├── services/
│   │   ├── ai.service.js             # Module 6 AI inference orchestration (HTTP fetch to Flask)
│   │   ├── ai-result.service.js      # Module 7 AI result persistence, sanitization, idempotency
│   │   ├── image-storage.service.js  # Module 5 file management and directory traversal protection
│   │   ├── confidence.service.js     # Stub placeholder for uncertainty calibration
│   │   ├── explainability.service.js # Stub placeholder for Grad-CAM overlay generation
│   │   ├── grading.service.js        # Stub placeholder for DR grading service
│   │   ├── preprocessing.service.js  # Stub placeholder for image resizing/normalization
│   │   ├── quality.service.js        # Stub placeholder for direct quality assessment
│   │   ├── report.service.js         # Stub placeholder for PDF report compilation
│   │   ├── screening.service.js      # Stub placeholder for multi-phase screening
│   │   ├── segmentation.service.js   # Stub placeholder for vessel/lesion segmentation
│   │   └── simulation.service.js     # Stub placeholder for MATLAB simulation
│   └── utils/
│       ├── file.utils.js             # Safe unlinking, directory creation, file stat helpers
│       ├── jwt.utils.js              # Cryptographic JWT signing and verification helpers
│       ├── logger.js                 # Winston logger configured for dev colorization and prod JSON
│       └── validation.js             # Regular expressions, ID validators, payload checkers
└── tests/
    ├── ai-inference.test.js          # Module 6 test suite (20 tests covering HTTP fetch, timeout, errors)
    ├── ai-results.test.js            # Module 7 test suite (27 tests covering persistence, idempotency)
    ├── auth.test.js                  # Module 1 test suite (authentication & JWT issuance)
    ├── cases.test.js                 # Module 3 test suite (screening case creation and querying)
    ├── image-storage.test.js         # Module 5 test suite (storage security & path traversal defenses)
    ├── image-upload.test.js          # Module 4 test suite (fundus image upload & validation)
    └── rbac.test.js                  # Module 2 test suite (role-based access control matrix)
```

---

## 5. API Inventory

### Summary Table of All Endpoints

| HTTP Method | Route Path | Implemented Module | Status | Auth Required | Allowed Roles | Controller File & Function | Service File & Function |
|---|---|---|---|---|---|---|---|
| `GET` | `/api/health` | Infrastructure | Live (200) | No | Public | `health.controller.js` → `getHealth` | None |
| `POST` | `/api/auth/register` | Module 1 | Live (201) | No | Public | `auth.controller.js` → `register` | `user.model.js` → `create` |
| `POST` | `/api/auth/login` | Module 1 | Live (200) | No | Public | `auth.controller.js` → `login` | `jwt.utils.js` → `generateToken` |
| `GET` | `/api/auth/me` | Module 1 | Live (200) | Yes | All roles | `auth.controller.js` → `getMe` | None |
| `POST` | `/api/auth/logout` | Module 1 | Live (200) | No | Public | `auth.controller.js` → `logout` | None |
| `POST` | `/api/auth/refresh` | Module 1 | Stub (501) | No | Public | `auth.controller.js` → `refresh` | None |
| `GET` | `/api/cases` | Module 3 | Live (200) | Yes | `technician`, `doctor`, `admin` | `cases.controller.js` → `listCases` | `case.model.js` → `findAll` |
| `GET` | `/api/cases/:id` | Module 3 | Live (200) | Yes | `technician`, `doctor`, `admin` | `cases.controller.js` → `getCaseById` | `case.model.js` → `findById` |
| `POST` | `/api/cases` | Module 3 | Live (201) | Yes | `technician`, `admin` | `cases.controller.js` → `createCase` | `case.model.js` → `create` |
| `PATCH` | `/api/cases/:id` | Module 3 | Live (200) | Yes | `technician`, `doctor`, `admin` | `cases.controller.js` → `updateCase` | `case.model.js` → `update` |
| `DELETE`| `/api/cases/:id` | Module 3 | Stub (501) | Yes | `admin` | `cases.controller.js` → `stub` | None |
| `POST` | `/api/cases/:id/image`| Module 4/5| Live (200) | Yes | `technician`, `admin` | `cases.controller.js` → `uploadCaseImage`| `image-storage.service.js` → `saveImage` |
| `POST` | `/api/cases/:id/ai` | Module 6/7| Live (200) | Yes | `technician`, `admin` | `cases.controller.js` → `runCaseInference`| `ai.service.js` → `runInference`, `ai-result.service.js` → `saveResult` |
| `GET` | `/api/cases/:id/ai-result`| Module 7 | Live (200) | Yes | `technician`, `doctor`, `admin` | `cases.controller.js` → `getCaseAiResult` | `ai-result.service.js` → `getResultByCaseId` |
| `GET` | `/api/cases/:id/ai` | Module 7 | Live (200) | Yes | `technician`, `doctor`, `admin` | `cases.controller.js` → `getCaseAiResult` | `ai-result.service.js` → `getResultByCaseId` |
| `POST` | `/api/screening/` | Placeholder | Stub (501) | Yes | `technician`, `doctor`, `admin` | `screening.controller.js` → `stub` | None |
| `POST` | `/api/screening/quality` | Placeholder | Stub (501) | Yes | `technician`, `doctor`, `admin` | `screening.controller.js` → `stub` | None |
| `GET` | `/api/screening/:id/status`| Placeholder| Stub (501)| Yes | `technician`, `doctor`, `admin` | `screening.controller.js` → `stub` | None |
| `GET` | `/api/screening/:id/result`| Placeholder| Stub (501)| Yes | `technician`, `doctor`, `admin` | `screening.controller.js` → `stub` | None |
| `GET` | `/api/reports/:caseId` | Placeholder | Stub (501) | Yes | `doctor`, `admin` | `reports.controller.js` → `stub` | None |
| `POST` | `/api/reports/:caseId/generate`| Placeholder| Stub (501)| Yes | `doctor`, `admin` | `reports.controller.js` → `stub` | None |
| `GET` | `/api/reports/:caseId/download`| Placeholder| Stub (501)| Yes | `doctor`, `admin` | `reports.controller.js` → `stub` | None |
| `GET` | `/api/simulation/results`| Placeholder| Stub (501)| Yes | `doctor`, `admin` | `simulation.controller.js` → `stub` | None |
| `POST` | `/api/simulation/run` | Placeholder | Stub (501) | Yes | `admin` | `simulation.controller.js` → `stub` | None |

---

### Detailed Endpoint Specifications for Key Operational Routes

#### 1. Fundus Image Upload
- **Route:** `POST /api/cases/:id/image`
- **Controller:** `backend/src/controllers/cases.controller.js → uploadCaseImage()`
- **Auth:** Required (`Bearer <token>`)
- **RBAC:** `technician`, `admin`
- **Request Headers:** `Authorization: Bearer <JWT>`, `Content-Type: multipart/form-data`
- **Path Parameters:** `id` (`string`, must match format `/^case_[0-9a-fA-F-]{1,64}$/`)
- **Multipart Form Fields:** `image` (binary file buffer, required)
- **Validation Rules:**
  - Case must exist and have status `'created'`.
  - Case must not already have an image attached (rejects with 409 Conflict).
  - Accepted MIME types: `image/jpeg`, `image/png`.
  - Accepted extensions: `.jpg`, `.jpeg`, `.png`.
  - Maximum size: Configurable via `MAX_IMAGE_UPLOAD_MB` (default `32MB`).
- **Success Response (200 OK):**
```json
{
  "status": "success",
  "success": true,
  "message": "Fundus image uploaded successfully",
  "case": {
    "id": "case_b74df74c-7bb3-402f-93ca-af2e88c76a7a",
    "status": "image_uploaded",
    "patientId": "PAT-2026-001",
    "createdBy": "usr_40413225-34f6-4396-aeee-0106a09fea00",
    "createdAt": "2026-09-25T23:27:03.000Z",
    "updatedAt": "2026-09-25T23:27:03.500Z"
  },
  "image": {
    "imageId": "img_8f8273c4-efb1-4323-b150-4432604f9e7f",
    "originalName": "patient_fundus_left.jpg",
    "storedFilename": "img_8f8273c4-efb1-4323-b150-4432604f9e7f.jpg",
    "mimeType": "image/jpeg",
    "extension": ".jpg",
    "sizeBytes": 1048576,
    "uploadedBy": "usr_40413225-34f6-4396-aeee-0106a09fea00",
    "uploadedAt": "2026-09-25T23:27:03.500Z"
  }
}
```

---

#### 2. Execute AI Inference & Persist Results
- **Route:** `POST /api/cases/:id/ai`
- **Controller:** `backend/src/controllers/ai.controller.js → runCaseInference()`
- **Auth:** Required (`Bearer <token>`)
- **RBAC:** `technician`, `admin`
- **Path Parameters:** `id` (`string`, must match `case_<uuid>`)
- **Request Body:** None required. If client sends JSON body attempting to supply `storagePath`, `path`, `aiServiceUrl`, or `prediction`, **these fields are completely ignored by the server**.
- **Execution Flow:**
  1. Validates `caseId`.
  2. Verifies case exists and has an attached image ID.
  3. Verifies image binary exists on disk via `ImageStorageService.imageExists(caseId, imageId)`.
  4. Generates unique trace ID: `inferenceRequestId = 'inf_' + crypto.randomUUID()`.
  5. Invokes `AIService.runInference({ caseId, imageId, inferenceRequestId })`.
  6. Dispatches HTTP POST multipart/form-data to `${AI_SERVICE_URL}${AI_SERVICE_ENDPOINT}` with `image` file and header `X-Inference-Request-ID`.
  7. Awaits JSON response from Flask.
  8. Passes response to `AIResultService.saveResult({ caseId, inferenceRequestId, inference })`.
  9. Sanitizes payload (stripping paths/secrets) and creates record in `AIResultModel` with `resultId = 'res_' + crypto.randomUUID()`.
  10. Transitions case status in `CaseModel` to `'completed'`.
- **Success Response (200 OK):**
```json
{
  "status": "success",
  "success": true,
  "message": "AI inference completed successfully",
  "inferenceRequestId": "inf_3c17a942-881e-4509-906d-74d75d71c4c9",
  "resultId": "res_a84e4f62-2319-4560-8438-e6732439c28e",
  "caseId": "case_b74df74c-7bb3-402f-93ca-af2e88c76a7a",
  "case": {
    "id": "case_b74df74c-7bb3-402f-93ca-af2e88c76a7a",
    "status": "completed",
    "patientId": "PAT-2026-001"
  },
  "inference": {
    "status": "success",
    "quality_label": "GOOD",
    "quality_score": 0.9654,
    "confidence": 0.9654,
    "action": "PROCEED",
    "recommendation": "High-quality retinal photograph suitable for automated diagnostic screening.",
    "guidance": "All clarity, contrast, and field-of-view criteria are satisfied.",
    "probabilities": {
      "good": 0.9654,
      "borderline": 0.0246,
      "reject": 0.0100
    },
    "model_info": {
      "name": "EyeQ-EfficientNetB4",
      "ensemble_size": 8,
      "input_size": [520, 520],
      "decision_policy": "argmax"
    }
  },
  "result": {
    "resultId": "res_a84e4f62-2319-4560-8438-e6732439c28e",
    "caseId": "case_b74df74c-7bb3-402f-93ca-af2e88c76a7a",
    "inferenceRequestId": "inf_3c17a942-881e-4509-906d-74d75d71c4c9",
    "status": "completed",
    "createdAt": "2026-09-25T23:27:04.000Z",
    "updatedAt": "2026-09-25T23:27:04.000Z",
    "inference": { ... }
  },
  "data": { ... }
}
```

---

#### 3. Retrieve Persisted AI Inference Result
- **Route:** `GET /api/cases/:id/ai-result` (Alias: `GET /api/cases/:id/ai`)
- **Controller:** `backend/src/controllers/ai.controller.js → getCaseAiResult()`
- **Auth:** Required (`Bearer <token>`)
- **RBAC:** `technician`, `doctor`, `admin`
- **Path Parameters:** `id` (`string`, must match `case_<uuid>`)
- **Success Response (200 OK):**
```json
{
  "status": "success",
  "success": true,
  "caseId": "case_b74df74c-7bb3-402f-93ca-af2e88c76a7a",
  "result": {
    "resultId": "res_a84e4f62-2319-4560-8438-e6732439c28e",
    "caseId": "case_b74df74c-7bb3-402f-93ca-af2e88c76a7a",
    "inferenceRequestId": "inf_3c17a942-881e-4509-906d-74d75d71c4c9",
    "status": "completed",
    "createdAt": "2026-09-25T23:27:04.000Z",
    "updatedAt": "2026-09-25T23:27:04.000Z",
    "inference": {
      "status": "success",
      "quality_label": "GOOD",
      "quality_score": 0.9654,
      "confidence": 0.9654,
      "action": "PROCEED",
      "recommendation": "High-quality retinal photograph suitable for automated diagnostic screening.",
      "guidance": "All clarity, contrast, and field-of-view criteria are satisfied.",
      "probabilities": {
        "good": 0.9654,
        "borderline": 0.0246,
        "reject": 0.0100
      },
      "model_info": {
        "name": "EyeQ-EfficientNetB4",
        "ensemble_size": 8
      }
    }
  },
  "data": { ... }
}
```

---

## 6. Complete Image Lifecycle

Below is the exact execution trace through the codebase when a technician uploads a fundus photograph and runs AI inference.

```
[Client / Device]
      │
      │ 1. POST /api/cases/:id/image (multipart/form-data, field='image', Bearer JWT)
      ▼
[Express Router: backend/src/routes/cases.routes.js]
      │
      │ 2. requireAuth (backend/src/middleware/auth.middleware.js:33)
      │    - Decodes JWT via verifyToken() (backend/src/utils/jwt.utils.js:49)
      │    - Looks up user in UserModel (backend/src/models/user.model.js:63)
      │    - Attaches safe user profile to req.user
      │
      │ 3. authorize(ROLES.TECHNICIAN, ROLES.ADMIN) (backend/src/middleware/auth.middleware.js:118)
      │    - Verifies req.user.role is technician or admin (doctors rejected with 403)
      │
      │ 4. validateCaseForUpload (backend/src/controllers/cases.controller.js:211)
      │    - Verifies isValidCaseId(req.params.id) (backend/src/utils/validation.js:151)
      │    - Checks CaseModel.findById(id) exists (404 if not found)
      │    - Verifies case.status === 'created' and !case.image (409 Conflict if image exists)
      │
      │ 5. handleImageUpload('image') (backend/src/middleware/upload.middleware.js:98)
      │    - Multer streams file into backend/storage/temp/upload_<timestamp>_<rand><ext>
      │    - Verifies MIME in ['image/jpeg', 'image/png']
      │    - Verifies extension in ['.jpg', '.jpeg', '.png']
      │    - Enforces MAX_IMAGE_UPLOAD_MB (32MB limit; returns 413 if exceeded)
      ▼
[Controller: uploadCaseImage in backend/src/controllers/cases.controller.js:255]
      │
      │ 6. File verification: validateFundusImage(req.file) (backend/src/utils/validation.js:116)
      │
      │ 7. Save Image: ImageStorageService.saveImage(req.file, { caseId, uploadedBy })
      │    (backend/src/services/image-storage.service.js:191)
      │    - Asserts assertSafeCaseId(caseId) (backend/src/services/image-storage.service.js:76)
      │    - Generates server-controlled imageId = 'img_' + crypto.randomUUID()
      │    - Builds destination: backend/storage/images/<caseId>/<imageId>.<ext>
      │    - Moves file from temp/ to images/<caseId>/
      │    - Returns sanitized imageMetadata
      │
      │ 8. Attach metadata to case: CaseModel.attachImage(caseId, imageMetadata)
      │    (backend/src/models/case.model.js:191)
      │    - Saves image metadata on case record
      │    - Updates status: 'created' ──► 'image_uploaded'
      │    - Sets updatedAt timestamp
      │
      │ 9. Returns 200 OK JSON envelope (hiding physical paths)
      ▼
[Client initiates Inference]
      │
      │ 10. POST /api/cases/:id/ai (Bearer JWT)
      ▼
[Controller: runCaseInference in backend/src/controllers/ai.controller.js:34]
      │
      │ 11. Auth & RBAC: requireAuth & authorize(ROLES.TECHNICIAN, ROLES.ADMIN)
      │
      │ 12. Case verification: CaseModel.findById(id)
      │     - Confirms case exists (404)
      │     - Confirms case.image.imageId is present (400)
      │     - Confirms image file exists on disk via ImageStorageService.imageExists() (404)
      │
      │ 13. Generate trace ID: inferenceRequestId = 'inf_' + crypto.randomUUID()
      │
      │ 14. Dispatch Inference: AIService.runInference({ caseId, imageId, inferenceRequestId })
      │     (backend/src/services/ai.service.js:145)
      │     - Resolves absolute path: ImageStorageService.getImagePath(caseId, imageId)
      │     - Reads binary buffer: fs.readFileSync(imagePath)
      │     - Appends to FormData: formData.append('image', blob, filename)
      │     - Injects header: 'X-Inference-Request-ID': inferenceRequestId
      │     - Executes native fetch(targetUrl, { method: 'POST', body: formData, signal })
      │     - Configures AbortController timeout (AI_SERVICE_TIMEOUT_MS, default 60000ms)
      │     - Parses JSON response from Flask
      ▼
[Flask AI Microservice: http://127.0.0.1:5000/api/quality]
      │
      │ 15. Flask receives multipart POST, executes EyeQ ensemble, returns JSON payload
      ▼
[Service: AIResultService.saveResult in backend/src/services/ai-result.service.js:78]
      │
      │ 16. Idempotency Check: AIResultModel.findByInferenceRequestId(infId)
      │
      │ 17. Sanitize Payload: sanitizeInference(inference)
      │     - Recursively deletes keys containing 'filepath', 'storagepath', 'token', etc.
      │
      │ 18. Persist Record: AIResultModel.create({ caseId, inferenceRequestId, inference, status: 'completed' })
      │     (backend/src/models/ai-result.model.js:91)
      │     - Generates resultId = 'res_' + crypto.randomUUID()
      │     - Stores record in memory indexes (resultsById, resultsByCaseId, resultsByInferenceRequestId)
      │
      │ 19. Case State Transition: CaseModel.updateStatus(caseId, 'completed')
      │     - Updates status: 'image_uploaded' ──► 'completed'
      │
      │ 20. Returns 200 OK envelope to client with full inference and persistence IDs
```

---

## 7. AI Integration Contract

This section defines the network-level contract between the Node.js backend and the Python AI service.

### A. AI Service URL Configuration
- **Base URL Variable:** `AI_SERVICE_URL`
- **Fallback Variables:** `FLASK_HOST` (default `127.0.0.1`), `FLASK_PORT` (default `5000`)
- **Resolved Base URL:** `http://${FLASK_HOST}:${FLASK_PORT}` (defaults to `http://127.0.0.1:5000`)
- **Endpoint Variable:** `AI_SERVICE_ENDPOINT` (default: `/api/quality`)
- **Full Inference URL:** `http://127.0.0.1:5000/api/quality`
- **Health Check URL:** `http://127.0.0.1:5000/api/status`
- **Timeout Variable:** `AI_SERVICE_TIMEOUT_MS` (default: `60000` ms / 60 seconds)
- **HTTP Client:** Node.js native `fetch` (with `AbortController`)

### B. Request Protocol & Payload
- **HTTP Method:** `POST`
- **Content-Type:** `multipart/form-data; boundary=...`
- **Form Field Name:** `'image'`
- **Payload Content:** Binary image stream (`image/jpeg` or `image/png`)
- **Headers:** `X-Inference-Request-ID: inf_<uuid>`
- **Important Note:** Node.js sends the **actual image binary**, NOT a local filesystem path or URL.

### C. Expected AI JSON Response Schema
```json
{
  "status": "success",
  "quality_label": "GOOD",
  "quality_score": 0.9654,
  "confidence": 0.9654,
  "action": "PROCEED",
  "recommendation": "High-quality retinal photograph suitable for automated diagnostic screening.",
  "guidance": "All clarity, contrast, and field-of-view criteria are satisfied.",
  "probabilities": {
    "good": 0.9654,
    "borderline": 0.0246,
    "reject": 0.0100
  },
  "model_info": {
    "name": "EyeQ-EfficientNetB4",
    "ensemble_size": 8,
    "input_size": [520, 520],
    "decision_policy": "argmax"
  }
}
```

---

## 8. Module 6 Contract (AI Orchestration Layer)

Implemented in `backend/src/services/ai.service.js` and `backend/src/controllers/ai.controller.js`.

### AIService Class API
- **`getBaseUrl()`:** Resolves `process.env.AI_SERVICE_URL || env.AI_SERVICE_URL || 'http://127.0.0.1:5000'`.
- **`getEndpoint()`:** Resolves `process.env.AI_SERVICE_ENDPOINT || '/api/quality'`.
- **`getTimeoutMs()`:** Resolves `process.env.AI_SERVICE_TIMEOUT_MS || 60000`.
- **`checkHealth()`:** Executes `GET /api/status` with a 5000ms timeout; returns `{ operational: boolean, details?: object, error?: string }`.
- **`runInference({ caseId, imageId, inferenceRequestId })`:**
  - Reads image binary via `ImageStorageService.getImagePath(caseId, imageId)`.
  - Dispatches multipart request to Flask.
  - Aborts request if execution exceeds timeout.
  - Returns `{ inferenceRequestId, caseId, imageId, inference: parsedJson }`.

### Error Class Hierarchy
```
AIServiceError (base, status: 502, code: 'AI_SERVICE_ERROR')
  ├── AIServiceUnavailableError (status: 503, code: 'AI_SERVICE_UNAVAILABLE')
  ├── AIServiceTimeoutError     (status: 504, code: 'AI_SERVICE_TIMEOUT')
  └── AIServiceMalformedResponseError (status: 502, code: 'AI_SERVICE_MALFORMED_RESPONSE')
```

---

## 9. Module 7 Result Contract (Persistence & Repository)

Implemented in `backend/src/services/ai-result.service.js` and `backend/src/models/ai-result.model.js`.

### Schema Pipeline: Input → Transformation → Persisted → Response

```
1. INPUT FROM AI SERVICE (Raw Flask Output)
   {
     "status": "success",
     "quality_label": "GOOD",
     "quality_score": 0.9654,
     "confidence": 0.9654,
     "action": "PROCEED",
     "recommendation": "...",
     "probabilities": { "good": 0.9654, "borderline": 0.0246, "reject": 0.0100 },
     "model_info": { "name": "EyeQ-EfficientNetB4" }
   }
              │
              │ 2. TRANSFORMATION (sanitizeInference in ai-result.service.js:32)
              │    - Recursively traverses object
              │    - Strips: 'storagepath', 'filepath', 'absolutepath', 'token', 'secret', 'password'
              │    - Generates server-controlled resultId: 'res_' + crypto.randomUUID()
              │    - Binds inferenceRequestId: 'inf_<uuid>'
              │    - Sets status: 'completed'
              │    - Captures timestamps: createdAt, updatedAt (ISO 8601 UTC)
              ▼
3. PERSISTED RESULT (Stored in AIResultModel)
   {
     "id": "res_a84e4f62-2319-4560-8438-e6732439c28e",
     "resultId": "res_a84e4f62-2319-4560-8438-e6732439c28e",
     "caseId": "case_b74df74c-7bb3-402f-93ca-af2e88c76a7a",
     "inferenceRequestId": "inf_3c17a942-881e-4509-906d-74d75d71c4c9",
     "status": "completed",
     "inference": { ... clean inference object ... },
     "error": null,
     "createdAt": "2026-09-25T23:27:04.000Z",
     "updatedAt": "2026-09-25T23:27:04.000Z"
   }
              │
              │ 4. API RESPONSE (GET /api/cases/:id/ai-result)
              │    - Projected via AIResultModel.toSafeResult()
              │    - Wrapped in standard success envelope
              ▼
{
  "status": "success",
  "success": true,
  "caseId": "case_b74df74c-7bb3-402f-93ca-af2e88c76a7a",
  "result": {
    "resultId": "res_a84e4f62-2319-4560-8438-e6732439c28e",
    "caseId": "case_b74df74c-7bb3-402f-93ca-af2e88c76a7a",
    "inferenceRequestId": "inf_3c17a942-881e-4509-906d-74d75d71c4c9",
    "status": "completed",
    "createdAt": "2026-09-25T23:27:04.000Z",
    "updatedAt": "2026-09-25T23:27:04.000Z",
    "inference": { ... }
  },
  "data": { ... }
}
```

### Idempotency Guarantee
The service maintains a dedicated index `resultsByInferenceRequestId`. If `POST /api/cases/:id/ai` is replayed with an identical `inferenceRequestId`, `AIResultService.saveResult()` returns the existing record immediately without creating duplicate rows or altering `createdAt`.

---

## 10. Case State Machine

The screening case lifecycle is managed by `backend/src/models/case.model.js` through the `CASE_STATUS` enumeration:

```text
               POST /api/cases
                      │
                      ▼
               ┌───────────────┐
               │    created    │
               └──────┬────────┘
                      │
                      │ POST /api/cases/:id/image
                      ▼
               ┌───────────────┐
               │ image_uploaded│
               └──────┬────────┘
                      │
                      │ POST /api/cases/:id/ai (Inference Succeeded)
                      ▼
               ┌───────────────┐
               │   completed   │
               └──────┬────────┘
                      │
                      │ Doctor Review (Module 10 - Future)
                      ▼
               ┌───────────────┐
               │   reviewed    │
               └───────────────┘

Alternative / Exception States:
- processing : Defined in enum (backend/src/models/case.model.js:35) for future async job queues.
- failed     : Defined in enum (backend/src/models/case.model.js:38) for unrecoverable pipeline failure.
```

### Lifecycle Transition Matrix

| Initial State | Target State | Triggering Endpoint | File & Function Responsible | Validation Guard |
|---|---|---|---|---|
| *(None)* | `created` | `POST /api/cases` | `cases.controller.js` → `createCase()` | Client cannot specify initial status; automatically forced to `'created'`. |
| `created` | `image_uploaded` | `POST /api/cases/:id/image` | `cases.controller.js` → `uploadCaseImage()`, `case.model.js` → `attachImage()` | Case must be in `'created'` status; target case must have `case.image === null`. |
| `image_uploaded` | `completed` | `POST /api/cases/:id/ai` | `ai.controller.js` → `runCaseInference()`, `ai-result.service.js` → `saveResult()` | Target case must have valid `image.imageId` on disk; Flask must return HTTP 200 with valid JSON. |
| `completed` | `reviewed` | *(Module 10 - Future)* | `review.model.js` | Doctor reviews findings and confirms or overrides diagnosis. |

---

## 11. Authentication and RBAC Requirements

### Client-to-Backend Layer
- **Protocol:** HTTP Bearer Token (`Authorization: Bearer <JWT>`).
- **Signature:** HMAC SHA256 verified against `JWT_SECRET` (loaded from `config/env.js`).
- **Expiration:** Default `8h` (`JWT_EXPIRES_IN`).
- **Token Claims:** Minimal user claims (`userId`, `role`, `email`). Patient data and medical records are **never** encoded in tokens.
- **Role Enforcement:**
  - `technician`: Can create cases, upload fundus images, and trigger AI inference.
  - `doctor`: Can list cases, view case details, and retrieve persisted AI results. Cannot upload images or trigger inference.
  - `admin`: Full administrative access to all endpoints.

### Backend-to-AI Service Layer
- **Communication Type:** Internal service-to-service HTTP.
- **Authentication:** **None currently required or expected.** The existing Node.js `AIService` does **not** attach Bearer tokens or API keys to the upstream Flask request.
- **Security Posture:** The Python AI service is assumed to run on the local loopback interface (`127.0.0.1:5000`) or within an isolated, private virtual network.
- **Guidance:** External AI developers must **not** require API keys, OAuth headers, or JWTs on `POST /api/quality` unless they are willing to configure reverse proxy authentication or update `backend/src/services/ai.service.js`.

---

## 12. AI/ML Developer Handoff

### "NETRA-DR AI/ML SERVICE INTEGRATION CONTRACT"

> [!NOTE]
> **To the External AI/ML Developer:**
> You do NOT need to modify the Node.js backend. Your objective is to run a Python microservice exposing an HTTP adapter that wraps your model inference.

### 15 Core Integration Specifications:
1. **Service to Run:** A Python HTTP server (Flask, FastAPI, or Gunicorn).
2. **Host and Port:** Bind to `127.0.0.1:5000` (or configure `FLASK_HOST` / `FLASK_PORT` in `backend/.env`).
3. **Endpoint to Expose:** `POST /api/quality`.
4. **HTTP Method:** `POST`.
5. **Request Encoding:** `multipart/form-data`.
6. **Form Field Name:** `'image'` (lowercase).
7. **Image Format:** Decodable by PIL (`PIL.Image.open`) or OpenCV (`cv2.imread`). Typical formats: JPEG or PNG, RGB 3-channel, resolutions 512x512 to 4000x3000.
8. **Response Envelope:** HTTP 200 with `Content-Type: application/json` returning at minimum:
   ```json
   {
     "status": "success",
     "quality_label": "GOOD",
     "quality_score": 0.95,
     "confidence": 0.95,
     "action": "PROCEED",
     "recommendation": "High quality image.",
     "guidance": "Clear view of retina.",
     "probabilities": { "good": 0.95, "borderline": 0.04, "reject": 0.01 }
   }
   ```
9. **Error Behavior:**
   - If an invalid/corrupted image is submitted, return **HTTP 400** with `{"status": "error", "error": "Corrupted image"}`.
   - If model execution crashes, return **HTTP 500** with `{"status": "error", "error": "Inference error description"}`.
   - Never return raw HTML stack traces or 502/504 gateway crash pages.
10. **Health Check Endpoint:** Expose `GET /api/status` returning HTTP 200 with `{"status": "operational"}`.
11. **Timeout Considerations:** Node.js terminates connections after **60,000 ms (60 seconds)** by default (`AI_SERVICE_TIMEOUT_MS`). The AI service should complete single-image quality inference within 1 to 5 seconds.
12. **Result Consumption:** The backend stores your exact JSON under the `inference` field in `AIResultModel` and marks the case `completed`.
13. **Independent AI Files:** Your model training scripts, checkpoint weights (`.pt`, `.ckpt`, `.onnx`), preprocessing functions, and PyTorch architecture definitions remain completely independent inside your Python codebase.
14. **Integration Interface:** The only file connecting your model to NETRA-DR is your Flask adapter (e.g. `SIH/app/app.py` or your standalone adapter).
15. **Backend Files You Must NOT Modify:**
    - `backend/src/routes/cases.routes.js`
    - `backend/src/controllers/cases.controller.js`
    - `backend/src/controllers/ai.controller.js`
    - `backend/src/services/ai.service.js`
    - `backend/src/services/ai-result.service.js`
    - `backend/src/services/image-storage.service.js`
    - `backend/src/models/case.model.js`
    - `backend/src/models/ai-result.model.js`

---

## 13. EyeQ Integration Boundary

The EyeQ system evaluates fundus image quality using an ensemble of 8 EfficientNet-B4 models trained to categorize fundus images into three classes:
- **Class 0:** Good quality
- **Class 1:** Uncertain / Borderline quality
- **Class 2:** Bad / Reject quality

### Architectural Isolation Boundary
The Node.js backend must never import PyTorch, torchvision, ONNX Runtime, or EyeQ. The separation is strictly maintained across HTTP:

```
┌──────────────────────────────────────────────┐
│            Node.js Backend (port 3000)       │
│  - Multer upload                             │
│  - ImageStorageService                       │
│  - AIService (fetch over HTTP)               │
└──────────────────────┬───────────────────────┘
                       │
                       │ HTTP POST multipart/form-data
                       │ Field: 'image'
                       ▼
┌──────────────────────────────────────────────┐
│           Flask AI Adapter (port 5000)       │
│  - Receives request.files['image']           │
│  - Saves to temporary buffer                 │
│  - Passes image to EyeQ Quality Service      │
└──────────────────────┬───────────────────────┘
                       │
                       │ Python function call
                       ▼
┌──────────────────────────────────────────────┐
│         EyeQ Quality Service Engine          │
│  - Resolves checkpoints                      │
│  - Loads 8-model EfficientNet-B4 ensemble   │
│  - Applies FOV crop & 520x520 resize         │
│  - Runs torch.no_grad() inference            │
│  - Computes softmax probabilities            │
│  - Maps argmax [0, 1, 2] → GOOD / BORDERLINE │
└──────────────────────┬───────────────────────┘
                       │
                       │ Returns Dict to Flask
                       ▼
┌──────────────────────────────────────────────┐
│           Flask JSON Serialization           │
│  - Serializes to NETRA JSON contract         │
│  - Returns HTTP 200 to Node.js               │
└──────────────────────────────────────────────┘
```

### Reference Implementation in Existing Repository
The repository already contains a tested, reference implementation in Python:
- **Flask Route:** `SIH/app/app.py` lines 651–706 (`api_quality`)
- **EyeQ Service Wrapper:** `SIH/pipeline/quality_service.py` (`EyeQQualityService`)
- **Model Checkpoints:** `SIH/external/EyeQ/checkpoints/efficientnet/`

### EyeQ Label Mapping Table
```python
EYEQ_TO_NETRA = {
    0: "GOOD",        # EyeQ 'good'       --> NETRA 'GOOD'
    1: "BORDERLINE",  # EyeQ 'uncertain'  --> NETRA 'BORDERLINE'
    2: "REJECT",      # EyeQ 'bad'        --> NETRA 'REJECT'
}
```

---

## 14. Portable AI Runtime Requirements

If moving the AI service to another workstation or server, ensure the target environment matches these specifications:

| Requirement Category | Specification / Value | Source Reference |
|---|---|---|
| **Python Version** | Python 3.10.x or 3.11.x (64-bit) | `SIH/requirements.txt` |
| **Virtual Environment** | Dedicated virtualenv (`venv` or `conda`) | `SIH/external/EyeQ/.venv` |
| **PyTorch Version** | PyTorch >= 2.0.0 (CUDA 11.8/12.1 recommended if GPU available; CPU supported) | `SIH/pipeline/quality_service.py:89` |
| **Required Pip Packages** | `flask>=2.3.0`, `torch`, `torchvision`, `numpy`, `pillow`, `opencv-python-headless` | `SIH/requirements.txt` |
| **Model Weights Directory** | Checkpoints for 8 EfficientNet models: `external/EyeQ/checkpoints/efficientnet/` | `SIH/pipeline/quality_service.py:76` |
| **Model Checkpoint Format** | PyTorch `.pt` or `.pth` state dictionaries | `SIH/external/EyeQ/` |
| **Image Resolution Required** | Resized internally to `[520, 520]` by EyeQ preprocessor | `SIH/pipeline/quality_service.py:115` |
| **Host Binding** | `127.0.0.1` | `SIH/backend/src/config/env.js:16` |
| **Port Binding** | `5000` | `SIH/backend/src/config/env.js:17` |
| **Health Check Route** | `GET http://127.0.0.1:5000/api/status` | `SIH/backend/src/services/ai.service.js:110` |
| **Inference Route** | `POST http://127.0.0.1:5000/api/quality` | `SIH/backend/src/services/ai.service.js:89` |
| **Minimum Hardware (GPU)** | 4GB VRAM (NVIDIA GTX 1650 or higher) | `SIH/docs/HANDOFF.md` |
| **Minimum Hardware (CPU)** | 4 CPU cores, 8GB System RAM (inference takes ~2-4s on CPU) | Empirical |

---

## 15. Environment Variables

The backend relies on the following environment variables (defined in `backend/.env` and handled by `backend/src/config/env.js`):

| Variable Name | Default Value | Description | Impact on AI Service |
|---|---|---|---|
| `NODE_ENV` | `'development'` | Environment mode (`development` or `production`). | In dev, stack traces are logged; in prod, logs are pure JSON. |
| `HOST` | `'127.0.0.1'` | HTTP host address for Express backend. | None. |
| `PORT` | `3000` | HTTP port for Express backend (dev: 3000 or 3001). | Port client connects to. |
| `FLASK_HOST` | `'127.0.0.1'` | Host address where Flask AI service is listening. | Node.js constructs base URL using this if `AI_SERVICE_URL` not set. |
| `FLASK_PORT` | `5000` | Port where Flask AI service is listening. | Node.js constructs base URL using this if `AI_SERVICE_URL` not set. |
| `AI_SERVICE_URL` | `http://127.0.0.1:5000` | Full base URL for the upstream AI service. | Target URL called by `AIService.getBaseUrl()`. |
| `AI_SERVICE_ENDPOINT`| `'/api/quality'` | Relative endpoint path for AI inference. | Appended to `AI_SERVICE_URL`. |
| `AI_SERVICE_TIMEOUT_MS`| `60000` | Timeout in milliseconds before aborting HTTP fetch. | Exceeding this triggers HTTP 504 `AI_SERVICE_TIMEOUT`. |
| `STORAGE_ROOT` | `'storage'` | Relative or absolute path to storage root. | Determines base directory for `storage/images/`. |
| `MAX_IMAGE_UPLOAD_MB` | `32` | Maximum allowable fundus image upload in MB. | Uploads exceeding this return HTTP 413. |
| `LOG_LEVEL` | `'info'` | Winston logging verbosity (`debug`, `info`, `warn`, `error`). | None. |
| `JWT_SECRET` | `'netra_dr_dev_jwt_secret_key_sih26038'` | Cryptographic secret for signing auth tokens. | Must match client token signature. |
| `JWT_EXPIRES_IN` | `'8h'` | Token validity window. | None. |

---

## 16. Integration Test Plan

Follow this 5-Level Verification Plan to certify that the AI service is correctly integrated with the Node.js backend:

### LEVEL 1: Flask Health Check
- **Prerequisite:** Flask server is started (`python app/app.py`).
- **Command:**
  ```bash
  curl -X GET http://127.0.0.1:5000/api/status
  ```
- **Expected Status:** `200 OK`
- **Expected Body:**
  ```json
  { "status": "operational", "phase1_eyeq": { "available": true } }
  ```
- **Failure Interpretation:** If connection fails, Flask is not running on port 5000. If `available: false`, EyeQ checkpoints are missing or PyTorch failed to load.

---

### LEVEL 2: Direct AI Inference (Flask Standalone)
- **Prerequisite:** A valid sample fundus JPEG image exists at `data/demo/good_sample.jpg`.
- **Command:**
  ```bash
  curl -X POST http://127.0.0.1:5000/api/quality \
    -F "image=@data/demo/good_sample.jpg"
  ```
- **Expected Status:** `200 OK`
- **Expected Body:**
  ```json
  {
    "status": "success",
    "quality_label": "GOOD",
    "quality_score": 0.9654,
    "confidence": 0.9654,
    "action": "PROCEED",
    "probabilities": { "good": 0.9654, "borderline": 0.0246, "reject": 0.0100 }
  }
  ```
- **Failure Interpretation:** If 400 is returned, the multipart field was not named `'image'`. If 500 is returned, EyeQ threw a PyTorch exception during `_model(img_tensor)`.

---

### LEVEL 3: Node.js to Flask Connectivity
- **Prerequisite:** Both Node.js (port 3000) and Flask (port 5000) are running.
- **Command (Programmatic or Health Probe):**
  Node.js internally calls `AIService.checkHealth()` (`backend/src/services/ai.service.js:109`).
- **Expected Behavior:** Node.js receives `operational: true` from Flask within 5,000ms.
- **Failure Interpretation:** Network routing or firewall is blocking Node.js from resolving `127.0.0.1:5000`.

---

### LEVEL 4: End-to-End Workflow (Upload → Storage → AI → Persistence)
- **Prerequisite:** Technician user registered and logged in; JWT token obtained.
- **Step 4A: Create Case**
  ```bash
  curl -X POST http://127.0.0.1:3000/api/cases \
    -H "Authorization: Bearer <TECH_JWT>" \
    -H "Content-Type: application/json" \
    -d '{"patientId": "PAT-E2E-TEST"}'
  # Save returned case ID: case_xxx
  ```
- **Step 4B: Upload Fundus Image**
  ```bash
  curl -X POST http://127.0.0.1:3000/api/cases/<CASE_ID>/image \
    -H "Authorization: Bearer <TECH_JWT>" \
    -F "image=@data/demo/good_sample.jpg"
  ```
  *Verify case status is now `"image_uploaded"`.*
- **Step 4C: Trigger AI Inference**
  ```bash
  curl -X POST http://127.0.0.1:3000/api/cases/<CASE_ID>/ai \
    -H "Authorization: Bearer <TECH_JWT>"
  ```
- **Expected Status:** `200 OK`
- **Expected Verification:**
  - Response contains `inferenceRequestId` starting with `inf_`.
  - Response contains `resultId` starting with `res_`.
  - `case.status` is updated to `"completed"`.
  - `inference.quality_label` matches EyeQ classification.

---

### LEVEL 5: Retrieve Persisted AI Result
- **Prerequisite:** Step 4 completed successfully.
- **Command:**
  ```bash
  curl -X GET http://127.0.0.1:3000/api/cases/<CASE_ID>/ai-result \
    -H "Authorization: Bearer <TECH_OR_DOCTOR_JWT>"
  ```
- **Expected Status:** `200 OK`
- **Expected Verification:**
  - Persisted record returned intact.
  - No internal filesystem paths (`storage/images`, `storagePath`) appear in JSON.
  - Repeated calls return identical `resultId` and timestamps.

---

## 17. Error Handling Contract

```text
+-----------------------+----------------------+---------------------------+----------------------------------------------+
| Condition             | HTTP Status to Client| Error Code in JSON Body   | Root Cause & Diagnostic Action               |
+-----------------------+----------------------+---------------------------+----------------------------------------------+
| Token Missing         | 401 Unauthorized     | 401                       | Missing 'Authorization: Bearer <token>'      |
| Token Expired         | 401 Unauthorized     | 401                       | JWT expired; user must re-authenticate       |
| Role Forbidden        | 403 Forbidden        | 403                       | User role (e.g. doctor) cannot run inference |
| Case ID Invalid       | 400 Bad Request      | ERR_INVALID_CASE_ID       | ID does not begin with 'case_' or bad format |
| Case Missing          | 404 Not Found        | ERR_CASE_NOT_FOUND        | Case ID does not exist in repository         |
| No Image on Case      | 400 Bad Request      | ERR_NO_IMAGE_UPLOADED     | Case status is 'created'; upload image first |
| Image Deleted on Disk | 404 Not Found        | ERR_STORED_IMAGE_NOT_FOUND| Image file missing from storage/images/      |
| AI Host Unreachable   | 503 Service Unavail. | AI_SERVICE_UNAVAILABLE    | Flask process not running on port 5000       |
| AI Inference Timeout  | 504 Gateway Timeout  | AI_SERVICE_TIMEOUT        | Inference took > 60s; check GPU / deadlock   |
| AI Returned 4xx       | 4xx (Pass-through)   | AI_SERVICE_REJECTED       | Corrupt file; unsupported format in Flask    |
| AI Returned 500       | 502 Bad Gateway      | AI_SERVICE_EXECUTION_ERROR| PyTorch threw exception; check Flask logs    |
| AI Returned HTML/text | 502 Bad Gateway      | AI_SERVICE_MALFORMED_RESP.| Flask crashed without JSON error handler     |
+-----------------------+----------------------+---------------------------+----------------------------------------------+
```

---

## 18. Security Requirements

The backend implements strict defensive controls. The AI integration must preserve these mechanisms:

1. **No Client Path Traversal:**
   `ImageStorageService.assertSafePath()`, `assertSafeCaseId()`, and `assertSafeImageId()` reject null bytes, encoded delimiters (`%2e%2e`), `..`, and drive letters. Clients can never supply filesystem paths.
2. **Server-Generated Filenames:**
   The backend generates random UUID identifiers (`img_<uuid>.<ext>`) for storage. The user's original filename is stored in metadata but never used as an active disk reference.
3. **No Internal Path Leakage:**
   `AIResultService.sanitizeInference()` recursively strips any keys containing `storagepath`, `filepath`, `absolutepath`, `token`, `secret`, or `password` before returning JSON or persisting records.
4. **No Client-Injected Inference Results:**
   `POST /api/cases/:id/ai` ignores any body attributes attempting to force a prediction, confidence, model name, or result ID.
5. **No Medical Data in JWTs:**
   JWT payloads only carry user identity and role. Screening results, patient identifiers, and diagnoses are never embedded in tokens.

---

## 19. "Do Not Break This" Rules

For any developer interacting with or extending this system:

- ❌ **DO NOT CHANGE** route signatures (`POST /api/cases/:id/image`, `POST /api/cases/:id/ai`, `GET /api/cases/:id/ai-result`).
- ❌ **DO NOT CHANGE** case ID formats (`case_<uuid>`), image ID formats (`img_<uuid>`), result ID formats (`res_<uuid>`), or trace formats (`inf_<uuid>`).
- ❌ **DO NOT CHANGE** the multipart form field name from `'image'`.
- ❌ **DO NOT CHANGE** the image storage hierarchy: `backend/storage/images/<caseId>/<imageId>.<ext>`.
- ❌ **DO NOT EXPECT** client file paths in the Flask service; you will receive a binary image stream.
- ❌ **DO NOT ATTEMPT** to bypass JWT authentication or RBAC guards.
- ❌ **DO NOT HARDCODE** quality thresholds in Node.js; quality labels and scores must originate faithfully from the AI service.

---

## 20. Final Integration Blueprint

```text
===================================================================================================
                               NETRA-DR END-TO-END INTEGRATION BLUEPRINT
===================================================================================================

[Technician Browser / Tablet]
       │
       │ 1. POST /api/cases/:id/image (multipart/form-data with image file)
       ▼
[Node.js Express Backend] (Host: 127.0.0.1, Port: 3000)
       │
       ├─► Route: backend/src/routes/cases.routes.js:52
       ├─► Middleware: requireAuth, authorize('technician', 'admin'), handleImageUpload('image')
       ├─► Controller: backend/src/controllers/cases.controller.js:uploadCaseImage()
       ├─► Service: backend/src/services/image-storage.service.js:saveImage()
       │        └── Persists to: backend/storage/images/<caseId>/<imageId>.<ext>
       └─► Model: backend/src/models/case.model.js:attachImage()
                └── Case state: 'created' ──► 'image_uploaded'
       │
       │ 2. POST /api/cases/:id/ai (Trigger inference)
       ▼
[Node.js AI Orchestration Layer]
       │
       ├─► Route: backend/src/routes/cases.routes.js:61
       ├─► Controller: backend/src/controllers/ai.controller.js:runCaseInference()
       ├─► Service: backend/src/services/ai.service.js:runInference()
       │        ├─ Resolves image from backend/storage/images/<caseId>/<imageId>.<ext>
       │        ├─ Reads binary buffer
       │        ├─ Constructs FormData with field 'image' and Blob
       │        ├─ Injects header 'X-Inference-Request-ID': 'inf_<uuid>'
       │        └─ Starts AbortController with 60000ms timeout
       │
       │ 3. HTTP POST multipart/form-data
       ▼
[Flask AI Microservice Adapter] (Host: 127.0.0.1, Port: 5000)
       │
       ├─► Route: POST /api/quality (SIH/app/app.py:651)
       ├─► Reads request.files['image']
       ├─► Service: pipeline/quality_service.py:EyeQQualityService.predict()
       │        ├─ In-memory cached 8-model EfficientNet-B4 ensemble
       │        ├─ Checkpoints: external/EyeQ/checkpoints/efficientnet/
       │        ├─ Preprocessing: FOV crop + 520x520 resize + Tensor normalization
       │        ├─ Inference: torch.no_grad()
       │        ├─ Argmax prediction: 0 (Good), 1 (Borderline), 2 (Reject)
       │        └─ Probabilities vector: [p_good, p_borderline, p_reject]
       │
       │ 4. HTTP 200 JSON Response
       ▼
[Node.js AI Results Persistence Layer]
       │
       ├─► Service: backend/src/services/ai-result.service.js:saveResult()
       │        ├─ Sanitizes inference payload (strips internal paths & secrets)
       │        └─ Persists via backend/src/models/ai-result.model.js:create()
       │                 ├── Generates resultId: 'res_<uuid>'
       │                 ├── Stores in memory maps (resultsById, resultsByCaseId)
       │                 └── Maintains idempotency index (resultsByInferenceRequestId)
       └─► Model: backend/src/models/case.model.js:updateStatus()
                └── Case state: 'image_uploaded' ──► 'completed'
       │
       │ 5. GET /api/cases/:id/ai-result
       ▼
[Ophthalmologist / Doctor Workstation]
       │
       ├─► Route: backend/src/routes/cases.routes.js:44
       ├─► Middleware: requireAuth, authorize('technician', 'doctor', 'admin')
       ├─► Controller: backend/src/controllers/ai.controller.js:getCaseAiResult()
       └─► Service: backend/src/services/ai-result.service.js:getResultByCaseId()
                └── Returns persisted quality scores, recommendations, and status: 'completed'

===================================================================================================
```

---

## 21. Known Limitations and Undefined Values

The following architectural aspects are not yet implemented or explicitly defined in the current backend repository:

1. **Persistent Database Implementation:**
   - Case data (`CaseModel`) and AI inference records (`AIResultModel`) are currently maintained in memory using JavaScript `Map` collections.
   - `backend/src/db/connection.js` throws `"Database connection not implemented yet."`
   - Persistent storage engines (e.g. MongoDB with Mongoose or PostgreSQL with Prisma) will replace the in-memory maps in a subsequent module without changing controller contracts.
2. **Multi-Stage Pipeline Orchestration in Node.js:**
   - Node.js Module 6 currently orchestrates the Phase 1 Quality Gate (`/api/quality`).
   - Phases 2 (vessel & lesion segmentation), 3 (ICDR severity grading & decision fusion), and 4 (Grad-CAM explainability) are fully implemented in the Python pipeline (`SIH/app/app.py` lines 500–650) but are represented as stubs (`501 Not Implemented`) in the Node.js service layer (`grading.service.js`, `segmentation.service.js`, `explainability.service.js`).
3. **External Service Authentication:**
   - **NOT DEFINED IN CURRENT BACKEND.** The Node.js backend does not send an `Authorization` header, mutual TLS certificate, or API key to the Flask AI service. The AI service must run on the local loopback interface or within a secure internal network.
4. **Asynchronous Task Queue / GPU Throttling:**
   - **NOT DEFINED IN CURRENT BACKEND.** Node.js issues synchronous HTTP `fetch` requests and holds open the client connection for up to 60 seconds. There is currently no BullMQ / Redis background worker queue for GPU job scheduling.
5. **Model Checkpoint Path Configuration in Backend:**
   - **NOT DEFINED IN CURRENT BACKEND.** The Node.js backend has no concept of model weights or `.pt` paths. Model checkpoint paths are configured strictly inside the Python service (`external/EyeQ/checkpoints/efficientnet/`).

---

## 22. Exact Source File Reference Map

Every technical specification in this PRD maps directly to the following source files in `SIH/backend/`:

| Specification Category | Exact Source File Path | Line Range | Key Function / Class / Symbol | Responsibility in Contract |
|---|---|---|---|---|
| **Server Startup** | `backend/src/server.js` | 1–64 | `server.listen()`, `shutdown()` | Binds HTTP port, manages SIGINT/SIGTERM |
| **App Configuration** | `backend/src/app.js` | 1–76 | `express()`, router registrations | Middleware pipeline and route mounting |
| **Environment Settings** | `backend/src/config/env.js` | 1–45 | `env` object | Resolves `AI_SERVICE_URL`, `TIMEOUT_MS` |
| **Path Resolution** | `backend/src/config/paths.js` | 1–41 | `paths` object | Resolves `STORAGE_ROOT`, `IMAGES_DIR` |
| **Role Definitions** | `backend/src/config/roles.js` | 1–62 | `ROLES`, `VALID_ROLES` | Central authority for role authorization |
| **JWT Verification** | `backend/src/middleware/auth.middleware.js` | 33–99 | `requireAuth` | Enforces Bearer JWT token presence |
| **Role Guard (RBAC)** | `backend/src/middleware/auth.middleware.js` | 118–168 | `authorize` | Enforces role-based permissions |
| **Image Upload Handling** | `backend/src/middleware/upload.middleware.js` | 98–136 | `handleImageUpload` | Multer staging, 32MB file size enforcement |
| **Error Handling** | `backend/src/middleware/error.middleware.js` | 21–48 | `errorHandler` | Maps exceptions to clean JSON error bodies |
| **Case Controller** | `backend/src/controllers/cases.controller.js` | 40–84 | `createCase` | Validates patient reference, inits case |
| **Upload Pre-check** | `backend/src/controllers/cases.controller.js` | 211–247 | `validateCaseForUpload` | Rejects re-uploads to existing cases (409) |
| **Upload Case Image** | `backend/src/controllers/cases.controller.js` | 255–349 | `uploadCaseImage` | Coordinates storage and status transition |
| **AI Controller** | `backend/src/controllers/ai.controller.js` | 34–207 | `runCaseInference` | Coordinates inference dispatch & persistence |
| **AI Result Query** | `backend/src/controllers/ai.controller.js` | 215–275 | `getCaseAiResult` | Retrieves persisted AI result by case ID |
| **Image Storage** | `backend/src/services/image-storage.service.js` | 191–328 | `saveImage` | Path-traversal safe image file persistence |
| **Path Traversal Check**| `backend/src/services/image-storage.service.js` | 36–109 | `assertSafePath`, `assertSafeCaseId` | Defense against `..` and malicious strings |
| **AI Orchestration** | `backend/src/services/ai.service.js` | 145–273 | `runInference` | Reads image, dispatches HTTP fetch to Flask |
| **AI Health Check** | `backend/src/services/ai.service.js` | 109–126 | `checkHealth` | Probes `GET /api/status` on Flask |
| **AI Error Classes** | `backend/src/services/ai.service.js` | 26–65 | `AIServiceUnavailableError`, etc. | Custom errors for 502, 503, 504 handling |
| **Result Sanitization**| `backend/src/services/ai-result.service.js` | 32–56 | `sanitizeInference` | Strips paths, secrets, tokens from payload |
| **Result Persistence** | `backend/src/services/ai-result.service.js` | 78–146 | `saveResult` | Enforces idempotency, updates case to completed |
| **Case Model Repo** | `backend/src/models/case.model.js` | 131–203 | `create`, `attachImage`, `updateStatus` | In-memory case lifecycle management |
| **AI Result Model Repo**| `backend/src/models/ai-result.model.js` | 91–134 | `create`, `toSafeResult` | Result indexing by `id`, `caseId`, `reqId` |
| **Validation Helpers** | `backend/src/utils/validation.js` | 105–286 | `validateFundusImage`, `isValidCaseId` | Input validation and regex rules |
