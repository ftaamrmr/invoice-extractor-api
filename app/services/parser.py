from __future__ import annotations

import re

from app.config import settings
from app.schemas import LineItem


def _normalize_digits(value: str) -> str:
    value = value.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    value = value.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    value = value.translate(str.maketrans("०१२३४५६७८९", "0123456789"))
    return value


def _search(patterns: list[str], text: str, flags: int = re.IGNORECASE) -> str | None:
    for pattern in patterns:
        m = re.search(pattern, text, flags)
        if not m:
            continue
        for g in m.groups():
            if g and g.strip():
                return g.strip()
    return None


def _to_float(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = _normalize_digits(value)
    cleaned = re.sub(r"[^\d,.-]", "", cleaned)
    if not cleaned:
        return None

    has_comma = "," in cleaned
    has_dot = "." in cleaned
    if has_comma and has_dot:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif has_comma and cleaned.count(",") == 1:
        cleaned = cleaned.replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")

    try:
        return float(cleaned)
    except ValueError:
        return None


INVOICE_NUMBER_PATTERNS = [
    r"(?:invoice\s*(?:no|number|#|num)[:\s#]+)([A-Z0-9\-/]+)",
    r"(?:facture\s*(?:n°|no|numéro|numero)[:\s#]+)([A-Z0-9\-/]+)",
    r"(?:fattura\s*(?:n°|numero)[:\s#]+)([A-Z0-9\-/]+)",
    r"(?:चालान\s*(?:संख्या|नंबर))[:\s]+([A-Z0-9\-/]+)",
    r"(?:رقم\s*الفاتورة|فاتورة\s*رقم)[:\s]+([A-Z0-9\-/٠-٩۰-۹]+)",
]

INVOICE_DATE_PATTERNS = [
    r"(?:invoice\s*date|date\s*of\s*invoice|issued)[:\s]+(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})",
    r"(?:date\s*de\s*facture|date\s*d'émission)[:\s]+(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})",
    r"(?:data\s*fattura|data\s*emissione)[:\s]+(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})",
    r"(?:चालान\s*तिथि)[:\s]+(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})",
    r"(?:تاريخ\s*الفاتورة|تاريخ\s*الإصدار)[:\s]+(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})",
]

DUE_DATE_PATTERNS = [
    r"(?:due\s*date|payment\s*due|pay\s*by)[:\s]+(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})",
    r"(?:date\s*d'échéance|date\s*limite)[:\s]+(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})",
    r"(?:scadenza|data\s*scadenza)[:\s]+(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})",
    r"(?:देय\s*तिथि|भुगतान\s*तिथि)[:\s]+(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})",
    r"(?:تاريخ\s*الاستحقاق|تاريخ\s*الدفع)[:\s]+(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})",
]

VENDOR_NAME_PATTERNS = [
    r"(?:vendor|company(?:\s*name)?|supplier|bill\s*from|issued\s*by|from)[:\s]+([^\n]{3,80})",
    r"(?:fournisseur|émetteur|vendeur|nom\s*de\s*la\s*société)[:\s]+([^\n]{3,80})",
    r"(?:fornitore|venditore|azienda)[:\s]+([^\n]{3,80})",
    r"(?:विक्रेता|कंपनी|आपूर्तिकर्ता)[:\s]+([^\n]{3,80})",
    r"(?:المورد|الشركة|اسم\s*الشركة|من)[:\s]+([^\n]{3,80})",
]

TAX_NUMBER_PATTERNS = [
    r"(?:vat\s*(?:number|no|reg|id)|tax\s*(?:id|number)|partita\s*iva|numéro\s*de\s*tva)[:\s:]+([A-Z0-9\-]{5,25})",
    r"(?:जीएसटीआईएन|कर\s*पहचान\s*संख्या|वैट\s*संख्या)[:\s:]+([A-Z0-9०-९\-]{5,25})",
    r"(?:الرقم\s*الضريبي|رقم\s*تسجيل\s*ضريبة\s*القيمة\s*المضافة)[:\s:]+([A-Z0-9٠-٩\-]{5,25})",
]

SUBTOTAL_PATTERNS = [
    r"(?:subtotal|sub\s*total|amount\s*before\s*tax|net\s*amount)[:\t ]+([\d,\.٠-٩०-९]+)",
    r"(?:sous-total|montant\s*net|total\s*ht)[:\t ]+([\d,\.٠-٩०-९]+)",
    r"(?:imponibile|totale\s*imponibile)[:\t ]+([\d,\.٠-٩०-९]+)",
    r"(?:उप-योग|कर\s*से\s*पहले\s*राशि)[:\t ]+([\d,\.٠-٩०-९]+)",
    r"(?:المجموع\s*الفرعي|المبلغ\s*قبل\s*الضريبة)[:\t ]+([\d,\.٠-٩०-९]+)",
]

TAX_PATTERNS = [
    r"(?:vat(?!\s*(?:number|id|no|reg))|tax\s*amount|gst|hst|sales\s*tax)\s*\(?[^\)\n]*\)?[:\t ]+([\d,\.٠-٩०-९]+)",
    r"(?:tva|taxe|iva|imposta)\s*\(?[^\)\n]*\)?[:\t ]+([\d,\.٠-٩०-९]+)",
    r"(?:कर\s*राशि|वैट\s*राशि)[:\t ]+([\d,\.٠-٩०-९]+)",
    r"(?:ضريبة\s*القيمة\s*المضافة|الضريبة)(?!\s*الرقم|\s*رقم)\s*\(?[^\)\n]*\)?[:\t ]+([\d,\.٠-٩०-९]+)",
]

TOTAL_PATTERNS = [
    r"(?:grand\s*total|total\s*amount|amount\s*due|total\s*due|total\s*payable)[:\t ]+([\d,\.٠-٩०-९]+)",
    r"(?:montant\s*total|total\s*ttc|total\s*à\s*payer)[:\t ]+([\d,\.٠-٩०-९]+)",
    r"(?:importo\s*totale|totale\s*da\s*pagare)[:\t ]+([\d,\.٠-٩०-९]+)",
    r"(?:कुल\s*राशि|कुल\s*देय|देय\s*राशि)[:\t ]+([\d,\.٠-٩०-९]+)",
    r"(?:الإجمالي|المبلغ\s*الإجمالي|المبلغ\s*المستحق)[:\t ]+([\d,\.٠-٩०-९]+)",
    r"(?<!sub)\btotal\b[:\t ]+([\d,\.٠-٩०-९]+)",
]

CURRENCY_PATTERNS = [
    r"\b(SAR|USD|EUR|AED|GBP|EGP|INR|CAD|AUD|CHF|JPY|CNY)\b",
    r"(\$|€|£|₹|¥)",
    r"(ريال|ر\.س\.?|درهم|جنيه|يورو|دولار|रूपये)",
]

PAYMENT_METHOD_PATTERNS = [
    r"(?:payment\s*method|paid\s*by|pay\s*via)[:\s]+([^\n]{3,40})",
    r"(?:mode\s*de\s*paiement|moyen\s*de\s*paiement)[:\s]+([^\n]{3,40})",
    r"(?:metodo\s*di\s*pagamento)[:\s]+([^\n]{3,40})",
    r"(?:भुगतान\s*विधि|भुगतान\s*का\s*तरीका)[:\s]+([^\n]{3,40})",
    r"(?:طريقة\s*الدفع)[:\s]+([^\n]{3,40})",
]

CURRENCY_SYMBOL_MAP = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "₹": "INR",
    "¥": "JPY",
    "ريال": "SAR",
    "ر.س": "SAR",
    "درهم": "AED",
    "جنيه": "EGP",
    "يورو": "EUR",
    "دولار": "USD",
    "रूपये": "INR",
}


