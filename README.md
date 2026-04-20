# Dossier Medical Reports Scraper

This project provides a Python tool for scraping and downloading medical reports (in JSON format) for a list of patients from the Dossier app. 

## Setup

First, ensure you have the required dependencies installed:
```bash
pip install requests pandas
```

You also must provide a CSV file named `case_list.csv` containing the list of target patient IDs. By default, the scripts look for a column named `CC`.

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

Once `case_list.csv` and `.auth_token` are in place, simply run the Python scraper script. For example:

```bash
python scrape_dossier_medical_reports.py
```

The script will automatically parse the `case_list.csv` file and download the corresponding JSON reports into the designated output directory `dossier_medical_reports/`.
