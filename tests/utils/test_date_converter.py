from datetime import datetime
from decimal import Decimal

from app.utils.date_converter import convert_datetime, convert_decimals


def test_convert_decimals_handles_nested_containers():
    payload = {
        "price": Decimal("19.99"),
        "items": [Decimal("1.5"), {"tax": Decimal("0.15")}],
        "name": "book",
    }

    converted = convert_decimals(payload)

    assert converted == {
        "price": "19.99",
        "items": ["1.5", {"tax": "0.15"}],
        "name": "book",
    }


def test_convert_datetime_handles_nested_containers():
    now = datetime(2026, 1, 2, 3, 4, 5)
    payload = {
        "created_at": now,
        "items": [now, {"updated_at": now}],
        "count": 2,
    }

    converted = convert_datetime(payload)

    assert converted == {
        "created_at": now.isoformat(),
        "items": [now.isoformat(), {"updated_at": now.isoformat()}],
        "count": 2,
    }


def test_converters_leave_non_matching_values_unchanged():
    assert convert_decimals("plain") == "plain"
    assert convert_datetime(42) == 42
