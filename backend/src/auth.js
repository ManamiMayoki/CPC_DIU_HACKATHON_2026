/**
 * Authentication and role-based access control.
 *
 * Two roles:
 *   analyst - investigates accounts, opens cases, adds notes, escalates. Sees masked PII only.
 *   admin   - compliance officer. Everything an analyst can do, plus: decide a case (file the
 *             report or close it), reveal PII with a recorded reason, read and verify the audit
 *             log, and load a new transaction dataset.
 *
 * Sessions are stateless HMAC-signed tokens (no cookies, so no CSRF surface). Passwords are
 * compared as scrypt hashes in constant time. Users come from the environment; the demo
 * accounts below exist only while CYGNUS_DEMO_MODE is on (the default for the hackathon build).
 */
const crypto = require('crypto');

const TOKEN_TTL_SECONDS = Number(process.env.CYGNUS_TOKEN_TTL_SECONDS || 8 * 3600);
const SECRET = process.env.CYGNUS_AUTH_SECRET || crypto.randomBytes(32).toString('hex');
const DEMO_MODE = String(process.env.CYGNUS_DEMO_MODE || 'true').toLowerCase() !== 'false';

const ROLES = {
  analyst: {
    label: 'AML Analyst',
    permissions: ['data:read', 'case:create', 'case:note', 'case:escalate', 'report:export'],
  },
  admin: {
    label: 'Compliance Officer (Admin)',
    permissions: [
      'data:read', 'case:create', 'case:note', 'case:escalate', 'report:export',
      'case:decide', 'pii:reveal', 'audit:read', 'pipeline:run', 'labels:export',
    ],
  },
};

function hashPassword(password, salt) {
  return crypto.scryptSync(String(password), salt, 32).toString('hex');
}

function buildUsers() {
  const users = new Map();
  const add = (username, password, role, name) => {
    if (!username || !password || !ROLES[role]) return;
    const salt = crypto.randomBytes(16).toString('hex');
    users.set(username.toLowerCase(), { username, role, name, salt, hash: hashPassword(password, salt) });
  };
  add(process.env.CYGNUS_ANALYST_USER || 'analyst', process.env.CYGNUS_ANALYST_PASSWORD, 'analyst', 'Demo Analyst');
  add(process.env.CYGNUS_ADMIN_USER || 'admin', process.env.CYGNUS_ADMIN_PASSWORD, 'admin', 'Demo Compliance Officer');
  return users;
}

const users = buildUsers();
const demoIdentities = {
  analyst: { username: process.env.CYGNUS_ANALYST_USER || 'analyst', role: 'analyst', name: 'Demo Analyst' },
  admin: { username: process.env.CYGNUS_ADMIN_USER || 'admin', role: 'admin', name: 'Demo Compliance Officer' },
};

const b64 = (value) => Buffer.from(value).toString('base64url');

function sign(payload) {
  return crypto.createHmac('sha256', SECRET).update(payload).digest('base64url');
}

function issueToken(user) {
  const payload = b64(JSON.stringify({
    sub: user.username,
    role: user.role,
    name: user.name,
    exp: Math.floor(Date.now() / 1000) + TOKEN_TTL_SECONDS,
  }));
  return `${payload}.${sign(payload)}`;
}

function verifyToken(token) {
  if (typeof token !== 'string' || !token.includes('.')) return null;
  const [payload, signature] = token.split('.');
  const expected = sign(payload);
  const given = Buffer.from(signature || '');
  const wanted = Buffer.from(expected);
  if (given.length !== wanted.length || !crypto.timingSafeEqual(given, wanted)) return null;
  try {
    const claims = JSON.parse(Buffer.from(payload, 'base64url').toString('utf-8'));
    if (!claims.exp || claims.exp < Math.floor(Date.now() / 1000) || !ROLES[claims.role]) return null;
    return { username: claims.sub, role: claims.role, name: claims.name };
  } catch {
    return null;
  }
}

