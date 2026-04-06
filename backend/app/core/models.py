"""Pydantic v2 models for FIRE Retirement Tracker input validation."""

from datetime import date
from typing import Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, Field, field_validator, model_validator

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    data: T
    message: Optional[str] = None


class FireInputs(BaseModel):
    """All user-configurable FIRE planning inputs.

    Derived values (debt_pct, total_sip, current_age, years_to_retirement,
    retirement_duration) are computed in engine.py, NOT stored.
    """

    dob: date
    retirement_age: int = Field(ge=19, le=99)
    life_expectancy: int = Field(ge=50, le=120)
    your_sip: float = Field(ge=0)
    wife_sip: float = Field(ge=0)
    step_up_pct: float = Field(ge=0, le=0.5)
    existing_corpus: float = Field(ge=0)
    equity_return: float = Field(gt=0, le=0.3)
    debt_return: float = Field(gt=0, le=0.3)
    precious_metals_return: float = Field(ge=0, le=0.3)
    cash_return: float = Field(ge=0, le=0.3)
    inflation: float = Field(gt=0, le=0.2)
    swr: float = Field(gt=0, le=0.10)
    equity_pct: float = Field(ge=0, le=1.0)
    precious_metals_pct: float = Field(ge=0, le=1.0)
    cash_pct: float = Field(ge=0, le=1.0)
    monthly_expense: float = Field(ge=0)

    @field_validator("life_expectancy")
    @classmethod
    def life_after_retirement(cls, v: int, info) -> int:
        retirement_age = info.data.get("retirement_age", 0)
        if v <= retirement_age:
            raise ValueError("Life expectancy must exceed retirement age")
        return v

    @field_validator("cash_pct")
    @classmethod
    def allocation_sum(cls, v: float, info) -> float:
        equity_pct = info.data.get("equity_pct", 0)
        precious_metals_pct = info.data.get("precious_metals_pct", 0)
        total = equity_pct + precious_metals_pct + v
        if total > 1.0:
            raise ValueError("Equity + Precious Metals + Cash cannot exceed 100%")
        return v


class IncomeEntry(BaseModel):
    """Monthly income log entry."""

    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2020, le=2100)
    your_income: float = Field(ge=0)
    wife_income: float = Field(ge=0)
    notes: str = Field(max_length=500, default="")


class FixedExpense(BaseModel):
    """Recurring fixed expense."""

    name: str = Field(max_length=100)
    amount: float = Field(gt=0)
    frequency: Literal["monthly", "quarterly", "yearly", "one-time"]
    owner: Literal["you", "wife", "household"] = "household"
    payment_method: Literal["upi", "credit_card", "cash"] = "upi"
    category: Literal["housing", "food", "transport", "utilities", "entertainment", "health", "education", "insurance", "subscriptions", "other"] = "other"
    expense_month: Optional[int] = Field(None, ge=1, le=12)
    expense_year: Optional[int] = Field(None, ge=2020, le=2100)

    @model_validator(mode="after")
    def one_time_requires_month_year(self):
        if self.frequency == "one-time":
            if self.expense_month is None or self.expense_year is None:
                raise ValueError("One-time expenses require expense_month and expense_year")
        return self


class FixedExpenseUpdate(BaseModel):
    """Partial update model for fixed expenses.

    Note: The DB has a CHECK constraint that also enforces month/year for
    one-time expenses, so this validator is a secondary safety net.
    """
    name: Optional[str] = Field(None, max_length=100)
    amount: Optional[float] = Field(None, gt=0)
    frequency: Optional[Literal["monthly", "quarterly", "yearly", "one-time"]] = None
    is_active: Optional[bool] = None
    owner: Optional[Literal["you", "wife", "household"]] = None
    payment_method: Optional[Literal["upi", "credit_card", "cash"]] = None
    category: Optional[Literal["housing", "food", "transport", "utilities", "entertainment", "health", "education", "insurance", "subscriptions", "other"]] = None
    expense_month: Optional[int] = Field(None, ge=1, le=12)
    expense_year: Optional[int] = Field(None, ge=2020, le=2100)

    @model_validator(mode="after")
    def one_time_requires_month_year(self):
        if self.frequency == "one-time":
            if self.expense_month is None or self.expense_year is None:
                raise ValueError(
                    "Updating frequency to 'one-time' requires expense_month and expense_year"
                )
        return self


# ---------------------------------------------------------------------------
# Precious Metals Portfolio Models (multi-metal: gold, silver, platinum)
# ---------------------------------------------------------------------------

