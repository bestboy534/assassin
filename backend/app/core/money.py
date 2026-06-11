from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, Field

MONEY_QUANTUM = Decimal("0.0001")


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


class Money(BaseModel):
    amount: Decimal = Field(max_digits=19, decimal_places=4)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
