"""Human-review routing: turn validation issues into a ``needs_review`` flag and a score.

The score is not a probability. It is a transparent penalty sum, so a reviewer can see
exactly why a document scored what it did. Whether the flag actually catches the errors
is measured by the eval harness against ground truth (see REPORT.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .validation import Issue, Severity

PENALTY = {Severity.ERROR: 0.40, Severity.WARNING: 0.15, Severity.INFO: 0.0}
RETRY_PENALTY = 0.05  # recovered after a corrective re-read: fine, but less certain


@dataclass(frozen=True)
class ReviewDecision:
    needs_review: bool
    confidence: float
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "needs_review": self.needs_review,
            "confidence": self.confidence,
            "reasons": self.reasons,
        }


def decide(issues: list[Issue], *, retried: bool) -> ReviewDecision:
    flagged = [issue for issue in issues if issue.severity in (Severity.ERROR, Severity.WARNING)]
    score = 1.0 - sum(PENALTY[issue.severity] for issue in issues)
    if retried:
        score -= RETRY_PENALTY
    return ReviewDecision(
        needs_review=bool(flagged),
        confidence=round(min(1.0, max(0.0, score)), 2),
        reasons=[issue.message for issue in flagged],
    )