class PreciousMetalPurchase(BaseModel):
    """New precious metal purchase entry."""
    metal_type: Literal["gold", "silver", "platinum"]
    purchase_date: date
    weight_grams: float = Field(gt=0, le=100000)
    price_per_gram: float = Field(gt=0, le=1000000)
    purity: str = Field(max_length=5)
    owner: Literal["you", "wife", "household"] = "household"
    notes: str = Field(max_length=500, default="")

    @model_validator(mode="after")
    def validate_purity_for_metal(self):
        valid = {
            "gold": ("24K", "22K", "18K"),
            "silver": ("999", "925", "900"),
            "platinum": ("999", "950", "900"),
        }
        allowed = valid.get(self.metal_type, ())
        if self.purity not in allowed:
            raise ValueError(
                f"Invalid purity '{self.purity}' for {self.metal_type}. Must be one of {allowed}"
            )
        return self

    @field_validator("purchase_date")
    @classmethod
    def purchase_date_in_range(cls, v: date) -> date:
        from datetime import date as date_type
        if not (date_type(2000, 1, 1) <= v <= date_type.today()):
            raise ValueError("purchase_date must be between 2000-01-01 and today")
        return v


class PreciousMetalPurchaseUpdate(BaseModel):
    """Partial update for a precious metal purchase.

    If purity is provided, metal_type MUST also be provided so we can
    validate the purity against the metal. The router can inject the
    existing metal_type from the DB row.
    """
    metal_type: Optional[Literal["gold", "silver", "platinum"]] = None
    purchase_date: Optional[date] = None
    weight_grams: Optional[float] = Field(None, gt=0, le=100000)
    price_per_gram: Optional[float] = Field(None, gt=0, le=1000000)
    purity: Optional[str] = Field(None, max_length=5)
    owner: Optional[Literal["you", "wife", "household"]] = None
    notes: Optional[str] = Field(None, max_length=500)

    @model_validator(mode="after")
    def validate_purity_if_provided(self):
        if self.purity is not None and self.metal_type is not None:
            valid = {
                "gold": ("24K", "22K", "18K"),
                "silver": ("999", "925", "900"),
                "platinum": ("999", "950", "900"),
            }
            allowed = valid.get(self.metal_type, ())
            if self.purity not in allowed:
                raise ValueError(
                    f"Invalid purity '{self.purity}' for {self.metal_type}. Must be one of {allowed}"
                )
        return self

    @field_validator("purchase_date")
    @classmethod
    def purchase_date_in_range(cls, v: Optional[date]) -> Optional[date]:
        if v is None:
            return v
        from datetime import date as date_type
        if not (date_type(2000, 1, 1) <= v <= date_type.today()):
            raise ValueError("purchase_date must be between 2000-01-01 and today")
        return v


class SipFund(BaseModel):
    """Per-fund SIP amount."""
    fund_name: str = Field(max_length=200)
    amount: float = Field(ge=0)


class SipLogEntry(BaseModel):
    """Monthly SIP tracking log entry."""

    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2020, le=2100)
    planned_sip: float = Field(ge=0)
    actual_invested: float = Field(ge=0)
    notes: str = Field(max_length=500, default="")
    funds: list[SipFund] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Project Expenses Models (multi-project expense tracking)
# ---------------------------------------------------------------------------

class ProjectCreate(BaseModel):
    """Create a new project."""
    name: str = Field(max_length=100)
    status: Literal["active", "completed"] = "active"
    budget: Optional[float] = Field(None, gt=0)
    start_date: date
    end_date: Optional[date] = None

    @model_validator(mode="after")
    def end_after_start(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be >= start_date")
        return self


class ProjectUpdate(BaseModel):
    """Partial update for a project."""
    name: Optional[str] = Field(None, max_length=100)
    status: Optional[Literal["active", "completed"]] = None
    budget: Optional[float] = Field(None, gt=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class ProjectExpenseCreate(BaseModel):
    """Create a new project expense."""
    project_id: str
    date: date
    category: str = Field(max_length=50)
    description: str = Field(max_length=200)
    total_amount: Optional[float] = Field(None, ge=0)
    paid_amount: float = Field(ge=0)
    paid_by: str = Field(default="Saurabh Harak", max_length=100)


class ProjectExpenseUpdate(BaseModel):
    """Partial update for a project expense."""
    date: Optional[date] = None
    category: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    total_amount: Optional[float] = Field(None, ge=0)
    paid_amount: Optional[float] = Field(None, ge=0)
    paid_by: Optional[str] = Field(None, max_length=100)
