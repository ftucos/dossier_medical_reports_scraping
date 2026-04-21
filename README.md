# Dossier Medical Reports Scraper

This project provides Python tools for scraping and downloading medical reports (in JSON format) for a list of patients from the Dossier app, downloading the PDFs of exams of interest, and extracting their textual content.

## Setup

Ensure you have the required python dependencies installed:
```bash
pip install requests pandas pdfplumber
```

You also must provide a CSV file named `case_list.csv` containing the list of target patient IDs and Exams IDs. By default, the scripts look for a column named `CC` and `EXAMID`.

## Authentication (Important)

The tool requires your personal authentication code to access the Dossier API securely. **Do not share that code.** It grants access to your active session.

### How to obtain and configure your token

1. Open **Google Chrome** and log in to [http://dossier.apps.ieo.it](http://dossier.apps.ieo.it)
2. Open the Chrome **Developer Tools** (Right-click -> Inspect, or `Ctrl+Shift+I` / `Cmd+Option+I` on Mac) and go to the **Network** tab.
3. In the Dossier web app, search for a patient CC in the `Codice Paziente` search field.
4. Watch the Network tab and wait for the specific request (usually `medicalReports?id=CC12345678`) to appear.
5. Right-click on that request and select **Copy** -> **Copy as cURL**.

The copied cURL payload will look something like this:

```bash
curl 'http://dossier.apps.ieo.it/api/v1/medicalReports?id=CC12345678' \
  -H 'Accept: */*' \
  -H 'Accept-Language: en-IT,en;q=0.9,it-IT;q=0.8,it;q=0.7,en-GB;q=0.6,en-US;q=0.5' \
  -H 'Connection: keep-alive' \
  -H 'Content-Type: application/json' \
...
  -H 'Referer: http://dossier.apps.ieo.it/CC12345678' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36' \
  -H 'authorization: Bearer XXXXXX' \
  --insecure
```

6. Locate the `authorization` header in the copied text: `-H 'authorization: Bearer XXXXXX'`.
7. Copy **only the authorization code** (the part *after* `Bearer `).
8. Create a new file named `.auth_token` in the root of this project folder and paste the copied code directly into it. 
9. Ensure `.auth_token` is included in your `.gitignore` to prevent uploading your session credentials.

## Usage

Once `case_list.csv` and `.auth_token` are in place, the workflow is split into two steps:

### Step 1: Scrape Medical Reports (JSON)

Run the first script to download medical reports for the patients in `case_list.csv`:

```bash
python 01-scrape_dossier_medical_reports.py
```

The script will automatically parse the `case_list.csv` file and download the corresponding JSON reports into the designated output directory `dossier_medical_reports/`.

### Step 2: Download PDF Reports

To download the specific PDFs for the medical reports, ensure your `case_list.csv` file also includes an `EXAMID` column for the target exams. Run the second script:

```bash
python 02-download_pdfs.py
```

This script will parse the downloaded JSON files from Step 1, identify the correct PDF URLs matching the `EXAMID`, and save them to the `histology_reports/pdf/` directory with the naming convention `<CC>_<EXAMID>.pdf`.

### Step 3: Extract Text from PDFs

Use the third script to extract the text content from all the downloaded histology PDFs using `pdfplumber`:

```bash
python 03-extract_text.py
```

This script will read all `.pdf` files from the `histology_reports/pdf/` directory, parse and extract the text from each page, and save the resulting string as a `.txt` file inside the `histology_reports/text/` directory.
