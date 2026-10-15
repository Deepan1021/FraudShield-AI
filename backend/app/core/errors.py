"""Application exception hierarchy. Every exception maps to a structured API error."""
from __future__ import annotations

from typing import Any, Optional


class FraudShieldError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.field = field
        self.details = details

    def to_dict(self) -> dict:
        err: dict = {"code": self.code, "message": self.message}
        if self.field:
            err["field"] = self.field
        if self.details is not None:
            err["details"] = self.details
        return {"success": False, "error": err}


class TransactionValidationError(FraudShieldError):
    status_code = 422
    code = "VALIDATION_ERROR"


class NotFoundError(FraudShieldError):
    status_code = 404
    code = "NOT_FOUND"


class DuplicateTransactionError(FraudShieldError):
    status_code = 409
    code = "DUPLICATE_TRANSACTION"


class RuleBaseError(FraudShieldError):
    code = "RULE_BASE_ERROR"


class InferenceError(FraudShieldError):
    code = "INFERENCE_ERROR"


class DatabaseError(FraudShieldError):
    code = "DATABASE_ERROR"


class ReportError(FraudShieldError):
    code = "REPORT_ERROR"


class ConfigurationError(FraudShieldError):
    code = "CONFIGURATION_ERROR"


class StartupError(FraudShieldError):
    code = "STARTUP_ERROR"


class RequestTooLargeError(FraudShieldError):
    status_code = 413
    code = "REQUEST_TOO_LARGE"
