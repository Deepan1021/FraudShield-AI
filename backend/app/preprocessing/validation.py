"""Input normalisation and validation. Treats all input as untrusted."""
from __future__ import annotations

import math
import re
from datetime import time
from typing import Any, List, Mapping, Optional, Tuple

from app.core.errors import TransactionValidationError
from app.domain.enums import AccountActivity, DeviceTrust, LoginBehavior, PaymentChannel
from app.domain.models import FieldError, Transaction

MAX_AMOUNT = 10_000_000.0
MAX_FREQUENCY = 1000
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{3,40}$")
_DEVICE_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
_LOCATION_RE = re.compile(r"^[A-Za-z][A-Za-z .,'-]{1,59}$")
_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?\s*([AaPp][Mm])?$")
_CCY_RE = re.compile(r"^[A-Za-z]{3}$")
_SESSION_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
_TEXT_RE = re.compile(r"^[A-Za-z0-9 &/_.,'-]{1,40}$")

REQUIRED_FIELDS = (
    "transaction_id", "user_id", "amount", "transaction_time", "device_trust",
    "location", "login_behavior", "transaction_frequency", "account_activity",
)
OPTIONAL_FIELDS = ("currency", "channel", "device_id", "merchant_category", "session_id")
# The platform never collects payment credentials.
SENSITIVE_FIELD_MARKERS = ("card", "cvv", "pin", "otp", "password", "passwd", "secret", "account_number", "ssn")


def _parse_enum(enum_cls, value: Any):
    if not isinstance(value, str):
        raise ValueError("must be a string")
    token = re.sub(r"[\s-]+", "_", value.strip().upper())
    try:
        return enum_cls(token)
    except ValueError:
        allowed = ", ".join(e.value for e in enum_cls)
        raise ValueError(f"must be one of: {allowed}") from None


def parse_time(value: Any) -> time:
    if isinstance(value, time):
        return value.replace(second=0, microsecond=0)
    if not isinstance(value, str):
        raise ValueError("must be a time string such as 14:30 or 02:15 AM")
    m = _TIME_RE.match(value.strip())
    if not m:
        raise ValueError("must be a time such as 14:30 or 02:15 AM")
    hour, minute, meridiem = int(m.group(1)), int(m.group(2)), m.group(4)
    if minute > 59:
        raise ValueError("minutes must be between 00 and 59")
    if meridiem:
        if not 1 <= hour <= 12:
            raise ValueError("hour must be between 1 and 12 when AM/PM is used")
        hour = hour % 12 + (12 if meridiem.lower() == "pm" else 0)
    elif hour > 23:
        raise ValueError("hour must be between 00 and 23")
    return time(hour, minute)


def _parse_amount(value: Any) -> float:
    if isinstance(value, bool) or value is None:
        raise ValueError("must be a number")
    if isinstance(value, str):
        value = value.strip()
        if not re.fullmatch(r"\d+(\.\d{1,2})?", value):
            raise ValueError("must be a plain positive number such as 85000 or 2500.50")
    try:
        amount = float(value)
    except (TypeError, ValueError):
        raise ValueError("must be a number") from None
    if not math.isfinite(amount):
        raise ValueError("must be a finite number")
    if amount <= 0:
        raise ValueError("Transaction amount must be greater than zero.")
    if amount > MAX_AMOUNT:
        raise ValueError(f"must not exceed {MAX_AMOUNT:,.0f}")
    return round(amount, 2)


def _parse_frequency(value: Any) -> int:
    if isinstance(value, bool) or value is None:
        raise ValueError("must be a whole number")
    if isinstance(value, str):
        if not re.fullmatch(r"\d+", value.strip()):
            raise ValueError("must be a whole number")
        value = int(value.strip())
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError("must be a whole number")
        value = int(value)
    if not isinstance(value, int):
        raise ValueError("must be a whole number")
    if value < 0 or value > MAX_FREQUENCY:
        raise ValueError(f"must be between 0 and {MAX_FREQUENCY}")
    return value