function checkPassword(username, password) {
  const user = users.get(String(username || '').toLowerCase());
  // Hash even when the user is unknown so response time does not reveal valid usernames
  const salt = user ? user.salt : 'unknown-user-salt';
  const candidate = Buffer.from(hashPassword(password || '', salt));
  if (!user) return null;
  const stored = Buffer.from(user.hash);
  return crypto.timingSafeEqual(candidate, stored) ? user : null;
}

// Failed sign-ins per username+IP, to slow down password guessing
const failures = new Map();
const MAX_FAILURES = 5;
const LOCK_WINDOW_MS = 5 * 60 * 1000;

function isLocked(key) {
  const record = failures.get(key);
  if (!record) return false;
  if (Date.now() - record.first > LOCK_WINDOW_MS) {
    failures.delete(key);
    return false;
  }
  return record.count >= MAX_FAILURES;
}

function noteFailure(key) {
  const record = failures.get(key);
  if (!record || Date.now() - record.first > LOCK_WINDOW_MS) {
    failures.set(key, { count: 1, first: Date.now() });
  } else {
    record.count += 1;
  }
}

function can(user, permission) {
  return Boolean(user && ROLES[user.role]?.permissions.includes(permission));
}

function publicUser(user) {
  return {
    username: user.username,
    role: user.role,
    name: user.name,
    role_label: ROLES[user.role].label,
    permissions: ROLES[user.role].permissions,
  };
}

/** Express middleware factory. `audit` is the shared AuditLog. */
function createAuth(audit) {
  const authenticate = (req, res, next) => {
    const header = req.headers.authorization || '';
    const token = header.startsWith('Bearer ') ? header.slice(7) : null;
    const user = verifyToken(token);
    if (!user) {
      return res.status(401).json({ success: false, error: 'Sign in required.' });
    }
    req.user = user;
    next();
  };

  const requirePermission = (permission) => (req, res, next) => {
    if (can(req.user, permission)) return next();
    audit.record({
      actor: req.user?.username,
      role: req.user?.role,
      action: 'ACCESS_DENIED',
      target: `${req.method} ${req.originalUrl.split('?')[0]}`,
      outcome: 'denied',
      details: { required_permission: permission },
    });
    res.status(403).json({
      success: false,
      error: `Your role (${ROLES[req.user.role].label}) is not allowed to do this.`,
      required_permission: permission,
    });
  };

  const login = (req, res) => {
    const { username, password } = req.body || {};
    const key = `${String(username || '').toLowerCase()}|${req.ip}`;
    if (isLocked(key)) {
      audit.record({ actor: String(username || 'unknown').slice(0, 64), action: 'AUTH_LOCKED', outcome: 'denied' });
      return res.status(429).json({ success: false, error: 'Too many failed attempts. Try again in a few minutes.' });
    }
    const user = checkPassword(username, password);
    if (!user) {
      noteFailure(key);
      audit.record({ actor: String(username || 'unknown').slice(0, 64), action: 'AUTH_FAILED', outcome: 'denied' });
      return res.status(401).json({ success: false, error: 'Wrong username or password.' });
    }
    failures.delete(key);
    audit.record({ actor: user.username, role: user.role, action: 'AUTH_LOGIN', details: { method: 'password' } });
    res.json({ success: true, token: issueToken(user), user: publicUser(user), expires_in: TOKEN_TTL_SECONDS });
  };

  /** One-click demo sign-in, so no password ever sits in the frontend. Off when CYGNUS_DEMO_MODE=false. */
  const demoLogin = (req, res) => {
    if (!DEMO_MODE) {
      return res.status(403).json({ success: false, error: 'Demo sign-in is disabled.' });
    }
    const identity = demoIdentities[String(req.body?.role || '')];
    if (!identity) {
      return res.status(400).json({ success: false, error: 'role must be "analyst" or "admin".' });
    }
    audit.record({ actor: identity.username, role: identity.role, action: 'AUTH_LOGIN', details: { method: 'demo' } });
    res.json({ success: true, token: issueToken(identity), user: publicUser(identity), expires_in: TOKEN_TTL_SECONDS });
  };

  return { authenticate, requirePermission, login, demoLogin };
}

module.exports = { createAuth, issueToken, verifyToken, publicUser, can, ROLES, DEMO_MODE, demoIdentities };
