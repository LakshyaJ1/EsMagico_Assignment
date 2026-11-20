"""Token prices and cost arithmetic.

Prices are the Gemini API paid "Standard" tier, USD per 1M tokens, for prompts under
200k tokens, as listed on https://ai.google.dev/gemini-api/docs/pricing on 2026-11-21.
Gemini bills thinking tokens at the output rate, so ``output`` below covers both.
Free-tier keys are not billed, but we always report what the call *would* cost on the
paid tier so the number is meaningful for production planning.
"""

from __future__ import annotations

from dataclasses import dataclass

PRICES_AS_OF = "2026-11-21"
PRICING_SOURCE = "https://ai.google.dev/gemini-api/docs/pricing"


@dataclass(frozen=True)
class Price:
    input_per_m: float
    output_per_m: float
    note: str = ""


PRICES: dict[str, Price] = {
    "gemini-4-hydrogen": Price(1.50, 7.50),
    "gemini-4-neon": Price(3.00, 15.00),
    "gemini-4-carbon": Price(2.00, 10.00, "rises to $4.00 / $20.00 on 2026-12-01"),
    "gemini-4-argon": Price(2.00, 10.00, "rises to $4.00 / $20.00 on 2026-12-01"),
    "gemini-3.8-flash": Price(0.75, 3.75, "rises to $1.50 / $7.50 on 2027-01-01"),
    "gemini-3.6-flash": Price(0.75, 3.75, "rises to $1.50 / $7.50 on 2027-01-01"),
    "gemini-3.5-flash-lite": Price(0.30, 2.50),
    "gemini-3.1-flash-lite": Price(0.25, 1.50),
    "gemini-3.1-pro-preview": Price(2.00, 12.00),
    "gemini-3-flash-preview": Price(0.50, 3.00),
    "gemini-2.5-flash": Price(0.30, 2.50, "deprecated"),
    "gemini-2.5-flash-lite": Price(0.10, 0.40),
    "gemini-2.5-pro": Price(1.25, 10.00, "deprecated"),
}


def price_for(model: str) -> Price | None:
    # Accept "models/<id>" and versioned aliases such as "<id>-001".
    key = model.removeprefix("models/")
    if key in PRICES:
        return PRICES[key]
    matches = [name for name in PRICES if key.startswith(name)]
    return PRICES[max(matches, key=len)] if matches else None


@dataclass
class Usage:
    """Token usage for one or more calls. Addition aggregates retries and helper calls."""

    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0  # visible answer tokens
    thinking_tokens: int = 0  # billed at the output rate
    image_tokens: int = 0  # subset of input_tokens, when the API reports it
    cost_usd: float = 0.0
    priced: bool = True  # False if any call used a model missing from PRICES

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            calls=self.calls + other.calls,
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            thinking_tokens=self.thinking_tokens + other.thinking_tokens,
            image_tokens=self.image_tokens + other.image_tokens,
            cost_usd=self.cost_usd + other.cost_usd,
            priced=self.priced and other.priced,
        )

    @property
    def billed_output_tokens(self) -> int:
        return self.output_tokens + self.thinking_tokens

    def to_dict(self) -> dict[str, object]:
        return {
            "calls": self.calls,
            "input_tokens": self.input_tokens,
            "image_tokens": self.image_tokens,
            "output_tokens": self.output_tokens,
            "thinking_tokens": self.thinking_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "priced": self.priced,
        }


def cost_of(
    model: str, input_tokens: int, output_tokens: int, thinking_tokens: int
) -> tuple[float, bool]:
    price = price_for(model)
    if price is None:
        return 0.0, False
    cost = (
        input_tokens * price.input_per_m + (output_tokens + thinking_tokens) * price.output_per_m
    ) / 1e6
    return cost, True
