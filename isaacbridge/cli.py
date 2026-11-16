import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from .db import connect
from .agent import run_schema_agent, load_approved_mapping
from .importer import (
    SOURCE_SYSTEM, read_csv, transform_patient,
    transform_appointment, transform_invoice
)

def migrate(source, db_path, report_path, dry_run=False, column_mappings=None):
    source = Path(source)
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter()
    errors = []

    raw = {
        "patients": read_csv(source / "patients.csv", "patients", (column_mappings or {}).get("patients")),
        "appointments": read_csv(source / "appointments.csv", "appointments", (column_mappings or {}).get("appointments")),
        "invoices": read_csv(source / "invoices.csv", "invoices", (column_mappings or {}).get("invoices")),
    }
    counts["source_patients"] = len(raw["patients"])
    counts["source_appointments"] = len(raw["appointments"])
    counts["source_invoices"] = len(raw["invoices"])

    conn = connect(db_path)
    try:
        with conn:
            patient_ids = {}
            seen_fingerprints = set()

            for line, row in enumerate(raw["patients"], start=2):
                try:
                    p = transform_patient(row)
                    if p["fingerprint"] in seen_fingerprints:
                        counts["duplicate_patients"] += 1
                        errors.append({"file": "patients.csv", "line": line, "legacy_id": p["legacy_id"],
                                       "error": "Potential duplicate identity fingerprint; review manually"})
                        continue
                    seen_fingerprints.add(p["fingerprint"])
                    if not dry_run:
                        conn.execute("""
                          INSERT INTO patients(source_system, legacy_id, first_name, last_name, dob,
                            phone, email, insurance_provider, fingerprint)
                          VALUES(?,?,?,?,?,?,?,?,?)
                          ON CONFLICT(source_system, legacy_id) DO UPDATE SET
                            first_name=excluded.first_name, last_name=excluded.last_name, dob=excluded.dob,
                            phone=excluded.phone, email=excluded.email,
                            insurance_provider=excluded.insurance_provider, fingerprint=excluded.fingerprint
                        """, (SOURCE_SYSTEM, p["legacy_id"], p["first_name"], p["last_name"], p["dob"],
                              p["phone"], p["email"], p["insurance_provider"], p["fingerprint"]))
                        pid = conn.execute("SELECT id FROM patients WHERE source_system=? AND legacy_id=?",
                                           (SOURCE_SYSTEM, p["legacy_id"])).fetchone()[0]
                        patient_ids[p["legacy_id"]] = pid
                    else:
                        patient_ids[p["legacy_id"]] = p["legacy_id"]
                    counts["valid_patients"] += 1
                except Exception as exc:
                    counts["rejected_patients"] += 1
                    errors.append({"file": "patients.csv", "line": line,
                                   "legacy_id": row.get("patient_id", ""), "error": str(exc)})

            for kind, transform, date_field in [
                ("appointments", transform_appointment, "appointment_date"),
                ("invoices", transform_invoice, "invoice_date"),
            ]:
                for line, row in enumerate(raw[kind], start=2):
                    try:
                        item = transform(row)
                        if item["patient_legacy_id"] not in patient_ids:
                            raise ValueError("Patient reference not found or patient was rejected/flagged")
                        if not dry_run:
                            if kind == "appointments":
                                conn.execute("""
                                  INSERT INTO appointments(source_system, legacy_id, patient_id, appointment_date,
                                    provider, procedure, status) VALUES(?,?,?,?,?,?,?)
                                  ON CONFLICT(source_system, legacy_id) DO UPDATE SET
                                    patient_id=excluded.patient_id, appointment_date=excluded.appointment_date,
                                    provider=excluded.provider, procedure=excluded.procedure, status=excluded.status
                                """, (SOURCE_SYSTEM, item["legacy_id"], patient_ids[item["patient_legacy_id"]],
                                      item[date_field], item["provider"], item["procedure"], item["status"]))
                            else:
                                conn.execute("""
                                  INSERT INTO invoices(source_system, legacy_id, patient_id, invoice_date, amount, status)
                                  VALUES(?,?,?,?,?,?)
                                  ON CONFLICT(source_system, legacy_id) DO UPDATE SET
                                    patient_id=excluded.patient_id, invoice_date=excluded.invoice_date,
                                    amount=excluded.amount, status=excluded.status
                                """, (SOURCE_SYSTEM, item["legacy_id"], patient_ids[item["patient_legacy_id"]],
                                      item[date_field], item["amount"], item["status"]))
                        counts[f"valid_{kind}"] += 1
                    except Exception as exc:
                        counts[f"rejected_{kind}"] += 1
                        errors.append({"file": f"{kind}.csv", "line": line,
                                       "legacy_id": row.get("appointment_id" if kind == "appointments" else "invoice_id", ""),
                                       "error": str(exc)})
    finally:
        conn.close()

    result = {
        "source_system": SOURCE_SYSTEM,
        "mode": "dry-run" if dry_run else "migration",
        "counts": dict(counts),
        "error_count": len(errors),
        "errors": errors,
        "note": "Synthetic demo only; potential duplicate matches require human review."
    }
    report_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    error_path = report_path.with_name(report_path.stem + ".errors.csv")
    if errors:
        with error_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["file", "line", "legacy_id", "error"])
            writer.writeheader()
            writer.writerows(errors)
    print(json.dumps(result, indent=2))
    return result

def main():
    parser = argparse.ArgumentParser(description="Migrate synthetic legacy dental CSV exports.")
    parser.add_argument("--source", default="data/legacy")
    parser.add_argument("--db", default="data/isaacbridge.db")
    parser.add_argument("--report", default="reports/latest.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--agent-plan", action="store_true", help="Use an LLM agent to inspect CSVs and propose column mappings")
    parser.add_argument("--confirm-synthetic-data", action="store_true", help="Confirm that sample rows may be sent to the configured Google Gemini API")
    parser.add_argument("--apply-agent-mapping", help="Apply a reviewed agent mapping JSON file to the migration")
    parser.add_argument("--model", default="gemini-3.8-flash", help="Gemini model used for the schema agent")
    args = parser.parse_args()

    if args.agent_plan:
        if not args.confirm_synthetic_data:
            parser.error("--agent-plan sends sample CSV rows to the Google Gemini API. Use only synthetic data and pass --confirm-synthetic-data after reviewing this warning.")
        plan_path = Path(args.report).with_name("agent-mapping.json")
        plan = run_schema_agent(args.source, plan_path, args.model)
        print(f"\nAgent mapping proposal saved to: {plan_path}")
        print(json.dumps(plan, indent=2))
        print("Review the JSON carefully. Then apply it with --apply-agent-mapping after approval.")
        return

    mappings = None
    if args.apply_agent_mapping:
        mappings = load_approved_mapping(args.apply_agent_mapping)
        approval = input("Have you reviewed and approved every proposed column mapping? Type YES to continue: ")
        if approval != "YES":
            print("Migration cancelled. No records were imported.")
            return
    migrate(args.source, args.db, args.report, args.dry_run, mappings)

if __name__ == "__main__":
    main()
