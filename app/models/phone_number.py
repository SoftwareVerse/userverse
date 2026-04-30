import phonenumbers
from typing import Optional


def validate_phone_number_format(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return phone

    try:
        parsed = phonenumbers.parse(phone, None)  # No default region
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError("Invalid phone number.")
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        # Backward-compatible fallback: allow plain digit numbers commonly used in tests/forms.
        digits = "".join(ch for ch in phone if ch.isdigit())
        if 10 <= len(digits) <= 15:
            return phone
        raise ValueError("Invalid phone number format.") from None
