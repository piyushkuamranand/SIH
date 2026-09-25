# NETRA-DR Backend — Node.js + Express

Node.js/Express backend service for the NETRA-DR SIH 26038 diabetic retinopathy
screening platform.

> **This service is separate from and must not interfere with the existing
> Python/Flask AI pipeline (`../app/` and `../pipeline/`).**

---

## Quick Start

```bash
# 1. Install dependencies
cd backend
npm install

# 2. Copy env file
cp .env.example .env

# 3. Start in development mode (auto-reload)
npm run dev

# 4. Start in production mode
npm start
```

Server starts at **http://127.0.0.1:3001**

---

## Health Check

```bash
curl http://127.0.0.1:3001/api/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "netra-dr-backend",
  "version": "1.0.0",
  "environment": "development",
  "uptime_s": 4,
  "timestamp": "2026-09-25T17:48:00.000Z",
  "ai_service": {
    "note": "Flask AI pipeline status not yet proxied — add in integration task",
    "flask_url": "http://127.0.0.1:5000"
  }
}
```

---

## Project Structure

```
backend/
├── src/
│   ├── app.js              Express application factory
│   ├── server.js           HTTP server entry point
│   ├── config/
│   │   ├── env.js          Environment variable config
│   │   └── paths.js        Filesystem path resolution
│   ├── routes/             Route registration (one file per resource)
│   ├── controllers/        Request handlers (call services)
│   ├── services/           Business logic (call Flask AI or DB)
│   ├── models/             Database model schemas
│   ├── middleware/
│   │   ├── auth.middleware.js    Authentication (placeholder)
│   │   ├── error.middleware.js   Centralised error handler
│   │   └── upload.middleware.js  Multer image upload
│   ├── utils/
│   │   ├── logger.js        Winston logger
│   │   ├── validation.js    Input validation helpers
│   │   └── file.utils.js    File system helpers
│   └── db/
│       ├── connection.js    Database connection (placeholder)
│       └── schema.js        Database schema (placeholder)
├── storage/
│   ├── images/             Uploaded fundus images
│   ├── masks/              Segmentation masks from pipeline
│   ├── heatmaps/           Grad-CAM heatmap overlays
│   └── reports/            Generated PDF reports
├── tests/                  Test suite (to be added)
├── .env                    Local environment (not committed)
├── .env.example            Environment template
└── package.json
```

---

## API Endpoints

### Implemented

| Method | Route | Status |
|--------|-------|--------|
| GET | `/api/health` | ✅ Live |

### Planned (return 501 until implemented)

| Method | Route | Notes |
|--------|-------|-------|
| POST | `/api/auth/login` | Auth task |
| POST | `/api/screening/` | Flask integration task |
| POST | `/api/screening/quality` | Flask integration task |
| GET | `/api/cases` | DB integration task |
| GET | `/api/reports/:caseId` | Report task |
| GET | `/api/simulation/results` | MATLAB integration task |

---

## Relationship with Python/Flask Service

The existing Python/Flask service runs independently at `http://127.0.0.1:5000`.
This Node.js backend will **call** the Flask service as an AI backend — it does not
replace or modify it.

```
Browser
  └── Node.js/Express (port 3001)  ← this service
        └── Python/Flask (port 5000)  ← AI pipeline (DO NOT MODIFY)
              └── pipeline/ modules
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `express` | HTTP framework |
| `cors` | CORS headers |
| `morgan` | HTTP request logging |
| `multer` | Multipart file upload |
| `dotenv` | Environment variable loading |
| `winston` | Structured logging |
| `nodemon` *(dev)* | Auto-reload on file change |
