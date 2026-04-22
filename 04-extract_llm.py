#!/usr/bin/env python3
import os
import glob
import json
import pandas as pd
from pydantic import BaseModel
from ollama import Client
from concurrent.futures import ThreadPoolExecutor, as_completed

# === CONFIG ===
INPUT_DIR      = "histology_reports/text"
OUTPUT_CSV     = "llm_extracted_data-medgemma_27b.csv"
FAILED_LOG     = "llm_failed_requests.jsonl"
PROMPT_FILE    = "LLM_prompt.md"
OLLAMA_MODEL   = "medgemma:27b"   # qwen3.5:latest | qwen3.5:122b
THINK          = False               # whether to use streaming response for better performance on large outputs
MAX_CONCURRENT = 2                    # number of parallel requests
OLLAMA_HOST    = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434") # revert to default ollama host if env var not set


# === STRUCTURED OUTPUT SCHEMA ===

# Pydantic models to define the expected structure of the LLM output for each specimen.
class SpecimenRecord(BaseModel):
    Label: str | None = ""
    Specimen_description: str = ""
    Diagnosis: str = ""
    Bladder_tumor: bool
    Stage: str | None = None
    Grade: str | None = None

# The overall response schema from each report, which contains one or more specimens.
class ReportExtraction(BaseModel):
    specimens: list[SpecimenRecord]

# === CLIENT SETUP ===
client = Client(host=OLLAMA_HOST)


# === CORE PROCESSING ===
def process_file(txt_path, base_prompt):
    """Process a single report file. Returns (filename, df | None, error | None)."""
    filename = os.path.basename(txt_path)

    with open(txt_path, "r", encoding="utf-8") as f:
        report_text = f.read()

    prompt = base_prompt + "\n" + report_text

    try:
        response = client.generate(
            model=OLLAMA_MODEL,
            prompt=prompt,
            format=ReportExtraction.model_json_schema(),
            stream=False,  # disable real-time partial output
            think=THINK,    # use streaming response for better performance on large outputs
            options={
                "num_predict": 8192,  # max outpout token
                "temperature": 0,     # deterministic output
                "num_ctx": 8192,      # max context window
            },
        )

        extraction = ReportExtraction.model_validate_json(response.response)

        rows = []
        for s in extraction.specimens:
            rows.append({
                "Source_File": filename,
                "Label": s.Label,
                "Specimen_description": s.Specimen_description,
                "Diagnosis": s.Diagnosis,
                "Bladder_tumor": s.Bladder_tumor,
                "Stage": s.Stage if s.Bladder_tumor else None,
                "Grade": s.Grade if s.Bladder_tumor else None,
            })

        return filename, pd.DataFrame(rows), None

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
