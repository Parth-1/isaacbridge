# IsaacBridge — Agentic AI-Powered Legacy Data Migration

IsaacBridge is a Python-based data migration prototype that helps transform inconsistent legacy dental practice data into a standardized relational database.

It combines **Google Gemini, Python, and SQLite** to inspect unfamiliar CSV schemas, propose column mappings, validate records, identify duplicates, and migrate approved data.

The project demonstrates a human-in-the-loop agentic AI workflow in which an LLM analyzes legacy data structures and proposes migration plans, while deterministic Python logic handles validation and database operations.

## Key Features

- **AI-Powered Schema Discovery:** Uses Google Gemini to inspect legacy CSV column names and sample records.
- **Tool Calling:** Provides Gemini with a Python inspection function to examine source CSV schemas.
- **Intelligent Column Mapping:** Generates mappings between legacy fields and standardized application fields.
- **Human-in-the-Loop Approval:** Requires explicit approval before applying AI-generated mappings.
- **Data Validation:** Checks required fields, formats, and record consistency.
- **Duplicate Detection:** Identifies duplicate records instead of silently merging potentially different patients.
- **Dry-Run Mode:** Validates migration results without inserting records.
- **Migration Reporting:** Generates JSON reports containing migration statistics and validation issues.
- **SQLite Persistence:** Stores approved and valid records in a structured relational database.

## Architecture

```text
        Legacy Dental CSV Files
       (Patients, Appointments,
              Invoices)
                  |
                  v
         Python CSV Inspector
                  |
                  v
          Google Gemini Agent
                  |
          Tool Calling / Analysis
                  |
                  v
       AI-Generated Mapping Plan
          (JSON Proposal)
                  |
                  v
          Human Approval
                  |
                  v
       Schema Mapping Validation
                  |
                  v
        Record Normalization
                  |
                  v
          Data Validation
                  |
           +------+------+
           |             |
           v             v
       Valid Data    Invalid Data
           |             |
           v             v
       SQLite DB     JSON Report
           |
           v
       Migration Report
```

## Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python |
| AI Model | Google Gemini |
| AI Integration | Google GenAI SDK |
| Database | SQLite |
| Input Format | CSV |
| Output Format | JSON |
| Testing | Python unittest |

## Project Structure

```text
IsaacBridge/
│
├── isaacbridge/
│   ├── __init__.py
│   ├── __main__.py
│   ├── agent.py
│   ├── cli.py
│   ├── db.py
│   ├── importer.py
│   ├── normalize.py
│   └── validate.py
│
├── data/
│   └── legacy_variant/
│       ├── patients.csv
│       ├── appointments.csv
│       └── invoices.csv
│
├── reports/
│   └── .gitkeep
│
├── tests/
│   ├── test_normalize.py
│   └── test_importer.py
│
├── requirements.txt
├── .gitignore
└── README.md
```

## How It Works

### 1. Inspect Legacy Data

IsaacBridge reads legacy CSV files containing patient, appointment, and invoice information.

The files may use different column names from the standardized database schema.

For example:

| Legacy Field | Standardized Field |
|---|---|
| `patient_number` | `patient_id` |
| `given_name` | `first_name` |
| `surname` | `last_name` |
| `date_of_birth` | `dob` |
| `telephone` | `phone` |
| `visit_date` | `appointment_date` |
| `total_due` | `amount` |

### 2. Generate AI Mapping Proposals

Google Gemini analyzes the CSV schemas through a Python inspection tool.

The agent proposes mappings for:

- Patients
- Appointments
- Invoices

The proposed mappings are saved as a JSON file:

`reports/agent-mapping.json`

The AI does not directly modify the database.

### 3. Human Approval

Before applying the generated mapping, IsaacBridge requires explicit human approval.

This helps prevent incorrect AI-generated mappings from silently affecting migrated data.

### 4. Validate and Normalize Records

Python processes the records using deterministic validation and normalization logic.

Records are categorized as:

- Valid records
- Duplicate records
- Invalid records

Invalid and duplicate records are reported rather than silently imported.

### 5. Migrate Approved Data

After validation, eligible records can be inserted into SQLite.