def _clean_location(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("must be text")
    text = re.sub(r"\s+", " ", value.strip())
    if not _LOCATION_RE.match(text):
        raise ValueError("must be 2-60 characters of letters, spaces and basic punctuation")
    return text.title()


def validate_transaction(raw: Mapping[str, Any]) -> Tuple[Transaction, List[dict]]:
    """Validate and normalise raw input.

    Returns (Transaction, normalisations). Raises TransactionValidationError carrying every
    field error when the input is invalid.
    """
    errors: List[FieldError] = []
    if not isinstance(raw, Mapping):
        raise TransactionValidationError("Transaction must be a JSON object.", details=[])

    for key in raw:
        k = str(key).lower()
        if any(marker in k for marker in SENSITIVE_FIELD_MARKERS):
            errors.append(FieldError(str(key), "SENSITIVE_FIELD_REJECTED",
                                     "Payment credentials and secrets are never accepted by this platform."))
        elif key not in REQUIRED_FIELDS and key not in OPTIONAL_FIELDS:
            errors.append(FieldError(str(key), "UNKNOWN_FIELD", "Unknown field."))

    values: dict = {}

    def take(name: str, parser, required: bool = True):
        v = raw.get(name)
        if v is None or (isinstance(v, str) and not v.strip()):
            if required:
                errors.append(FieldError(name, "REQUIRED", f"{name} is required."))
            return None
        try:
            return parser(v)
        except ValueError as exc:
            errors.append(FieldError(name, "INVALID_VALUE", str(exc) if str(exc).startswith("Transaction") else f"{name} {exc}"))
            return None

    def ident(pattern, label):
        def _p(v):
            if not isinstance(v, str) or not pattern.match(v.strip()):
                raise ValueError(f"must be {label}")
            return v.strip().upper()
        return _p

    values["transaction_id"] = take("transaction_id", ident(_ID_RE, "3-40 characters: letters, digits, '-' or '_'"))
    values["user_id"] = take("user_id", ident(_ID_RE, "3-40 characters: letters, digits, '-' or '_'"))
    values["amount"] = take("amount", _parse_amount)
    values["transaction_time"] = take("transaction_time", parse_time)
    values["device_trust"] = take("device_trust", lambda v: _parse_enum(DeviceTrust, v))
    values["location"] = take("location", _clean_location)
    values["login_behavior"] = take("login_behavior", lambda v: _parse_enum(LoginBehavior, v))
    values["transaction_frequency"] = take("transaction_frequency", _parse_frequency)
    values["account_activity"] = take("account_activity", lambda v: _parse_enum(AccountActivity, v))
    currency = take("currency", lambda v: (_ for _ in ()).throw(ValueError("must be a 3-letter code")) if not (isinstance(v, str) and _CCY_RE.match(v.strip())) else v.strip().upper(), required=False)
    channel = take("channel", lambda v: _parse_enum(PaymentChannel, v).value, required=False)
    device_id = take("device_id", ident(_DEVICE_RE, "1-64 characters: letters, digits, '.', ':', '-' or '_'"), required=False)
    merchant = take("merchant_category", lambda v: v.strip() if isinstance(v, str) and _TEXT_RE.match(v.strip()) else (_ for _ in ()).throw(ValueError("contains unsupported characters")), required=False)
    session = take("session_id", ident(_SESSION_RE, "1-64 characters: letters, digits, '.', ':', '-' or '_'"), required=False)

    if errors:
        first = errors[0]
        raise TransactionValidationError(first.message, field=first.field, details=[e.to_dict() for e in errors])

    tx = Transaction(
        transaction_id=values["transaction_id"], user_id=values["user_id"], amount=values["amount"],
        transaction_time=values["transaction_time"], device_trust=values["device_trust"],
        location=values["location"], login_behavior=values["login_behavior"],
        transaction_frequency=values["transaction_frequency"], account_activity=values["account_activity"],
        currency=currency or "INR", channel=channel, device_id=device_id,
        merchant_category=merchant, session_id=session,
    )
    normalisations = []
    for name in ("transaction_id", "user_id", "location", "transaction_time"):
        original = raw.get(name)
        normal = tx.snapshot()[name]
        if isinstance(original, str) and original != normal:
            normalisations.append({"field": name, "from": original, "to": normal})
    return tx, normalisations
