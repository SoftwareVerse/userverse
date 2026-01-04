import phonenumbers
from typing import Optional


def validate_phone_number_format(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return phone

    try:
        parsed = phonenumbers.parse(phone, None)  # No default region
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError("Invalid phone number.")
    except phonenumbers.NumberParseException as exc:
        raise ValueError("Invalid phone number format.") from exc

    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
