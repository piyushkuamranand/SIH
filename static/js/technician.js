/**
 * technician.js
 * OcuScan AI — Technician Upload Workspace
 * Phase 1 AI Quality Check Simulation
 */

(function () {
  "use strict";

  /* ── ROUTE GUARD ─────────────────────────────────────────
     Only 'technician' role may access this page.
     Requires auth.js to be loaded first.
  ─────────────────────────────────────────────────────────── */
  if (typeof routeGuard === "function") {
    if (!routeGuard("technician")) return;
  }

  /* ── DOM REFS ───────────────────────────────────────────── */
  const dropZone       = document.getElementById("drop-zone");
  const dropIdle       = document.getElementById("drop-idle");
  const previewCont    = document.getElementById("preview-container");
  const previewImg     = document.getElementById("preview-img");
  const previewTag     = document.getElementById("preview-tag");
  const clearBtn       = document.getElementById("clear-btn");
  const fileInput      = document.getElementById("file-input");
  const browseTrigger  = document.getElementById("browse-trigger");
  const fileInfoStrip  = document.getElementById("file-info-strip");
  const fileNameEl     = document.getElementById("file-name");
  const fileSizeEl     = document.getElementById("file-size");
  const qualityBadges  = document.getElementById("quality-badges");
  const badgeSize      = document.getElementById("badge-size");
  const uploadBtn      = document.getElementById("upload-btn");
  const loadingBanner  = document.getElementById("loading-banner");
  const loadingText    = document.getElementById("loading-text");
  const aiBanner       = document.getElementById("ai-banner");
  const bannerIcon     = document.getElementById("banner-icon");
  const bannerText     = document.getElementById("banner-text");

  // DICOM meta fields
  const metaFormat     = document.getElementById("meta-format");
  const metaRes        = document.getElementById("meta-res");
  const metaSize       = document.getElementById("meta-size");

  // Steps
  const step2          = document.getElementById("step-2");
  const step3          = document.getElementById("step-3");
  const step4          = document.getElementById("step-4");

  let currentFile = null;

  /* ── UTILITIES ──────────────────────────────────────────── */

  function formatBytes(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(2) + " MB";
  }

  function getExtension(name) {
    return name.split(".").pop().toUpperCase() || "IMG";
  }

  function hideBanner() {
    aiBanner.style.display    = "none";
    loadingBanner.style.display = "none";
    aiBanner.className        = "";
  }

  function showLoadingBanner(text) {
    hideBanner();
    loadingText.textContent   = text;
    loadingBanner.style.display = "flex";
  }

  function showResultBanner(type, message) {
    loadingBanner.style.display = "none";
    aiBanner.className          = type;       // "success" | "error"
    aiBanner.style.display      = "flex";
    bannerText.textContent      = message;

    if (type === "success") {
      bannerIcon.innerHTML = `<path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>`;
      bannerIcon.setAttribute("stroke", "currentColor");
    } else {
      bannerIcon.innerHTML = `<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>`;
      bannerIcon.setAttribute("stroke", "currentColor");
    }
  }

  function advanceStep(stepEl) {
    stepEl.classList.add("active");
  }

  function markStepDone(stepEl) {
    stepEl.classList.remove("active");
    stepEl.classList.add("done");
    const num = stepEl.querySelector(".step-num");
    // Checkmark
    num.innerHTML = `
      <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="3">
        <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
      </svg>`;
  }

  /* ── LOAD FILE: shared handler ───────────────────────────── */

  function loadFile(file) {
    if (!file) return;

    // Basic type guard
    const allowed = ["image/png", "image/jpeg", "image/tiff", "image/tif", "application/dicom"];
    if (!allowed.includes(file.type) && !file.name.toLowerCase().endsWith(".dcm")) {
      showResultBanner("error", "Unsupported file type. Please upload PNG, JPEG, TIFF, or DICOM.");
      return;
    }

    currentFile = file;
    hideBanner();

    const reader = new FileReader();

    reader.onload = function (e) {
      // Show image preview
      previewImg.src           = e.target.result;
      previewTag.textContent   = getExtension(file.name);
      previewImg.onload        = function () {
        const w = previewImg.naturalWidth;
        const h = previewImg.naturalHeight;
        metaRes.textContent     = w && h ? `${w}×${h}` : "Unknown";
      };

      dropIdle.style.display      = "none";
      previewCont.style.display   = "block";
      dropZone.classList.add("has-preview");

      // File info strip
      fileNameEl.textContent       = file.name;
      fileSizeEl.textContent       = `(${formatBytes(file.size)})`;
      fileInfoStrip.style.display  = "flex";

      // DICOM meta strip
      metaFormat.textContent  = getExtension(file.name);
      metaSize.textContent    = formatBytes(file.size);

      // Quality badges
      qualityBadges.style.display = "flex";
      badgeSize.className = file.size <= 50 * 1024 * 1024
        ? "quality-badge ok"
        : "quality-badge error";
      badgeSize.innerHTML = `<div class="quality-badge-dot"></div> ${
        file.size <= 50 * 1024 * 1024 ? "Size OK" : "File Too Large"
      }`;

      // Enable upload button
      uploadBtn.disabled = false;

      // Advance stepper to step 2
      markStepDone(document.getElementById("step-1"));
      advanceStep(step2);
    };

    reader.readAsDataURL(file);
  }

  /* ── CLEAR ───────────────────────────────────────────────── */

  function clearPreview() {
    currentFile                  = null;
    previewImg.src               = "";
    previewCont.style.display    = "none";
    dropIdle.style.display       = "block";
    dropZone.classList.remove("has-preview", "drag-over");
    fileInfoStrip.style.display  = "none";
    qualityBadges.style.display  = "none";
    uploadBtn.disabled           = true;
    fileInput.value              = "";
    metaFormat.textContent       = "—";
    metaRes.textContent          = "—";
    metaSize.textContent         = "—";
    hideBanner();

    // Reset steps
    ["step-1", "step-2", "step-3", "step-4"].forEach(function (id) {
      const el = document.getElementById(id);
      el.className = "step";
      const num = el.querySelector(".step-num");
      num.innerHTML = id.replace("step-", "");
    });
    document.getElementById("step-1").classList.add("active");
  }

  /* ── DRAG & DROP ─────────────────────────────────────────── */

  ["dragenter", "dragover"].forEach(function (evt) {
    dropZone.addEventListener(evt, function (e) {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.add("drag-over");
    });
  });

  ["dragleave", "dragend"].forEach(function (evt) {
    dropZone.addEventListener(evt, function (e) {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.remove("drag-over");
    });
  });

  dropZone.addEventListener("drop", function (e) {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.remove("drag-over");

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      loadFile(files[0]);
    }
  });

  /* ── BROWSE FILE PICKER ──────────────────────────────────── */

  browseTrigger.addEventListener("click", function (e) {
    e.stopPropagation();
    fileInput.click();
  });

  // Also allow clicking empty area of drop zone
  dropZone.addEventListener("click", function (e) {
    if (e.target === dropZone || e.target === dropIdle || e.target.closest("#drop-idle")) {
      fileInput.click();
    }
  });

  fileInput.addEventListener("change", function () {
    if (fileInput.files && fileInput.files.length > 0) {
      loadFile(fileInput.files[0]);
    }
  });

  /* ── CLEAR BUTTON ────────────────────────────────────────── */

  clearBtn.addEventListener("click", function (e) {
    e.stopPropagation();
    clearPreview();
  });

  /* ── AI QUALITY CHECK SIMULATION ────────────────────────── */

  uploadBtn.addEventListener("click", function () {
    if (!currentFile) return;

    // Validate patient form required fields
    const pid   = document.getElementById("patient-id").value.trim();
    const pname = document.getElementById("patient-name").value.trim();
    const page  = document.getElementById("patient-age").value.trim();
    const eye   = document.querySelector("input[name='eye']:checked");

    if (!pid || !pname || !page || !eye) {
      showResultBanner("error", "Please complete all required Patient Details fields (ID, Name, Age, Eye) before uploading.");
      return;
    }

    // Disable button, hide any previous result, show loading
    uploadBtn.disabled    = true;
    hideBanner();

    markStepDone(step2);
    advanceStep(step3);

    // Phase 1: Simulated upload & transfer (1s)
    showLoadingBanner("Uploading scan to hospital node…");

    setTimeout(function () {
      // Phase 2: AI quality analysis (2s more)
      showLoadingBanner("AI analyzing image quality (blur/lighting)…");

      setTimeout(function () {
        // 30% rejection rate
        const rejected = Math.random() < 0.30;

        if (rejected) {
          // ── QUALITY FAIL ──────────────────────────────────
          showResultBanner(
            "error",
            "Quality Check Failed: Image is too blurry or under-exposed. Please retake the scan and re-upload."
          );
          uploadBtn.disabled = false;

          // Reset step 3 back to active (not done), step 4 stays pending
          step3.className = "step active";
          step3.querySelector(".step-num").innerHTML = "3";

          // Clear preview to force re-upload
          setTimeout(function () {
            clearPreview();
            markStepDone(document.getElementById("step-1"));
            advanceStep(step2);
          }, 4000);

          // ── QUALITY PASS ──────────────────────────────────
          markStepDone(step3);
          advanceStep(step4);

          showResultBanner(
            "success",
            "Quality Check Passed. Scan routed to Ophthalmologist Queue. Case ID: #OQ-" +
            Math.floor(10000 + Math.random() * 89999) +
            " — Patient: " + pname
          );

          // Save to shared localStorage queue with status 'awaiting_doctor'
          const selectedEyeVal = eye ? eye.value : "OD";
          const patientNotesEl = document.getElementById("patient-notes");
          const deviceEl = document.getElementById("device-type");

          const patientData = {
            id: pid,
            name: pname,
            age: parseInt(page, 10) || 50,
            eye: selectedEyeVal === "OD" ? "OD (Right Eye)" : "OS (Left Eye)",
            status: "awaiting_doctor",
            aiGrade: 3,
            confidence: 94,
            received: new Date().toUTCString().slice(17, 22) + " UTC",
            device: deviceEl ? deviceEl.value : "TOPCON TRC-NW400",
            notes: (patientNotesEl ? patientNotesEl.value.trim() : "") || "Technician ingest validated. Ready for grading.",
            priority: "urgent"
          };

          if (typeof addPatient === "function") {
            addPatient(patientData);
          } else if (window.OcuStore && typeof window.OcuStore.addPatient === "function") {
            window.OcuStore.addPatient(patientData);
          }

          // Show toast: "Patient sent to Doctor Queue."
          const toastEl = document.getElementById("tech-toast");
          const toastMsg = document.getElementById("tech-toast-msg");
          if (toastEl) {
            if (toastMsg) toastMsg.textContent = "Patient sent to Doctor Queue.";
            toastEl.classList.add("show");
            setTimeout(function () {
              toastEl.classList.remove("show");
            }, 3800);
          }

          // Don't re-enable button; scan is submitted
          uploadBtn.textContent = "✓ Submitted to Queue";
          uploadBtn.style.background = "linear-gradient(135deg, #16a34a, #15803d)";
          uploadBtn.style.cursor = "default";
        }

      }, 2000);
    }, 1000);

  });

})();
