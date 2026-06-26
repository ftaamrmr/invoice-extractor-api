"""
Pydantic schemas for request validation and response models.
"""
from typing import List, Optional
from pydantic import BaseModel


# ── Line item inside an invoice ──────────────────────────────────────────────

class LineItem(BaseModel):
    description: str = ""
    quantity: float = 1.0
    unit_price: float = 0.0
    total: float = 0.0


# ── Core invoice data ─────────────────────────────────────────────────────────

class InvoiceData(BaseModel):
    vendor_name: Optional[str] = None
    vendor_tax_number: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    currency: Optional[str] = None
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    total_amount: Optional[float] = None
    payment_method: Optional[str] = None
    line_items: List[LineItem] = []
    confidence_score: float = 0.0
    raw_text: str = ""


# ── Metadata attached to every response ──────────────────────────────────────

class ResponseMeta(BaseModel):
    filename: str
    file_type: str          # "pdf" | "image"
    extraction_method: str  # "pdf_text" | "ocr" | "fallback"
    processing_time_ms: int


# ── Success response ──────────────────────────────────────────────────────────

class ExtractResponse(BaseModel):
    success: bool = True
    data: InvoiceData
    meta: ResponseMeta


# ── Error detail ──────────────────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


# ── Raw-text-only response ────────────────────────────────────────────────────

class RawTextData(BaseModel):
    raw_text: str


class RawTextResponse(BaseModel):
    success: bool = True
    data: RawTextData
    meta: ResponseMeta
