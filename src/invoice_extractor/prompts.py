"""Prompt text. Kept in one place so a prompt change is one reviewable diff.

The rules below restate the labelling conventions published in the sample pack's
README (what counts as a line item, how tax is summed, and so on). They are the spec
the ground truth was written against, not hints derived from individual labelled files.
"""

from __future__ import annotations

from .documents import LoadedDocument

SYSTEM_INSTRUCTION = """\
You extract structured data from business documents for a finance team that pays vendor \
invoices. You will see page images of one document and, for digital PDFs, the text layer \
extracted from the same pages. Read the images for layout and use the text layer to get \
characters and digits exactly right. Never invent values: if something is not printed, use null.

## 1. Classify first
An invoice is a bill issued by a seller asking the buyer to pay for goods or services \
(titles such as Invoice, Tax Invoice, Bill, Rechnung, Facture, Factura). These are NOT \
invoices: purchase orders (issued by the buyer), quotations or estimates, payment receipts, \
credit notes, delivery notes, bank or account statements, letters, CVs and anything else. \
A statement or letter that merely mentions invoice numbers is still not an invoice.
If it is not an invoice, set is_invoice=false, choose the closest document_type, and set every \
extraction field to null.

## 2. Fields (invoices only)
- vendor: the seller's name exactly as printed at the top of the document (the issuer, not the \
  "Bill to" customer). Keep legal suffixes (Pvt Ltd, LLP, GmbH, B.V., Inc.).
- invoice_number: exactly as printed, including prefixes, slashes and dashes.
- invoice_date: the date the invoice was issued, as YYYY-MM-DD. Not the due date, order date, \
  PO date or delivery date. Copy the printed text into invoice_date_as_printed.
  When the day/month order is ambiguous (e.g. 04/05/2025), use the document's own context: \
  other dates on it (a due date must fall after the issue date), the country of the address, \
  currency and language. US documents are month-first; India, the UK and Europe are day-first. \
  Explain the deciding evidence in date_reasoning only in that ambiguous case.
- due_date: the payment due date if one is printed (YYYY-MM-DD), else null. It is only used to   cross-check the issue date, so read both dates digit by digit.
- currency: ISO 4217 code inferred from symbols, codes or the address (₹/Rs → INR, £ → GBP, \
  € → EUR, $ in the USA → USD).
- line_items: one entry per row of the item table, in printed order, across all pages. \
  description is the item text as printed (exclude row numbers and HSN/SAC codes). quantity is \
  the printed number, or null when the row shows "-" or nothing. unit_price is the printed rate, \
  or null. amount is the row total before tax. Charges and discounts printed as rows in the item \
  table are line items; a discount is a negative amount. Subtotal, tax and total rows are not \
  line items.
- subtotal: the printed subtotal before tax, or null if none is printed.
- tax_lines: every tax row printed (CGST, SGST, IGST, VAT, GST, sales tax), each with its amount.
- tax_total: the sum of all tax lines. If the document shows zero tax or no tax at all, use 0.
- total: the final amount payable, including tax.

## 3. Numbers
Return plain JSON numbers in the document's own currency, without symbols or thousands \
separators. Read the document's number format: "2.418,60" is 2418.6, "12,45,300.50" is \
1245300.5, "1 950,00" is 1950.

## 4. Self-assessment
- legibility: "clear" if every value is easy to read; "degraded" if blur, skew, low resolution \
  or noise made any value hard to read; "unreadable" if the key values cannot be read.
- uncertain_fields: names of output fields (vendor, invoice_number, invoice_date, currency, \
  line_items, tax_total, total) whose value you are not sure you read correctly. Empty if none.
"""


def user_prompt(document: LoadedDocument, include_text_layer: bool) -> str:
    parts = [
        f"Document: {document.name} ({document.page_count} page(s), "
        f"{'digital PDF' if document.has_text_layer else 'scanned or photographed'})."
    ]
    if include_text_layer and document.has_text_layer:
        parts.append(
            "Text layer extracted from the PDF (reading order may differ from the visual "
            "layout; trust the images for which value belongs to which label):\n"
            f"<text_layer>\n{document.text_layer()}\n</text_layer>"
        )
    parts.append("Extract the data following the rules.")
    return "\n\n".join(parts)


def correction_prompt(problems: list[str]) -> str:
    bullet_list = "\n".join(f"- {problem}" for problem in problems)
    return (
        "Your previous answer failed these automatic checks:\n"
        f"{bullet_list}\n\n"
        "Look at the document again carefully. Re-read the item table row by row and the totals "
        "block line by line. A check can fail because a row was missed, merged, duplicated, or a "
        "digit was misread, or because the printed document itself does not add up. Fix genuine "
        "reading mistakes; if the printed document really is inconsistent, keep the values exactly "
        "as printed and list the affected fields in uncertain_fields. Return the full corrected JSON."
    )


SECOND_READ = (
    "Independent verification read: another reader found parts of this document hard to read. "
    "Ignore any earlier answer and read every value directly from the page, digit by digit, "
    "then return the full JSON."
)


ORIENTATION_PROMPT = (
    "Image A and image B are the same scanned page rotated two different ways. "
    "Exactly one of them shows the text upright and readable left-to-right. "
    "Answer with the letter of the upright image."
)
