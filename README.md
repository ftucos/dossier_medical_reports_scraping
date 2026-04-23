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

The fourth script, `04-extract_llm.py`, sends each extracted report text to a local Ollama server and writes the structured output to a CSV file. In this project, this step is designed to run on an HPC with a GPU through two dedicated Slurm scripts:

- `04a-start_ollama_server.sbatch`
- `04b-llm_extraction.sbatch`

The execution model is intentionally two-stage:

1. Submit `04a-start_ollama_server.sbatch` to start `ollama serve` on a GPU node.
2. Wait for the job to start, then identify the exact node assigned to that Ollama server job.
3. Edit `04b-llm_extraction.sbatch` so that `#SBATCH --nodelist=...` matches that same node.
4. Submit `04b-llm_extraction.sbatch` so that `04b-llm_extraction.py` runs on the same host and can reach the local Ollama endpoint.

This same-node requirement is important because both scripts are configured to use:

```bash
export OLLAMA_HOST=127.0.0.1:11437
```

That address only works if the extraction job is scheduled onto the very same node where the Ollama server is running.

Submit the server first:

```bash
sbatch 04a-start_ollama_server.sbatch
```

Check where it landed:

```bash
squeue -u $USER
```

Once the Ollama server job is running, note the assigned node name and update `04-submit_llm_job.sbatch` accordingly. For example:

```bash
#SBATCH --nodelist=gpu01
```

Then submit the extraction job:

```bash
sbatch 04b-llm_extraction.sbatch
```

What the two Slurm scripts currently do:

- `04a-start_ollama_server.sbatch` requests `1` GPU, loads `CUDA/12.6.0`, sets the local Ollama binary path, points `OLLAMA_MODELS` to the shared model directory, disables cloud features with `OLLAMA_NO_CLOUD=1`, binds Ollama to `127.0.0.1:11437`, and runs `ollama serve`.
- `04a-start_ollama_server.sbatch` requests a GPU job on a specific `--nodelist`, reuses the same Ollama environment variables, activates the `ollama` mamba environment, and runs `python3 04-extract_llm.py`.
