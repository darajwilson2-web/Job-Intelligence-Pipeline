"""
scoring.py — Job scoring and classification.

score_job()         — weighted keyword scoring with combo bonuses
detect_role_type()  — which of the 4 career paths does this match?
detect_work_type()  — Remote / Contract / In-Office / Hybrid?
detect_sector()     — Government / Healthcare / Banking / Compliance/Risk / General?
"""

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SECTOR KEYWORDS
# ---------------------------------------------------------------------------
SECTOR_KEYWORDS: dict[str, list[str]] = {
    "Compliance / Risk / Fraud": [
        "fraud prevention", "fraud detection", "risk management",
        "compliance", "regulatory", "aml", "anti-money laundering",
        "kyc", "sox", "internal controls", "identity verification",
        "loss prevention", "revenue integrity", "audit",
        "sanctions", "data privacy", "hipaa compliance",
    ],
    "Government": [
        "government", "federal", "state agency", "public sector",
        "county", "municipal", "medicaid", "medicare", "eligibility",
        "case management", "benefits administration", "hhs", "cms",
        "department of", "city of", "nc dhhs",
    ],
    "Healthcare": [
        "healthcare", "health system", "health plan", "clinical",
        "hipaa", "patient care", "pharmacy", "medical center",
        "health insurance", "claims processing", "revenue cycle",
        "managed care", "atrium", "novant", "carolinas health",
        "wellcare", "humana", "aetna", "cigna", "blue cross", "bcbs",
        "cvs health", "optum", "epic systems", "ehr",
    ],
    "Banking": [
        "bank", "banking", "financial services", "fintech",
        "credit union", "investment", "insurance company",
        "mortgage", "lending",
        "wells fargo", "bank of america", "truist", "pnc",
        "ally financial", "regions bank", "capital one", "fidelity",
        "vanguard", "schwab", "jpmorgan", "chase bank",
    ],
}

# Companies that should not be tagged Healthcare even if "hospital" appears
# in their benefits text (e.g. "hospitality")
_HOSPITALITY_COMPANIES = {
    "airbnb", "marriott", "hilton", "hyatt", "ihg", "wyndham",
    "accor", "expedia", "booking", "vrbo", "numa",
}

# Combo bonus signals
_FRAUD_SIGNALS   = {"fraud", "compliance", "risk analyst", "audit",
                    "fraud analyst", "compliance analyst", "hipaa", "fraud prevention"}
_EA_SIGNALS      = {"executive assistant", "executive business partner",
                    "chief of staff", "calendar management", "c-suite"}
_DATA_SIGNALS    = {"power bi", "sql", "dashboard", "data analytics",
                    "data analysis", "tableau", "python"}
_OPS_SIGNALS     = {"operations analyst", "business operations", "sales operations",
                    "process improvement", "forecasting"}


# ---------------------------------------------------------------------------
# SCORING
# ---------------------------------------------------------------------------

def score_job(title: str, description: str,
              keyword_weights: dict[str, int]) -> tuple[int, list[str]]:
    """
    Score a job posting by summing weighted keyword matches,
    then adding combo bonuses for postings that bridge two skillsets.

    Returns (score, list_of_matched_keywords).
    """
    text    = f"{title} {description}".lower()
    score   = 0
    matched = []

    for kw, weight in keyword_weights.items():
        if kw.lower() in text:
            score += weight
            matched.append(kw)

    # Combo bonuses — postings that intersect your two skillsets score higher
    has_fraud = any(s in text for s in _FRAUD_SIGNALS)
    has_ea    = any(s in text for s in _EA_SIGNALS)
    has_data  = any(s in text for s in _DATA_SIGNALS)
    has_ops   = any(s in text for s in _OPS_SIGNALS)

    if has_fraud and has_data:
        score += 5
        matched.append("COMBO:Fraud+Data ⭐")
    if has_fraud and has_ea:
        score += 3
        matched.append("COMBO:Fraud+EA")
    if has_ea and has_data:
        score += 3
        matched.append("COMBO:EA+Data")
    if has_ea and has_ops:
        score += 2
        matched.append("COMBO:EA+Ops")
    if has_ops and has_data:
        score += 2
        matched.append("COMBO:Ops+Data")

    return score, matched


# ---------------------------------------------------------------------------
# CLASSIFICATION
# ---------------------------------------------------------------------------

def detect_role_type(title: str) -> str:
    """Map a job title to one of the 5 role categories."""
    t = title.lower()

    if any(x in t for x in ["fraud analyst", "compliance analyst", "risk analyst",
                              "revenue integrity", "audit analyst",
                              "risk and compliance"]):
        return "Compliance / Risk / Fraud"

    if any(x in t for x in ["executive assistant", "executive business partner",
                              "chief of staff", "administrative assistant",
                              "executive support", "office manager"]):
        return "EA / Business Partner"

    if any(x in t for x in ["operations analyst", "business operations",
                              "sales operations", "salesops"]):
        return "Operations Analytics"

    if any(x in t for x in ["project coordinator", "program coordinator",
                              "operations coordinator",
                              "project management analyst",
                              "program management analyst"]):
        return "Project / Program Coordinator"

    if any(x in t for x in ["data analyst", "business analyst",
                              "reporting analyst", "analytics"]):
        return "Data / Analytics"

    return "Other"


def detect_work_type(title: str, description: str, location: str) -> str:
    """Classify a posting as Remote, Contract, or In-Office/Hybrid."""
    text = f"{title} {description} {location}".lower()

    is_contract = any(w in text for w in [
        "contract", "contractor", "freelance", "temp ",
        "temporary", "fixed term", "part-time", "part time",
    ])
    is_remote = any(w in text for w in ["remote", "work from home", "wfh"])

    if is_contract:
        return "Contract"
    if is_remote:
        return "Remote"
    return "In-Office / Hybrid"


def detect_sector(title: str, description: str, company: str) -> str:
    """
    Classify a posting into Government, Healthcare, Banking,
    Compliance/Risk/Fraud, or General.

    Hospitality companies are excluded from Healthcare detection
    even if "hospital" appears in their benefits text.
    """
    company_l = company.lower()
    is_hospitality = any(h in company_l for h in _HOSPITALITY_COMPANIES)

    text = f"{title} {description} {company}".lower()

    # Check Compliance first — it's the primary career target
    for sector, keywords in SECTOR_KEYWORDS.items():
        if sector == "Healthcare" and is_hospitality:
            continue
        if any(k in text for k in keywords):
            return sector

    return "General"
