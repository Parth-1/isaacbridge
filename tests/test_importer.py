import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from isaacbridge.importer import transform_patient, transform_invoice, read_csv

class ImporterTests(unittest.TestCase):
    def test_patient_normalization(self):
        p = transform_patient({"patient_id":"X1","first_name":" jane ","last_name":"DOE",
                               "dob":"01/14/1988","phone":"4085550101","email":"JANE@EXAMPLE.COM"})
        self.assertEqual(p["first_name"], "Jane")
        self.assertEqual(p["phone"], "+14085550101")
        self.assertEqual(p["email"], "jane@example.com")
    def test_negative_invoice_rejected(self):
        with self.assertRaises(ValueError):
            transform_invoice({"invoice_id":"I1","patient_id":"P1","invoice_date":"2026-01-01","amount":"-2"})

    def test_read_csv_with_agent_column_mapping(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "patients.csv"
            path.write_text("id,given,family,birth\nP1,Jane,Doe,1988-01-14\n", encoding="utf-8")
            mapping = {"patient_id": "id", "first_name": "given", "last_name": "family", "dob": "birth"}
            rows = read_csv(path, "patients", mapping)
            self.assertEqual(rows[0]["patient_id"], "P1")
            self.assertEqual(rows[0]["first_name"], "Jane")

if __name__ == "__main__":
    unittest.main()
