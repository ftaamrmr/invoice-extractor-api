"""
Rule-based invoice parser.

Extracts structured fields from raw invoice text using regex patterns.
Supports English, Arabic, French, Italian, and Hindi invoices.
"""
import re
from typing import Optional, List
from app.schemas import LineItem


# ── Regex helpers ─────────────────────────────────────────────────────────────

# Common Indic digits (Devanagari) → ASCII
def _normalize_indic_digits(value: str) -> str:
    """Convert Devanagari/Hindi digits to ASCII."""
    indic_map = str.maketrans(
        "०१२३४५६७८९",  # Devanagari 0-9
        "0123456789"
    )
    return value.translate(indic_map)


def _search(patterns: List[str], text: str, flags: int = re.IGNORECASE) -> Optional[str]:
    """Return the first non-empty capture group from the first matching pattern."""
    for pattern in patterns:
        m = re.search(pattern, text, flags)
        if m:
            # Return first non-None group
            for g in m.groups():
                if g and g.strip():
                    return g.strip()
    return None


def _to_float(value: Optional[str]) -> Optional[float]:
    """Convert a string like '1,234.56', '١٢٣٤', or '१,२३४.५६' to float."""
    if not value:
        return None
    # Remove currency symbols and whitespace
    cleaned = re.sub(r"[^\d.,٠-٩०-९]", "", value)
    # Arabic-Indic + Devanagari digits → ASCII
    arabic_map = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    cleaned = cleaned.translate(arabic_map)
    cleaned = _normalize_indic_digits(cleaned)
    # Normalise decimal separator: 1.234,56 → 1234.56 and 1,234.56 → 1234.56
    if cleaned.count(",") == 1 and cleaned.count(".") == 0:
        cleaned = cleaned.replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


# ── Field patterns ────────────────────────────────────────────────────────────

INVOICE_NUMBER_PATTERNS = [
    r"(?:invoice\s*(?:no|number|#|num)[:\s#]+)([A-Z0-9\-/]+)",
    r"(?:inv\s*(?:no|#)[:\s]+)([A-Z0-9\-/]+)",
    r"(?:facture\s*(?:n°|no|numéro|numero)[:\s#]+)([A-Z0-9\-/]+)",
    r"(?:fattura\s*(?:n°|numero)[:\s#]+)([A-Z0-9\-/]+)",
    r"(?:चालान\s*(?:संख्या|नंबर))[:\s]+([A-Z0-9\-/]+)",
    r"(?:रिक्त\s*संख्या)?",  # placeholder to keep list lengths safe; never matches alone
    r"(?:रिक्त\s*संख्या)?",
    r"(?:رقم\s*الفاتورة[:\s]+)([A-Z0-9\-/٠-٩]+)",
    r"(?:فاتورة\s*رقم[:\s]+)([A-Z0-9\-/٠-٩]+)",
]

INVOICE_DATE_PATTERNS = [
    r"(?:invoice\s*date|date\s*of\s*invoice)[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
    r"(?:^date|issued)[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
    r"(?:date\s*de\s*facture|date\s*de\s*la\s*facture|date\s*d'émission)[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
    r"(?:data\s*fattura|data\s*emissione)[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
    r"(?:चालान\s*तिथि)[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
    r"(?:تاريخ\s*الفاتورة|تاريخ\s*الإصدار)[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
]

DUE_DATE_PATTERNS = [
    r"(?:due\s*date|payment\s*due|pay\s*by)[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
    r"(?:date\s*d'échéance|à\s*payer\s*avant|date\s*limite)[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
    r"(?:scadenza|data\s*scadenza)[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
    r"(?:भुगतान\s*तिथि|देय\s*तिथि)[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
    r"(?:تاريخ\s*الاستحقاق|تاريخ\s*الدفع)[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
]

VENDOR_NAME_PATTERNS = [
    r"(?:vendor|company(?:\s*name)?|from|bill\s*from|supplier|issued\s*by)[:\s]+([^\n]{3,60})",
    r"(?:fournisseur|émetteur|vendeur|nom\s*de\s*la\s*société)[:\s]+([^\n]{3,60})",
    r"(?:fornitore|venditore|azienda)[:\s]+([^\n]{3,60})",
    r"(?:विक्रेता|कंपनी|आपूर्तिकर्ता)[:\s]+([^\n]{3,60})",
    r"(?:من|المورد|الشركة|اسم\s*الشركة)[:\s]+([^\n]{3,60})",
]

