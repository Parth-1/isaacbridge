import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS patients (
  id INTEGER PRIMARY KEY,
  source_system TEXT NOT NULL,
  legacy_id TEXT NOT NULL,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  dob TEXT NOT NULL,
  phone TEXT,
  email TEXT,
  insurance_provider TEXT,
  fingerprint TEXT NOT NULL,
  UNIQUE(source_system, legacy_id)
);
CREATE INDEX IF NOT EXISTS idx_patient_fingerprint ON patients(fingerprint);
CREATE TABLE IF NOT EXISTS appointments (
  id INTEGER PRIMARY KEY,
  source_system TEXT NOT NULL,
  legacy_id TEXT NOT NULL,
  patient_id INTEGER NOT NULL REFERENCES patients(id),
  appointment_date TEXT NOT NULL,
  provider TEXT,
  procedure TEXT,
  status TEXT,
  UNIQUE(source_system, legacy_id)
);
CREATE TABLE IF NOT EXISTS invoices (
  id INTEGER PRIMARY KEY,
  source_system TEXT NOT NULL,
  legacy_id TEXT NOT NULL,
  patient_id INTEGER NOT NULL REFERENCES patients(id),
  invoice_date TEXT NOT NULL,
  amount TEXT NOT NULL,
  status TEXT,
  UNIQUE(source_system, legacy_id)
);
"""

def connect(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn
