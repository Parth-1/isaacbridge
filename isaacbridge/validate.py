REQUIRED_COLUMNS = {
    "patients": {"patient_id", "first_name", "last_name", "dob"},
    "appointments": {"appointment_id", "patient_id", "appointment_date"},
    "invoices": {"invoice_id", "patient_id", "invoice_date", "amount"},
}

def check_columns(kind, fieldnames):
    missing = REQUIRED_COLUMNS[kind] - set(fieldnames or [])
    if missing:
        raise ValueError(f"{kind}.csv missing required columns: {', '.join(sorted(missing))}")
