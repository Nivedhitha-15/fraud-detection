from risk_rules import label_risk, score_transaction


def _base_tx(**overrides):
    tx = {
        "device_risk_score": 10,
        "is_international": 0,
        "amount_usd": 100,
        "velocity_24h": 1,
        "failed_logins_24h": 0,
        "prior_chargebacks": 0,
    }
    tx.update(overrides)
    return tx


def test_label_risk_thresholds():
    assert label_risk(10) == "low"
    assert label_risk(35) == "medium"
    assert label_risk(75) == "high"


def test_large_amount_adds_risk():
    assert score_transaction(_base_tx(amount_usd=1200)) >= 25


# Flaw 1 fix: high-risk device should increase the score
def test_high_risk_device_increases_score():
    low_device = score_transaction(_base_tx(device_risk_score=10))
    high_device = score_transaction(_base_tx(device_risk_score=80))
    assert high_device > low_device


def test_medium_risk_device_increases_score():
    low_device = score_transaction(_base_tx(device_risk_score=10))
    medium_device = score_transaction(_base_tx(device_risk_score=50))
    assert medium_device > low_device


# Flaw 2 fix: international transactions should increase the score
def test_international_transaction_increases_score():
    domestic = score_transaction(_base_tx(is_international=0))
    international = score_transaction(_base_tx(is_international=1))
    assert international > domestic


# Flaw 3 fix: high velocity should increase the score
def test_high_velocity_increases_score():
    low_vel = score_transaction(_base_tx(velocity_24h=1))
    high_vel = score_transaction(_base_tx(velocity_24h=8))
    assert high_vel > low_vel


def test_medium_velocity_increases_score():
    low_vel = score_transaction(_base_tx(velocity_24h=1))
    medium_vel = score_transaction(_base_tx(velocity_24h=4))
    assert medium_vel > low_vel


# Flaw 4 fix: prior chargebacks should increase the score
def test_prior_chargebacks_increase_score():
    no_cb = score_transaction(_base_tx(prior_chargebacks=0))
    one_cb = score_transaction(_base_tx(prior_chargebacks=1))
    two_cb = score_transaction(_base_tx(prior_chargebacks=2))
    assert one_cb > no_cb
    assert two_cb > one_cb


# End-to-end: worst-case fraud profile should score high
def test_worst_case_fraud_profile_is_high_risk():
    tx = _base_tx(
        device_risk_score=80,
        is_international=1,
        amount_usd=1500,
        velocity_24h=8,
        failed_logins_24h=6,
        prior_chargebacks=3,
    )
    assert label_risk(score_transaction(tx)) == "high"


# End-to-end: clean profile should score low
def test_clean_profile_is_low_risk():
    tx = _base_tx(
        device_risk_score=5,
        is_international=0,
        amount_usd=50,
        velocity_24h=1,
        failed_logins_24h=0,
        prior_chargebacks=0,
    )
    assert label_risk(score_transaction(tx)) == "low"
