import unittest

from app.core.errors import TransactionValidationError
from app.domain.enums import DeviceTrust
from app.preprocessing.validation import parse_time, validate_transaction
from tests.helpers import TXN001, tx


class ValidationTests(unittest.TestCase):
    def test_valid_transaction_is_normalised(self):
        t, norm = validate_transaction(TXN001)
        self.assertEqual(t.device_trust, DeviceTrust.UNTRUSTED)
        self.assertEqual(t.transaction_time.hour, 2)
        self.assertEqual(t.amount, 85000.0)
        self.assertTrue(any(n["field"] == "transaction_time" for n in norm))

    def test_ids_are_uppercased_and_location_title_cased(self):
        t, _ = validate_transaction(tx(transaction_id="txn-77", location="  new   delhi "))
        self.assertEqual(t.transaction_id, "TXN-77")
        self.assertEqual(t.location, "New Delhi")

    def test_time_formats(self):
        self.assertEqual(parse_time("14:30").hour, 14)
        self.assertEqual(parse_time("02:15 AM").hour, 2)
        self.assertEqual(parse_time("12:05 AM").hour, 0)
        self.assertEqual(parse_time("12:05 PM").hour, 12)
        self.assertEqual(parse_time("11:59 pm").hour, 23)
        for bad in ("25:00", "12:60", "13:00 PM", "noon", "", "7"):
            with self.assertRaises(ValueError, msg=bad):
                parse_time(bad)

    def assert_invalid(self, field, **over):
        with self.assertRaises(TransactionValidationError) as ctx:
            validate_transaction(tx(**over))
        self.assertEqual(ctx.exception.field, field)
        return ctx.exception

    def test_amount_rules(self):
        e = self.assert_invalid("amount", amount=0)
        self.assertEqual(e.message, "Transaction amount must be greater than zero.")
        self.assert_invalid("amount", amount=-5)
        self.assert_invalid("amount", amount="abc")
        self.assert_invalid("amount", amount=float("nan"))
        self.assert_invalid("amount", amount=float("inf"))
        self.assert_invalid("amount", amount=10 ** 9)
        self.assert_invalid("amount", amount=True)

    def test_enum_fields(self):
        self.assert_invalid("device_trust", device_trust="SUPER_TRUSTED")
        self.assert_invalid("login_behavior", login_behavior=5)
        self.assert_invalid("account_activity", account_activity="gone")
        t, _ = validate_transaction(tx(login_behavior="failed attempts", account_activity="recently-reactivated"))
        self.assertEqual(t.login_behavior.value, "FAILED_ATTEMPTS")
        self.assertEqual(t.account_activity.value, "RECENTLY_REACTIVATED")

    def test_frequency_rules(self):
        self.assert_invalid("transaction_frequency", transaction_frequency=-1)
        self.assert_invalid("transaction_frequency", transaction_frequency=1.5)
        self.assert_invalid("transaction_frequency", transaction_frequency=5000)
        t, _ = validate_transaction(tx(transaction_frequency="7"))
        self.assertEqual(t.transaction_frequency, 7)

    def test_location_and_ids_reject_injection_like_input(self):
        self.assert_invalid("location", location="Delhi'; DROP TABLE users;--")
        self.assert_invalid("location", location="<script>alert(1)</script>")
        self.assert_invalid("transaction_id", transaction_id="../../etc/passwd")
        self.assert_invalid("user_id", user_id="a b")

    def test_missing_required_fields_collects_all_errors(self):
        with self.assertRaises(TransactionValidationError) as ctx:
            validate_transaction({"transaction_id": "TXN9"})
        fields = {d["field"] for d in ctx.exception.details}
        self.assertTrue({"user_id", "amount", "transaction_time", "device_trust", "location",
                         "login_behavior", "transaction_frequency", "account_activity"} <= fields)

    def test_credentials_are_rejected(self):
        for name in ("card_number", "cvv", "pin", "otp", "password"):
            with self.assertRaises(TransactionValidationError) as ctx:
                validate_transaction({**tx(), name: "1234"})
            self.assertEqual(ctx.exception.details[0]["code"], "SENSITIVE_FIELD_REJECTED")

    def test_unknown_field_rejected_and_non_mapping(self):
        with self.assertRaises(TransactionValidationError):
            validate_transaction({**tx(), "colour": "red"})
        with self.assertRaises(TransactionValidationError):
            validate_transaction([1, 2, 3])  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
