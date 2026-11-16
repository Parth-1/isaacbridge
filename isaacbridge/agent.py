"""Gemini-powered tool-using agent for proposing legacy CSV column mappings.

The agent can inspect synthetic CSV schemas and sample rows, then propose a
mapping to IsaacBridge's canonical fields. It never writes to the database.
A human must review the saved JSON plan and explicitly approve its use.
"""

import csv
import json
import os
from pathlib import Path

CANONICAL_FIELDS = {
    "patients": ["patient_id", "first_name", "last_name", "dob", "phone", "email", "insurance_provider"],
    "appointments": ["appointment_id", "patient_id", "appointment_date", "provider", "procedure", "status"],
    "invoices": ["invoice_id", "patient_id", "invoice_date", "amount", "status"],
}


def inspect_source_file(source_dir, kind):
    """Agent tool: inspect one allowed CSV and return headers plus up to 3 rows."""
    if kind not in CANONICAL_FIELDS:
        raise ValueError(f"Unsupported source file type: {kind}")
    path = Path(source_dir) / f"{kind}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return {
            "file": path.name,
            "columns": reader.fieldnames or [],
            "sample_rows": [
                {key: value for key, value in row.items() if key is not None}
                for _, row in zip(range(3), reader)
            ],
        }


def _validate_proposal(proposal, source_dir):
    """Reject invented source columns and mappings that omit required fields."""
    mappings = proposal.get("mappings")
    if not isinstance(mappings, dict):
        raise ValueError("The AI response did not contain a mappings object")

    validated = {}
    for kind, targets in CANONICAL_FIELDS.items():
        if kind not in mappings or not isinstance(mappings[kind], dict):
            raise ValueError(f"AI response is missing mappings for {kind}")
        source_info = inspect_source_file(source_dir, kind)
        available = set(source_info["columns"])
        current = mappings[kind]
        required = {
            "patients": {"patient_id", "first_name", "last_name", "dob"},
            "appointments": {"appointment_id", "patient_id", "appointment_date"},
            "invoices": {"invoice_id", "patient_id", "invoice_date", "amount"},
        }[kind]
        missing = required - set(current)
        if missing:
            raise ValueError(f"AI mapping for {kind} omitted required fields: {sorted(missing)}")
        clean = {}
        for target, source in current.items():
            if target not in targets:
                raise ValueError(f"Unknown canonical field for {kind}: {target}")
            if source is not None and source not in available:
                raise ValueError(f"AI invented source column {source!r} for {kind}")
            if source is not None:
                clean[target] = source
        validated[kind] = clean
    proposal["mappings"] = validated
    return proposal


def run_schema_agent(source_dir, output_path, model="gemini-3.5-flash-lite"):
    """Run a Gemini tool-calling agent and save its proposed mapping plan.

    The Google GenAI SDK automatically executes the Python inspection function
    when Gemini requests it. Only this read-only function is exposed as a tool.
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "Google GenAI SDK missing. Install dependencies with: pip install -r requirements.txt"
        ) from exc

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Gemini API key not found. Set GEMINI_API_KEY (or GOOGLE_API_KEY) in your environment."
        )

    source_dir = Path(source_dir)

    # This is the only tool Gemini can call. It reads at most three sample rows
    # from one of the three expected CSV files and cannot modify any data.
    def inspect_csv(kind: str) -> dict:
        """Inspect a source CSV by type: patients, appointments, or invoices.

        Returns its exact column names and up to three sample rows. Use this
        tool to inspect each of the three source files before proposing mappings.
        """
        return inspect_source_file(source_dir, kind)

    system_instruction = (
        "You are a careful data-migration planning agent. You MUST call the "
        "inspect_csv tool for patients, appointments, and invoices before proposing "
        "any mappings. Map source columns to the exact canonical field names in "
        "the user request. Use sample values to resolve reasonable aliases, but "
        "never invent a source column. If a field cannot be mapped, explain the "
        "uncertainty in notes. Do not merge patients, infer missing patient "
        "identities, or modify data. Return only valid JSON with keys mappings "
        "and notes. mappings must contain all three file kinds and map canonical "
        "field names to exact source column names. For optional fields that do "
        "not exist, use null or omit them. Required fields must be mapped."
    )
    prompt = (
        "Inspect all three source CSV files using your inspect_csv tool and "
        "propose column mappings. Canonical fields: "
        f"{json.dumps(CANONICAL_FIELDS)}. "
        'Return JSON only: {"mappings": {"patients": {}, "appointments": {}, '
        '"invoices": {}}, "notes": []}.'
    )

    client = genai.Client(api_key=api_key)

    try:
        chat = client.chats.create(
            model=model,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=[inspect_csv],
                temperature=0.1,
            ),
        )

        print("Connecting to Gemini...")
        response = chat.send_message(prompt)
        print("Gemini response received.")

    except Exception as exc:
        raise RuntimeError(
            "Gemini request failed. Check your API key, model availability, "
            "internet connection, and Google AI Studio quota. "
            f"Original error: {exc}"
        ) from exc
    content = response.text
    if not content:
        raise RuntimeError("Gemini returned no final mapping proposal")
    proposal = json.loads(content)
    proposal = _validate_proposal(proposal, source_dir)
    proposal["model"] = model
    proposal["provider"] = "Google Gemini"
    proposal["approval_required"] = True
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(proposal, indent=2), encoding="utf-8")
    return proposal


def load_approved_mapping(mapping_path):
    """Load a reviewed mapping plan and verify required fields before import."""
    data = json.loads(Path(mapping_path).read_text(encoding="utf-8"))
    mappings = data.get("mappings", {})
    required = {
        "patients": {"patient_id", "first_name", "last_name", "dob"},
        "appointments": {"appointment_id", "patient_id", "appointment_date"},
        "invoices": {"invoice_id", "patient_id", "invoice_date", "amount"},
    }
    for kind, fields in required.items():
        missing = fields - set(mappings.get(kind, {}))
        if missing:
            raise ValueError(f"Mapping file is missing required {kind} fields: {sorted(missing)}")
    return mappings
