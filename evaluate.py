"""Run the eval harness on the labelled documents and print the results table."""

from invoice_extractor.cli import eval_app, run

if __name__ == "__main__":
    run(eval_app)