_LINE_ITEM_PATTERN = re.compile(
    r"^(.{2,80}?)\s{2,}(\d[\d,\.٠-٩०-९]*)\s{2,}(\d[\d,\.٠-٩०-९]*)\s{2,}(\d[\d,\.٠-٩०-९]*)$",
    re.MULTILINE,
)


def _extract_line_items(text: str) -> list[LineItem]:
    items: list[LineItem] = []
    for m in _LINE_ITEM_PATTERN.finditer(text):
        desc, qty, unit, total = m.groups()
        quantity = _to_float(qty) or 0.0
        unit_price = _to_float(unit) or 0.0
        total_value = _to_float(total) or 0.0
        if quantity <= 0 or unit_price < 0 or total_value < 0:
            continue
        if quantity and abs((quantity * unit_price) - total_value) > max(1.0, total_value * 0.2):
            continue
        items.append(LineItem(description=desc.strip(), quantity=quantity, unit_price=unit_price, total=total_value))
    return items[: settings.MAX_LINE_ITEMS]


def parse_invoice(raw_text: str) -> dict:
    text = _normalize_digits(raw_text)

    invoice_number = _search(INVOICE_NUMBER_PATTERNS, text)
    invoice_date = _search(INVOICE_DATE_PATTERNS, text)
    due_date = _search(DUE_DATE_PATTERNS, text)
    vendor_name = _search(VENDOR_NAME_PATTERNS, text)
    vendor_tax_no = _search(TAX_NUMBER_PATTERNS, text)
    payment_method = _search(PAYMENT_METHOD_PATTERNS, text)

    subtotal = _to_float(_search(SUBTOTAL_PATTERNS, text))
    tax_amount = _to_float(_search(TAX_PATTERNS, text))
    total_amount = _to_float(_search(TOTAL_PATTERNS, text))

    if subtotal is not None and total_amount is not None and subtotal == total_amount:
        tax_amount = tax_amount if tax_amount not in (0.0, None) else None

    if tax_amount is not None and subtotal is not None and total_amount is None:
        total_amount = subtotal + tax_amount

    if subtotal is None and tax_amount is not None and total_amount is not None and total_amount > tax_amount:
        subtotal = total_amount - tax_amount

    currency: str | None = None
    for pattern in CURRENCY_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1)
            currency = CURRENCY_SYMBOL_MAP.get(value, value.upper())
            break

    line_items = _extract_line_items(text)

    field_confidence = {
        "invoice_number": 0.95 if invoice_number else 0.0,
        "invoice_date": 0.85 if invoice_date else 0.0,
        "due_date": 0.75 if due_date else 0.0,
        "vendor_name": 0.75 if vendor_name else 0.0,
        "vendor_tax_number": 0.8 if vendor_tax_no else 0.0,
        "subtotal": 0.8 if subtotal is not None else 0.0,
        "tax_amount": 0.75 if tax_amount is not None else 0.0,
        "total_amount": 0.9 if total_amount is not None else 0.0,
        "currency": 0.7 if currency else 0.0,
        "payment_method": 0.6 if payment_method else 0.0,
        "line_items": 0.7 if line_items else 0.0,
    }
    confidence_score = round(sum(field_confidence.values()) / len(field_confidence) * 100, 2)

    return {
        "vendor_name": vendor_name,
        "vendor_tax_number": vendor_tax_no,
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "due_date": due_date,
        "currency": currency,
        "subtotal": subtotal,
        "tax_amount": tax_amount,
        "total_amount": total_amount,
        "payment_method": payment_method,
        "line_items": line_items,
        "confidence_score": confidence_score,
        "field_confidence": field_confidence,
        "raw_text": raw_text,
    }
