from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from app.errors import DomainError

CENT = Decimal("0.01")

def parse_price(raw) -> Decimal:
    if raw is None:
        raise DomainError("EMPTY_VALUE", "缺少站点约定单价 unit_price")
    if isinstance(raw, bool) or not isinstance(raw, (str, int, float, Decimal)):
        raise DomainError("BAD_FORMAT", "单价必须是数值或数值字符串")
    try:
        price = Decimal(str(raw).strip())
    except InvalidOperation:
        raise DomainError("BAD_FORMAT", f"单价 {raw!r} 不是合法数值")
    if not price.is_finite() or price < 0:
        raise DomainError("BAD_FORMAT", "单价必须是非负有限数")
    return price

def price_str(price: Decimal) -> str:
    return format(price.normalize(), "f")

def money_str(value: Decimal) -> str:
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))

def amount_str(price: Decimal, qty: int) -> str:
    return money_str(price * qty)