TAX_NUMBER_PATTERNS = [
    r"(?:vat\s*(?:number|no|reg)|tax\s*(?:id|number|no)|tax\s*registration\s*(?:no|number)|tva\s*(?:n°|numéro|no)|numéro\s*de\s*tva|partita\s*iva)[:\s:]+([A-Z0-9\-]{5,20})",
    r"(?:vat\s*id|numéro\s*tva|n°\s*tva)[:\s:]+([A-Z0-9\-]{5,20})",
    r"(?:वैट\s*संख्या|जीएसटीआईएन|कर\s*पहचान\s*संख्या)[:\s:]+([A-Z0-9०-९\-]{5,20})",
    r"(?:الرقم\s*الضريبي|رقم\s*تسجيل\s*ضريبة\s*القيمة\s*المضافة)[:\s:]+([A-Z0-9٠-٩\-]{5,20})",
]

SUBTOTAL_PATTERNS = [
    r"(?:subtotal|sub\s*total|net\s*amount|amount\s*before\s*tax)[:\t ]+([\d,\.]+)",
    r"(?:sous-total|montant\s*net|total\s*ht|montant\s*hors\s*taxe)[:\t ]+([\d,\.]+)",
    r"(?:imponibile|totale\s*imponibile|imponibile\s*totale)[:\t ]+([\d,\.]+)",
    r"(?:उप-योग|कर\s*से\s*पहले\s*राशि)[:\t ]+([\d,\.]+)",
    r"(?:المجموع\s*الفرعي|المبلغ\s*قبل\s*الضريبة)[:\t ]+([\d,\.]+)",
]

TAX_PATTERNS = [
    r"(?:vat(?!\s*(?:number|no|reg|registration|id))\b|tax\s*amount|gst|hst|sales\s*tax)\s*\(?[^\)\n]*\)?[:\t ]+([\d,\.]+)",
    r"(?:tva|taxe)\s*\(?[^\)\n]*\)?[:\t ]+([\d,\.]+)",
    r"(?:iva|imposta)\s*\(?[^\)\n]*\)?[:\t ]+([\d,\.]+)",
    r"(?:importo\s*iva)[:\t ]+([\d,\.]+)",
    r"(?:जीएसटी\s*\(\d+%\)|कर\s*राशि|वैट\s*राशि)[:\t ]+([\d,\.]+)",
    r"(?:ضريبة\s*القيمة\s*المضافة\b|الضريبة\b|ضريبة\b)(?!\s*الرقم|\s*رقم)\s*\(?[^\)\n]*\)?[:\t ]+([\d,\.]+)",
]

TOTAL_PATTERNS = [
    # Language-specific totals first so they win over the generic "Total" pattern.
    r"(?:montant\s*total|total\s*ttc|reste\s*à\s*payer|total\s*à\s*payer)\b[:\t ]+([\d,\.]+)",
    r"(?:importo\s*totale|totale\s*da\s*pagare)\b[:\t ]+([\d,\.]+)",
    r"(?:totale)(?!\s*da\s*pagare)\b[:\t ]+([\d,\.]+)",
    r"(?:कुल\s*राशि|देय\s*राशि|कुल\s*देय)[:\t ]+([\d,\.]+)",
    r"(?:الإجمالي|المبلغ\s*الإجمالي|المبلغ\s*المستحق|الإجمالي\s*المستحق)[:\t ]+([\d,\.]+)",
    # Generic totals — use negative lookbehind to avoid matching "Subtotal" as "total".
    r"(?:total\s*amount|amount\s*due|balance\s*due|total\s*due|grand\s*total|total\s*payable)\b[:\t ]+([\d,\.]+)",
    r"(?<!sub)\btotal\b[:\t ]+([\d,\.]+)",
]

CURRENCY_PATTERNS = [
    r"\b(SAR|USD|EUR|AED|GBP|EGP|INR|CAD|AUD|CHF|JPY|CNY)\b",
    r"(ريال|ر\.س|ر\.س\.|درهم|جنيه|يورو|دولار)",
    r"(\$|€|£|₹|₽|¥)",
    r"(रूपये|₹)",
]

