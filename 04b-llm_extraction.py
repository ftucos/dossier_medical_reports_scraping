#!/usr/bin/env python3
import os
import glob
import json
import pandas as pd
from typing import Literal
from pydantic import BaseModel, Field, model_validator
from ollama import Client
from concurrent.futures import ThreadPoolExecutor, as_completed

# === CONFIG ===
INPUT_DIR      = "histology_reports/text"
OLLAMA_MODEL   = "medgemma:27b"   # qwen3.5:latest | qwen3.5:122b
OUTPUT_CSV     = f"llm_extracted_data-{OLLAMA_MODEL.replace(':', '_')}.csv"
FAILED_LOG     = f"llm_failed_requests-{OLLAMA_MODEL.replace(':', '_')}.jsonl"
PROMPT_FILE    = "LLM_prompt.md"
THINK          = False               # whether to use streaming response for better performance on large outputs
MAX_CONCURRENT = 2                    # number of parallel requests
OLLAMA_HOST    = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434") # revert to default ollama host if env var not set


# === STRUCTURED OUTPUT SCHEMA ===

# Pydantic models to define the expected structure of the LLM output for each specimen.
class SpecimenRecord(BaseModel):
    Label: Literal["NA", "A", "B", "C", "D", "E","F",
                   "G", "H", "I", "J", "K", "L", "M",
                   "N", "O", "P", "Q", "R", "S", "T",
                   "U", "V", "W", "X", "Y", "Z"] = Field(
        ...,
        description=f"Specimen label.",
    )
    Specimen_description: str = Field(
        ...,
        min_length=4,
        description="Mandatory concise description of the submitted specimen. Never empty.",
    )
    Diagnosis: str = Field(
        ...,
        min_length=4,
        description="Mandatory normalized diagnosis in Italian. Never empty.",
    )
    Bladder_tumor: bool = Field(..., description="true if this specimen is a bladder tumor lesion, otherwise false.")
    Stage: Literal["PUNLMP", "pTa", "pT1", "CIS",
                   "displasia", "pT2", "pTa + CIS",
                   "pT1 + CIS", "pT2 + CIS", "pTX",
                   "Not Applicable"] = Field(
        ...,
        description=f"Mandatory bladder tumor stage.",
    )
    Grade: Literal["Low", "High", "High and Low", "G1",
                   "G2", "G3", "G4", "G1/2", "G2/3",
                   "Undefined", "Not Applicable"] = Field(
        ...,
        description=f"Mandatory bladder tumor grade.",
    )

    @model_validator(mode="after")
    def validate_bladder_fields(self):
        if self.Bladder_tumor:
            if self.Stage == "Not Applicable":
                raise ValueError("Stage must not be 'Not Applicable' when Bladder_tumor is true")
            if self.Grade == "Not Applicable":
                raise ValueError("Grade must not be 'Not Applicable' when Bladder_tumor is true")
        else:
            if self.Stage != "Not Applicable":
                raise ValueError("Stage must be 'Not Applicable' when Bladder_tumor is false")
            if self.Grade != "Not Applicable":
                raise ValueError("Grade must be 'Not Applicable' when Bladder_tumor is false")
        return self

# The overall response schema from each report, which contains one or more specimens.
class ReportExtraction(BaseModel):
    specimens: list[SpecimenRecord]

# === CLIENT SETUP ===
client = Client(host=OLLAMA_HOST)


# === CORE PROCESSING ===
def build_messages(base_prompt, report_text, failure_reason=None):

    if failure_reason:
        message_content = f"""Your previous answer failed validation.\n
        Validation error: {failure_reason}\n
        Retry now respeeecting the JSON schema provided.\n
        REPORT_TEXT:\n{report_text}
        """
    else:
        message_content = f"REPORT_TEXT:\n{report_text}"   

    messages = [
        {"role": "system", "content": base_prompt},
        {"role": "user", "content": message_content},
    ]

    return messages

