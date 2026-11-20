"""Run the experiment matrix behind REPORT.md and build a comparison table.

    uv run python scripts/run_experiments.py              # everything (~$0.50 on Flash-Lite)
    uv run python scripts/run_experiments.py main models  # only some groups
    uv run python scripts/run_experiments.py --summary    # just rebuild the table

Each experiment is one ``evaluate.py`` invocation; reports land in
``eval_results/experiments/<tag>.{json,md}``. The fallback model is disabled so a
comparison never silently mixes two models.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "eval_results" / "experiments"

PRIMARY = "gemini-3.5-flash-lite"
# Free-tier keys allow ~15 requests/minute; one document at a time stays under it.
WORKERS = os.getenv("EXPERIMENT_WORKERS", "1")

EXPERIMENTS: dict[str, list[tuple[str, list[str]]]] = {
    "main": [("main", ["--model", PRIMARY])],
    "repeat": [
        ("repeat-2", ["--model", PRIMARY, "--no-cache"]),
        ("repeat-3", ["--model", PRIMARY, "--no-cache"]),
    ],
    "models": [("model-3.1-flash-lite", ["--model", "gemini-3.1-flash-lite"])],
    "modes": [
        ("mode-images", ["--model", PRIMARY, "--mode", "images"]),
        ("mode-pdf", ["--model", PRIMARY, "--mode", "pdf"]),
    ],
    "stress": [
        (f"stress-{kind}", ["--model", PRIMARY, "--perturb", kind])
        for kind in (
            "rotate90",
            "rotate270",
            "rotate180",
            "skew7",
            "blur",
            "lowres",
            "fax",
            "photo",
        )
    ],
    "ablations": [
        (
            "ablation-rotate90-nofix",
            ["--model", PRIMARY, "--perturb", "rotate90", "--no-orientation-fix"],
        ),
        *[
            (
                f"ablation-{kind}-no-second-read",
                ["--model", PRIMARY, "--perturb", kind, "--no-second-read"],
            )
            for kind in ("blur", "lowres", "fax", "photo")
        ],
        *[
            (
                f"ablation-{kind}-same-model-second-read",
                ["--model", PRIMARY, "--perturb", kind, "--second-read-model", PRIMARY],
            )
            for kind in ("blur", "lowres", "fax")
        ],
    ],
}


def run(tag: str, args: list[str]) -> None:
    print(f"\n=== {tag}: evaluate.py {' '.join(args)}", flush=True)
    env = {
        **os.environ,
        "INVOICE_FALLBACK_MODEL": "none",
        "PYTHONIOENCODING": "utf-8",
        "COLUMNS": "200",
    }
    command = [
        sys.executable,
        str(ROOT / "evaluate.py"),
        "--save",
        str(OUT),
        "--tag",
        tag,
        "--workers",
        WORKERS,
        *args,
    ]
    result = subprocess.run(command, cwd=ROOT, env=env, check=False)
    if result.returncode:
        print(f"!!! {tag} exited with {result.returncode}", flush=True)


def summarize() -> str:
    rows = []
    for path in sorted(OUT.glob("*.json")):
        report = json.loads(path.read_text(encoding="utf-8"))
        accuracy, review, cost = report["field_accuracy"], report["review"], report["cost"]
        failed = sum(1 for doc in report["documents"] if doc["error"])
        rows.append(
            "| {tag} | {model} | {mode} | {perturb} | {perfect} | {fields} | {lines} | {total} | {flag} | {cost} | {latency} | {failed} |".format(
                tag=path.stem,
                model=report["run"]["model"],
                mode=report["run"]["input_mode"],
                perturb=(report["run"].get("perturbation") or "-")
                + ("" if report["run"].get("orientation_fix", True) else " (no orientation fix)")
                + ("" if report["run"].get("second_read", True) else " (no second read)"),
                perfect=f"{accuracy['all_fields']['correct']}/{accuracy['all_fields']['total']}",
                fields=f"{_field_mean(accuracy):.1%}",
                lines=f"{accuracy['line_items']['correct']}/{accuracy['line_items']['total']}",
                total=f"{accuracy['total']['correct']}/{accuracy['total']['total']}",
                flag=(
                    f"{review['errors_caught']}/{review['documents_with_errors']} caught, "
                    f"{review['false_alarms']} false"
                ),
                cost=f"${cost.get('avg_cost_usd', 0):.4f}" if cost else "-",
                latency=f"{cost['avg_latency_ms'] / 1000:.1f}s"
                if cost and cost.get("avg_latency_ms")
                else "-",
                failed=failed,
            )
        )
    table = "\n".join(
        [
            "| Experiment | Model | Input | Perturbation | Docs all-correct | Mean field acc. | Line items | Total | Review flag | Avg cost/doc | Avg latency | Failed calls |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|",
            *rows,
        ]
    )
    (OUT / "SUMMARY.md").write_text("# Experiment summary\n\n" + table + "\n", encoding="utf-8")
    return table


def _field_mean(accuracy: dict) -> float:
    fields = [row for name, row in accuracy.items() if name != "all_fields"]
    return sum(row["correct"] for row in fields) / sum(row["total"] for row in fields)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    groups = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    if "--summary" not in sys.argv:
        for group in groups or list(EXPERIMENTS):
            for tag, args in EXPERIMENTS[group]:
                run(tag, args)
    print(summarize())


if __name__ == "__main__":
    main()
