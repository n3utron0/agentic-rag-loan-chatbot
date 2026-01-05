# rag/pdf_extraction.py
import os
import json
import pdfplumber


# with pdfplumber.open("data/pdfs/pricing-grid.pdf") as pdf: #(Me trying to learn)
#     first_page = pdf.pages[0]
#     print(first_page)
#     print(first_page.extract_tables())
#     print(first_page.extract_text())


# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
PDF_FOLDER = "data/pdfs"
OUTPUT_JSON = "data/pdf_extraction/raw_data.json"

# ------------------------------------------------------------
# Helper to clean table format
# Converts table rows (list of lists) into readable lines of text
# ------------------------------------------------------------
def table_to_string(table):
    """Convert a pdfplumber table (list of rows) into clean text."""
    lines = []
    for row in table:
        # Replace None with empty string and join columns with ' | '
        clean_row = [col if col is not None else "" for col in row]
        line = " | ".join(clean_row)
        lines.append(line)
    return "\n".join(lines)


# ------------------------------------------------------------
# Main extraction function
# ------------------------------------------------------------
def extract_all_pdfs(pdf_folder):
    """
    Loops through all PDFs in the folder
    Extracts text and tables page-by-page
    Returns a list of dicts, one dict per PDF:
    {
      "pdf_name": "...",
      "pages": [
          {"page_num": 1, "text": "...", "tables": ["...", "..."]},
          ...
      ]
    }
    """
    all_pdfs_data = []

    for filename in os.listdir(pdf_folder):
        if not filename.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(pdf_folder, filename)
        print(f"Processing: {filename}")

        pdf_data = {
            "pdf_name": filename,
            "pages": []
        }
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""  # Sometimes None
                    
                    raw_tables = page.extract_tables()
                    tables_as_text = []

                    if raw_tables:
                        for table in raw_tables:
                            table_text = table_to_string(table)
                            tables_as_text.append(table_text)

                    pdf_data["pages"].append({
                        "page_num": i,
                        "text": text,
                        "tables": tables_as_text
                    })
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue

        all_pdfs_data.append(pdf_data)

    return all_pdfs_data


# ------------------------------------------------------------
# Save extracted data into JSON
# ------------------------------------------------------------
def save_json(data, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"\nSaved extracted data to: {output_path}")


# ------------------------------------------------------------
# Main Script Execution
# ------------------------------------------------------------
if __name__ == "__main__":
    extracted = extract_all_pdfs(PDF_FOLDER)
    save_json(extracted, OUTPUT_JSON)

