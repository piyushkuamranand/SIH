/**
 * models/case.model.js — NETRA-DR Screening Case Model & Repository Abstraction
 *
 * Implements the screening case data model and repository abstraction.
 * Represents a single diabetic-retinopathy screening workflow.
 *
 * Designed database-agnostic so that persistent storage (e.g. MongoDB/Mongoose)
 * can replace the in-memory store in a later module without changing controllers.
 *
 * Lifecycle States:
 *   - created:         Case created, awaiting fundus image upload (Module 3)
 *   - image_uploaded:  Fundus image received (Module 4)
 *   - processing:      Inference running on Flask service (Module 6)
 *   - completed:       AI inference completed and results stored (Module 7)
 *   - reviewed:        Doctor reviewed and confirmed/overrode findings (Module 10)
 *   - failed:          Pipeline processing failed
 *
 * Fields supported:
 *   - id:        unique case ID string ('case_<uuid>')
 *   - patientId: patient identifier / reference string
 *   - createdBy: user ID string of authenticated creator
 *   - status:    lifecycle status string (defaults to 'created')
 *   - notes:     optional clinical/screening notes
 *   - createdAt: ISO 8601 UTC timestamp string
 *   - updatedAt: ISO 8601 UTC timestamp string
 */

'use strict';

const crypto = require('crypto');

const CASE_STATUS = Object.freeze({
  CREATED:        'created',
  IMAGE_UPLOADED: 'image_uploaded',
  PROCESSING:     'processing',
  COMPLETED:      'completed',
  REVIEWED:       'reviewed',
  FAILED:         'failed',
});

const VALID_CASE_STATUSES = Object.freeze(Object.values(CASE_STATUS));

// In-memory data store for screening cases
const casesById = new Map();

