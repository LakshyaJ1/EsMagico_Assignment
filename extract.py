"""Extract invoice data. Example: python extract.py invoice.pdf > out.json"""

from invoice_extractor.cli import extract_app, run

if __name__ == "__main__":
    run(extract_app)
