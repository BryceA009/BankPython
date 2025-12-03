from pdfminer.high_level import extract_text

def extract_text_pdfminer(path):
    text = extract_text(path)
    return text.split("\n")