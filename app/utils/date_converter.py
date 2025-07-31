from decimal import Decimal
from datetime import datetime


def convert_decimals(data):
    """Recursively convert Decimal objects to strings or floats in a dictionary/list."""
    if isinstance(data, dict):
        return {key: convert_decimals(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_decimals(item) for item in data]
    elif isinstance(data, Decimal):
        return str(data)  # Or return `float(data)` if you prefer float
    return data


def convert_datetime(obj):
    """Recursively convert datetime objects to ISO format."""
    if isinstance(obj, dict):
        return {key: convert_datetime(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    return obj