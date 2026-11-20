"""Command-line entry points.

    python extract.py invoice.pdf > out.json          # one file -> schema-exact JSON on stdout
    python extract.py data/labelled data/unlabelled --out outputs
    python evaluate.py                                 # eval on the 10 labelled documents
    python serve.py                                    # API + web UI on http://127.0.0.1:8000

Exit codes for ``extract`` on a single file: 0 ok, 3 extracted but flagged for review
(the JSON is still written), 1 the document could not be processed.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import replace
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from .batch import BatchItem, collect_inputs, run_batch, write_outputs
from .config import PROJECT_ROOT, PROMPT_VERSION, InputMode, Settings
from .errors import PipelineError
from .pipeline import ExtractionOutcome, InvoicePipeline

stderr = Console(stderr=True)

EXIT_OK, EXIT_FAILED, EXIT_NEEDS_REVIEW = 0, 1, 3

ModelOption = Annotated[
    str | None,
    typer.Option(help="Gemini model id (default: INVOICE_MODEL or gemini-3.5-flash-lite)."),
]
ModeOption = Annotated[
    InputMode | None, typer.Option("--mode", help="What the model sees: hybrid, images or pdf.")
]
ThinkingOption = Annotated[
    str | None, typer.Option(help="Thinking level: minimal, low, medium, high.")
]
CacheOption = Annotated[
    bool,
    typer.Option("--cache/--no-cache", help="Reuse identical earlier API responses from .cache/."),
]
VerboseOption = Annotated[
    bool, typer.Option("--verbose", "-v", help="Log pipeline steps to stderr.")
]


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(message)s",
        handlers=[RichHandler(console=stderr, show_path=False)],
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("google_genai").setLevel(logging.WARNING)


def _settings(
    model: str | None, mode: InputMode | None, thinking: str | None, cache: bool
) -> Settings:
    settings = Settings.from_env().with_overrides(
        model=model, input_mode=mode, thinking_level=thinking
    )
    return settings if cache else replace(settings, cache_dir=None)


# --------------------------------------------------------------------------------------
# extract
# --------------------------------------------------------------------------------------

extract_app = typer.Typer(add_completion=False, help="Extract invoice data as schema-valid JSON.")


@extract_app.command()
def extract(
    paths: Annotated[
        list[Path], typer.Argument(help="PDF/image files or directories.", exists=True)
    ],
    out: Annotated[
        Path | None,
        typer.Option("--out", "-o", help="Write <name>.json files here instead of stdout."),
    ] = None,
    meta: Annotated[
        bool,
        typer.Option(
            "--meta", help="Single-file mode: print {result, meta} instead of the bare result."
        ),
    ] = False,
    workers: Annotated[int, typer.Option(help="Parallel documents in batch mode.")] = 4,
    model: ModelOption = None,
    mode: ModeOption = None,
    thinking: ThinkingOption = None,
    cache: CacheOption = True,
    verbose: VerboseOption = False,
) -> None:
    _setup_logging(verbose)
    pipeline = InvoicePipeline(_settings(model, mode, thinking, cache))
    files = collect_inputs(paths)

    if out is None and len(files) == 1 and files[0].is_file():
        raise typer.Exit(_extract_one(pipeline, files[0], meta))

    out = out or PROJECT_ROOT / "outputs"
    with stderr.status(f"Extracting {len(files)} documents with {pipeline.settings.model}…"):
        items = run_batch(pipeline, files, workers=workers, on_done=lambda item: _log_item(item))
    summary = write_outputs(items, out)
    _print_batch_summary(items, summary, out)
    raise typer.Exit(EXIT_FAILED if summary["errors"] else EXIT_OK)


def _extract_one(pipeline: InvoicePipeline, path: Path, with_meta: bool) -> int:
    try:
        outcome = pipeline.extract_path(path)
    except PipelineError as exc:
        stderr.print(f"[red]error[/red] {path.name}: {exc.code}: {exc.message}")
        if with_meta:
            print(
                json.dumps(
                    {"result": None, "meta": {"status": "error", "error": exc.to_dict()}}, indent=2
                )
            )
        return EXIT_FAILED

    payload = (
        {"result": outcome.output(), "meta": outcome.meta()} if with_meta else outcome.output()
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    usage = outcome.usage
    stderr.print(
        f"{path.name}: [bold]{outcome.status}[/bold] · confidence {outcome.review.confidence:.2f} · "
        f"{usage.input_tokens} in / {usage.billed_output_tokens} out tokens · ${usage.cost_usd:.5f} · "
        f"{outcome.latency_ms / 1000:.1f}s"
    )
    for reason in outcome.review.reasons:
        stderr.print(f"  [yellow]review:[/yellow] {reason}")
    return EXIT_NEEDS_REVIEW if outcome.review.needs_review else EXIT_OK


def _log_item(item: BatchItem) -> None:
    if item.outcome:
        colour = "yellow" if item.outcome.review.needs_review else "green"
        stderr.print(f"  [{colour}]{item.outcome.status:12s}[/{colour}] {item.path.name}")
    else:
        stderr.print(f"  [red]{'error':12s}[/red] {item.path.name}: {item.error.message}")  # type: ignore[union-attr]


def _print_batch_summary(items: list[BatchItem], summary: dict, out: Path) -> None:
    table = Table(title=f"Wrote {summary['succeeded']} results to {out}", title_justify="left")
    for column in ("document", "status", "invoice?", "confidence", "cost", "time"):
        table.add_column(column)
    for item in items:
        if item.outcome:
            o = item.outcome
            table.add_row(
                item.path.name,
                o.status,
                "yes" if o.result.is_invoice else "no",
                f"{o.review.confidence:.2f}",
                f"${o.usage.cost_usd:.5f}",
                f"{o.latency_ms / 1000:.1f}s",
            )
        else:
            table.add_row(item.path.name, f"[red]{item.error.code}[/red]", "-", "-", "-", "-")  # type: ignore[union-attr]
    stderr.print(table)
    usage = summary["usage"]
    stderr.print(
        f"{summary['needs_review']} flagged for review · {summary['errors']} failed · "
        f"total ${usage['cost_usd']:.4f} (avg ${summary['avg_cost_usd']:.5f}/doc)"
    )


# --------------------------------------------------------------------------------------
# evaluate
# --------------------------------------------------------------------------------------

eval_app = typer.Typer(add_completion=False, help="Score the extractor on the labelled documents.")


@eval_app.command()
def evaluate(
    labelled: Annotated[
        Path, typer.Option(help="Folder with Lnn.pdf/jpg and Lnn.json ground truth.")
    ] = PROJECT_ROOT / "data" / "labelled",
    predictions: Annotated[
        Path | None,
        typer.Option(help="Score saved outputs from this folder instead of calling the API."),
    ] = None,
    save: Annotated[
        Path, typer.Option(help="Where to write the JSON and Markdown report.")
    ] = PROJECT_ROOT / "eval_results",
    tag: Annotated[
        str | None, typer.Option(help="Name for the saved report (default: model name).")
    ] = None,
    workers: Annotated[int, typer.Option(help="Parallel documents.")] = 4,
    perturb: Annotated[
        str | None,
        typer.Option(
            help="Stress test: degrade every document first "
            "(rotate90, rotate270, rotate180, skew7, blur, lowres, fax, photo)."
        ),
    ] = None,
    no_orientation_fix: Annotated[
        bool, typer.Option("--no-orientation-fix", help="Ablation: skip sideways-page correction.")
    ] = False,
    no_second_read: Annotated[
        bool, typer.Option("--no-second-read", help="Ablation: never verify doubtful reads.")
    ] = False,
    second_read_model: Annotated[
        str | None,
        typer.Option(help="Verify doubtful reads with this model instead of the primary."),
    ] = None,
    model: ModelOption = None,
    mode: ModeOption = None,
    thinking: ThinkingOption = None,
    cache: CacheOption = True,
    verbose: VerboseOption = False,
) -> None:
    from .evaluation.harness import build_report, from_batch, from_predictions
    from .evaluation.perturb import PERTURBATIONS, perturbed_pdf
    from .evaluation.render import print_report, to_markdown

    if perturb is not None and perturb not in PERTURBATIONS:
        stderr.print(
            f"[red]Unknown perturbation '{perturb}'.[/red] Choose from {', '.join(PERTURBATIONS)}."
        )
        raise typer.Exit(EXIT_FAILED)

    _setup_logging(verbose)
    if not labelled.exists():
        stderr.print(f"[red]{labelled} not found.[/red] Run: uv run python scripts/fetch_data.py")
        raise typer.Exit(EXIT_FAILED)

    documents = [p for p in collect_inputs([labelled]) if (labelled / f"{p.stem}.json").exists()]
    settings = _settings(model, mode, thinking, cache)
    if no_orientation_fix:
        settings = replace(settings, fix_orientation=False)
    if no_second_read:
        settings = replace(settings, second_read=False)
    if second_read_model:
        settings = replace(settings, second_read_model=second_read_model)

    if predictions is not None:
        docs = from_predictions(predictions, labelled, documents)
        source = f"saved predictions in {predictions}"
    else:
        pipeline = InvoicePipeline(settings)

        def degraded(path: Path) -> ExtractionOutcome:
            return pipeline.extract_bytes(
                perturbed_pdf(path, perturb), f"{path.stem}-{perturb}.pdf"
            )  # type: ignore[arg-type]

        label = f" ({perturb})" if perturb else ""
        with stderr.status(
            f"Running {settings.model} on {len(documents)} labelled documents{label}…"
        ):
            items = run_batch(
                pipeline,
                documents,
                workers=workers,
                on_done=_log_item,
                extract=degraded if perturb else None,
            )
        docs = from_batch(items, labelled)
        source = "live run" + label

    report = build_report(
        docs,
        {
            "model": settings.model,
            "input_mode": settings.input_mode.value,
            "thinking_level": settings.thinking_level,
            "prompt_version": PROMPT_VERSION,
            "documents": len(docs),
            "source": source,
            "perturbation": perturb,
            "orientation_fix": settings.fix_orientation,
            "second_read": settings.second_read,
            "second_read_model": settings.second_read_model,
        },
    )
    print_report(report, Console())

    save.mkdir(parents=True, exist_ok=True)
    name = tag or settings.model
    (save / f"{name}.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (save / f"{name}.md").write_text(to_markdown(report), encoding="utf-8")
    stderr.print(f"Saved {save / (name + '.json')} and .md")


# --------------------------------------------------------------------------------------
# serve
# --------------------------------------------------------------------------------------

serve_app = typer.Typer(add_completion=False, help="Run the HTTP API and the web UI.")


@serve_app.command()
def serve(
    host: Annotated[str, typer.Option()] = "127.0.0.1",
    port: Annotated[int, typer.Option()] = 8000,
    reload: Annotated[
        bool, typer.Option(help="Auto-reload on code changes (development).")
    ] = False,
) -> None:
    import uvicorn

    stderr.print(f"Invoice extractor UI on [link]http://{host}:{port}[/link]")
    uvicorn.run("invoice_extractor.api.app:app", host=host, port=port, reload=reload)


def run(app: typer.Typer) -> None:
    # Windows consoles default to a legacy code page; force UTF-8 for ₹, €, ✓.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    app()


app = extract_app