PAYMENT_METHOD_PATTERNS = [
    r"(?:payment\s*method|paid\s*by|pay\s*via)[:\s]+([^\n]{3,30})",
    r"(?:mode\s*de\s*paiement|moyen\s*de\s*paiement|paiement)[:\s]+([^\n]{3,30})",
    r"(?:metodo\s*di\s*pagamento|pagamento)[:\s]+([^\n]{3,30})",
    r"(?:भुगतान\s*विधि|भुगतान\s*का\s*तरीका)[:\s]+([^\n]{3,30})",
    r"(?:طريقة\s*الدفع)[:\s]+([^\n]{3,30})",
]

CURRENCY_SYMBOL_MAP = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "₹": "INR",
    "₽": "RUB",
    "¥": "JPY",
    "ريال": "SAR",
    "ر.س": "SAR",
    "ر.س.": "SAR",
    "درهم": "AED",
    "جنيه": "EGP",
    "يورو": "EUR",
    "دولار": "USD",
    "रूपये": "INR",
}


# ── Line item extraction ──────────────────────────────────────────────────────

def _extract_line_items(text: str) -> List[LineItem]:
    """
    Very simple line-item extractor.
    Looks for lines that match: description  qty  unit_price  total
    """
    items: List[LineItem] = []
    # Pattern: words  number  number  number  (tab or multi-space separated)
    pattern = re.compile(
        r"^(.{3,40}?)\s{2,}(\d[\d,.]*)\s{2,}(\d[\d,.]*)\s{2,}(\d[\d,.]*)$",
        re.MULTILINE,
    )
    for m in pattern.finditer(text):
        desc, qty, unit, total = m.groups()
        items.append(
            LineItem(
                description=desc.strip(),
                quantity=_to_float(qty) or 1.0,
                unit_price=_to_float(unit) or 0.0,
                total=_to_float(total) or 0.0,
            )
        )
    return items[:20]  # cap at 20 items for MVP


# ── Confidence scoring ────────────────────────────────────────────────────────

def compute_confidence(
    invoice_number: Optional[str],
    invoice_date: Optional[str],
    total_amount: Optional[float],
    tax_amount: Optional[float],
    vendor_name: Optional[str],
    currency: Optional[str],
    line_items: List[LineItem],
) -> float:
    score = 0.0
    if invoice_number:
        score += 20
    if invoice_date:
        score += 15
    if total_amount:
        score += 25
    if tax_amount:
        score += 10
    if vendor_name:
        score += 10
    if currency:
        score += 10
    if line_items:
        score += 10
    return min(score, 100.0)


# ── Main parse function ───────────────────────────────────────────────────────

def parse_invoice(raw_text: str) -> dict:
    """
    Parse raw invoice text and return a dict matching InvoiceData fields.
    """
    text = raw_text  # keep original case for some patterns

    invoice_number = _search(INVOICE_NUMBER_PATTERNS, text)
    invoice_date   = _search(INVOICE_DATE_PATTERNS, text)
    due_date       = _search(DUE_DATE_PATTERNS, text)
    vendor_name    = _search(VENDOR_NAME_PATTERNS, text)
    vendor_tax_no  = _search(TAX_NUMBER_PATTERNS, text)
    payment_method = _search(PAYMENT_METHOD_PATTERNS, text)

    subtotal_str   = _search(SUBTOTAL_PATTERNS, text)
    tax_str        = _search(TAX_PATTERNS, text)
    total_str      = _search(TOTAL_PATTERNS, text)

    subtotal       = _to_float(subtotal_str)
    tax_amount     = _to_float(tax_str)
    total_amount   = _to_float(total_str)

    # Currency detection
    currency: Optional[str] = None
    for pattern in CURRENCY_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            raw_currency = m.group(1)
            currency = CURRENCY_SYMBOL_MAP.get(raw_currency, raw_currency.upper())
            break

    line_items = _extract_line_items(raw_text)

    confidence = compute_confidence(
        invoice_number, invoice_date, total_amount,
        tax_amount, vendor_name, currency, line_items,
    )

    return {
        "vendor_name":       vendor_name,
        "vendor_tax_number": vendor_tax_no,
        "invoice_number":    invoice_number,
        "invoice_date":      invoice_date,
        "due_date":          due_date,
        "currency":          currency,
        "subtotal":          subtotal,
        "tax_amount":        tax_amount,
        "total_amount":      total_amount,
        "payment_method":    payment_method,
        "line_items":        line_items,
        "confidence_score":  confidence,
        "raw_text":          raw_text,
    }
