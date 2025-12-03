import json
from extract_pymupdf import extract_text_pymupdf
from extract_pdfminer import extract_text_pdfminer
from parse_statement import parse_statement

PDF_PATH = "StandardBankSample.pdf"

# Run both extractors
pymu_lines = extract_text_pymupdf(PDF_PATH)
pdfminer_lines = extract_text_pdfminer(PDF_PATH)

# Parse both versions
pymu_parsed = parse_statement(pymu_lines)
# pdfminer_parsed = parse_statement(pdfminer_lines)

# Save results
output = {
    "pymupdf_results": pymu_parsed,
    # "pdfminer_results": pdfminer_parsed
}

with open("statement.json", "w") as f:
    json.dump(output, f, indent=2)

print("Extraction complete → statement.json")