import unittest
from isaacbridge.normalize import normalize_phone, normalize_email, normalize_date, normalize_amount

class NormalizeTests(unittest.TestCase):
    def test_phone(self):
        self.assertEqual(normalize_phone("(408) 555-0101"), "+14085550101")
    def test_email(self):
        self.assertEqual(normalize_email(" JANE@EXAMPLE.COM "), "jane@example.com")
    def test_dates(self):
        self.assertEqual(normalize_date("01/14/1988"), "1988-01-14")
    def test_amount(self):
        self.assertEqual(normalize_amount("$1,250.5"), "1250.50")
    def test_bad_date(self):
        with self.assertRaises(ValueError):
            normalize_date("not-a-date")

if __name__ == "__main__":
    unittest.main()
