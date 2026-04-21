#!/usr/bin/env python3
import os
import json
import time
import pandas as pd
import requests

# === CONFIG ===
CSV_PATH = "case_list.csv"    # CSV containing CC and Exam IDs
CSV_CC_COLUMN = "CC"          # Patient ID column name in CSV  
CSV_CODE_COLUMN = "EXAMID"    # Exam ID column name in CSV

JSON_DIR = "dossier_medical_reports"
PDF_DIR = "histology_reports/pdf"

# === FUNCTIONS ===
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_pdf_url(entries, exam_id):
    exam_id = str(exam_id).strip()

    for entry in entries:
        if str(entry.get("nEsame", "")).strip() == exam_id:
            for doc in entry.get("documents", []):
                if doc.get("type", "").lower() == "pdf":
                    return doc.get("url")
    return None


def download_pdf(url, output_path):
    r = requests.get(url, verify=False, stream=True)

    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}")

    with open(output_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                
# === MAIN ===
def main():
    os.makedirs(PDF_DIR, exist_ok=True)
    df = pd.read_csv(CSV_PATH, dtype=str)
    
    success_count = 0
    fail_count = 0
    
    for _, row in df.iterrows():
        cc = str(row[CSV_CC_COLUMN]).strip()
        exam_id = str(row[CSV_CODE_COLUMN]).strip()

        json_path = os.path.join(JSON_DIR, f"{cc}.json")

        if not os.path.exists(json_path):
            print(f"⚠️ Missing JSON for {cc}")
            fail_count += 1
            continue

        try:
            entries = load_json(json_path)
        except Exception as e:
            print(f"❌ Error reading {cc}: {e}")
            fail_count += 1
            continue

        pdf_url = find_pdf_url(entries, exam_id)

        if not pdf_url:
            print(f"⚠️ No match for {cc} / {exam_id}")
            continue

        output_file = os.path.join(PDF_DIR, f"{cc}_{exam_id}.pdf")

        try:
            download_pdf(pdf_url, output_file)
            print(f"✅ Saved {cc}_{exam_id}.pdf")
            success_count += 1
        except Exception as e:
            print(f"❌ Failed {cc} / {exam_id}: {e}")
            fail_count += 1

        time.sleep(0.2)
    
    print("\n=== Download Summary ===")
    print(f"Total processed: {len(df)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {fail_count}")

if __name__ == "__main__":
    main()