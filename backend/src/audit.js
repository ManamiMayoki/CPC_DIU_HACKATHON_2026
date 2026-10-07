/**
 * Append-only, hash-chained audit log.
 *
 * Every security-relevant action (sign-in, PII reveal, case change, report export, denied
 * request) is written as one JSON line. Each entry stores the SHA-256 hash of the previous
 * entry, so editing or deleting any line breaks the chain and verify() reports where.
 * Entries hold account IDs and usernames only, never unmasked personal data.
 */
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const GENESIS_HASH = '0'.repeat(64);

function hashEntry(entry) {
  const { hash: _ignored, ...body } = entry;
  return crypto.createHash('sha256').update(JSON.stringify(body)).digest('hex');
}

class AuditLog {
  constructor(filePath) {
    this.filePath = filePath;
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    this.seq = 0;
    this.lastHash = GENESIS_HASH;
    for (const entry of this.readAll()) {
      this.seq = entry.seq;
      this.lastHash = entry.hash;
    }
  }

  readAll() {
    if (!fs.existsSync(this.filePath)) return [];
    return fs
      .readFileSync(this.filePath, 'utf-8')
      .split('\n')
      .filter((line) => line.trim())
      .map((line) => {
        try {
          return JSON.parse(line);
        } catch {
          return { seq: -1, corrupt: true, raw: line.slice(0, 80) };
        }
      });
  }

  /** Appends one entry and returns it. Field order is fixed because it is part of the hash. */
  record({ actor = 'anonymous', role = 'none', action, target = null, details = {}, outcome = 'success' }) {
    const entry = {
      seq: this.seq + 1,
      timestamp: new Date().toISOString(),
      actor,
      role,
      action,
      target,
      outcome,
      details,
      prev_hash: this.lastHash,
    };
    entry.hash = hashEntry(entry);
    fs.appendFileSync(this.filePath, `${JSON.stringify(entry)}\n`, 'utf-8');
    this.seq = entry.seq;
    this.lastHash = entry.hash;
    return entry;
  }

  /** Recomputes the whole chain from the file on disk. */
  verify() {
    const entries = this.readAll();
    let prev = GENESIS_HASH;
    for (let i = 0; i < entries.length; i += 1) {
      const e = entries[i];
      const broken =
        e.corrupt || e.seq !== i + 1 || e.prev_hash !== prev || hashEntry(e) !== e.hash;
      if (broken) {
        return { valid: false, entries: entries.length, broken_at_seq: e.corrupt ? i + 1 : e.seq, head_hash: prev };
      }
      prev = e.hash;
    }
    return { valid: true, entries: entries.length, broken_at_seq: null, head_hash: prev };
  }

  list({ limit = 200, action, actor } = {}) {
    let entries = this.readAll().filter((e) => !e.corrupt);
    if (action) entries = entries.filter((e) => e.action === action);
    if (actor) entries = entries.filter((e) => e.actor === actor);
    return entries.slice(-limit).reverse();
  }
}

module.exports = { AuditLog, GENESIS_HASH, hashEntry };
