"""Synthetic account-holder (KYC) profiles.

Every value here is made up: names are random pairings from short name lists, phone and
national-ID numbers are random digits. A profile is derived only from the account ID, so the
same account always gets the same profile. They exist so the product can demonstrate PII
masking, controlled reveal and tier-level bias checks without touching real customer data.
"""

from __future__ import annotations

import datetime
import hashlib
import random
from typing import Any, Dict, Iterable, Optional

FIRST_NAMES = [
    "Rahim", "Karim", "Nusrat", "Farhana", "Tanvir", "Sadia", "Imran", "Sharmin", "Arif", "Jannat",
    "Mahmud", "Rumana", "Shakil", "Tasnim", "Habib", "Sumaiya", "Rakib", "Nazma", "Faisal", "Mim",
]
LAST_NAMES = [
    "Ahmed", "Hossain", "Islam", "Akter", "Rahman", "Khatun", "Chowdhury", "Begum", "Uddin", "Sarker",
    "Miah", "Sultana", "Haque", "Khan", "Das", "Mondal",
]
# (district, division)
DISTRICTS = [
    ("Dhaka", "Dhaka"), ("Gazipur", "Dhaka"), ("Narayanganj", "Dhaka"), ("Chattogram", "Chattogram"),
    ("Cox's Bazar", "Chattogram"), ("Cumilla", "Chattogram"), ("Sylhet", "Sylhet"), ("Rajshahi", "Rajshahi"),
    ("Bogura", "Rajshahi"), ("Khulna", "Khulna"), ("Jashore", "Khulna"), ("Barishal", "Barishal"),
    ("Rangpur", "Rangpur"), ("Mymensingh", "Mymensingh"),
]
ACCOUNT_TIERS = ("personal", "agent", "merchant")
REFERENCE_DATE = datetime.date(2026, 3, 1)


def infer_tier(account_id: str) -> str:
    """Account tier from the naming convention of the synthetic generators."""
    upper = account_id.upper()
    if "AGENT" in upper or "CASHOUT" in upper or upper.startswith("AGT"):
        return "agent"
    if "MERCH" in upper or upper.startswith("MER") or "BILLER" in upper:
        return "merchant"
    return "personal"


def build_profile(account_id: str, tier: Optional[str] = None) -> Dict[str, Any]:
    rng = random.Random(int(hashlib.sha256(account_id.encode("utf-8")).hexdigest()[:16], 16))
    district, division = rng.choice(DISTRICTS)
    age_days = rng.randint(20, 2400)
    tier = tier or infer_tier(account_id)
    return {
        "holder_name": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
        "phone": "01" + str(rng.randint(3, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(8)),
        "national_id": "".join(str(rng.randint(0, 9)) for _ in range(10)),
        "account_tier": tier,
        "kyc_level": rng.choice(["Full e-KYC", "Full e-KYC", "Basic KYC"]) if tier == "personal" else "Full KYC + trade licence",
        "district": district,
        "division": division,
        "account_age_days": age_days,
        "opened_on": (REFERENCE_DATE - datetime.timedelta(days=age_days)).isoformat(),
        "synthetic": True,
    }


def build_profiles(account_ids: Iterable[str], tiers: Optional[Dict[str, str]] = None) -> Dict[str, Dict[str, Any]]:
    tiers = tiers or {}
    return {acc: build_profile(acc, tiers.get(acc)) for acc in sorted(set(account_ids))}
