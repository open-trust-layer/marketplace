"""Transport-free local visual contract over the merged-green M75 interaction path."""
from __future__ import annotations

from dataclasses import dataclass
from html import escape

from .local_console_v1 import LocalConsoleInteractionError, run_local_buy_sell_console
from .local_demo_v1 import LocalBuySellDemoResult


_FORM_ACTION = "/local-buy-sell"
_EXPECTED_PROMPTS = (
    "Seller principal URI: ",
    "Subject URI: ",
    "Listing title: ",
    "Listing description: ",
    "Consideration amount (exact decimal): ",
    "Currency code (3 uppercase letters): ",
    "Quantity (exact decimal): ",
    "Quantity unit URI: ",
    "Latitude (decimal degrees, max 6 fractional digits): ",
    "Longitude (decimal degrees, max 6 fractional digits): ",
    "Buyer principal URI: ",
    "Buyer action URI: ",
)


class LocalVisualInteractionError(RuntimeError):
    """Stable transport-free visual failure that never reflects hostile input."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class LocalVisualSubmission:
    """Exact immutable human-field submission consumed through the M75 adapter."""

    seller_principal: str
    subject_uri: str
    title: str
    description: str
    consideration: str
    currency_code: str
    quantity: str
    unit_uri: str
    latitude: str
    longitude: str
    buyer_principal: str
    buyer_action_uri: str


def _style() -> str:
    return """<style>
