from __future__ import annotations

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile, status

from app.config import settings
from app.errors import APIError
from app.schemas import (
    ExtractResponse,
    InvoiceData,
    LineItem,
    RawTextData,
    RawTextResponse,
    ResponseMeta,
)
from app.security import verify_api_key
from app.services.file_validator import validate_upload
from app.services.invoice_extractor import extract_from_image, extract_from_pdf

router = APIRouter(prefix="/v1/invoices", tags=["invoices"])


def _build_invoice_data(parsed: dict) -> InvoiceData:
    line_items = [item if isinstance(item, LineItem) else LineItem(**item) for item in parsed.get("line_items", [])]
    raw_text = parsed.get("raw_text") if settings.INCLUDE_RAW_TEXT else None
    return InvoiceData(
        vendor_name=parsed.get("vendor_name"),
        vendor_tax_number=parsed.get("vendor_tax_number"),
        invoice_number=parsed.get("invoice_number"),
        invoice_date=parsed.get("invoice_date"),
        due_date=parsed.get("due_date"),
        currency=parsed.get("currency"),
        subtotal=parsed.get("subtotal"),
        tax_amount=parsed.get("tax_amount"),
        total_amount=parsed.get("total_amount"),
        payment_method=parsed.get("payment_method"),
        line_items=line_items,
        confidence_score=parsed.get("confidence_score", 0.0),
        field_confidence=parsed.get("field_confidence"),
        raw_text=raw_text,
    )


def _build_meta(request: Request, validated, result: dict) -> ResponseMeta:
    return ResponseMeta(
        request_id=getattr(request.state, "request_id", "unknown"),
        version=settings.APP_VERSION,
        filename=validated.sanitized_filename,
        file_type=validated.file_type,
        file_size=validated.size_bytes,
        page_count=validated.page_count,
        extraction_method=result["extraction_method"],
        processing_time_ms=result["processing_time_ms"],
    )


@router.post("/extract", response_model=ExtractResponse, response_model_exclude_none=True)
async def extract_invoice(
    request: Request,
    response: Response,
    file: UploadFile = File(..., description="PDF, PNG, JPG, or JPEG invoice file"),
    _: None = Depends(verify_api_key),
):
    validated = await validate_upload(file)
    result = await (extract_from_pdf(validated.content) if validated.file_type == "pdf" else extract_from_image(validated.content))

    if result.get("error") and not result["parsed"].get("raw_text"):
        raise APIError(status.HTTP_422_UNPROCESSABLE_ENTITY, "EXTRACTION_FAILED", "Invoice extraction failed.")

    response.headers["X-Processing-Time"] = str(result["processing_time_ms"])
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Request-ID"] = getattr(request.state, "request_id", "unknown")

    invoice_data = _build_invoice_data(result["parsed"])
    return ExtractResponse(success=True, data=invoice_data, meta=_build_meta(request, validated, result))


@router.post("/extract-text", response_model=RawTextResponse, response_model_exclude_none=True)
async def extract_text_only(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    _: None = Depends(verify_api_key),
):
    if not settings.INCLUDE_RAW_TEXT:
        raise APIError(status.HTTP_403_FORBIDDEN, "RAW_TEXT_DISABLED", "Raw text extraction is disabled.")

    validated = await validate_upload(file)
    result = await (extract_from_pdf(validated.content) if validated.file_type == "pdf" else extract_from_image(validated.content))

    if result.get("error") and not result["parsed"].get("raw_text"):
        raise APIError(status.HTTP_422_UNPROCESSABLE_ENTITY, "EXTRACTION_FAILED", "Invoice text extraction failed.")

    response.headers["X-Processing-Time"] = str(result["processing_time_ms"])
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Request-ID"] = getattr(request.state, "request_id", "unknown")

    raw_text = result["parsed"].get("raw_text", "")[: settings.MAX_EXTRACTED_TEXT_LENGTH]
    return RawTextResponse(success=True, data=RawTextData(raw_text=raw_text), meta=_build_meta(request, validated, result))
