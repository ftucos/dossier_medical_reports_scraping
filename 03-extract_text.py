#!/usr/bin/env python3
import os
import glob
import pdfplumber

# === CONFIG ===
INPUT_DIR = "histology_reports/pdf"
OUTPUT_DIR = "histology_reports/text"

def remove_watermark(page):
    filtered_chars = [
        ch for ch in page.chars
        if ch["size"] <= 60
    ]
    return filtered_chars

def main():
    if not os.path.exists(INPUT_DIR):
        print(f"❌ Input directory '{INPUT_DIR}' does not exist.")
        return

    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Find all PDFs in the input directory
    pdf_files = glob.glob(os.path.join(INPUT_DIR, "*.pdf"))
    
    if not pdf_files:
        print(f"⚠️ No PDF files found in '{INPUT_DIR}'.")
        return

    print(f"🔍 Found {len(pdf_files)} PDF files. Starting text extraction...")

    success_count = 0
    fail_count = 0

    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        output_txt_path = os.path.join(OUTPUT_DIR, filename.replace(".pdf", ".txt"))

        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    #text = page.extract_text()
                    filtered_chars = remove_watermark(page)
                    text = pdfplumber.utils.extract_text(filtered_chars)

                    if text:
                        full_text += text + "\n"
            
            if not full_text:
                raise Exception(f"No text found in {filename}")
                
            # Write to the output .txt file
            with open(output_txt_path, "w", encoding="utf-8") as f:
                f.write(full_text)

            print(f"✅ Saved text for {filename}")
            success_count += 1
            
        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")
            fail_count += 1

    print("\n=== Extraction Summary ===")
    print(f"Total processed: {len(pdf_files)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {fail_count}")

if __name__ == "__main__":
    main()
