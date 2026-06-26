"""
Invoice extraction routes.

POST /v1/invoices/extract        – full structured JSON response
POST /v1/invoices/extract-text   – raw text only (useful for debugging)

Both endpoints:
  - Require authentication via X-API-Key or X-RapidAPI-Proxy-Secret
  - Accept multipart/form-data with a single "file" field
  - Return X-Processing-Time response header (milliseconds)
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response, status
from app.security import verify_api_key
from app.services.file_validator import validate_upload
from app.services.invoice_extractor import extract_from_pdf, extract_from_image
from app.schemas import (
    ExtractResponse,
    InvoiceData,
    LineItem,
    ResponseMeta,
    RawTextResponse,
    RawTextData,
)

router = APIRouter(prefix="/v1/invoices", tags=["invoices"])


def _file_type(filename: str) -> str:
    """Return 'pdf' or 'image' based on file extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return "pdf" if ext == "pdf" else "image"


def _build_invoice_data(parsed: dict) -> InvoiceData:
    """Convert the parser output dict into an InvoiceData Pydantic model."""
    raw_items = parsed.get("line_items", [])
    line_items = [
        item if isinstance(item, LineItem) else LineItem(**item)
        for item in raw_items
    ]
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
        raw_text=parsed.get("raw_text", ""),
    )


@router.post(
    "/extract",
    response_model=ExtractResponse,
    summary="Extract structured invoice data from PDF or image",
    description=(
        "Upload a PDF or image invoice and receive structured JSON with "
        "vendor name, invoice number, dates, amounts, line items, and more. "
        "Requires X-API-Key or X-RapidAPI-Proxy-Secret header."
    ),
    responses={
        401: {"description": "Missing or invalid API key"},
        413: {"description": "File exceeds size limit"},
        422: {"description": "Unsupported file type, empty file, or extraction error"},
    },
)
async def extract_invoice(
    response: Response,
    file: UploadFile = File(..., description="PDF, PNG, JPG, or JPEG invoice file"),
    _: None = Depends(verify_api_key),
):
    content = await validate_upload(file)
    filename = file.filename or "unknown"
    ftype = _file_type(filename)

    result = extract_from_pdf(content) if ftype == "pdf" else extract_from_image(content)

    # Surface the processing time as a response header for observability
    response.headers["X-Processing-Time"] = str(result["processing_time_ms"])

    # If extraction completely failed (e.g. OCR unavailable for image), raise 422
    if result.get("error") and not result["parsed"].get("raw_text"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "success": False,
                "error": {
                    "code": "EXTRACTION_FAILED",
                    "message": result["error"],
                },
            },
        )

    # Partial success: extraction worked but OCR had issues — return what we have
    invoice_data = _build_invoice_data(result["parsed"])
    meta = ResponseMeta(
        filename=filename,
        file_type=ftype,
        extraction_method=result["extraction_method"],
        processing_time_ms=result["processing_time_ms"],
    )
    return ExtractResponse(success=True, data=invoice_data, meta=meta)


@router.post(
    "/extract-text",
    response_model=RawTextResponse,
    summary="Extract raw text from PDF or image",
    description=(
        "Returns only the raw extracted text. "
        "Useful for debugging, validating OCR quality, and RapidAPI testing. "
        "Requires X-API-Key or X-RapidAPI-Proxy-Secret header."
    ),
    responses={
        401: {"description": "Missing or invalid API key"},
        413: {"description": "File exceeds size limit"},
        422: {"description": "Unsupported file type, empty file, or extraction error"},
    },
)
async def extract_text_only(
    response: Response,
    file: UploadFile = File(...),
    _: None = Depends(verify_api_key),
):
    content = await validate_upload(file)
    filename = file.filename or "unknown"
    ftype = _file_type(filename)

    result = extract_from_pdf(content) if ftype == "pdf" else extract_from_image(content)

    response.headers["X-Processing-Time"] = str(result["processing_time_ms"])

    if result.get("error") and not result["parsed"].get("raw_text"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "success": False,
                "error": {
                    "code": "EXTRACTION_FAILED",
                    "message": result["error"],
                },
            },
        )

    meta = ResponseMeta(
        filename=filename,
        file_type=ftype,
        extraction_method=result["extraction_method"],
        processing_time_ms=result["processing_time_ms"],
    )
    return RawTextResponse(
        success=True,
        data=RawTextData(raw_text=result["parsed"].get("raw_text", "")),
        meta=meta,
    )
