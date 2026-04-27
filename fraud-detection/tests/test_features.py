"""Tests for features.py — build_model_frame."""
import pandas as pd
import pytest
from features import build_model_frame


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_accounts():
    return pd.DataFrame([
        {"account_id": 1, "prior_chargebacks": 0},
        {"account_id": 2, "prior_chargebacks": 2},
        {"account_id": 3, "prior_chargebacks": 1},
    ])


@pytest.fixture
def sample_transactions():
    return pd.DataFrame([
        {"transaction_id": 101, "account_id": 1, "amount_usd": 50.0,   "failed_logins_24h": 0},
        {"transaction_id": 102, "account_id": 2, "amount_usd": 1500.0, "failed_logins_24h": 1},
        {"transaction_id": 103, "account_id": 3, "amount_usd": 999.0,  "failed_logins_24h": 2},
        {"transaction_id": 104, "account_id": 3, "amount_usd": 1000.0, "failed_logins_24h": 5},
    ])


# ---------------------------------------------------------------------------
# Merge behaviour
# ---------------------------------------------------------------------------

class TestMerge:
    def test_output_row_count_matches_transactions(self, sample_transactions, sample_accounts):
        df = build_model_frame(sample_transactions, sample_accounts)
        assert len(df) == len(sample_transactions)

    def test_account_fields_joined(self, sample_transactions, sample_accounts):
        df = build_model_frame(sample_transactions, sample_accounts)
        assert "prior_chargebacks" in df.columns

    def test_unknown_account_produces_nan(self, sample_accounts):
        txs = pd.DataFrame([
            {"transaction_id": 999, "account_id": 9999, "amount_usd": 100.0, "failed_logins_24h": 0}
        ])
        df = build_model_frame(txs, sample_accounts)
        assert df.loc[0, "prior_chargebacks"] != df.loc[0, "prior_chargebacks"]  # NaN check


# ---------------------------------------------------------------------------
# is_large_amount column
# ---------------------------------------------------------------------------

class TestIsLargeAmount:
    def test_column_exists(self, sample_transactions, sample_accounts):
        df = build_model_frame(sample_transactions, sample_accounts)
        assert "is_large_amount" in df.columns

    def test_below_threshold_is_zero(self, sample_transactions, sample_accounts):
        df = build_model_frame(sample_transactions, sample_accounts)
        row = df[df["transaction_id"] == 101].iloc[0]
        assert row["is_large_amount"] == 0

    def test_below_threshold_999_is_zero(self, sample_transactions, sample_accounts):
        df = build_model_frame(sample_transactions, sample_accounts)
        row = df[df["transaction_id"] == 103].iloc[0]
        assert row["is_large_amount"] == 0

    def test_at_threshold_1000_is_one(self, sample_transactions, sample_accounts):
        df = build_model_frame(sample_transactions, sample_accounts)
        row = df[df["transaction_id"] == 104].iloc[0]
        assert row["is_large_amount"] == 1

    def test_above_threshold_is_one(self, sample_transactions, sample_accounts):
        df = build_model_frame(sample_transactions, sample_accounts)
        row = df[df["transaction_id"] == 102].iloc[0]
        assert row["is_large_amount"] == 1

    def test_column_is_integer(self, sample_transactions, sample_accounts):
        df = build_model_frame(sample_transactions, sample_accounts)
        assert df["is_large_amount"].dtype in (int, "int64", "int32")


# ---------------------------------------------------------------------------
# login_pressure column
# ---------------------------------------------------------------------------

class TestLoginPressure:
    def test_column_exists(self, sample_transactions, sample_accounts):
        df = build_model_frame(sample_transactions, sample_accounts)
        assert "login_pressure" in df.columns

    def test_zero_logins_is_none(self, sample_transactions, sample_accounts):
        df = build_model_frame(sample_transactions, sample_accounts)
        row = df[df["transaction_id"] == 101].iloc[0]
        assert str(row["login_pressure"]) == "none"

    def test_one_login_is_none(self, sample_transactions, sample_accounts):
        # bins=[-1, 0, 2, 100] means 1 falls in (0, 2] → label "low"
        df = build_model_frame(sample_transactions, sample_accounts)
        row = df[df["transaction_id"] == 102].iloc[0]
        assert str(row["login_pressure"]) == "low"

    def test_two_logins_is_low(self, sample_transactions, sample_accounts):
        df = build_model_frame(sample_transactions, sample_accounts)
        row = df[df["transaction_id"] == 103].iloc[0]
        assert str(row["login_pressure"]) == "low"

    def test_five_logins_is_high(self, sample_transactions, sample_accounts):
        df = build_model_frame(sample_transactions, sample_accounts)
        row = df[df["transaction_id"] == 104].iloc[0]
        assert str(row["login_pressure"]) == "high"
