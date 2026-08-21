"""Validation tests for the parlour module Pydantic models.

Uses make_valid_* builder functions (matching test_models_retirement_validation.py)
with one rejection test per constraint.
"""
import pytest
from pydantic import ValidationError

from app.core.models import (
    ParlourCreate,
    ParlourUpdate,
    ParlourMemberAdd,
    ParlourMemberUpdate,
    AmulDailySaleCreate,
    AmulDailySaleUpdate,
    AmulInvoiceCreate,
    AmulInvoiceUpdate,
    AmulInvoiceItemCreate,
    AmulInvoiceItemUpdate,
    AmulOtherExpenseCreate,
    AmulOtherExpenseUpdate,
)


def make_valid_parlour(**overrides) -> dict:
    base = {"name": "Vrindavan Treats", "sarvam_starting_credits": 100}
    base.update(overrides)
    return base


def make_valid_sale(**overrides) -> dict:
    base = {
        "sale_date": "2026-08-15",
        "cash_amount": 2750,
        "online_amount": 5769,
        "sender_name": "Swapnil 555 Harak",
    }
    base.update(overrides)
    return base


def make_valid_invoice(**overrides) -> dict:
    base = {
        "distributor": "M/S.MAHAVIR SUPER MARKET",
        "bill_no": "AMUL2602568",
        "bill_date": "2026-07-01",
        "invoice_type": "tax_invoice",
        "total_amount": 1761.88,
        "tax_amount": 83.90,
        "taxable_amount": 1677.98,
    }
    base.update(overrides)
    return base


def make_valid_item(**overrides) -> dict:
    base = {
        "sr_no": 1,
        "hsn": "1806",
        "description": "Amul Bindaaz Wafer Choco 6x75x12 Gm Jar",
        "mrp": 5.0,
        "rate": 3.97,
        "box_qty": 1,
        "pcs_qty": 0,
        "free_qty": 0,
        "scheme": "",
        "discount": 0,
        "gst_pct": 5.0,
        "gst_amount": 14.88,
        "net_amount": 312.38,
    }
    base.update(overrides)
    return base


# ===================================================================
# ParlourCreate / ParlourUpdate
# ===================================================================
class TestParlourCreate:
    def test_valid_parlour_accepted(self):
        p = ParlourCreate(**make_valid_parlour())
        assert p.name == "Vrindavan Treats"
        assert p.sarvam_starting_credits == 100

    def test_name_over_100_rejected(self):
        with pytest.raises(ValidationError):
            ParlourCreate(**make_valid_parlour(name="x" * 101))

    def test_name_required(self):
        with pytest.raises(ValidationError):
            ParlourCreate(**make_valid_parlour(name=""))

    def test_negative_starting_credits_rejected(self):
        with pytest.raises(ValidationError):
            ParlourCreate(**make_valid_parlour(sarvam_starting_credits=-1))

    def test_zero_starting_credits_accepted(self):
        p = ParlourCreate(**make_valid_parlour(sarvam_starting_credits=0))
        assert p.sarvam_starting_credits == 0

    def test_starting_credits_defaults_to_zero(self):
        p = ParlourCreate(name="Test")
        assert p.sarvam_starting_credits == 0


class TestParlourUpdate:
    def test_all_optional(self):
        u = ParlourUpdate()
        assert u.name is None

    def test_partial_fields_accepted(self):
        u = ParlourUpdate(name="New Name")
        assert u.name == "New Name"

    def test_negative_credits_rejected(self):
        with pytest.raises(ValidationError):
            ParlourUpdate(sarvam_starting_credits=-5)


