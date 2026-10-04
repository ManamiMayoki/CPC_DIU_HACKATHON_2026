"""Security and Data Validation Layer for Financial Transactions.

Ensures no invalid, malformed, negative, NaN, infinite, or duplicate transactions
silently pass through into graph or ML processing pipelines.
"""

from __future__ import annotations

import datetime
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import pandas as pd


class TransactionValidationError(ValueError):
    """Raised when financial transaction data fails strict security/integrity checks."""
    pass


@dataclass
class ValidationResult:
    """Encapsulates the result of transaction batch validation."""
    is_valid: bool
    total_processed: int
    valid_transactions: List[Dict[str, Any]]
    invalid_transactions: List[Dict[str, Any]]
    errors: List[str] = field(default_factory=list)

    @property
    def valid_count(self) -> int:
        return len(self.valid_transactions)

    @property
    def invalid_count(self) -> int:
        return len(self.invalid_transactions)


# Upper bound for realistic single synthetic transaction in standard currency units
DEFAULT_MAX_AMOUNT: float = 1_000_000_000.0  # 1 Billion max threshold


def parse_iso_timestamp(timestamp_val: Any) -> Optional[datetime.datetime]:
    """Parse various timestamp representations (ISO 8601 string, integer/float unix epoch)."""
    if timestamp_val is None:
        return None

    if isinstance(timestamp_val, (int, float)):
        if math.isnan(timestamp_val) or math.isinf(timestamp_val):
            return None
        # Must be positive timestamp
        if timestamp_val < 0:
            return None
        try:
            return datetime.datetime.fromtimestamp(timestamp_val, tz=datetime.timezone.utc)
        except (ValueError, OverflowError, OSError):
            return None

    if isinstance(timestamp_val, str):
        cleaned = timestamp_val.strip()
        if not cleaned:
            return None
        # Handle trailing Z
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        try:
            return datetime.datetime.fromisoformat(cleaned)
        except ValueError:
            # Fallback for standard space-separated format
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.datetime.strptime(cleaned, fmt).replace(tzinfo=datetime.timezone.utc)
                except ValueError:
                    continue
            return None

    if isinstance(timestamp_val, datetime.datetime):
        return timestamp_val

    return None


