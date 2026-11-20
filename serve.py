"""Start the API and web UI on http://127.0.0.1:8000"""

from invoice_extractor.cli import run, serve_app

if __name__ == "__main__":
    run(serve_app)
