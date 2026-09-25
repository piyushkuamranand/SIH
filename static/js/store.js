/**
 * store.js
 * OcuScan AI — Shared Clinical Queue & LocalStorage Database
 * 
 * Provides unified state management across:
 *  - Technician Upload Workspace (ingest -> adds patient to queue)
 *  - Hospital Kanban Flow Board (renders queue by status, updates on drag & drop)
 *  - Ophthalmologist Workstation (fetches first awaiting_doctor patient, marks completed)
 */

(function () {
  "use strict";

  const STORAGE_KEY = "ocuscan_patient_queue";

  /**
   * Default initial dataset if localStorage is empty
   */
  const DEFAULT_QUEUE = [
    {
      id: "PT-1001",
      name: "Eleanor Vance",
      age: 45,
      eye: "OD (Right Eye)",
      status: "awaiting_precheck",
      aiGrade: null,
      confidence: null,
      received: "07:15 UTC",
      device: "Canon CR-2 · 45° Color",
      notes: "Routine screening. Fasting glucose 138 mg/dL. No prior photocoagulation.",
      priority: "routine"
    },
    {
      id: "PT-1002",
      name: "Arthur Pendelton",
      age: 54,
      eye: "OS (Left Eye)",
      status: "awaiting_doctor",
      aiGrade: 3,
      confidence: 94,
      received: "06:04 UTC",
      device: "TOPCON TRC-NW400",
      notes: "T2DM 12yrs · HbA1c 9.2% · Hypertension · Prev Grade 2 at 18-mo review",
      priority: "urgent",
      lesions: { ma: 7, he: 3, ex: 4, nv: "Absent" }
    },
    {
      id: "PT-1003",
      name: "Grace Hopper",
      age: 61,
      eye: "OD (Right Eye)",
      status: "awaiting_doctor",
      aiGrade: 1,
      confidence: 88,
      received: "06:42 UTC",
      device: "Topcon TRC-NW400",
      notes: "T2DM 8yrs · HbA1c 7.8% · Controlled BP · Mild microaneurysm cluster",
      priority: "high",
      lesions: { ma: 2, he: 0, ex: 0, nv: "Absent" }
    },
    {
      id: "PT-1004",
      name: "Marcus Brody",
      age: 52,
      eye: "OU (Bilateral)",
      status: "completed",
      aiGrade: 0,
      confidence: 99,
      received: "05:20 UTC",
      device: "Canon CR-2",
      notes: "Grade 0 Normal. Clear fovea. Annual screen cleared.",
      priority: "completed",
      signoffTime: "05:48 UTC"
    }
  ];

  /**
   * Retrieve the full patient queue from localStorage
   * @returns {Array<Object>}
   */
  function getQueue() {
    try {
      const data = localStorage.getItem(STORAGE_KEY);
      if (!data) {
        saveQueue(DEFAULT_QUEUE);
        return DEFAULT_QUEUE;
      }
      const parsed = JSON.parse(data);
      if (!Array.isArray(parsed) || parsed.length === 0) {
        saveQueue(DEFAULT_QUEUE);
        return DEFAULT_QUEUE;
      }
      return parsed;
    } catch (e) {
      console.warn("Failed to parse queue from localStorage, resetting to default:", e);
      saveQueue(DEFAULT_QUEUE);
      return DEFAULT_QUEUE;
    }
  }

  /**
   * Save queue array to localStorage
   * @param {Array<Object>} queue 
   */
  function saveQueue(queue) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(queue));
    } catch (e) {
      console.error("Failed to save queue to localStorage:", e);
    }
  }

  /**
   * Update the status and optional metadata of a patient by ID
   * @param {string} id 
   * @param {string} newStatus 'awaiting_precheck' | 'system' | 'awaiting_doctor' | 'completed'
   * @param {Object} [extraProps] 
   * @returns {Object|null}
   */
  function updatePatientStatus(id, newStatus, extraProps = {}) {
    const queue = getQueue();
    const patient = queue.find(p => p.id === id);
    if (!patient) {
      console.warn(`Patient with ID "${id}" not found in queue.`);
      return null;
    }

    patient.status = newStatus;

    if (newStatus === "completed" && !patient.signoffTime) {
      const now = new Date();
      const hours = String(now.getUTCHours()).padStart(2, "0");
      const mins = String(now.getUTCMinutes()).padStart(2, "0");
      patient.signoffTime = `${hours}:${mins} UTC`;
      patient.priority = "completed";
    }

    Object.assign(patient, extraProps);

    saveQueue(queue);

    // Dispatch custom browser event for reactive UI sync if open in same window
    window.dispatchEvent(new CustomEvent("ocuscan_queue_change", { detail: { id, newStatus, patient } }));

    return patient;
  }

  /**
   * Add a new patient object to the queue
   * @param {Object} patientObj 
   * @returns {Object}
   */
  function addPatient(patientObj) {
    const queue = getQueue();

    // Ensure ID exists
    const id = patientObj.id || ("PT-" + Math.floor(1000 + Math.random() * 9000));
    const now = new Date();
    const hours = String(now.getUTCHours()).padStart(2, "0");
    const mins = String(now.getUTCMinutes()).padStart(2, "0");

    const newPatient = {
      id: id,
      name: patientObj.name || "Patient " + id,
      age: patientObj.age || 50,
      eye: patientObj.eye || "OS (Left Eye)",
      status: patientObj.status || "awaiting_doctor",
      aiGrade: patientObj.aiGrade !== undefined ? patientObj.aiGrade : 2,
      confidence: patientObj.confidence || 92,
      received: patientObj.received || `${hours}:${mins} UTC`,
      device: patientObj.device || "TOPCON TRC-NW400",
      notes: patientObj.notes || "Quality passed. Routed from Technician ingest.",
      priority: patientObj.priority || (patientObj.aiGrade >= 3 ? "urgent" : "high"),
      lesions: patientObj.lesions || { ma: 4, he: 2, ex: 1, nv: "Absent" }
    };

    // Prepend or add to queue
    queue.push(newPatient);
    saveQueue(queue);

    window.dispatchEvent(new CustomEvent("ocuscan_queue_change", { detail: { newPatient } }));

    return newPatient;
  }

  /**
   * Reset database back to default initial state
   */
  function resetQueue() {
    saveQueue(DEFAULT_QUEUE);
    window.dispatchEvent(new CustomEvent("ocuscan_queue_change", { detail: { reset: true } }));
    return DEFAULT_QUEUE;
  }

  // Initialize database if not already present
  if (!localStorage.getItem(STORAGE_KEY)) {
    saveQueue(DEFAULT_QUEUE);
  }

  // Expose helpers globally and under namespace
  window.getQueue = getQueue;
  window.updatePatientStatus = updatePatientStatus;
  window.addPatient = addPatient;
  window.resetQueue = resetQueue;

  window.OcuStore = {
    getQueue,
    saveQueue,
    updatePatientStatus,
    addPatient,
    resetQueue,
    STORAGE_KEY
  };

})();