def validate_single_transaction(
    tx: Any,
    seen_tx_ids: Optional[Set[str]] = None,
    max_amount: float = DEFAULT_MAX_AMOUNT,
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """Validates a single transaction against financial security integrity constraints.

    Returns:
        (is_valid, error_reason, cleaned_transaction_dict)
    """
    if not isinstance(tx, dict):
        return False, f"Malformed transaction record: expected dict, received {type(tx).__name__}", None

    # Required field presence check
    # We accept sender_id (or sender) and receiver_id (or receiver)
    sender = tx["sender_id"] if "sender_id" in tx else tx.get("sender")
    receiver = tx["receiver_id"] if "receiver_id" in tx else tx.get("receiver")
    amount = tx["amount"] if "amount" in tx else None
    timestamp = tx["timestamp"] if "timestamp" in tx else None
    tx_id = tx["transaction_id"] if "transaction_id" in tx else tx.get("tx_id")

    # 1. Missing fields check
    missing = []
    if sender is None:
        missing.append("sender_id")
    if receiver is None:
        missing.append("receiver_id")
    if amount is None:
        missing.append("amount")
    if timestamp is None:
        missing.append("timestamp")

    if missing:
        return False, f"Missing required fields: {', '.join(missing)}", None

    # 2. Account IDs validity
    if not isinstance(sender, (str, int)) or not str(sender).strip():
        return False, "Invalid sender_id: must be non-empty string or integer identifier", None
    if not isinstance(receiver, (str, int)) or not str(receiver).strip():
        return False, "Invalid receiver_id: must be non-empty string or integer identifier", None

    clean_sender = str(sender).strip()
    clean_receiver = str(receiver).strip()

    if clean_sender == clean_receiver:
        return False, f"Self-transfer detected: sender_id equals receiver_id ({clean_sender})", None

    # 3. Amount checks (type, NaN, inf, negative, zero, extreme values)
    if isinstance(amount, (str, bytes)):
        try:
            amount_val = float(amount)
        except ValueError:
            return False, f"Invalid amount format: cannot parse '{amount}' as numeric", None
    elif isinstance(amount, (int, float)):
        amount_val = float(amount)
    else:
        return False, f"Invalid amount type: {type(amount).__name__}", None

    if math.isnan(amount_val):
        return False, "Invalid amount: NaN is strictly prohibited", None
    if math.isinf(amount_val):
        return False, "Invalid amount: infinite value detected", None
    if amount_val < 0:
        return False, f"Invalid amount: negative value ({amount_val}) is not permitted", None
    if amount_val == 0.0:
        return False, "Invalid amount: zero-value transactions are invalid", None
    if amount_val > max_amount:
        return False, f"Extreme amount: {amount_val} exceeds maximum allowed limit ({max_amount})", None

    # 4. Timestamp validity
    parsed_dt = parse_iso_timestamp(timestamp)
    if parsed_dt is None:
        return False, f"Invalid timestamp: '{timestamp}' cannot be parsed as a valid ISO-8601 or epoch date", None

    # 5. Duplicate transaction ID check
    clean_tx_id = str(tx_id).strip() if tx_id is not None else None
    if clean_tx_id:
        if seen_tx_ids is not None:
            if clean_tx_id in seen_tx_ids:
                return False, f"Duplicate transaction_id detected: '{clean_tx_id}'", None
            seen_tx_ids.add(clean_tx_id)

    # Standardized clean output dictionary
    cleaned: Dict[str, Any] = {
        "transaction_id": clean_tx_id or f"TX_{id(tx)}",
        "sender_id": clean_sender,
        "receiver_id": clean_receiver,
        "amount": round(amount_val, 4),
        "timestamp": parsed_dt.isoformat(),
    }

    return True, None, cleaned


def validate_transactions(
    transactions: Union[List[Dict[str, Any]], pd.DataFrame],
    strict: bool = False,
    max_amount: float = DEFAULT_MAX_AMOUNT,
) -> ValidationResult:
    """Validates a collection of transactions.

    Args:
        transactions: List of dicts or Pandas DataFrame.
        strict: If True, raises TransactionValidationError on empty or invalid data.
        max_amount: Cap on maximum permitted numeric value.

    Returns:
        ValidationResult containing clean transactions, invalid transactions, and errors.
    """
    # 1. Empty dataset validation
    if transactions is None:
        err = "Empty dataset: transactions input is None"
        if strict:
            raise TransactionValidationError(err)
        return ValidationResult(is_valid=False, total_processed=0, valid_transactions=[], invalid_transactions=[], errors=[err])

    if isinstance(transactions, pd.DataFrame):
        if transactions.empty:
            err = "Empty dataset: transactions DataFrame contains 0 rows"
            if strict:
                raise TransactionValidationError(err)
            return ValidationResult(is_valid=False, total_processed=0, valid_transactions=[], invalid_transactions=[], errors=[err])
        tx_list = transactions.to_dict(orient="records")
    elif isinstance(transactions, list):
        if len(transactions) == 0:
            err = "Empty dataset: transactions list is empty"
            if strict:
                raise TransactionValidationError(err)
            return ValidationResult(is_valid=False, total_processed=0, valid_transactions=[], invalid_transactions=[], errors=[err])
        tx_list = transactions
    else:
        err = f"Malformed input: expected list or DataFrame, received {type(transactions).__name__}"
        if strict:
            raise TransactionValidationError(err)
        return ValidationResult(is_valid=False, total_processed=0, valid_transactions=[], invalid_transactions=[], errors=[err])

    valid_txs: List[Dict[str, Any]] = []
    invalid_txs: List[Dict[str, Any]] = []
    errors: List[str] = []
    seen_ids: Set[str] = set()

    for idx, tx in enumerate(tx_list):
        ok, reason, cleaned = validate_single_transaction(tx, seen_tx_ids=seen_ids, max_amount=max_amount)
        if ok and cleaned is not None:
            valid_txs.append(cleaned)
        else:
            err_msg = f"Row {idx}: {reason}"
            errors.append(err_msg)
            invalid_txs.append({"raw": tx, "error": reason, "row_index": idx})
            if strict:
                raise TransactionValidationError(err_msg)

    is_overall_valid = (len(invalid_txs) == 0) and (len(valid_txs) > 0)
    return ValidationResult(
        is_valid=is_overall_valid,
        total_processed=len(tx_list),
        valid_transactions=valid_txs,
        invalid_transactions=invalid_txs,
        errors=errors,
    )
