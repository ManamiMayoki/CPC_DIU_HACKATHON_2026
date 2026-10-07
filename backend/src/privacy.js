/**
 * PII masking for account-holder (KYC) profiles.
 *
 * Profiles are synthetic (data/synthetic/account_profiles.json) and stay on the server.
 * Every response carries the masked form. The full record is returned only by the explicit
 * "reveal" endpoint, which needs the pii:reveal permission and a written reason, and is audited.
 */

function maskWord(word) {
  if (!word) return '';
  return word.length <= 1 ? '*' : `${word[0]}${'*'.repeat(Math.max(word.length - 1, 3))}`;
}

function maskName(name) {
  return String(name || '')
    .split(/\s+/)
    .filter(Boolean)
    .map(maskWord)
    .join(' ');
}

/** 01712345678 -> 017*****678 */
function maskPhone(phone) {
  const digits = String(phone || '');
  if (digits.length < 7) return '*'.repeat(digits.length);
  return `${digits.slice(0, 3)}${'*'.repeat(digits.length - 6)}${digits.slice(-3)}`;
}

/** National ID: keep the last 4 digits only. */
function maskNid(nid) {
  const digits = String(nid || '');
  if (digits.length <= 4) return '*'.repeat(digits.length);
  return `${'*'.repeat(digits.length - 4)}${digits.slice(-4)}`;
}

const NON_SENSITIVE_FIELDS = ['account_tier', 'kyc_level', 'district', 'division', 'account_age_days', 'opened_on'];

function maskProfile(profile) {
  if (!profile) return null;
  const masked = { masked: true };
  for (const field of NON_SENSITIVE_FIELDS) {
    if (profile[field] !== undefined) masked[field] = profile[field];
  }
  masked.holder_name = maskName(profile.holder_name);
  masked.phone = maskPhone(profile.phone);
  masked.national_id = maskNid(profile.national_id);
  return masked;
}

function fullProfile(profile) {
  return profile ? { ...profile, masked: false } : null;
}

module.exports = { maskName, maskPhone, maskNid, maskProfile, fullProfile };
