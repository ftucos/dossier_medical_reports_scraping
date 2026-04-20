#!/usr/bin/env python3
import pandas as pd
import requests
import os
import time

# === CONFIG ===
CSV_PATH = "case_list.csv"   # CSV containing CC IDs
ID_COLUMN = "CC"             # column name in CSV
TOKEN_FILE  = ".auth_token"  # single line: your Bearer token
OUTPUT_DIR = "dossier_medical_reports"
BASE_URL = "http://dossier.apps.ieo.it/api/v1/medicalReports?id="

# === LOAD TOKEN ===
if not os.path.exists(TOKEN_FILE):
    raise FileNotFoundError(f"{TOKEN_FILE} not found")

with open(TOKEN_FILE, "r") as f:
    TOKEN = f.read().strip()

if not TOKEN:
    raise ValueError("Token file is empty")

HEADERS = {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {TOKEN}",
    "User-Agent": "Mozilla/5.0",
    "Referer": "http://dossier.apps.ieo.it/"
}

# === SETUP ===
os.makedirs(OUTPUT_DIR, exist_ok=True)

df = pd.read_csv(CSV_PATH)

# === LOOP ===
for cc in df[ID_COLUMN].dropna().unique():
    cc = cc.strip()
    url = f"{BASE_URL}{cc}"

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            verify=False  # equivalent to --insecure
        )

        if response.status_code == 200:
            output_path = os.path.join(OUTPUT_DIR, f"{cc}.json")
            with open(output_path, "w") as f:
                f.write(response.text)

            print(f"✅ Saved {cc}")
        else:
            print(f"⚠️ Failed {cc} - Status: {response.status_code}")

    except Exception as e:
        print(f"❌ Error with {cc}: {e}")

    time.sleep(0.3)  # avoid hammering the server