The migration process also generates a JSON report containing processing statistics and validation issues.

## Getting Started

### Prerequisites

- Python 3.10 or newer
- Google AI Studio API key
- Internet connection for Gemini API requests

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/IsaacBridge.git
cd IsaacBridge
```

### 2. Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
python3 -m pip install -r requirements.txt
```

### 4. Configure Gemini API Key

Create an API key through [Google AI Studio](https://aistudio.google.com/).

Set it in your terminal:

```bash
export GEMINI_API_KEY="your-api-key"
```

Do not commit your API key to GitHub.

### 5. Generate an AI Mapping Proposal

Run the schema agent:

```bash
python3 -u -m isaacbridge \
  --source data/legacy_variant \
  --report reports/agent-run.json \
  --agent-plan \
  --confirm-synthetic-data \
  --model gemini-3.8-flash
```

The agent inspects the source CSV files and generates:

```text
reports/agent-mapping.json
```

### 6. Review and Dry-Run the Migration

```bash
python3 -u -m isaacbridge \
  --source data/legacy_variant \
  --report reports/agent-dry-run.json \
  --apply-agent-mapping reports/agent-mapping.json \
  --confirm-synthetic-data \
  --dry-run
```

Review the proposed mappings and explicitly approve them when prompted.

The dry run validates the migration without inserting records.

### 7. Execute the Migration

After reviewing the dry-run report:

```bash
python3 -u -m isaacbridge \
  --source data/legacy_variant \
  --report reports/agent-migration.json \
  --apply-agent-mapping reports/agent-mapping.json \
  --confirm-synthetic-data
```

Review and approve the mappings again when prompted.

### 8. Run Tests

```bash
python3 -m unittest discover -s tests -v
```

## Example AI Mapping Output

Gemini can generate a mapping proposal similar to:

```json
{
  "mappings": {
    "patients": {
      "patient_id": "patient_number",
      "first_name": "given_name",
      "last_name": "surname",
      "dob": "date_of_birth",
      "phone": "telephone",
      "email": "email_address",
      "insurance_provider": "plan_name"
    },
    "appointments": {
      "appointment_id": "visit_id",
      "patient_id": "patient_number",
      "appointment_date": "visit_date",
      "provider": "provider_name",
      "procedure": "treatment",
      "status": "visit_status"
    },
    "invoices": {
      "invoice_id": "bill_number",
      "patient_id": "patient_number",
      "invoice_date": "billed_on",
      "amount": "total_due",
      "status": "payment_status"
    }
  },
  "approval_required": true
}
```

This is an example of how the agent translates unfamiliar legacy schemas into a standardized structure.

## Design Decisions

**Why use an LLM?**

Legacy systems often have inconsistent naming conventions and undocumented schemas. An LLM can help interpret unfamiliar column names and propose mappings without requiring every source format to be hardcoded.

**Why use deterministic validation?**

AI-generated mappings can be incorrect. Python validation provides predictable checks before data reaches the database.

**Why require human approval?**

Patient identity and financial records are sensitive. Ambiguous mappings should be reviewed rather than automatically accepted.

**Why include dry-run mode?**

A migration should be tested before modifying the target database. Dry-run mode provides an opportunity to inspect errors and migration statistics first.

## Limitations and Future Improvements

- Support additional legacy formats such as Excel and JSON.
- Add confidence scores and explanations for proposed mappings.
- Improve patient identity matching with human-reviewed conflict resolution.
- Add transactional migration and rollback support.
- Introduce richer audit logs and migration history.
- Add support for larger datasets through batch processing.
- Integrate with real practice-management systems through secure APIs.

## Security and Data Privacy

This repository uses synthetic dental data for demonstration purposes.

- Do not use real patient information with the demo.
- Do not upload protected health information (PHI) to an external LLM.
- API keys must be stored in environment variables.
- AI-generated mappings require human approval.

This project is a prototype and is not HIPAA-certified or intended for production healthcare deployments.

## Author

**Parth Juvatkar**


---

*IsaacBridge demonstrates how agentic AI can assist with legacy data discovery and migration while keeping critical data operations validated, auditable, and under human control.*