"""
tests/test_filters.py — Unit tests for all filtering logic.

Run with:  python -m pytest tests/ -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from filters import is_us_location, title_matches, contract_ok

TITLE_FILTERS = [
    "fraud analyst", "compliance analyst", "risk analyst",
    "executive assistant", "executive business partner", "chief of staff",
    "data analyst", "business analyst", "analytics",
    "project coordinator", "program coordinator", "operations coordinator",
    "operations analyst", "business operations analyst",
]


# ---------------------------------------------------------------------------
# is_us_location
# ---------------------------------------------------------------------------

class TestIsUsLocation:

    def test_empty_location_allowed(self):
        assert is_us_location("") is True

    def test_remote_allowed(self):
        assert is_us_location("Remote") is True

    def test_worldwide_allowed(self):
        assert is_us_location("Worldwide") is True

    def test_united_states_allowed(self):
        assert is_us_location("United States - Remote") is True

    def test_remote_us_allowed(self):
        assert is_us_location("Remote US") is True

    def test_remote_comma_us_allowed(self):
        assert is_us_location("Remote, US") is True

    def test_charlotte_nc_allowed(self):
        assert is_us_location("Charlotte, NC") is True

    def test_menlo_park_ca_allowed(self):
        assert is_us_location("Menlo Park, CA") is True

    def test_new_york_ny_allowed(self):
        assert is_us_location("New York, NY") is True

    def test_north_carolina_allowed(self):
        assert is_us_location("North Carolina") is True

    def test_multi_city_us_allowed(self):
        assert is_us_location("CHI, SF, NYC, SEA, US Remote") is True

    def test_california_full_name_allowed(self):
        assert is_us_location("California, California, United States") is True

    # International — should be blocked
    def test_canada_blocked(self):
        assert is_us_location("Canada - Remote (ON, AB, BC)") is False

    def test_montreal_canada_blocked(self):
        assert is_us_location("Montreal, Canada") is False

    def test_remote_canada_blocked(self):
        assert is_us_location("Remote, Canada") is False

    def test_australia_blocked(self):
        assert is_us_location("Sydney, Australia") is False

    def test_remote_australia_blocked(self):
        assert is_us_location("Remote, Australia") is False

    def test_india_blocked(self):
        assert is_us_location("Gurugram, India") is False

    def test_uk_blocked(self):
        assert is_us_location("Remote, United Kingdom") is False

    def test_portugal_blocked(self):
        assert is_us_location("Lisboa, Lisboa, Portugal") is False

    def test_spain_blocked(self):
        assert is_us_location("Barcelona, Spain") is False

    def test_germany_blocked(self):
        assert is_us_location("Berlin, Germany") is False

    def test_brazil_blocked(self):
        assert is_us_location("São Paulo, Brazil") is False

    def test_mexico_city_blocked(self):
        assert is_us_location("Mexico City") is False

    def test_costa_rica_blocked(self):
        assert is_us_location("Costa Rica") is False

    # Key edge cases — the bugs we fixed
    def test_australia_does_not_match_us(self):
        """'us' must not match inside 'australia'"""
        assert is_us_location("Sydney, Australia") is False

    def test_canada_does_not_match_ca(self):
        """', ca' must not match inside 'canada'"""
        assert is_us_location("Montreal, Canada") is False

    def test_toronto_new_york_san_francisco_allowed(self):
        """Has both Toronto (non-US) and San Francisco (US) — US wins"""
        assert is_us_location("Toronto, New York, San Francisco") is True


# ---------------------------------------------------------------------------
# title_matches
# ---------------------------------------------------------------------------

class TestTitleMatches:

    def test_fraud_analyst_matches(self):
        assert title_matches("Senior Fraud Analyst", TITLE_FILTERS) is True

    def test_compliance_analyst_matches(self):
        assert title_matches("Compliance Analyst II", TITLE_FILTERS) is True

    def test_risk_analyst_matches(self):
        assert title_matches("Risk Analyst - Remote", TITLE_FILTERS) is True

    def test_executive_assistant_matches(self):
        assert title_matches("Executive Assistant to CEO", TITLE_FILTERS) is True

    def test_data_analyst_matches(self):
        assert title_matches("Data Analyst, Core Analytics", TITLE_FILTERS) is True

    def test_project_coordinator_matches(self):
        assert title_matches("Project Coordinator", TITLE_FILTERS) is True

    def test_software_engineer_no_match(self):
        assert title_matches("Senior Software Engineer", TITLE_FILTERS) is False

    def test_marketing_manager_no_match(self):
        assert title_matches("Marketing Manager", TITLE_FILTERS) is False

    def test_case_insensitive(self):
        assert title_matches("FRAUD ANALYST", TITLE_FILTERS) is True


# ---------------------------------------------------------------------------
# contract_ok
# ---------------------------------------------------------------------------

class TestContractOk:

    def test_full_time_always_ok(self):
        assert contract_ok("Data Analyst", "Full-time remote role", True) is True
        assert contract_ok("Data Analyst", "Full-time remote role", False) is True

    def test_contract_ok_when_included(self):
        assert contract_ok("Data Analyst", "This is a contract role", True) is True

    def test_contract_blocked_when_excluded(self):
        assert contract_ok("Data Analyst", "This is a contract role", False) is False

    def test_contractor_blocked(self):
        assert contract_ok("Fraud Analyst", "Looking for a contractor", False) is False

    def test_freelance_blocked(self):
        assert contract_ok("EA", "Freelance opportunity", False) is False

    def test_temp_blocked(self):
        assert contract_ok("Coordinator", "temp position available", False) is False
