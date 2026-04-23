# Dossier Medical Reports Scraper

This project provides Python tools for scraping and downloading medical reports (in JSON format) for a list of patients from the Dossier app, downloading the PDFs of exams of interest, extracting their textual content, and running an LLM-based structured extraction step.

## Setup

Ensure you have the required python dependencies installed:
```bash
pip install requests pandas pdfplumber pydantic ollama
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
7. Copy **only the authorization code** (the part after `Bearer `).
8. Create a new file named `.auth_token` in the root of this project folder and paste the copied code directly into it. 
9. Note that the **authorization token expires** and must be refreshed after each session.

## Usage

Once `case_list.csv` and `.auth_token` are in place, the workflow is split into four steps:

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

### Step 4: Extract Structured Data with the LLM

The fourth step sends each extracted report text to a local Ollama server and writes the structured output to a CSV file. The `04-llm_extraction.sbatch` script submits a Slurm job to a gpu node that starts the Ollama server in background and runs the extraction script `llm_extraction.py` in the same batch job.

Submit the job with:

```bash
sbatch 04-llm_extraction.sbatch
```

By default, `llm_extraction.py`:

- reads `.txt` files from `histology_reports/text/`
- loads the extraction prompt from `LLM_prompt.md`
- queries the Ollama model `medgemma:27b`
- writes successful structured outputs to `llm_extracted_data-medgemma_27b.csv`
- appends failed cases to `llm_failed_requests-medgemma_27b.jsonl`
- supports resume behavior by skipping files already present in the output CSV

#### Troubleshooting LLM output

The extraction script exposes a few important generation settings in `llm_extraction.py`:

- `THINK`: enables thinking mode
- `MAX_OUT_TOKEN`: maximum number of generated output tokens
- `repeat_penalty`: repetition control, currently set to `1.5`

Thinking models usually require more output tokens, so if you enable `THINK = True`, you may also need to increase `MAX_OUT_TOKEN`.

If you see an error like:

```text
Validation failed after 2 attempts: 1 validation error for ReportExtraction
  Invalid JSON: EOF while parsing a value
```

the most common causes are:

- **the model ran out of output tokens before finishing the JSON response**. You can usually confirm it in `llm_failed_requests-{model}.jsonl`. You will usually see under `raw_response`. either no output at all, or a partial but otherwise correct-looking JSON object that stops before completion. In which case **increasing `MAX_OUT_TOKEN` musually helps**.
- **the model started stuttering** and repeating the same text multiple times, which can also prevent valid JSON completion. You can usually confirm it by the presence of repeated text patterns such as `High grade. High grade. High grade....`  under `raw_response`. In the stuttering case, **increasing `repeat_penalty` may help**. Be careful though, people often warn against pushing `repeat_penalty` much above `1.5`, because too high a value can hurt output quality.