const CaseModel = {
  CASE_STATUS,
  VALID_CASE_STATUSES,

  /**
   * Return a safe representation of a case object.
   * Strips any internal storage artifacts.
   *
   * @param {object} caseRecord
   * @returns {object|null}
   */
  toSafeCase(caseRecord) {
    if (!caseRecord) return null;
    const safe = {
      id:        caseRecord.id,
      patientId: caseRecord.patientId,
      createdBy: caseRecord.createdBy,
      status:    caseRecord.status,
      createdAt: caseRecord.createdAt,
      updatedAt: caseRecord.updatedAt,
    };
    if (caseRecord.notes !== undefined && caseRecord.notes !== null) {
      safe.notes = caseRecord.notes;
    }
    if (caseRecord.image) {
      safe.image = {
        imageId:        caseRecord.image.imageId,
        originalName:   caseRecord.image.originalName,
        storedFilename: caseRecord.image.storedFilename,
        mimeType:       caseRecord.image.mimeType,
        extension:      caseRecord.image.extension,
        sizeBytes:      caseRecord.image.sizeBytes,
        uploadedBy:     caseRecord.image.uploadedBy,
        uploadedAt:     caseRecord.image.uploadedAt,
      };
    }
    return safe;
  },

  /**
   * Find a case by its unique ID.
   *
   * @param {string} id
   * @returns {Promise<object|null>}
   */
  async findById(id) {
    if (!id || typeof id !== 'string') return null;
    const record = casesById.get(id.trim());
    return record ? CaseModel.toSafeCase(record) : null;
  },

  /**
   * List all cases, with optional filtering.
   *
   * @param {object} [filter={}]
   * @returns {Promise<Array<object>>}
   */
  async findAll(filter = {}) {
    let records = Array.from(casesById.values());

    if (filter.patientId) {
      records = records.filter(c => c.patientId === filter.patientId);
    }
    if (filter.createdBy) {
      records = records.filter(c => c.createdBy === filter.createdBy);
    }
    if (filter.status) {
      records = records.filter(c => c.status === filter.status);
    }

    // Sort by createdAt descending (newest first)
    records.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

    return records.map(c => CaseModel.toSafeCase(c));
  },

  /**
   * Create and persist a new screening case.
   *
   * @param {object} data
   * @param {string} data.patientId - Required patient reference
   * @param {string} data.createdBy - User ID of creator
   * @param {string} [data.notes]   - Optional screening notes
   * @returns {Promise<object>} Created safe case record
   */
  async create({ patientId, createdBy, notes }) {
    if (!patientId || typeof patientId !== 'string' || patientId.trim().length === 0) {
      throw new Error('patientId is required to create a case');
    }
    if (!createdBy || typeof createdBy !== 'string' || createdBy.trim().length === 0) {
      throw new Error('createdBy is required to create a case');
    }

    const now = new Date().toISOString();
    const id = `case_${crypto.randomUUID()}`;

    const record = {
      id,
      patientId: patientId.trim(),
      createdBy: createdBy.trim(),
      status:    CASE_STATUS.CREATED,
      notes:     typeof notes === 'string' && notes.trim().length > 0 ? notes.trim() : null,
      createdAt: now,
      updatedAt: now,
    };

    casesById.set(id, record);
    return CaseModel.toSafeCase(record);
  },

  /**
   * Update allowed metadata of an existing case.
   * Protected fields (id, createdBy, createdAt, status) cannot be changed here.
   *
   * @param {string} id
   * @param {object} updates
   * @returns {Promise<object|null>}
   */
  async update(id, updates = {}) {
    if (!id || typeof id !== 'string') return null;
    const existing = casesById.get(id.trim());
    if (!existing) return null;

    const now = new Date().toISOString();
    const updated = { ...existing, updatedAt: now };

    if (updates.patientId !== undefined && typeof updates.patientId === 'string' && updates.patientId.trim().length > 0) {
      updated.patientId = updates.patientId.trim();
    }
    if (updates.notes !== undefined) {
      updated.notes = updates.notes !== null && typeof updates.notes === 'string' ? updates.notes.trim() : null;
    }

    casesById.set(existing.id, updated);
    return CaseModel.toSafeCase(updated);
  },

  /**
   * Associate an uploaded fundus image with an existing case and transition status.
   * Transitions lifecycle status from 'created' to 'image_uploaded'.
   *
   * @param {string} id - Case ID
   * @param {object} imageMetadata - Minimum image metadata
   * @returns {Promise<object|null>} Updated safe case record
   */
  async attachImage(id, imageMetadata) {
    if (!id || typeof id !== 'string') return null;
    const existing = casesById.get(id.trim());
    if (!existing) return null;

    const now = new Date().toISOString();
    existing.image = { ...imageMetadata };
    existing.status = CASE_STATUS.IMAGE_UPLOADED;
    existing.updatedAt = now;

    casesById.set(existing.id, existing);
    return CaseModel.toSafeCase(existing);
  },

  /**
   * Get raw case record (internal repository use only — not for client exposure).
   *
   * @param {string} id
   * @returns {Promise<object|null>}
   */
  async getRawById(id) {
    if (!id || typeof id !== 'string') return null;
    const record = casesById.get(id.trim());
    return record ? { ...record } : null;
  },

  /**
   * Update case status (reserved for internal workflow transitions in later modules).
   *
   * @param {string} id
   * @param {string} newStatus
   * @returns {Promise<object|null>}
   */
  async updateStatus(id, newStatus) {
    if (!id || typeof id !== 'string') return null;
    if (!VALID_CASE_STATUSES.includes(newStatus)) {
      throw new Error(`Invalid case status: ${newStatus}`);
    }
    const existing = casesById.get(id.trim());
    if (!existing) return null;

    const now = new Date().toISOString();
    existing.status = newStatus;
    existing.updatedAt = now;

    casesById.set(existing.id, existing);
    return CaseModel.toSafeCase(existing);
  },

  /**
   * Delete a case (admin only or test cleanup).
   *
   * @param {string} id
   * @returns {Promise<boolean>}
   */
  async delete(id) {
    if (!id || typeof id !== 'string') return false;
    return casesById.delete(id.trim());
  },

  /**
   * Clear all cases (for test suite isolation).
   */
  async clear() {
    casesById.clear();
  },

  /**
   * Get total case count.
   *
   * @returns {Promise<number>}
   */
  async count() {
    return casesById.size;
  },
};

module.exports = CaseModel;
