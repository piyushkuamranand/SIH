/**
 * db/connection.js — NETRA-DR Database Connection (Placeholder)
 *
 * Will establish and export the database connection.
 * Not implemented yet — stub only.
 *
 * The choice of database (SQLite for prototype / MongoDB for production)
 * will be made in the database integration task.
 */

'use strict';

const connect = async () => {
  throw new Error('Database connection not implemented yet.');
};

const disconnect = async () => {
  // no-op until implemented
};

module.exports = { connect, disconnect };
