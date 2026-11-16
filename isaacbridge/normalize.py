import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

def clean_text(value):
    return " ".join((value or "").strip().split())

def normalize_name(value):
    return clean_text(value).title()

def normalize_phone(value):
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"+1{digits}"
    return digits or None

def normalize_email(value):
    value = clean_text(value).lower()
    return value or None

def normalize_date(value):
    value = clean_text(value)
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"Unsupported date format: {value}")

def normalize_amount(value):
    try:
        amount = Decimal(clean_text(value).replace("$", "").replace(",", ""))
    except (InvalidOperation, AttributeError):
        raise ValueError(f"Invalid amount: {value}")
    if amount < 0:
        raise ValueError("Amount cannot be negative")
    return str(amount.quantize(Decimal("0.01")))

def patient_fingerprint(patient):
    return "|".join([
        (patient.get("first_name") or "").casefold(),
        (patient.get("last_name") or "").casefold(),
        patient.get("dob") or "",
    ])