def extract_with_retry(base_prompt, report_text, max_attempts=2):
    """Call the LLM and return a validated ReportExtraction object."""
    failure_reason = None
    last_raw_response = ""

    for _ in range(max_attempts):
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=build_messages(base_prompt, report_text, failure_reason),
            format=ReportExtraction.model_json_schema(),
            stream=False,
            think=THINK,
            options={
                "num_predict": 4096,
                "temperature": 0,
                "repeat_penalty": 1.5,
                "num_ctx": 16384,
            },
        )

        last_raw_response = response.message.content

        try:
            return ReportExtraction.model_validate_json(last_raw_response)
        except Exception as e:
            failure_reason = str(e)

    raise ValueError(
        f"Validation failed after {max_attempts} attempts: "
        f"{failure_reason} | raw_response={last_raw_response}"
    )


def extraction_to_dataframe(extraction, filename):
    """Convert a ReportExtraction object to a DataFrame."""
    rows = [
        {
            "Source_File": filename,
            "Label": s.Label,
            "Specimen_description": s.Specimen_description,
            "Diagnosis": s.Diagnosis,
            "Bladder_tumor": s.Bladder_tumor,
            "Stage": s.Stage,
            "Grade": s.Grade,
        }
        for s in extraction.specimens
    ]
    return pd.DataFrame(rows)


def process_file(txt_path, base_prompt):
    """Process a single report file. Returns (filename, df | None, error | None)."""
    filename = os.path.basename(txt_path)

    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            report_text = f.read()

        extraction = extract_with_retry(base_prompt, report_text)
        df = extraction_to_dataframe(extraction, filename)

        return filename, df, None

    except Exception as e:
        return filename, None, str(e)


# === MAIN ===
def main():
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        base_prompt = f.read().strip()

    txt_files = sorted(glob.glob(os.path.join(INPUT_DIR, "*.txt")))
    print(f"🔍 Found {len(txt_files)} text files. Model: {OLLAMA_MODEL!r} | host: {OLLAMA_HOST} | workers: {MAX_CONCURRENT}")

    # Resume support
    processed_files = set()
    if os.path.exists(OUTPUT_CSV):
        try:
            existing_df = pd.read_csv(OUTPUT_CSV)
            if "Source_File" in existing_df.columns:
                processed_files = set(existing_df["Source_File"].dropna().astype(str).unique())
                print(f"ℹ️  Resuming — {len(processed_files)} files already processed.")
        except Exception as e:
            print(f"⚠️  Could not read existing output CSV for resume: {e}")

    pending = [p for p in txt_files if os.path.basename(p) not in processed_files]
    skipped = len(txt_files) - len(pending)
    if skipped:
        print(f"⏩ Skipping {skipped} already-processed file(s).")

    if not pending:
        print("✅ Nothing to do.")
        return

    success_count = 0
    fail_count = 0

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as executor:
        futures = {
            executor.submit(process_file, p, base_prompt): os.path.basename(p)
            for p in pending
        }

        for future in as_completed(futures):
            filename, df, error = future.result()

            if error:
                print(f"❌ {filename}: {error}")
                with open(FAILED_LOG, "a", encoding="utf-8") as flog:
                    flog.write(json.dumps({"file": filename, "error": error}, ensure_ascii=False) + "\n")
                fail_count += 1
                continue

            if df is None or df.empty:
                print(f"⚠️  {filename}: model returned no specimens.")
                with open(FAILED_LOG, "a", encoding="utf-8") as flog:
                    flog.write(json.dumps({"file": filename, "error": "model returned no specimens"}, ensure_ascii=False) + "\n")
                fail_count += 1
                continue

            write_header = not os.path.exists(OUTPUT_CSV)
            df.to_csv(OUTPUT_CSV, mode="a", index=False, header=write_header)
            print(f"✅ {filename} ({len(df)} specimen(s))")
            success_count += 1

    print("\n=== Processing Summary ===")
    print(f"Total files in directory : {len(txt_files)}")
    print(f"Already processed (skip) : {skipped}")
    print(f"Newly successful         : {success_count}")
    print(f"Failed                   : {fail_count}")
    print(f"📄 Output → {OUTPUT_CSV}")
    print(f"🪵 Failures → {FAILED_LOG}")


if __name__ == "__main__":
    main()
