# SIH Frontend File — OcuScan AI Clinical Suite

A full-stack frontend demo for **OcuScan AI**, a diabetic retinopathy screening system built for Smart India Hackathon (SIH). It simulates the complete hospital clinical workflow — from retinal scan ingestion to ophthalmologist review and audit — using **Vanilla HTML/CSS/JS** for all operational screens and **Next.js 14 (App Router)** for the React portal layer.

---

## 🗂 Project Structure

```
SIH_frontend_file/
│
├── index.html              ← Public-facing landing portal (hero + roles + DR education)
├── login.html              ← Secure role-based auth gateway
├── technician.html         ← Phase 1 & 2: Upload & AI Quality Check workspace
├── doctor.html             ← Phase 3: Ophthalmologist PACS-style review workstation
├── dashboard.html          ← Central hospital Kanban flow & audit log
│
├── static/
│   ├── js/
│   │   ├── auth.js         ← Login logic, sessionStorage roles, route guards
│   │   ├── store.js        ← Shared localStorage clinical queue database
│   │   ├── ui.js           ← Canvas animation, glass tilt, slide-in menu
│   │   ├── technician.js   ← Technician workspace logic
│   │   ├── doctor.js       ← Doctor workstation logic (PDF export, magnifier, shortcuts)
│   │   └── dashboard.js    ← Kanban drag-and-drop, live render from store
│   ├── css/
│   │   └── styles.css      ← Shared styles for landing page
│   └── assets/             ← SVG icons and favicon
│
├── src/                    ← Next.js App Router source (React layer)
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── globals.css
│   ├── components/
│   │   ├── canvas/         ← Retinal canvas animation
│   │   ├── dashboard/      ← Clinical alerts, lab panels, telemetry, triage
│   │   ├── glass/          ← Liquid glass card effect
│   │   ├── hero/           ← Hero section lede column
│   │   ├── home/           ← Roles section, DR education section
│   │   ├── layout/         ← Header, footer, sidebar, slide menu, portal nav
│   │   └── ui/             ← Shared UI primitives (badge, button, card, SVG filters)
│   ├── lib/
│   │   ├── constants.ts
│   │   ├── mock-data.ts
│   │   └── utils.ts
│   └── types/
│       ├── clinical.ts
│       └── index.ts
│
├── docs/                   ← Documentation (see below)
├── serve.mjs               ← Node.js dev server (port 8123)
├── package.json
├── next.config.ts
├── tsconfig.json
└── postcss.config.mjs
```

---

## 🚀 Quick Start

### Option A — Open directly (no server needed)
The static HTML pages work standalone:
```bash
open index.html
```
> All `<script>` and `<link>` paths are relative (`./static/js/...`), so double-clicking any HTML file works.

### Option B — Dev server (recommended for full Next.js portal)
```bash
npm install
npm run dev        # Next.js dev server on http://localhost:3000
# OR
node serve.mjs     # Static-first server on http://localhost:8123
```

---

## 🔐 Demo Login Credentials

Navigate to `login.html` and use the **Evaluator Quick Access** pills, or enter manually:

| Role | Username | Password | Redirects To |
|---|---|---|---|
| Technician | `tech_demo` | `password` | `technician.html` |
| Ophthalmologist | `doc_demo` | `password` | `doctor.html` |
| Admin / Queue | `admin_demo` | `password` | `dashboard.html` |

Route guards are enforced on every protected page — direct URL access redirects back to `login.html`.

---

## 🩺 Application Flow

```
index.html  →  login.html  →  technician.html   (Phase 1 & 2)
                          →  doctor.html         (Phase 3)
                          →  dashboard.html      (Kanban Audit)
```

1. **Technician** uploads fundus scan → AI quality check (blur/exposure) → if passed, patient pushed to `localStorage` queue as `awaiting_doctor`
2. **Doctor** reviews AI Grad-CAM heatmap & lesion bounding boxes → approves or overrides grade → PDF clinical report auto-generated → patient marked `completed`
3. **Dashboard** shows the full Kanban board (drag-and-drop between stages) — live-synced with `localStorage`

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Static pages | Vanilla HTML5 · CSS3 · JavaScript (ES6+) |
| React portal | Next.js 14 App Router · TypeScript · Tailwind v4 |
| State / DB | Browser `localStorage` (`ocuscan_patient_queue`) |
| Auth | Browser `sessionStorage` (`currentUserRole`) |
| PDF Export | `html2pdf.js` (CDN, doctor workstation) |
| Build tool | Turbopack (Next.js) |

---

## ⌨️ Doctor Workstation Keyboard Shortcuts

| Key | Action |
|---|---|
| `Space` | Toggle Grad-CAM heatmap layer |
| `B` | Toggle lesion bounding box layer |
| `G` | Toggle Magic Glass magnifier |
| `A` | Approve AI decision → generate PDF |
| `M` | Open grade override panel |

---

## 📁 Key Files Reference

| File | Purpose |
|---|---|
| `static/js/store.js` | Shared clinical queue (localStorage CRUD) |
| `static/js/auth.js` | Login validation, `routeGuard()`, demo pills |
| `static/js/doctor.js` | Full PACS workstation logic |
| `src/components/ui/svg-filters.tsx` | Liquid glass SVG displacement filter (R:65 G:56 B:47) |

---

*OcuScan AI — Smart India Hackathon 2024/2025*
