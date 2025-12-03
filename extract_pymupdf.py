import fitz

def extract_text_pymupdf(path):
    doc = fitz.open(path)
    lines = []

    for page in doc:
        text = page.get_text()
        lines.extend(text.split("\n"))

    return lines