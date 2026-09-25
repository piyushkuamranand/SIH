# 🔌 OcuScan AI — Frontend ↔ Backend Integration Guide

This guide contains the **Master Prompt** and complete technical specification required to connect this frontend (`SIH_frontend_file`) to your existing or pre-built backend service (e.g., Python FastAPI, Flask, Django, Node.js/Express, or Go).

---

## 📑 Table of Contents
1. [Overview & Current Frontend Architecture](#1-overview--current-frontend-architecture)
2. [🤖 Master Prompt (Copy & Paste for AI / Developer)](#2--master-prompt-copy--paste-for-ai--developer)
3. [📡 API Specification & Data Contracts](#3--api-specification--data-contracts)
4. [🛠 Step-by-Step Frontend File Modifications](#4--step-by-step-frontend-file-modifications)
5. [🌐 CORS Configuration Examples](#5--cors-configuration-examples)
6. [🧪 End-to-End Testing Checklist](#6--end-to-end-testing-checklist)

---

## 1. Overview & Current Frontend Architecture

This frontend is a clinical-grade Diabetic Retinopathy (DR) diagnostic workflow designed for the Smart India Hackathon (SIH). It consists of two layers:

1. **Operational Clinical Workstations (Vanilla HTML5 / Modern JS / CSS)**:
   - [`index.html`](./index.html): Public landing portal & clinical overview.
   - [`login.html`](./login.html): Role-based access gateway (`technician`, `doctor`, `admin`).
   - [`technician.html`](./technician.html): Retinal scan upload, DICOM/image ingestion, and AI quality check.
   - [`doctor.html`](./doctor.html): Ophthalmologist PACS review workstation with AI Grad-CAM heatmaps, lesion bounding boxes, and diagnostic sign-off.
   - [`dashboard.html`](./dashboard.html): Hospital clinical flow Kanban board and patient triage audit log.
   - [`static/js/store.js`](./static/js/store.js): **Currently simulates the database in `localStorage`**.
   - [`static/js/auth.js`](./static/js/auth.js): **Currently simulates role validation in `sessionStorage`**.

2. **Next.js 14 / React Layer (`src/`)**:
   - Modern App Router portal running at port 3000 for hospital analytics, vitals monitoring, and component library.

---

## 2. 🤖 Master Prompt (Copy & Paste for AI / Developer)

> **Instructions**: Copy the entire prompt block below and paste it into Antigravity, Claude, ChatGPT, or provide it to your backend developer to immediately connect the frontend to your backend.

```markdown
### SYSTEM ROLE & OBJECTIVE
You are an expert full-stack engineer tasked with integrating an existing clinical frontend (`SIH_frontend_file`) with our backend API.

The frontend currently uses simulated client-side mock data stored in `localStorage` (`static/js/store.js`) and mock credentials in `sessionStorage` (`static/js/auth.js`). Your objective is to replace these simulations with real HTTP REST API calls and/or WebSockets to connect the frontend to our preformed backend.

---

### BACKEND BASE URL & ENVIRONMENT CONFIGURATION
1. Create a global configuration file at `static/js/config.js` and include it in all HTML files before other scripts:
   ```javascript
   window.API_CONFIG = {
     BASE_URL: window.ENV_API_URL || "http://localhost:8000/api/v1",
     WS_URL: window.ENV_WS_URL || "ws://localhost:8000/ws",
     TOKEN_KEY: "ocuscan_auth_token",
     USER_KEY: "currentUserRole",
     USER_ID_KEY: "currentUserId"
   };
   ```
2. For the Next.js portal (`src/`), use the environment variable `NEXT_PUBLIC_BACKEND_URL=http://localhost:8000/api/v1` in `.env.local`.

---

### REQUIRED ENDPOINTS & INTEGRATION POINTS

#### 1. Authentication & RBAC (`static/js/auth.js` -> `login.html`)
- **Action**: Replace `VALID_USERS` lookup in `auth.js` with a POST request to:
  `POST /api/v1/auth/login`
- **Request Body**:
  ```json
  { "username": "doc_demo", "password": "password" }
  ```
- **Response Expected**:
  ```json
  {
    "token": "eyJhbGciOi...",
    "user": {
      "id": "USR-102",
      "name": "Dr. Sarah Lin, MD",
      "role": "doctor" // "technician" | "doctor" | "admin"
    }
  }
  ```
- Store the returned JWT token in `localStorage.setItem(API_CONFIG.TOKEN_KEY, token)`.
- Attach `Authorization: Bearer <token>` to all subsequent requests.
- Redirect user based on `role` (`technician.html`, `doctor.html`, `dashboard.html`).

#### 2. Scan Upload & AI Quality Triage (`static/js/technician.js` -> `technician.html`)
- **Action**: In `technician.js`, when the technician drops a retinal image/DICOM and clicks "Upload & Analyze", send a `multipart/form-data` request to:
  `POST /api/v1/scans/upload-and-triage`
- **Form Data Fields**:
  - `file`: Retinal image file (`image/jpeg`, `image/png`, or `.dcm`)
  - `patientId`: e.g. "PT-1008"
  - `patientName`: e.g. "John Doe"
  - `patientAge`: 52
  - `eye`: "OD" or "OS"
  - `device`: Camera model string (e.g. "Topcon NW400")
  - `notes`: Clinical history string
- **Response Expected**:
  ```json
  {
    "success": true,
    "patient": {
      "id": "PT-1008",
      "status": "awaiting_doctor",
      "aiGrade": 2,
      "confidence": 91.5,
      "qualityScore": 96.0,
      "imageUrl": "/media/scans/PT-1008_base.png",
      "heatmapUrl": "/media/scans/PT-1008_gradcam.png",
      "lesions": { "ma": 5, "he": 2, "ex": 1, "nv": "Absent" },
      "received": "05:15 UTC"
    }
  }
  ```
- Display the returned AI confidence, quality badges, and update the UI notification before redirecting or clearing the drop-zone.

#### 3. Clinical Kanban Queue Management (`static/js/store.js` & `static/js/dashboard.js`)
- **Action**: Refactor `OcuScanStore` in `store.js` from synchronous `localStorage` to asynchronous API methods:
  - `OcuScanStore.getQueue()` -> `GET /api/v1/patients/queue`
  - `OcuScanStore.updatePatientStatus(id, newStatus, extraProps)` -> `PATCH /api/v1/patients/{id}/status`
    Request payload:
    ```json
    { "status": "completed", "notes": "Approved by Dr. Lin", "verifiedGrade": 3 }
    ```
- **Optional Real-Time Sync**: Connect `static/js/dashboard.js` to `ws://localhost:8000/ws/queue` so cards move in real-time when another doctor or technician updates a case.

#### 4. Ophthalmologist PACS Workstation (`static/js/doctor.js` -> `doctor.html`)
- **Action**: In `doctor.js`:
  1. On page load, fetch the active patient for review:
     `GET /api/v1/doctor/next-case` or `GET /api/v1/patients/{id}`
  2. Populate:
     - Base Retinal Image: update `layer-base` src to `patient.imageUrl`
     - AI Heatmap Overlay: update `layer-heatmap` src to `patient.heatmapUrl`
     - Bounding boxes: render lesion markers from `patient.lesions`
     - Clinical meta: update patient ID, age, eye, pre-existing conditions, AI confidence, and AI Grade.
  3. When clicking "Approve AI Decision":
     `POST /api/v1/doctor/diagnose`
     Payload:
     ```json
     {
       "patientId": "PT-1002",
       "action": "approved",
       "finalGrade": 3,
       "notes": "Confirmed severe NPDR. Retinal photocoagulation referral issued.",
       "physicianSignature": "Dr. Sarah Lin, MD"
     }
     ```
  4. When clicking "Modify AI Decision":
     Payload:
     ```json
     {
       "patientId": "PT-1002",
       "action": "modified",
       "overrideGrade": 2,
       "notes": "Downgraded to Moderate NPDR; artifacts mistaken for neovascularization.",
       "physicianSignature": "Dr. Sarah Lin, MD"
     }
     ```
  5. PDF Clinical Report:
     Trigger `GET /api/v1/reports/pdf/{patientId}` to stream or download the official signed diagnostic report.

---

### NON-FUNCTIONAL REQUIREMENTS
1. **Backward Compatibility**: If the backend is temporarily offline or unreachable, fall back gracefully to `localStorage` data with a console warning or visual banner ("Offline / Demo Mode").
2. **CORS Handling**: Ensure requests send standard credentials/headers:
   ```javascript
   headers: {
     "Authorization": `Bearer ${localStorage.getItem(API_CONFIG.TOKEN_KEY)}`,
     "Content-Type": "application/json"
   }
   ```
3. **No Breaking Changes to UI**: Preserve all animations, glassmorphism styles, keyboard shortcuts (Space, A, M, B, G), and canvas layers in `technician.html`, `doctor.html`, and `dashboard.html`.
```

---

## 3. 📡 API Specification & Data Contracts

### 3.1 Authentication
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/auth/login` | Authenticate user and issue JWT | No |
| `GET` | `/api/v1/auth/me` | Fetch authenticated user profile | Bearer Token |
| `POST` | `/api/v1/auth/logout` | Invalidate token/session | Bearer Token |

### 3.2 Clinical Queue & Patient Operations
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/patients/queue` | List all patients sorted by priority & status | Bearer Token |
| `GET` | `/api/v1/patients/:id` | Get full clinical details, scans, and AI audit for a patient | Bearer Token |
| `PATCH` | `/api/v1/patients/:id/status` | Move patient across Kanban columns (`awaiting_precheck`, `awaiting_doctor`, `completed`, `flagged_audit`) | Bearer Token |
| `POST` | `/api/v1/patients` | Manually register a patient | Bearer Token |

### 3.3 Scan Ingestion & AI Model Pipeline
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/scans/upload` | Upload raw retinal image / DICOM file | Bearer Token |
| `POST` | `/api/v1/scans/ai-triage` | Trigger deep learning inference (DR Grade 0-4, Grad-CAM, lesion segmentation) | Bearer Token |
| `GET` | `/api/v1/doctor/next-case` | Get next waiting patient for doctor triage | Bearer (Doctor) |
| `POST` | `/api/v1/doctor/diagnose` | Record doctor's final diagnostic sign-off or override | Bearer (Doctor) |
| `GET` | `/api/v1/reports/:id/pdf` | Generate & download certified clinical PDF report | Bearer Token |

---

## 4. 🛠 Step-by-Step Frontend File Modifications

To connect this frontend manually without an AI agent:

### Step 1: Add `static/js/config.js`
Create `static/js/config.js`:
```javascript
window.API_CONFIG = {
  BASE_URL: "http://localhost:8000/api/v1",
  TOKEN_KEY: "ocuscan_auth_token",
  USER_KEY: "currentUserRole",
  USER_ID_KEY: "currentUserId"
};
```
Reference it in `<head>` of all HTML files (`index.html`, `login.html`, `technician.html`, `doctor.html`, `dashboard.html`):
```html
<script src="./static/js/config.js"></script>
```

### Step 2: Update `static/js/auth.js`
Replace the local credential check with:
```javascript
async function loginUser(username, password) {
  try {
    const res = await fetch(`${window.API_CONFIG.BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });
    if (!res.ok) throw new Error("Invalid credentials");
    const data = await res.json();
    
    // Store token and role
    localStorage.setItem(window.API_CONFIG.TOKEN_KEY, data.token);
    sessionStorage.setItem("currentUserRole", data.user.role);
    sessionStorage.setItem("currentUserId", data.user.id);
    
    // Redirect
    const redirectMap = {
      technician: "technician.html",
      doctor: "doctor.html",
      admin: "dashboard.html"
    };
    window.location.href = redirectMap[data.user.role] || "index.html";
  } catch (err) {
    showError(err.message);
  }
}
```

### Step 3: Update `static/js/store.js`
Wrap API calls with fallbacks so the application remains functional even during server maintenance:
```javascript
const OcuScanStore = {
  async getQueue() {
    try {
      const res = await fetch(`${window.API_CONFIG.BASE_URL}/patients/queue`, {
        headers: { "Authorization": `Bearer ${localStorage.getItem(window.API_CONFIG.TOKEN_KEY)}` }
      });
      if (!res.ok) throw new Error("Network error");
      return await res.json();
    } catch (e) {
      console.warn("Using offline fallback queue:", e);
      return JSON.parse(localStorage.getItem("ocuscan_patient_queue")) || DEFAULT_QUEUE;
    }
  },

  async updatePatientStatus(id, newStatus, extraProps = {}) {
    try {
      const res = await fetch(`${window.API_CONFIG.BASE_URL}/patients/${id}/status`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem(window.API_CONFIG.TOKEN_KEY)}`
        },
        body: JSON.stringify({ status: newStatus, ...extraProps })
      });
      return await res.json();
    } catch (e) {
      console.warn("Falling back to local storage status update:", e);
      // fallback to existing localStorage logic
    }
  }
};
window.OcuScanStore = OcuScanStore;
```

---

## 5. 🌐 CORS Configuration Examples

Ensure your backend allows cross-origin requests from the frontend origin (`http://localhost:3000` or `http://localhost:8123` or `file://`).

### Python FastAPI Example
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="OcuScan AI Backend")

origins = [
    "http://localhost:3000",
    "http://localhost:8123",
    "http://127.0.0.1:8123",
    "http://127.0.0.1:5500",  # Live Server
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Node.js / Express Example
```javascript
const express = require("express");
const cors = require("cors");
const app = express();

app.use(cors({
  origin: ["http://localhost:3000", "http://localhost:8123", "http://127.0.0.1:8123"],
  credentials: true
}));
```

---

## 6. 🧪 End-to-End Testing Checklist

1. [ ] **Authentication**: Log in with `tech_demo`, `doc_demo`, or `admin_demo` and verify token is stored in `localStorage`.
2. [ ] **Technician Upload**: Upload a fundus scan in `technician.html` and verify the file is received at `/api/v1/scans/upload-and-triage`.
3. [ ] **AI Response**: Verify image quality score, confidence, and DR grade display properly on the technician workspace.
4. [ ] **Hospital Kanban**: Check `dashboard.html` to confirm the newly uploaded patient appears under "Awaiting Doctor Review".
5. [ ] **Doctor Workstation**: Open `doctor.html`, verify that the base image and Grad-CAM heatmap load from the backend, and click "Approve AI Decision" to verify status changes to `completed`.
6. [ ] **Audit Trail**: Confirm the audit log records the doctor's name, timestamp, and final diagnosis in the database.
