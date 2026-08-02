from __future__ import annotations

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    description: str = ""
    quantity: float = 1.0
    unit_price: float = 0.0
    total: float = 0.0


class InvoiceData(BaseModel):
    vendor_name: str | None = None
    vendor_tax_number: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    currency: str | None = None
    subtotal: float | None = None
    tax_amount: float | None = None
    total_amount: float | None = None
    payment_method: str | None = None
    line_items: list[LineItem] = Field(default_factory=list)
    confidence_score: float = 0.0
    field_confidence: dict[str, float] | None = None
    raw_text: str | None = None


class ResponseMeta(BaseModel):
    request_id: str
    version: str
    filename: str
    file_type: str
    file_size: int
    page_count: int | None = None
    extraction_method: str
    processing_time_ms: int


class ExtractResponse(BaseModel):
    success: bool = True
    data: InvoiceData
    meta: ResponseMeta


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
    request_id: str


class RawTextData(BaseModel):
    raw_text: str


class RawTextResponse(BaseModel):
    success: bool = True
    data: RawTextData
    meta: ResponseMeta