# ===================================================================
# ParlourMemberAdd / ParlourMemberUpdate
# ===================================================================
class TestParlourMemberAdd:
    def test_valid_member_accepted(self):
        m = ParlourMemberAdd(member_email="swapnil@example.com", role="data_entry")
        assert m.role == "data_entry"

    def test_default_role_is_data_entry(self):
        m = ParlourMemberAdd(member_email="swapnil@example.com")
        assert m.role == "data_entry"

    def test_owner_role_accepted(self):
        m = ParlourMemberAdd(member_email="a@b.com", role="owner")
        assert m.role == "owner"

    def test_invalid_role_rejected(self):
        with pytest.raises(ValidationError):
            ParlourMemberAdd(member_email="a@b.com", role="admin")

    def test_email_required(self):
        with pytest.raises(ValidationError):
            ParlourMemberAdd(member_email="")


class TestParlourMemberUpdate:
    def test_valid_role(self):
        u = ParlourMemberUpdate(role="owner")
        assert u.role == "owner"

    def test_invalid_role_rejected(self):
        with pytest.raises(ValidationError):
            ParlourMemberUpdate(role="superadmin")


# ===================================================================
# AmulDailySaleCreate / Update
# ===================================================================
class TestAmulDailySaleCreate:
    def test_valid_sale_accepted(self):
        s = AmulDailySaleCreate(**make_valid_sale())
        assert s.cash_amount == 2750
        assert s.online_amount == 5769

    def test_default_sender_empty(self):
        s = AmulDailySaleCreate(
            sale_date="2026-08-15", cash_amount=100, online_amount=0
        )
        assert s.sender_name == ""

    def test_negative_cash_rejected(self):
        with pytest.raises(ValidationError):
            AmulDailySaleCreate(**make_valid_sale(cash_amount=-1))

    def test_negative_online_rejected(self):
        with pytest.raises(ValidationError):
            AmulDailySaleCreate(**make_valid_sale(online_amount=-1))

    def test_both_cash_online_zero_rejected(self):
        with pytest.raises(ValidationError):
            AmulDailySaleCreate(
                sale_date="2026-08-15", cash_amount=0, online_amount=0
            )

    def test_sale_date_required(self):
        with pytest.raises(ValidationError):
            AmulDailySaleCreate(cash_amount=100, online_amount=0)

    def test_sender_over_100_rejected(self):
        with pytest.raises(ValidationError):
            AmulDailySaleCreate(**make_valid_sale(sender_name="x" * 101))


class TestAmulDailySaleUpdate:
    def test_all_optional(self):
        u = AmulDailySaleUpdate()
        assert u.cash_amount is None

    def test_negative_amount_rejected(self):
        with pytest.raises(ValidationError):
            AmulDailySaleUpdate(cash_amount=-10)


# ===================================================================
# AmulInvoiceCreate / Update
# ===================================================================
class TestAmulInvoiceCreate:
    def test_valid_tax_invoice_accepted(self):
        inv = AmulInvoiceCreate(**make_valid_invoice())
        assert inv.invoice_type == "tax_invoice"
        assert inv.bill_no == "AMUL2602568"

    def test_valid_bill_of_supply_with_null_bill_no_accepted(self):
        inv = AmulInvoiceCreate(**make_valid_invoice(invoice_type="bill_of_supply", bill_no=None))
        assert inv.bill_no is None

    def test_invalid_invoice_type_rejected(self):
        with pytest.raises(ValidationError):
            AmulInvoiceCreate(**make_valid_invoice(invoice_type="credit_note"))

    def test_negative_total_rejected(self):
        with pytest.raises(ValidationError):
            AmulInvoiceCreate(**make_valid_invoice(total_amount=-1))

    def test_negative_tax_rejected(self):
        with pytest.raises(ValidationError):
            AmulInvoiceCreate(**make_valid_invoice(tax_amount=-0.01))

    def test_distributor_required(self):
        with pytest.raises(ValidationError):
            AmulInvoiceCreate(**make_valid_invoice(distributor=""))

    def test_bill_date_required(self):
        with pytest.raises(ValidationError):
            AmulInvoiceCreate(
                distributor="D", invoice_type="tax_invoice", total_amount=100
            )


