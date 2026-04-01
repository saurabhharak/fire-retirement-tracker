"""Pydantic v2 models for FIRE Retirement Tracker input validation."""

from datetime import date
from typing import Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, Field, field_validator

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
    gold_return: float = Field(ge=0, le=0.3)
    cash_return: float = Field(ge=0, le=0.3)
    inflation: float = Field(gt=0, le=0.2)
    swr: float = Field(gt=0, le=0.10)
    equity_pct: float = Field(ge=0, le=1.0)
    gold_pct: float = Field(ge=0, le=1.0)
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
        gold_pct = info.data.get("gold_pct", 0)
        total = equity_pct + gold_pct + v
        if total > 1.0:
            raise ValueError("Equity + Gold + Cash cannot exceed 100%")
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
    owner: str = Field(default="household", max_length=50)


class FixedExpenseUpdate(BaseModel):
    """Partial update model for fixed expenses."""
    name: Optional[str] = Field(None, max_length=100)
    amount: Optional[float] = Field(None, gt=0)
    frequency: Optional[Literal["monthly", "quarterly", "yearly", "one-time"]] = None
    is_active: Optional[bool] = None
    owner: Optional[str] = None


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
