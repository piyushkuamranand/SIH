/**
 * dashboard.js
 * OcuScan AI — Central Hospital Flow & Audit Log (Kanban Board)
 * 
 * Dynamically renders patients from store.js (`getQueue()`),
 * manages HTML5 Drag & Drop, and persists gate transitions via `updatePatientStatus()`.
 */

(function () {
  "use strict";

  /* ── ROUTE GUARD ─────────────────────────────────────────
     'admin' OR 'doctor' roles may view the dashboard.
     Requires auth.js to be loaded first.
  ─────────────────────────────────────────────────────────── */
  if (typeof routeGuard === "function") {
    if (!routeGuard(["admin", "doctor"])) return;
  }

  // Elements
  const dropzones = document.querySelectorAll(".kanban-dropzone");
  const liveClock = document.getElementById("live-clock");
  const toast = document.getElementById("dashboard-toast");
  const toastMessage = document.getElementById("toast-message");
  const statActiveCases = document.getElementById("stat-active-cases");

  let draggedCard = null;
  let toastTimer = null;

  /* ── 1. Live UTC Clock ────────────────────────────────────────── */
  function updateLiveClock() {
    if (!liveClock) return;
    const now = new Date();
    const utcHours = String(now.getUTCHours()).padStart(2, "0");
    const utcMinutes = String(now.getUTCMinutes()).padStart(2, "0");
    const utcSeconds = String(now.getUTCSeconds()).padStart(2, "0");
    liveClock.textContent = `${utcHours}:${utcMinutes}:${utcSeconds} UTC`;
  }
  setInterval(updateLiveClock, 1000);
  updateLiveClock();

  function getCurrentTimeString() {
    const now = new Date();
    const hours = String(now.getUTCHours()).padStart(2, "0");
    const minutes = String(now.getUTCMinutes()).padStart(2, "0");
    const seconds = String(now.getUTCSeconds()).padStart(2, "0");
    return `${hours}:${minutes}:${seconds} UTC`;
  }

  /* ── 2. Toast Notification ────────────────────────────────────── */
  function showToast(msg) {
    if (!toast || !toastMessage) return;
    clearTimeout(toastTimer);
    toastMessage.textContent = msg;
    toast.classList.add("show");
    toastTimer = setTimeout(() => {
      toast.classList.remove("show");
    }, 3200);
  }

  /* ── 3. Helper: Map Status to Column Dropzone ID ────────────────── */
  function getDropzoneIdForStatus(status) {
    switch (status) {
      case "awaiting_precheck":
        return "dropzone-precheck";
      case "system":
      case "processing":
        return "dropzone-system";
      case "awaiting_doctor":
        return "dropzone-doctor";
      case "completed":
        return "dropzone-completed";
      default:
        return "dropzone-precheck";
    }
  }

  function getStatusFromColId(colId) {
    switch (colId) {
      case "precheck":
        return "awaiting_precheck";
      case "system":
        return "system";
      case "doctor":
        return "awaiting_doctor";
      case "completed":
        return "completed";
      default:
        return "awaiting_precheck";
    }
  }

  /* ── 4. Card Creation & HTML Generator ────────────────────────── */
  function createPatientCardElement(pt) {
    const card = document.createElement("article");
    card.className = "patient-card";
    card.id = "card-" + pt.id.toLowerCase().replace(/[^a-z0-9_-]/g, "");
    card.setAttribute("draggable", "true");
    card.setAttribute("data-patient-id", pt.id);

    // Determine priority styling
    let priorityClass = "priority-routine";
    let priorityLabel = pt.priority || "Routine";

    if (pt.status === "completed") {
      priorityClass = "priority-completed";
      priorityLabel = "Report Archived";
    } else if (pt.aiGrade >= 3 || pt.priority === "urgent") {
      priorityClass = "priority-urgent";
      priorityLabel = "Urgent Eval";
    } else if (pt.aiGrade === 1 || pt.aiGrade === 2 || pt.priority === "high") {
      priorityClass = "priority-high";
      priorityLabel = "Review Req";
    } else if (pt.status === "system") {
      priorityClass = "priority-active";
      priorityLabel = "Processing";
    }

    // Determine status badge
    let badgeClass = "badge-cyan";
    let badgeLabel = "● Ingested";

    if (pt.status === "completed") {
      badgeClass = "badge-green";
      badgeLabel = "✓ Finalized & Synced";
    } else if (pt.aiGrade !== null && pt.aiGrade !== undefined) {
      if (pt.aiGrade >= 3) {
        badgeClass = "badge-rose";
        badgeLabel = `● Grade ${pt.aiGrade} Severe`;
      } else if (pt.aiGrade >= 1) {
        badgeClass = "badge-amber";
        badgeLabel = `● Grade ${pt.aiGrade} (${pt.confidence || 88}%)`;
      } else {
        badgeClass = "badge-green";
        badgeLabel = "● Grade 0 Normal";
      }
    } else if (pt.status === "system") {
      badgeClass = "badge-purple";
      badgeLabel = "● AI Model v2.4";
    } else {
      badgeClass = "badge-cyan";
      badgeLabel = "● Awaiting Pre-Check";
    }

    card.innerHTML = `
      <div class="card-top">
        <span class="patient-id">${pt.id}</span>
        <span class="patient-priority ${priorityClass}">${priorityLabel}</span>
      </div>
      <div class="card-meta">
        <div class="meta-row"><span class="meta-label">Patient:</span> <strong>${pt.name || pt.id}</strong></div>
        <div class="meta-row"><span class="meta-label">Age:</span> <strong>${pt.age} yrs</strong></div>
        <div class="meta-row"><span class="meta-label">Eye:</span> <span>${pt.eye || "OD (Right)"}</span></div>
        <div class="meta-row"><span class="meta-label">Device:</span> <span>${pt.device ? pt.device.split("·")[0].trim() : "Topcon TRC"}</span></div>
      </div>
      <div class="card-badge-row">
        <span class="status-badge ${badgeClass}">${badgeLabel}</span>
        <span class="card-time">${pt.received || "Recent"}</span>
      </div>
      ${pt.signoffTime ? `<div class="audit-signoff"><span>✓ Signed off at: ${pt.signoffTime}</span></div>` : ""}
    `;

    setupCardDragEvents(card);
    return card;
  }

  /* ── 5. HTML5 Drag-and-Drop Implementation ────────────────────── */
  function setupCardDragEvents(card) {
    card.addEventListener("dragstart", function (e) {
      draggedCard = this;
      this.classList.add("dragging");
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", this.getAttribute("data-patient-id"));
    });

    card.addEventListener("dragend", function () {
      this.classList.remove("dragging");
      draggedCard = null;
      dropzones.forEach(zone => zone.classList.remove("drag-over"));
    });
  }

  // Dropzone drag/drop listeners
  dropzones.forEach(zone => {
    zone.addEventListener("dragover", function (e) {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      this.classList.add("drag-over");
    });

    zone.addEventListener("dragenter", function (e) {
      e.preventDefault();
      this.classList.add("drag-over");
    });

    zone.addEventListener("dragleave", function (e) {
      if (!this.contains(e.relatedTarget)) {
        this.classList.remove("drag-over");
      }
    });

    zone.addEventListener("drop", function (e) {
      e.preventDefault();
      this.classList.remove("drag-over");

      if (!draggedCard) return;

      const ptId = draggedCard.getAttribute("data-patient-id");
      const parentCol = this.closest(".kanban-col");
      const colId = parentCol ? parentCol.getAttribute("data-col-id") : "";
      const colTitle = parentCol ? parentCol.getAttribute("data-col-title") : "New Stage";
      const newStatus = getStatusFromColId(colId);

      // Append card to this dropzone
      this.appendChild(draggedCard);

      // Update in localStorage via store.js
      let extra = {};
      const currentTime = getCurrentTimeString();

      if (newStatus === "completed") {
        extra.signoffTime = currentTime;

        // Ensure sign-off badge is rendered on the card
        let signoffEl = draggedCard.querySelector(".audit-signoff");
        if (!signoffEl) {
          signoffEl = document.createElement("div");
          signoffEl.className = "audit-signoff";
          draggedCard.appendChild(signoffEl);
        }
        signoffEl.innerHTML = `<span>✓ Signed off at: ${currentTime}</span>`;

        // Update priority pill
        const priorityPill = draggedCard.querySelector(".patient-priority");
        if (priorityPill) {
          priorityPill.className = "patient-priority priority-completed";
          priorityPill.textContent = "Report Archived";
        }

        // Update status badge
        const statusBadge = draggedCard.querySelector(".status-badge");
        if (statusBadge) {
          statusBadge.className = "status-badge badge-green";
          statusBadge.textContent = "✓ Finalized & Synced";
        }

        showToast(`${ptId} finalized and signed off at ${currentTime}.`);
      } else {
        // If moved out of completed, remove signoff badge
        const signoffEl = draggedCard.querySelector(".audit-signoff");
        if (signoffEl) signoffEl.remove();

        showToast(`${ptId} transitioned to "${colTitle}".`);
      }

      if (window.OcuStore && typeof window.OcuStore.updatePatientStatus === "function") {
        window.OcuStore.updatePatientStatus(ptId, newStatus, extra);
      } else if (typeof updatePatientStatus === "function") {
        updatePatientStatus(ptId, newStatus, extra);
      }

      // Update column counter badges
      updateColumnCounts();
    });
  });

  /* ── 6. Column Count Recalculation ────────────────────────────── */
  function updateColumnCounts() {
    const cols = [
      { id: "dropzone-precheck", countEl: "count-precheck" },
      { id: "dropzone-system", countEl: "count-system" },
      { id: "dropzone-doctor", countEl: "count-doctor" },
      { id: "dropzone-completed", countEl: "count-completed" },
    ];

    let total = 0;
    cols.forEach(col => {
      const zone = document.getElementById(col.id);
      const counter = document.getElementById(col.countEl);
      if (zone && counter) {
        const count = zone.querySelectorAll(".patient-card").length;
        counter.textContent = count;
        total += count;
      }
    });

    if (statActiveCases) {
      statActiveCases.textContent = `${total} Patients`;
    }
  }

  /* ── 7. Render Board from store.js ────────────────────────────── */
  function renderBoard() {
    // Clear all dropzones first
    dropzones.forEach(zone => {
      zone.innerHTML = "";
    });

    const queue = (window.OcuStore && typeof window.OcuStore.getQueue === "function")
      ? window.OcuStore.getQueue()
      : (typeof getQueue === "function" ? getQueue() : []);

    queue.forEach(pt => {
      const dropzoneId = getDropzoneIdForStatus(pt.status);
      const targetZone = document.getElementById(dropzoneId);
      if (targetZone) {
        const cardEl = createPatientCardElement(pt);
        targetZone.appendChild(cardEl);
      }
    });

    updateColumnCounts();
  }

  // Reactive listener for queue updates in other tabs/pages
  window.addEventListener("ocuscan_queue_change", function () {
    renderBoard();
  });

  window.addEventListener("storage", function (e) {
    if (e.key === "ocuscan_patient_queue") {
      renderBoard();
    }
  });

  // Initial load
  renderBoard();

})();
