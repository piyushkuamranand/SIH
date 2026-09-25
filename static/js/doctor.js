/**
 * doctor.js
 * OcuScan AI — Ophthalmologist Workstation
 *
 * Connected to shared store.js database:
 *  1. On load, queries `getQueue()` for the first patient with `status: 'awaiting_doctor'`.
 *  2. Displays Patient ID, Age, Eye, and Clinical Notes on the review panel.
 *  3. On "Approve AI Decision", updates patient to `status: 'completed'`, generates clinical PDF,
 *     and reloads page to fetch the next waiting patient in queue.
 *  4. Layer toggle checkboxes (Base / Heatmap / Boxes) & Magic Glass 3× Magnifier.
 *  5. Keyboard shortcuts: Space=heatmap, A=approve, M=modify, B=boxes, G=glass.
 */

(function () {
  "use strict";

  /* ── ROUTE GUARD ─────────────────────────────────────────
     Only 'doctor' role may access this page.
     Requires auth.js to be loaded first.
  ─────────────────────────────────────────────────────────── */
  if (typeof routeGuard === "function") {
    if (!routeGuard("doctor")) return;
  }

  /* ── DOM REFS ──────────────────────────────────────────── */
  const layerBase      = document.getElementById("layer-base");
  const layerHeatmap   = document.getElementById("layer-heatmap");
  const layerBoxes     = document.getElementById("layer-boxes");

  const chkBase        = document.getElementById("chk-base");
  const chkHeatmap     = document.getElementById("chk-heatmap");
  const chkBoxes       = document.getElementById("chk-boxes");

  const approveBtn     = document.getElementById("approve-btn");
  const modifyBtn      = document.getElementById("modify-btn");
  const modifyPanel    = document.getElementById("modify-panel");
  const submitOverride = document.getElementById("submit-override-btn");
  const mpGrade        = document.getElementById("mp-grade");
  const mpNotes        = document.getElementById("mp-notes");

  const toast          = document.getElementById("toast");
  const toastTitle     = document.getElementById("toast-title");
  const toastSub       = document.getElementById("toast-sub");
  const toastIcon      = document.getElementById("toast-icon");

  const emptyState     = document.getElementById("empty-state");
  const decisionCol    = document.getElementById("decision-col");

  const zoomInBtn      = document.getElementById("zoom-in");
  const zoomOutBtn     = document.getElementById("zoom-out");
  const zoomLevelEl    = document.getElementById("zoom-level");
  const viewerMain     = document.getElementById("viewer-main");
  const confFill       = document.getElementById("conf-fill");

  /* Live patient/AI elements */
  const ptId           = document.getElementById("pt-id");
  const ptAge          = document.getElementById("pt-age");
  const ptEye          = document.getElementById("pt-eye");
  const ptReceived     = document.getElementById("pt-received");
  const ptNotes        = document.getElementById("pt-notes");
  const aiGradeBadge   = document.getElementById("ai-grade-badge");
  const aiPredictionEm = document.getElementById("ai-prediction-em");
  const confValueLabel = document.getElementById("conf-value-label");
  const lesionChips    = document.getElementById("lesion-chips");
  const queueBadge     = document.querySelector(".queue-badge");

  /* Magnifier */
  const magToggleBtn   = document.getElementById("mag-toggle-btn");
  const magToggleLabel = magToggleBtn ? magToggleBtn.querySelector(".mag-toggle-label") : null;
  const magnifier      = document.getElementById("magnifier");
  const magCanvas      = document.getElementById("magnifier-canvas");
  const magCtx         = magCanvas ? magCanvas.getContext("2d") : null;

  /* Patient loading overlay & PDF datetime */
  const patientOverlay = document.getElementById("patient-loading-overlay");
  const pdfDatetimeEl  = document.getElementById("pdf-datetime");

  /* ── CONSTANTS ─────────────────────────────────────────── */
  const MAG_SIZE   = 150;
  const MAG_RADIUS = MAG_SIZE / 2;
  const ZOOM       = 3;
  const SRC_SIZE   = MAG_SIZE / ZOOM;
  const LAYER_SIZE = 560;

  /* ── STATE ─────────────────────────────────────────────── */
  let currentPatient    = null;
  let modifyOpen        = false;
  let zoomLevel         = 100;
  let isMagnifierActive = false;

  /* ══════════════════════════════════════════════════════════
     1. QUEUE INITIALIZATION & PATIENT LOADING
  ══════════════════════════════════════════════════════════ */
  function loadActivePatientFromStore() {
    const queue = (window.OcuStore && typeof window.OcuStore.getQueue === "function")
      ? window.OcuStore.getQueue()
      : (typeof getQueue === "function" ? getQueue() : []);

    const waitingPatients = queue.filter(p => p.status === "awaiting_doctor");
    currentPatient = waitingPatients.length > 0 ? waitingPatients[0] : null;

    // Update Top Navbar Queue Badge
    if (queueBadge) {
      const count = waitingPatients.length;
      if (count > 0) {
        queueBadge.style.cssText = "display:flex;align-items:center;gap:7px;padding:5px 14px;border-radius:999px;font-size:11px;font-weight:600;font-family:monospace;background:rgba(251,191,36,.08);border:1px solid rgba(251,191,36,.25);color:var(--amber);";
        queueBadge.innerHTML = `<div class="queue-dot"></div>Queue: ${count} Patient${count > 1 ? "s" : ""} Waiting`;
      } else {
        queueBadge.style.cssText = "display:flex;align-items:center;gap:7px;padding:5px 14px;border-radius:999px;font-size:11px;font-weight:600;font-family:monospace;background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.3);color:#22c55e;";
        queueBadge.innerHTML = '<div class="queue-dot" style="background:#22c55e;animation:none;"></div>Queue: 0 Clear';
      }
    }

    if (!currentPatient) {
      // No patients waiting — show empty / all clear state
      showEmptyQueueState();
      return;
    }

    // Populate Right-side Patient Details Panel
    if (ptId) ptId.textContent = currentPatient.id;
    if (ptAge) ptAge.textContent = (currentPatient.age || 50) + " yrs";
    if (ptEye) ptEye.textContent = currentPatient.eye || "OS (Left Eye)";
    if (ptReceived) ptReceived.textContent = currentPatient.received || "Recent";
    if (ptNotes && currentPatient.notes) ptNotes.textContent = currentPatient.notes;

    // AI Grade Badge & Diagnostic Result
    const grade = currentPatient.aiGrade !== null && currentPatient.aiGrade !== undefined ? currentPatient.aiGrade : 3;
    const confidence = currentPatient.confidence || (grade >= 3 ? 94 : 88);

    if (aiGradeBadge) {
      aiGradeBadge.textContent = `ETDRS GRADE ${grade}`;
      aiGradeBadge.style.cssText = grade >= 3
        ? "background:rgba(248,113,113,.12);border:1px solid rgba(248,113,113,.3);color:var(--red);"
        : "background:rgba(251,191,36,.12);border:1px solid rgba(251,191,36,.3);color:var(--amber);";
    }

    if (aiPredictionEm) {
      if (grade >= 3) {
        aiPredictionEm.textContent = `Grade ${grade} (Severe DR)`;
      } else if (grade === 1 || grade === 2) {
        aiPredictionEm.textContent = `Grade ${grade} (${grade === 1 ? "Mild" : "Moderate"} NPDR)`;
      } else {
        aiPredictionEm.textContent = "Grade 0 (No DR Detected)";
      }
    }

    if (confValueLabel) {
      confValueLabel.textContent = `${confidence}%`;
      confValueLabel.style.color = grade >= 3 ? "var(--green)" : "var(--amber)";
    }

    if (confFill) {
      confFill.style.width = "0%";
      setTimeout(() => {
        confFill.style.width = `${confidence}%`;
        confFill.className = "conf-fill" + (grade < 3 ? " amber" : "");
      }, 300);
    }

    // Lesions summary
    if (lesionChips && currentPatient.lesions) {
      const l = currentPatient.lesions;
      lesionChips.innerHTML = `
        <span class="lc ma">MA ×${l.ma || 0}</span>
        <span class="lc he">HE ×${l.he || 0}</span>
        <span class="lc ex">EX ×${l.ex || 0}</span>
        <span class="lc nv">NV: ${l.nv || "Absent"}</span>
      `;
    }

    // Viewer Titlebar
    const viewerTag = document.querySelector(".viewer-tag");
    const viewerMetaEl = document.querySelector(".viewer-titlebar span:not(.viewer-tag)");
    if (viewerTag) {
      viewerTag.textContent = currentPatient.eye && currentPatient.eye.includes("OD") ? "FUNDUS · OD" : "FUNDUS · OS";
    }
    if (viewerMetaEl) {
      viewerMetaEl.textContent = `${currentPatient.id} · Age ${currentPatient.age} · ${currentPatient.eye || "Fundus"}`;
    }

    // Update off-screen PDF template elements to match this patient
    updatePdfTemplate(currentPatient, grade, confidence);
  }

  function showEmptyQueueState() {
    const viewerCol = document.querySelector(".viewer-col");
    if (viewerCol) {
      viewerCol.style.transition = "opacity .5s ease";
      viewerCol.style.opacity = "0.08";
      viewerCol.style.pointerEvents = "none";
    }
    setMagnifierState(false);

    const panels = decisionCol.querySelectorAll(".panel-block, .modify-panel");
    panels.forEach(p => (p.style.display = "none"));

    if (emptyState) {
      emptyState.style.display = "flex";
      const emptySub = emptyState.querySelector(".empty-sub");
      if (emptySub) {
        emptySub.textContent = "All patients in queue have been reviewed and approved. Queue is clear.";
      }
    }

    showToast("Queue Empty", "No patients currently waiting for ophthalmologist review.", "✓", "success", 4000);
  }

  function updatePdfTemplate(pt, grade, confidence) {
    const pdfEl = document.getElementById("pdf-report");
    if (!pdfEl) return;

    // Update case title & patient grid inside PDF
    const pidEls = pdfEl.querySelectorAll(".pdf-pt-id, div");
    pidEls.forEach(el => {
      if (el.textContent === "PT-8922") el.textContent = pt.id;
      if (el.textContent === "54 years") el.textContent = `${pt.age} years`;
      if (el.textContent === "OS (Left Eye)") el.textContent = pt.eye || "OS (Left Eye)";
    });
  }

  /* ══════════════════════════════════════════════════════════
     2. LAYER TOGGLES
  ══════════════════════════════════════════════════════════ */
  function applyLayerVisibility() {
    layerBase.style.opacity    = chkBase.checked    ? "1" : "0";
    layerHeatmap.style.opacity = chkHeatmap.checked ? "1" : "0";
    layerBoxes.style.opacity   = chkBoxes.checked   ? "1" : "0";
    scheduleImageRefresh();
  }

  chkBase.addEventListener("change",    applyLayerVisibility);
  chkHeatmap.addEventListener("change", applyLayerVisibility);
  chkBoxes.addEventListener("change",   applyLayerVisibility);

  /* ══════════════════════════════════════════════════════════
     3. MAGIC GLASS 3× MAGNIFIER
  ══════════════════════════════════════════════════════════ */
  let baseImg = new Image();
  let heatmapImg = new Image();
  let boxesImg = new Image();
  let imagesReady = false;
  let refreshTimer = null;

  function serializeSVGToImage(svgEl, callback) {
    try {
      let s = new XMLSerializer().serializeToString(svgEl);
      if (!s.includes("xmlns=")) s = s.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"');
      const blob = new Blob([s], { type: "image/svg+xml;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const img = new Image();
      img.onload = function () { callback(img); URL.revokeObjectURL(url); };
      img.onerror = function () { URL.revokeObjectURL(url); };
      img.src = url;
    } catch (e) {}
  }

  function scheduleImageRefresh() {
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(refreshImages, 80);
  }

  function refreshImages() {
    imagesReady = false;
    let loaded = 0;
    function onLoad() { if (++loaded >= 3) imagesReady = true; }
    const fundusSVG = document.getElementById("fundus-svg");
    const heatmapSVG = document.getElementById("heatmap-svg");
    const boxesSVG = document.getElementById("layer-boxes");
    if (fundusSVG)  serializeSVGToImage(fundusSVG,  i => { baseImg = i; onLoad(); });
    if (heatmapSVG) serializeSVGToImage(heatmapSVG, i => { heatmapImg = i; onLoad(); });
    if (boxesSVG)   serializeSVGToImage(boxesSVG,   i => { boxesImg = i; onLoad(); });
  }

  function drawMagnifier(layerX, layerY) {
    if (!imagesReady || !magCtx) return;
    const half = SRC_SIZE / 2;
    const srcX = Math.max(0, Math.min(LAYER_SIZE - SRC_SIZE, layerX - half));
    const srcY = Math.max(0, Math.min(LAYER_SIZE - SRC_SIZE, layerY - half));

    magCtx.clearRect(0, 0, MAG_SIZE, MAG_SIZE);
    magCtx.save();
    magCtx.beginPath();
    magCtx.arc(MAG_RADIUS, MAG_RADIUS, MAG_RADIUS, 0, Math.PI * 2);
    magCtx.clip();

    if (chkBase.checked && baseImg.complete && baseImg.naturalWidth) {
      magCtx.globalCompositeOperation = "source-over";
      magCtx.globalAlpha = 1;
      magCtx.drawImage(baseImg, srcX, srcY, SRC_SIZE, SRC_SIZE, 0, 0, MAG_SIZE, MAG_SIZE);
    } else {
      magCtx.fillStyle = "#050810";
      magCtx.fillRect(0, 0, MAG_SIZE, MAG_SIZE);
    }

    if (chkHeatmap.checked && heatmapImg.complete && heatmapImg.naturalWidth) {
      magCtx.globalCompositeOperation = "hard-light";
      magCtx.globalAlpha = 1;
      magCtx.drawImage(heatmapImg, srcX, srcY, SRC_SIZE, SRC_SIZE, 0, 0, MAG_SIZE, MAG_SIZE);
      magCtx.globalCompositeOperation = "source-over";
    }

    if (chkBoxes.checked && boxesImg.complete && boxesImg.naturalWidth) {
      magCtx.globalAlpha = 1;
      magCtx.drawImage(boxesImg, srcX, srcY, SRC_SIZE, SRC_SIZE, 0, 0, MAG_SIZE, MAG_SIZE);
    }

    magCtx.restore();
  }

  viewerMain.addEventListener("mousemove", function (e) {
    if (!isMagnifierActive) return;
    const rect = viewerMain.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    const cx = rect.width / 2;
    const cy = rect.height / 2;
    const dist = Math.sqrt((mouseX - cx) * (mouseX - cx) + (mouseY - cy) * (mouseY - cy));

    if (dist > LAYER_SIZE / 2) {
      magnifier.style.display = "none";
      viewerMain.style.cursor = "crosshair";
      return;
    }

    viewerMain.style.cursor = "none";
    magnifier.style.display = "block";
    magnifier.style.left = (mouseX - MAG_RADIUS) + "px";
    magnifier.style.top  = (mouseY - MAG_RADIUS) + "px";
    drawMagnifier(mouseX - cx + LAYER_SIZE / 2, mouseY - cy + LAYER_SIZE / 2);
  });

  viewerMain.addEventListener("mouseleave", function () {
    magnifier.style.display = "none";
    if (isMagnifierActive) viewerMain.style.cursor = "crosshair";
  });

  function setMagnifierState(active) {
    isMagnifierActive = active;
    if (magToggleBtn) magToggleBtn.classList.toggle("active", active);
    if (magToggleLabel) magToggleLabel.textContent = active ? "Magic Glass: ON" : "Magic Glass";
    if (!active) {
      magnifier.style.display = "none";
      viewerMain.style.cursor = "default";
    } else {
      viewerMain.style.cursor = "crosshair";
      scheduleImageRefresh();
    }
  }

  if (magToggleBtn) {
    magToggleBtn.addEventListener("click", function () {
      setMagnifierState(!isMagnifierActive);
      showToast(
        isMagnifierActive ? "Magic Glass Active" : "Magic Glass Disabled",
        isMagnifierActive ? "Hover retinal image to magnify 3×" : "Normal cursor restored",
        isMagnifierActive ? "🔍" : "✕", "success"
      );
    });
  }

  /* ══════════════════════════════════════════════════════════
     4. ZOOM CONTROLS
  ══════════════════════════════════════════════════════════ */
  function applyZoom() {
    const scale = zoomLevel / 100;
    [layerBase, layerHeatmap, layerBoxes].forEach(el => {
      el.style.transform = `translate(-50%, -50%) scale(${scale})`;
      el.style.transformOrigin = "center center";
    });
    zoomLevelEl.textContent = `${zoomLevel}%`;
  }

  zoomInBtn.addEventListener("click",  () => { if (zoomLevel < 200) { zoomLevel += 15; applyZoom(); } });
  zoomOutBtn.addEventListener("click", () => { if (zoomLevel > 50)  { zoomLevel -= 15; applyZoom(); } });

  /* ══════════════════════════════════════════════════════════
     5. TOAST NOTIFICATIONS
  ══════════════════════════════════════════════════════════ */
  let toastTimer = null;

  function showToast(title, sub, icon, type, duration) {
    clearTimeout(toastTimer);
    toastTitle.textContent = title;
    toastSub.textContent   = sub || "";
    toastIcon.textContent  = icon || "✓";

    if (type === "warning") {
      toastIcon.style.background  = "rgba(251,191,36,.12)";
      toastIcon.style.borderColor = "rgba(251,191,36,.3)";
      toastIcon.style.color       = "#fbbf24";
    } else if (type === "info") {
      toastIcon.style.background  = "rgba(34,211,238,.12)";
      toastIcon.style.borderColor = "rgba(34,211,238,.3)";
      toastIcon.style.color       = "#22c55e";
    } else {
      toastIcon.style.background  = "rgba(34,197,94,.12)";
      toastIcon.style.borderColor = "rgba(34,197,94,.25)";
      toastIcon.style.color       = "#22c55e";
    }

    toast.classList.add("show");
    toastTimer = setTimeout(() => { toast.classList.remove("show"); }, duration || 4000);
  }

  /* ══════════════════════════════════════════════════════════
     6. CLINICAL PDF GENERATION
  ══════════════════════════════════════════════════════════ */
  function generateClinicalPDF(patientId, callback) {
    const now = new Date();
    const dateStr = now.toISOString().replace("T", " ").substring(0, 19) + " UTC";
    if (pdfDatetimeEl) pdfDatetimeEl.textContent = `Generated: ${dateStr}`;

    const pdfEl = document.getElementById("pdf-report");
    if (!pdfEl || typeof html2pdf === "undefined") {
      console.warn("html2pdf not available — continuing workflow");
      if (callback) callback();
      return;
    }

    const filename = `OcuScan_Report_${patientId || "Case"}.pdf`;
    const opts = {
      margin:      [0, 0, 0, 0],
      filename:    filename,
      image:       { type: "jpeg", quality: 0.97 },
      html2canvas: { scale: 2, useCORS: true, logging: false, backgroundColor: "#ffffff" },
      jsPDF:       { unit: "pt", format: "a4", orientation: "portrait" },
      pagebreak:   { mode: "avoid-all" }
    };

    html2pdf()
      .set(opts)
      .from(pdfEl)
      .save()
      .then(() => {
        if (callback) callback();
      })
      .catch(err => {
        console.error("PDF generation error:", err);
        if (callback) callback();
      });
  }

  /* ══════════════════════════════════════════════════════════
     7. APPROVE & ADVANCE QUEUE WORKFLOW
  ══════════════════════════════════════════════════════════ */
  approveBtn.addEventListener("click", function () {
    if (!currentPatient || approveBtn.disabled) return;
    approveBtn.disabled = true;
    approveBtn.style.opacity = "0.5";
    approveBtn.style.pointerEvents = "none";

    const approvedId = currentPatient.id;

    // 1. Update status in localStorage to 'completed'
    if (window.OcuStore && typeof window.OcuStore.updatePatientStatus === "function") {
      window.OcuStore.updatePatientStatus(approvedId, "completed");
    } else if (typeof updatePatientStatus === "function") {
      updatePatientStatus(approvedId, "completed");
    }

    // 2. Trigger PDF report generation
    showToast(
      "Generating Clinical PDF Report...",
      `Compiling OcuScan_Report_${approvedId}.pdf`,
      "📄", "info", 5000
    );

    setTimeout(() => {
      generateClinicalPDF(approvedId, () => {
        // 3. Show progression toast and reload to pull next patient
        showToast(
          `Patient ${approvedId} Approved & Cleared`,
          "Loading next waiting patient from queue...",
          "✓", "success", 3000
        );

        setTimeout(() => {
          window.location.reload();
        }, 1600);
      });
    }, 350);
  });

  /* ══════════════════════════════════════════════════════════
     8. MODIFY / OVERRIDE WORKFLOW
  ══════════════════════════════════════════════════════════ */
  modifyBtn.addEventListener("click", function () {
    if (!currentPatient) return;
    modifyOpen = !modifyOpen;
    modifyPanel.classList.toggle("open", modifyOpen);
    modifyBtn.style.background = modifyOpen ? "rgba(251,191,36,.16)" : "rgba(251,191,36,.07)";
    if (modifyOpen) setTimeout(() => { mpNotes.focus(); }, 50);
  });

  submitOverride.addEventListener("click", function () {
    if (!currentPatient) return;

    if (!mpGrade.value) {
      mpGrade.style.borderColor = "rgba(248,113,113,.6)";
      mpGrade.style.boxShadow   = "0 0 0 3px rgba(248,113,113,.15)";
      setTimeout(() => { mpGrade.style.borderColor = ""; mpGrade.style.boxShadow = ""; }, 2000);
      return;
    }

    const overriddenGrade = parseInt(mpGrade.value, 10);
    const gradeTxt = mpGrade.options[mpGrade.selectedIndex].text || "—";
    const overrideNotes = mpNotes.value.trim() || "Ophthalmologist clinical override applied.";

    // Update patient status in localStorage
    if (window.OcuStore && typeof window.OcuStore.updatePatientStatus === "function") {
      window.OcuStore.updatePatientStatus(currentPatient.id, "completed", {
        aiGrade: overriddenGrade,
        notes: overrideNotes
      });
    }

    showToast("Override Submitted", `Grade: ${gradeTxt}. Report signed off.`, "✓", "success");

    setTimeout(() => {
      window.location.reload();
    }, 1500);
  });

  /* ══════════════════════════════════════════════════════════
     9. KEYBOARD SHORTCUTS
  ══════════════════════════════════════════════════════════ */
  document.addEventListener("keydown", function (e) {
    const tag = (e.target.tagName || "").toLowerCase();
    if (tag === "textarea" || tag === "input" || tag === "select") return;

    switch (e.key) {
      case " ":
      case "Spacebar":
        e.preventDefault();
        chkHeatmap.checked = !chkHeatmap.checked;
        applyLayerVisibility();
        showToast(
          chkHeatmap.checked ? "Grad-CAM: ON" : "Grad-CAM: OFF",
          "Press Space to toggle",
          chkHeatmap.checked ? "🔥" : "⬜", "success"
        );
        break;
      case "g": case "G":
        if (magToggleBtn) magToggleBtn.click();
        break;
      case "a": case "A":
        if (!approveBtn.disabled) approveBtn.click();
        break;
      case "m": case "M":
        modifyBtn.click();
        break;
      case "b": case "B":
        chkBoxes.checked = !chkBoxes.checked;
        applyLayerVisibility();
        break;
      case "+": case "=": zoomInBtn.click();  break;
      case "-": case "_": zoomOutBtn.click(); break;
    }
  });

  /* ══════════════════════════════════════════════════════════
     INITIALIZATION
  ══════════════════════════════════════════════════════════ */
  applyLayerVisibility();
  scheduleImageRefresh();

  // Load first awaiting_doctor patient from store
  loadActivePatientFromStore();

  // Add G shortcut hint if not present
  const shortcutBar = document.querySelector(".shortcut-bar");
  if (shortcutBar && !shortcutBar.querySelector(".shortcut-glass")) {
    const gHint = document.createElement("span");
    gHint.className = "shortcut-glass";
    gHint.innerHTML = '<kbd class="kbd">G</kbd> Glass';
    shortcutBar.insertBefore(gHint, shortcutBar.firstChild);
  }

})();