body { font-family: system-ui, sans-serif; margin: 0; background: #f6f7f9; color: #17202a; }
main { max-width: 840px; margin: 0 auto; padding: 24px; }
.card { background: #fff; border: 1px solid #d9dee5; border-radius: 12px; padding: 20px; }
.notice { background: #f3f6f8; border: 1px solid #d9dee5; border-radius: 10px; padding: 12px 14px; }
form { display: grid; gap: 14px; }
label { display: grid; gap: 6px; font-weight: 650; }
input, textarea { box-sizing: border-box; width: 100%; font: inherit; padding: 10px; border: 1px solid #aeb8c2; border-radius: 8px; }
textarea { min-height: 96px; resize: vertical; }
button { font: inherit; font-weight: 700; padding: 10px 16px; border: 1px solid #17202a; border-radius: 8px; background: #fff; cursor: pointer; }
dl { display: grid; grid-template-columns: minmax(140px, 190px) 1fr; gap: 8px 12px; }
dt { font-weight: 700; }
dd { margin: 0; overflow-wrap: anywhere; }
</style>"""


def _field(label: str, name: str, *, textarea: bool = False) -> str:
    if textarea:
        control = f'<textarea name="{name}" required></textarea>'
    else:
        control = f'<input name="{name}" type="text" required>'
    return f"<label>{label}{control}</label>"


def render_local_buy_sell_form() -> str:
    """Return one deterministic self-contained form without performing external I/O."""
    fields = "".join(
        (
            _field("Seller principal URI", "seller_principal"),
            _field("Subject URI", "subject_uri"),
            _field("Listing title", "title"),
            _field("Listing description", "description", textarea=True),
            _field("Consideration amount (exact decimal)", "consideration"),
            _field("Currency code", "currency_code"),
            _field("Quantity (exact decimal)", "quantity"),
            _field("Quantity unit URI", "unit_uri"),
            _field("Latitude", "latitude"),
            _field("Longitude", "longitude"),
            _field("Buyer principal URI", "buyer_principal"),
            _field("Buyer action URI", "buyer_action_uri"),
        )
    )
    return (
        "<!doctype html>"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Open Layer Marketplace — Local Buy/Sell</title>"
        f"{_style()}</head><body><main>"
        '<section class="card"><h1>Local Marketplace Buy/Sell</h1>'
        '<p class="notice"><strong>Local demonstration only.</strong> '
        "No agreement, no payment, no settlement, no ownership transfer, and no protocol truth are created.</p>"
        f'<form method="post" action="{_FORM_ACTION}">{fields}'
        '<button type="submit">Evaluate local compatibility</button></form>'
        "</section></main></body></html>"
    )


def _submission_values(submission: LocalVisualSubmission) -> tuple[object, ...]:
    return (
        submission.seller_principal,
        submission.subject_uri,
        submission.title,
        submission.description,
        submission.consideration,
        submission.currency_code,
        submission.quantity,
        submission.unit_uri,
        submission.latitude,
        submission.longitude,
        submission.buyer_principal,
        submission.buyer_action_uri,
    )


def _result_page(result: LocalBuySellDemoResult) -> str:
    seller_id = escape(result.seller_record_id, quote=True)
    buyer_id = escape(result.buyer_record_id, quote=True)
    conclusion = escape(result.match_conclusion, quote=True)
    return (
        "<!doctype html>"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Open Layer Marketplace — Local Result</title>"
        f"{_style()}</head><body><main>"
        '<section class="card"><h1>Local compatibility result</h1>'
        '<p class="notice">Method-relative local evidence only. No agreement, no payment, '
        "no settlement, no ownership transfer, and no protocol truth are created.</p>"
        "<dl>"
        f"<dt>Seller record</dt><dd>seller_record_id={seller_id}</dd>"
        f"<dt>Buyer record</dt><dd>buyer_record_id={buyer_id}</dd>"
        f"<dt>Match conclusion</dt><dd>{conclusion}</dd>"
        "<dt>Protocol truth</dt><dd>protocol_truth=false</dd>"
        "<dt>Creates agreement</dt><dd>creates_agreement=false</dd>"
        "</dl>"
        '<p><a href="/">Start another local interaction</a></p>'
        "</section></main></body></html>"
    )


def submit_local_buy_sell_form(submission: LocalVisualSubmission) -> str:
    """Consume one exact submission through M75 and return bounded inert result HTML."""
    if type(submission) is not LocalVisualSubmission:
        raise LocalVisualInteractionError(
            "SUBMISSION_INVALID",
            "local visual submission must be the exact immutable submission type",
        )

    values = _submission_values(submission)
    if len(values) != len(_EXPECTED_PROMPTS):
        raise LocalVisualInteractionError(
            "VISUAL_BINDING_DRIFT",
            "local visual submission binding changed",
        )
    prompt_values = dict(zip(_EXPECTED_PROMPTS, values, strict=True))
    seen: set[str] = set()

    def read_line(prompt: str) -> object:
        if type(prompt) is not str or prompt not in prompt_values or prompt in seen:
            raise RuntimeError("M75 prompt binding changed")
        seen.add(prompt)
        return prompt_values[prompt]

    def discard_line(_line: str) -> None:
        return None

    try:
        result = run_local_buy_sell_console(read_line=read_line, write_line=discard_line)
    except LocalConsoleInteractionError as exc:
        if exc.code == "INPUT_INVALID":
            code = "SUBMISSION_INVALID"
            message = "local visual submission is invalid"
        elif exc.code == "INPUT_READ_FAILED":
            code = "VISUAL_BINDING_DRIFT"
            message = "reviewed M75 input binding changed"
        else:
            code = "SUBMISSION_FAILED"
            message = "local visual submission could not complete through the reviewed M75 path"
        raise LocalVisualInteractionError(code, message) from exc

    if len(seen) != len(_EXPECTED_PROMPTS):
        raise LocalVisualInteractionError(
            "VISUAL_BINDING_DRIFT",
            "reviewed M75 input binding changed",
        )
    if type(result) is not LocalBuySellDemoResult:
        raise LocalVisualInteractionError(
            "VISUAL_RESULT_INVALID",
            "reviewed M75 returned an unexpected result type",
        )
    if result.protocol_truth is not False or result.creates_agreement is not False:
        raise LocalVisualInteractionError(
            "VISUAL_AUTHORITY_VIOLATION",
            "local visual result attempted to promote authority",
        )
    return _result_page(result)


__all__ = [
    "LocalVisualInteractionError",
    "LocalVisualSubmission",
    "render_local_buy_sell_form",
    "submit_local_buy_sell_form",
]
