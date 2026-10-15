"""Pydantic request schemas and the standard response envelope (drives the OpenAPI documentation)."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class TransactionIn(BaseModel):
    """The seven core security parameters plus optional supporting metadata. Never include card numbers, CVV, PIN or OTP."""
    model_config = ConfigDict(extra="forbid", json_schema_extra={"example": {
        "transaction_id": "TXN100", "user_id": "USER001", "amount": 85000, "transaction_time": "02:15",
        "device_trust": "UNTRUSTED", "location": "Delhi", "login_behavior": "SUSPICIOUS",
        "transaction_frequency": 12, "account_activity": "ACTIVE"}})

    transaction_id: str = Field(..., min_length=1, max_length=64, description="Unique synthetic transaction identifier")
    user_id: str = Field(..., min_length=1, max_length=64)
    amount: float = Field(..., description="Payment amount (> 0)")
    transaction_time: str = Field(..., max_length=16, description="HH:MM (24h) or hh:mm AM/PM")
    device_trust: str = Field(..., max_length=32, description="TRUSTED | KNOWN | UNTRUSTED | UNKNOWN")
    location: str = Field(..., max_length=80)
    login_behavior: str = Field(..., max_length=32, description="NORMAL | UNUSUAL | FAILED_ATTEMPTS | SUSPICIOUS | HIGH_RISK")
    transaction_frequency: int = Field(..., description="Transactions in the relevant period (0-1000)")
    account_activity: str = Field(..., max_length=32,
                                  description="NORMAL | ACTIVE | SUSPICIOUS | DORMANT | RECENTLY_REACTIVATED | UNUSUAL")
    currency: Optional[str] = Field(None, max_length=3)
    channel: Optional[str] = Field(None, max_length=32, description="UPI | WALLET | ONLINE_BANKING | CARD | OTHER")
    device_id: Optional[str] = Field(None, max_length=64)
    merchant_category: Optional[str] = Field(None, max_length=40)
    session_id: Optional[str] = Field(None, max_length=64)


class ReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transaction_id: str = Field(..., min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    format: Literal["json", "csv", "pdf"] = "json"


class ApiResponse(BaseModel):
    """Every successful response uses this envelope: {"success": true, "data": ...}."""
    success: bool = True
    data: Any = None


class ApiError(BaseModel):
    code: str
    message: str
    field: Optional[str] = None
    details: Any = None


class ApiErrorResponse(BaseModel):
    success: bool = False
    error: ApiError
