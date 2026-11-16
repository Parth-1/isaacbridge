import csv
from pathlib import Path
from .normalize import (
    clean_text, normalize_name, normalize_phone, normalize_email,
    normalize_date, normalize_amount, patient_fingerprint
)
from .validate import check_columns

SOURCE_SYSTEM = "legacy_csv"

def read_csv(path, kind, column_mapping=None):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}")
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if column_mapping is None:
            check_columns(kind, reader.fieldnames)
            return list(reader)
        available = set(reader.fieldnames or [])
        missing_sources = {source for source in column_mapping.values() if source not in available}
        if missing_sources:
            raise ValueError(f"{path.name} mapping references missing columns: {', '.join(sorted(missing_sources))}")
        required = {
            "patients": {"patient_id", "first_name", "last_name", "dob"},
            "appointments": {"appointment_id", "patient_id", "appointment_date"},
            "invoices": {"invoice_id", "patient_id", "invoice_date", "amount"},
        }[kind]
        missing_targets = required - set(column_mapping)
        if missing_targets:
            raise ValueError(f"{path.name} mapping omits required fields: {', '.join(sorted(missing_targets))}")
        return [
            {target: row.get(source, "") for target, source in column_mapping.items()}
            for row in reader
        ]

def transform_patient(row):
    patient = {
        "legacy_id": clean_text(row.get("patient_id")),
        "first_name": normalize_name(row.get("first_name")),
        "last_name": normalize_name(row.get("last_name")),
        "dob": normalize_date(row.get("dob")),
        "phone": normalize_phone(row.get("phone")),
        "email": normalize_email(row.get("email")),
        "insurance_provider": clean_text(row.get("insurance_provider")) or None,
    }
    if not patient["legacy_id"] or not patient["first_name"] or not patient["last_name"] or not patient["dob"]:
        raise ValueError("Patient is missing a required identity field")
    patient["fingerprint"] = patient_fingerprint(patient)
    return patient

def transform_appointment(row):
    result = {
        "legacy_id": clean_text(row.get("appointment_id")),
        "patient_legacy_id": clean_text(row.get("patient_id")),
        "appointment_date": normalize_date(row.get("appointment_date")),
        "provider": clean_text(row.get("provider")) or None,
        "procedure": clean_text(row.get("procedure")) or None,
        "status": clean_text(row.get("status")).lower() or "unknown",
    }
    if not result["legacy_id"] or not result["patient_legacy_id"] or not result["appointment_date"]:
        raise ValueError("Appointment is missing a required field")
    return result

def transform_invoice(row):
    result = {
        "legacy_id": clean_text(row.get("invoice_id")),
        "patient_legacy_id": clean_text(row.get("patient_id")),
        "invoice_date": normalize_date(row.get("invoice_date")),
        "amount": normalize_amount(row.get("amount")),
        "status": clean_text(row.get("status")).lower() or "unknown",
    }
    if not result["legacy_id"] or not result["patient_legacy_id"] or not result["invoice_date"]:
        raise ValueError("Invoice is missing a required field")
    return result
