"""Security and Data Validation Tests for Financial Transaction Inputs."""

from __future__ import annotations

import math
import os
import sys
import pandas as pd
import pytest

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
ML_DIR = os.path.join(PROJECT_ROOT, "ml")
for p in (PROJECT_ROOT, ML_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from ml.validation import (
    TransactionValidationError,
    validate_single_transaction,
    validate_transactions,
)


class TestSecurityValidation:
    """Rigorous security checks for transactional integrity."""

    def test_missing_fields(self):
        # Missing receiver_id and amount
        tx = {"transaction_id": "T1", "sender_id": "A", "timestamp": "2026-03-01T10:00:00Z"}
        ok, reason, _ = validate_single_transaction(tx)
        assert ok is False
        assert "Missing required fields" in reason

    def test_invalid_account_ids(self):
        # Empty string sender
        tx1 = {"transaction_id": "T1", "sender_id": "", "receiver_id": "B", "amount": 10.0, "timestamp": "2026-03-01T10:00:00Z"}
        ok, reason, _ = validate_single_transaction(tx1)
        assert ok is False
        assert "Invalid sender_id" in reason

        # Whitespace sender
        tx2 = {"transaction_id": "T2", "sender_id": "   ", "receiver_id": "B", "amount": 10.0, "timestamp": "2026-03-01T10:00:00Z"}
        ok, reason, _ = validate_single_transaction(tx2)
        assert ok is False

    def test_self_transfer_prevention(self):
        tx = {"transaction_id": "T1", "sender_id": "ACC_SAME", "receiver_id": "ACC_SAME", "amount": 10.0, "timestamp": "2026-03-01T10:00:00Z"}
        ok, reason, _ = validate_single_transaction(tx)
        assert ok is False
        assert "Self-transfer detected" in reason

    def test_negative_amount(self):
        tx = {"transaction_id": "T1", "sender_id": "A", "receiver_id": "B", "amount": -50.0, "timestamp": "2026-03-01T10:00:00Z"}
        ok, reason, _ = validate_single_transaction(tx)
        assert ok is False
        assert "negative" in reason.lower()

    def test_zero_amount(self):
        tx = {"transaction_id": "T1", "sender_id": "A", "receiver_id": "B", "amount": 0.0, "timestamp": "2026-03-01T10:00:00Z"}
        ok, reason, _ = validate_single_transaction(tx)
        assert ok is False
        assert "zero" in reason.lower()

    def test_nan_and_infinity_amount(self):
        tx_nan = {"transaction_id": "T1", "sender_id": "A", "receiver_id": "B", "amount": float("nan"), "timestamp": "2026-03-01T10:00:00Z"}
        ok1, reason1, _ = validate_single_transaction(tx_nan)
        assert ok1 is False
        assert "nan" in reason1.lower()

        tx_inf = {"transaction_id": "T2", "sender_id": "A", "receiver_id": "B", "amount": float("inf"), "timestamp": "2026-03-01T10:00:00Z"}
        ok2, reason2, _ = validate_single_transaction(tx_inf)
        assert ok2 is False
        assert "infinite" in reason2.lower()

    def test_extreme_amount_limit(self):
        # Exceeds 1 billion default threshold
        tx = {"transaction_id": "T1", "sender_id": "A", "receiver_id": "B", "amount": 5_000_000_000.0, "timestamp": "2026-03-01T10:00:00Z"}
        ok, reason, _ = validate_single_transaction(tx, max_amount=1_000_000_000.0)
        assert ok is False
        assert "exceeds maximum allowed limit" in reason.lower()

    def test_invalid_timestamp(self):
        tx = {"transaction_id": "T1", "sender_id": "A", "receiver_id": "B", "amount": 100.0, "timestamp": "not-a-timestamp"}
        ok, reason, _ = validate_single_transaction(tx)
        assert ok is False
        assert "Invalid timestamp" in reason

    def test_malformed_input_type(self):
        ok, reason, _ = validate_single_transaction("this is a string, not a transaction dict")
        assert ok is False
        assert "Malformed transaction record" in reason

    def test_duplicate_transaction_ids(self):
        txs = [
            {"transaction_id": "DUP_ID", "sender_id": "A", "receiver_id": "B", "amount": 10.0, "timestamp": "2026-03-01T10:00:00Z"},
            {"transaction_id": "DUP_ID", "sender_id": "C", "receiver_id": "D", "amount": 20.0, "timestamp": "2026-03-01T10:01:00Z"},
        ]
        res = validate_transactions(txs, strict=False)
        assert res.valid_count == 1
        assert res.invalid_count == 1
        assert "Duplicate transaction_id" in res.invalid_transactions[0]["error"]

    def test_empty_input_dataset(self):
        # Empty list
        res_list = validate_transactions([], strict=False)
        assert res_list.is_valid is False
        assert "empty dataset" in res_list.errors[0].lower()

        # Empty DataFrame
        res_df = validate_transactions(pd.DataFrame(), strict=False)
        assert res_df.is_valid is False

        # Strict mode raises exception
        with pytest.raises(TransactionValidationError):
            validate_transactions([], strict=True)

    def test_strict_mode_rejects_silently_invalid(self):
        txs = [
            {"transaction_id": "T1", "sender_id": "A", "receiver_id": "B", "amount": 10.0, "timestamp": "2026-03-01T10:00:00Z"},
            {"transaction_id": "T2", "sender_id": "B", "receiver_id": "C", "amount": -99.0, "timestamp": "2026-03-01T10:05:00Z"},
        ]
        with pytest.raises(TransactionValidationError):
            validate_transactions(txs, strict=True)
