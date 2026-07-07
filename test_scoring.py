"""
tests/test_scoring.py — Unit tests for scoring and classification.

Run with:  python -m pytest tests/ -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scoring import score_job, detect_role_type, detect_work_type, detect_sector

# Minimal keyword weights for testing
TEST_WEIGHTS = {
    "fraud analyst":      4,
    "fraud detection":    4,
    "compliance analyst": 4,
    "risk analyst":       4,
    "sql":                3,
    "power bi":           3,
    "python":             3,
    "executive assistant":3,
    "data analyst":       3,
    "dashboard":          2,
    "hipaa":              3,
    "audit":              2,
}


# ---------------------------------------------------------------------------
# score_job
# ---------------------------------------------------------------------------

class TestScoreJob:

    def test_fraud_analyst_scores_high(self):
        score, matched = score_job(
            "Senior Fraud Analyst",
            "We need someone for fraud detection and compliance analytics using SQL.",
            TEST_WEIGHTS,
        )
        assert score >= 8
        assert "fraud analyst" in matched or "fraud detection" in matched

    def test_empty_description_scores_low(self):
        score, _ = score_job("Software Engineer", "", TEST_WEIGHTS)
        assert score == 0

    def test_combo_fraud_data_bonus(self):
        score, matched = score_job(
            "Fraud Analyst",
            "Use SQL, Python, and Power BI to build fraud detection dashboards.",
            TEST_WEIGHTS,
        )
        assert "COMBO:Fraud+Data ⭐" in matched
        # Combo adds 5 points
        assert score >= 5

    def test_combo_ea_data_bonus(self):
        score, matched = score_job(
            "Executive Assistant",
            "Support the CEO. Build dashboards in Power BI and SQL reporting.",
            TEST_WEIGHTS,
        )
        assert "COMBO:EA+Data" in matched

    def test_no_false_combo_for_unrelated(self):
        _, matched = score_job(
            "Accountant",
            "Manage accounts payable and prepare financial statements.",
            TEST_WEIGHTS,
        )
        assert "COMBO:Fraud+Data ⭐" not in matched

    def test_matched_keywords_returned(self):
        _, matched = score_job(
            "Compliance Analyst",
            "HIPAA compliance, audit trail, SQL reporting.",
            TEST_WEIGHTS,
        )
        assert "compliance analyst" in matched
        assert "hipaa" in matched
        assert "sql" in matched


# ---------------------------------------------------------------------------
# detect_role_type
# ---------------------------------------------------------------------------

class TestDetectRoleType:

    def test_fraud_analyst(self):
        assert detect_role_type("Fraud Analyst II") == "Compliance / Risk / Fraud"

    def test_compliance_analyst(self):
        assert detect_role_type("Senior Compliance Analyst") == "Compliance / Risk / Fraud"

    def test_risk_analyst(self):
        assert detect_role_type("Risk Analyst - Remote") == "Compliance / Risk / Fraud"

    def test_executive_assistant(self):
        assert detect_role_type("Executive Assistant to VP") == "EA / Business Partner"

    def test_chief_of_staff(self):
        assert detect_role_type("Associate Chief of Staff") == "EA / Business Partner"

    def test_data_analyst(self):
        assert detect_role_type("Data Analyst, Core Analytics") == "Data / Analytics"

    def test_operations_analyst(self):
        assert detect_role_type("Operations Analyst") == "Operations Analytics"

    def test_project_coordinator(self):
        assert detect_role_type("Project Coordinator") == "Project / Program Coordinator"

    def test_program_coordinator(self):
        assert detect_role_type("Program Coordinator") == "Project / Program Coordinator"

    def test_unknown(self):
        assert detect_role_type("Barista") == "Other"


# ---------------------------------------------------------------------------
# detect_work_type
# ---------------------------------------------------------------------------

class TestDetectWorkType:

    def test_remote(self):
        assert detect_work_type("Data Analyst", "fully remote role", "Remote") == "Remote"

    def test_contract(self):
        assert detect_work_type("Analyst", "this is a contract position", "Remote") == "Contract"

    def test_in_office(self):
        assert detect_work_type("EA", "in our Charlotte office", "Charlotte, NC") == "In-Office / Hybrid"

    def test_contract_takes_priority_over_remote(self):
        assert detect_work_type("Analyst", "remote contract role", "Remote") == "Contract"


# ---------------------------------------------------------------------------
# detect_sector
# ---------------------------------------------------------------------------

class TestDetectSector:

    def test_government(self):
        assert detect_sector("Eligibility Specialist", "Medicaid program", "Mecklenburg County") == "Government"

    def test_healthcare(self):
        assert detect_sector("Claims Analyst", "HIPAA compliance", "Atrium Health") == "Healthcare" or \
               detect_sector("Claims Analyst", "HIPAA compliance", "Atrium Health") == "Compliance / Risk / Fraud"

    def test_banking(self):
        assert detect_sector("Data Analyst", "Financial services", "Wells Fargo") == "Banking"

    def test_compliance(self):
        assert detect_sector("Fraud Analyst", "AML fraud detection", "Stripe") == "Compliance / Risk / Fraud"

    def test_general(self):
        assert detect_sector("Office Manager", "Manage calendars", "TechCo") == "General"

    def test_airbnb_not_healthcare(self):
        """Airbnb should not be tagged Healthcare even though 'hospital' appears in benefits text"""
        sector = detect_sector(
            "Data Analyst",
            "Great benefits including hospital coverage and employee perks",
            "airbnb",
        )
        assert sector != "Healthcare"