class TestAmulInvoiceUpdate:
    def test_all_optional(self):
        u = AmulInvoiceUpdate()
        assert u.total_amount is None

    def test_partial_accepted(self):
        u = AmulInvoiceUpdate(total_amount=500)
        assert u.total_amount == 500

    def test_negative_total_rejected(self):
        with pytest.raises(ValidationError):
            AmulInvoiceUpdate(total_amount=-1)


# ===================================================================
# AmulInvoiceItemCreate / Update
# ===================================================================
class TestAmulInvoiceItemCreate:
    def test_valid_item_accepted(self):
        it = AmulInvoiceItemCreate(**make_valid_item())
        assert it.description.startswith("Amul")

    def test_description_required(self):
        with pytest.raises(ValidationError):
            AmulInvoiceItemCreate(**make_valid_item(description=""))

    def test_negative_rate_rejected(self):
        with pytest.raises(ValidationError):
            AmulInvoiceItemCreate(**make_valid_item(rate=-1))

    def test_negative_net_rejected(self):
        with pytest.raises(ValidationError):
            AmulInvoiceItemCreate(**make_valid_item(net_amount=-1))

    def test_negative_qty_rejected(self):
        with pytest.raises(ValidationError):
            AmulInvoiceItemCreate(**make_valid_item(pcs_qty=-1))

    def test_zero_sr_no_rejected(self):
        with pytest.raises(ValidationError):
            AmulInvoiceItemCreate(**make_valid_item(sr_no=0))

    def test_defaults_applied(self):
        it = AmulInvoiceItemCreate(sr_no=1, description="D", rate=10, net_amount=10)
        assert it.mrp == 0
        assert it.free_qty == 0
        assert it.discount == 0
        assert it.gst_pct == 0


class TestAmulInvoiceItemUpdate:
    def test_all_optional(self):
        u = AmulInvoiceItemUpdate()
        assert u.net_amount is None

    def test_negative_rejected(self):
        with pytest.raises(ValidationError):
            AmulInvoiceItemUpdate(net_amount=-5)


# ===================================================================
# AmulOtherExpenseCreate / Update
# ===================================================================
class TestAmulOtherExpenseCreate:
    def make_valid(self, **overrides) -> dict:
        base = {
            "expense_date": "2026-07-01",
            "category": "rent",
            "description": "Shop rent",
            "amount": 20000,
        }
        base.update(overrides)
        return base

    def test_valid_expense_accepted(self):
        e = AmulOtherExpenseCreate(**self.make_valid())
        assert e.amount == 20000
        assert e.category == "rent"

    def test_description_defaults_empty(self):
        e = AmulOtherExpenseCreate(expense_date="2026-07-01", category="rent", amount=100)
        assert e.description == ""

    def test_zero_amount_rejected(self):
        with pytest.raises(ValidationError):
            AmulOtherExpenseCreate(**self.make_valid(amount=0))

    def test_negative_amount_rejected(self):
        with pytest.raises(ValidationError):
            AmulOtherExpenseCreate(**self.make_valid(amount=-1))

    def test_category_required(self):
        with pytest.raises(ValidationError):
            AmulOtherExpenseCreate(**self.make_valid(category=""))

    def test_category_over_50_rejected(self):
        with pytest.raises(ValidationError):
            AmulOtherExpenseCreate(**self.make_valid(category="x" * 51))

    def test_date_required(self):
        with pytest.raises(ValidationError):
            AmulOtherExpenseCreate(category="rent", amount=100)


class TestAmulOtherExpenseUpdate:
    def test_all_optional(self):
        u = AmulOtherExpenseUpdate()
        assert u.amount is None

    def test_partial_accepted(self):
        u = AmulOtherExpenseUpdate(amount=500)
        assert u.amount == 500

    def test_negative_amount_rejected(self):
        with pytest.raises(ValidationError):
            AmulOtherExpenseUpdate(amount=-10)
