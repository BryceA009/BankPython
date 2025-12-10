import fitz

def extract_text_pymupdf(path):
    doc = fitz.open(path)
    lines = []

    for page in doc:
        page_number = page.number  # <-- this guy matters
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if "lines" not in block:
                continue

            for line in block["lines"]:
                # Combine all span text into one full line
                full_text = " ".join(span["text"] for span in line["spans"]).strip()
                if not full_text:
                    continue

                x0, y0, x1, y1 = line["bbox"]

                lines.append({
                    "text": full_text,
                    "x": x0,
                    "y": y0,
                    "page_number": page_number + 1 
                })

    return lines


def extract_text_pymupdf_original(path):
    doc = fitz.open(path)
    lines = []

    for page in doc:
        text = page.get_text()
        lines.extend(text.split("\n"))

    return lines