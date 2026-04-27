"""
Tests for risk_rules.py.

Point values for each rule (used to build exact-score assertions):
  device_risk_score >= 70  → +25
  device_risk_score 40-69  → +10
  is_international == 1    → +15
  amount_usd >= 1000       → +25
  amount_usd 500-999       → +10
  velocity_24h >= 6        → +20
  velocity_24h 3-5         → +5
  failed_logins_24h >= 5   → +20
  failed_logins_24h 2-4    → +10
  prior_chargebacks >= 2   → +20
  prior_chargebacks == 1   → +10
  Maximum possible: 125, clamped to 100
"""
import pytest
from risk_rules import label_risk, score_transaction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tx(**overrides):
    """Return a minimal, all-zero-risk transaction with optional overrides."""
    base = {
        "device_risk_score": 0,
        "is_international": 0,
        "amount_usd": 0,
        "velocity_24h": 0,
        "failed_logins_24h": 0,
        "prior_chargebacks": 0,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# label_risk — boundary conditions
# ---------------------------------------------------------------------------

class TestLabelRisk:
    def test_zero_is_low(self):
        assert label_risk(0) == "low"

    def test_just_below_medium_threshold_is_low(self):
        assert label_risk(29) == "low"

    def test_medium_threshold_is_medium(self):
        assert label_risk(30) == "medium"

    def test_just_below_high_threshold_is_medium(self):
        assert label_risk(59) == "medium"

    def test_high_threshold_is_high(self):
        assert label_risk(60) == "high"

    def test_max_score_is_high(self):
        assert label_risk(100) == "high"


# ---------------------------------------------------------------------------
# score_transaction — return type and clamping
# ---------------------------------------------------------------------------

class TestScoreTransactionContract:
    def test_returns_int(self):
        assert isinstance(score_transaction(_tx()), int)

    def test_all_zero_risk_scores_zero(self):
        assert score_transaction(_tx()) == 0

    def test_score_never_exceeds_100(self):
        tx = _tx(
            device_risk_score=99,
            is_international=1,
            amount_usd=9999,
            velocity_24h=99,
            failed_logins_24h=99,
            prior_chargebacks=99,
        )
        assert score_transaction(tx) == 100

    def test_score_never_below_zero(self):
        # All inputs at minimum — already tested above, but explicit floor check
        assert score_transaction(_tx()) >= 0


# ---------------------------------------------------------------------------
# Device risk rule  (isolated: only device_risk_score varies)
# ---------------------------------------------------------------------------

class TestDeviceRiskRule:
    def test_low_device_score_adds_nothing(self):
        assert score_transaction(_tx(device_risk_score=39)) == 0

    def test_medium_device_score_boundary_adds_10(self):
        assert score_transaction(_tx(device_risk_score=40)) == 10

    def test_medium_device_score_mid_adds_10(self):
        assert score_transaction(_tx(device_risk_score=55)) == 10

    def test_medium_device_score_top_adds_10(self):
        assert score_transaction(_tx(device_risk_score=69)) == 10

    def test_high_device_score_boundary_adds_25(self):
        assert score_transaction(_tx(device_risk_score=70)) == 25

    def test_high_device_score_max_adds_25(self):
        assert score_transaction(_tx(device_risk_score=100)) == 25


# ---------------------------------------------------------------------------
# International transaction rule
# ---------------------------------------------------------------------------

class TestInternationalRule:
    def test_domestic_adds_nothing(self):
        assert score_transaction(_tx(is_international=0)) == 0

    def test_international_adds_15(self):
        assert score_transaction(_tx(is_international=1)) == 15


# ---------------------------------------------------------------------------
# Amount rule
# ---------------------------------------------------------------------------

class TestAmountRule:
    def test_small_amount_adds_nothing(self):
        assert score_transaction(_tx(amount_usd=499)) == 0

    def test_medium_amount_boundary_adds_10(self):
        assert score_transaction(_tx(amount_usd=500)) == 10

    def test_medium_amount_mid_adds_10(self):
        assert score_transaction(_tx(amount_usd=750)) == 10

    def test_medium_amount_top_adds_10(self):
        assert score_transaction(_tx(amount_usd=999)) == 10

    def test_large_amount_boundary_adds_25(self):
        assert score_transaction(_tx(amount_usd=1000)) == 25

    def test_large_amount_high_adds_25(self):
        assert score_transaction(_tx(amount_usd=5000)) == 25


# ---------------------------------------------------------------------------
# Velocity rule
# ---------------------------------------------------------------------------

class TestVelocityRule:
    def test_low_velocity_adds_nothing(self):
        assert score_transaction(_tx(velocity_24h=2)) == 0

    def test_medium_velocity_boundary_adds_5(self):
        assert score_transaction(_tx(velocity_24h=3)) == 5

    def test_medium_velocity_mid_adds_5(self):
        assert score_transaction(_tx(velocity_24h=4)) == 5

    def test_medium_velocity_top_adds_5(self):
        assert score_transaction(_tx(velocity_24h=5)) == 5

    def test_high_velocity_boundary_adds_20(self):
        assert score_transaction(_tx(velocity_24h=6)) == 20

    def test_high_velocity_extreme_adds_20(self):
        assert score_transaction(_tx(velocity_24h=50)) == 20


# ---------------------------------------------------------------------------
# Failed logins rule
# ---------------------------------------------------------------------------

class TestFailedLoginsRule:
    def test_no_failed_logins_adds_nothing(self):
        assert score_transaction(_tx(failed_logins_24h=0)) == 0

    def test_one_failed_login_adds_nothing(self):
        assert score_transaction(_tx(failed_logins_24h=1)) == 0

    def test_medium_logins_boundary_adds_10(self):
        assert score_transaction(_tx(failed_logins_24h=2)) == 10

    def test_medium_logins_mid_adds_10(self):
        assert score_transaction(_tx(failed_logins_24h=3)) == 10

    def test_high_logins_boundary_adds_20(self):
        assert score_transaction(_tx(failed_logins_24h=5)) == 20

    def test_high_logins_extreme_adds_20(self):
        assert score_transaction(_tx(failed_logins_24h=20)) == 20


# ---------------------------------------------------------------------------
# Prior chargebacks rule
# ---------------------------------------------------------------------------

class TestPriorChargebacksRule:
    def test_no_chargebacks_adds_nothing(self):
        assert score_transaction(_tx(prior_chargebacks=0)) == 0

    def test_one_chargeback_adds_10(self):
        assert score_transaction(_tx(prior_chargebacks=1)) == 10

    def test_two_chargebacks_adds_20(self):
        assert score_transaction(_tx(prior_chargebacks=2)) == 20

    def test_many_chargebacks_adds_20(self):
        assert score_transaction(_tx(prior_chargebacks=10)) == 20


# ---------------------------------------------------------------------------
# Additive scoring — rules combine correctly
# ---------------------------------------------------------------------------

class TestAdditiveScoring:
    def test_international_plus_high_device_adds_correctly(self):
        # +15 (international) + +25 (device >= 70) = 40
        assert score_transaction(_tx(is_international=1, device_risk_score=75)) == 40

    def test_high_velocity_plus_chargebacks_adds_correctly(self):
        # +20 (velocity >= 6) + +20 (chargebacks >= 2) = 40
        assert score_transaction(_tx(velocity_24h=8, prior_chargebacks=3)) == 40

    def test_all_medium_tiers_add_correctly(self):
        # +10 (device 40-69) + +10 (amount 500-999) + +5 (velocity 3-5) + +10 (logins 2-4) = 35
        tx = _tx(device_risk_score=50, amount_usd=750, velocity_24h=4, failed_logins_24h=3)
        assert score_transaction(tx) == 35


# ---------------------------------------------------------------------------
# Real-data scenarios (derived from data/transactions.csv + accounts.csv)
# ---------------------------------------------------------------------------

class TestRealDataScenarios:
    """
    These mirror transactions in the actual CSV files so the scoring logic
    can be validated against known outcomes.
    """

    def test_tx50001_low_risk(self):
        # Ava Patel: grocery, $45, device=8, domestic, vel=1, logins=0, cb=0 → score=0
        tx = _tx(device_risk_score=8, is_international=0, amount_usd=45,
                 velocity_24h=1, failed_logins_24h=0, prior_chargebacks=0)
        assert score_transaction(tx) == 0
        assert label_risk(score_transaction(tx)) == "low"

    def test_tx50003_high_risk(self):
        # Mia Chen: gift_cards, $1250, device=81, international, vel=6, logins=5, cb=0 → 25+15+25+20+20 = 105 → 100
        tx = _tx(device_risk_score=81, is_international=1, amount_usd=1250,
                 velocity_24h=6, failed_logins_24h=5, prior_chargebacks=0)
        assert score_transaction(tx) == 100
        assert label_risk(score_transaction(tx)) == "high"

    def test_tx50011_high_risk(self):
        # Harper Allen: crypto, $1400, device=85, international, vel=8, logins=7, cb=1 → 25+15+25+20+20+10 = 115 → 100
        tx = _tx(device_risk_score=85, is_international=1, amount_usd=1400,
                 velocity_24h=8, failed_logins_24h=7, prior_chargebacks=1)
        assert score_transaction(tx) == 100
        assert label_risk(score_transaction(tx)) == "high"

    def test_tx50009_low_risk(self):
        # Amelia Martinez: food_delivery, $18, device=6, domestic, vel=1, logins=0, cb=2
        # account has prior_chargebacks=2 → score should include +20
        tx = _tx(device_risk_score=6, is_international=0, amount_usd=18,
                 velocity_24h=1, failed_logins_24h=0, prior_chargebacks=2)
        assert score_transaction(tx) == 20
        assert label_risk(score_transaction(tx)) == "low"

    def test_tx50006_high_risk(self):
        # Ethan Brown (NG): electronics $399, device=77, international, vel=7, logins=6, cb=3
        # 25 + 15 + 0 + 20 + 20 + 20 = 100
        tx = _tx(device_risk_score=77, is_international=1, amount_usd=399,
                 velocity_24h=7, failed_logins_24h=6, prior_chargebacks=3)
        assert score_transaction(tx) == 100
        assert label_risk(score_transaction(tx)) == "high"

    def test_tx50005_medium_risk(self):
        # Sophia Garcia (GB): travel $2200, device=52, domestic, vel=1, logins=0, cb=0
        # +10 (device 40-69) + +25 (amount>=1000) = 35
        tx = _tx(device_risk_score=52, is_international=0, amount_usd=2200,
                 velocity_24h=1, failed_logins_24h=0, prior_chargebacks=0)
        assert score_transaction(tx) == 35
        assert label_risk(score_transaction(tx)) == "medium"
