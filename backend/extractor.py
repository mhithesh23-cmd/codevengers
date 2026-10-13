"""
extractor.py - Document field extraction module for InvoiceTrust.

Extracts structured metadata (invoice_no, seller_name, buyer_name, gstin, amount,
invoice_date, po_no, quantity) from PDF document bytes using pdfplumber and regex.
"""

import io
import re
from typing import Any, Dict, Optional
import pdfplumber


def extract(file_bytes: bytes, doc_type: str = "invoice") -> Dict[str, Any]:
    """
    Extracts structured fields from PDF document bytes.

    :param file_bytes: Raw bytes of the PDF document.
    :param doc_type: Type of document ('invoice', 'po', 'delivery', 'contract').
    :return: Dictionary containing extracted fields.
    """
    extracted_text = ""
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"
    except Exception as e:
        print(f"Error parsing PDF with pdfplumber: {e}")

    # Standard clean fields
    data: Dict[str, Any] = {
        "doc_type": doc_type,
        "invoice_no": "",
        "seller_name": "",
        "buyer_name": "",
        "gstin": "",
        "amount": 0.0,
        "invoice_date": "",
        "po_no": "",
        "quantity": 0,
    }

    if not extracted_text:
        return data

    lines = [line.strip() for line in extracted_text.splitlines() if line.strip()]

    for line in lines:
        # Match 'Invoice No: ...' or 'Invoice Number: ...'
        inv_match = re.match(r"^Invoice\s*No(?:\.|umber)?\s*:\s*(.+)$", line, re.IGNORECASE)
        if inv_match:
            data["invoice_no"] = inv_match.group(1).strip()

        # Match 'Seller: ...' or 'Seller Name: ...'
        seller_match = re.match(r"^Seller(?:\s*Name)?\s*:\s*(.+)$", line, re.IGNORECASE)
        if seller_match:
            data["seller_name"] = seller_match.group(1).strip()

        # Match 'Buyer: ...' or 'Buyer Name: ...'
        buyer_match = re.match(r"^Buyer(?:\s*Name)?\s*:\s*(.+)$", line, re.IGNORECASE)
        if buyer_match:
            data["buyer_name"] = buyer_match.group(1).strip()

        # Match 'GSTIN: ...'
        gstin_match = re.match(r"^GSTIN\s*:\s*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})", line, re.IGNORECASE)
        if gstin_match:
            data["gstin"] = gstin_match.group(1).strip().upper()
        elif re.match(r"^GSTIN\s*:\s*(.+)$", line, re.IGNORECASE):
            raw_gst = re.match(r"^GSTIN\s*:\s*(.+)$", line, re.IGNORECASE).group(1).strip()
            data["gstin"] = raw_gst.upper()

        # Match 'Amount: ...'
        amount_match = re.match(r"^Amount\s*:\s*(.+)$", line, re.IGNORECASE)
        if amount_match:
            raw_amt = amount_match.group(1).strip()
            # Clean currency symbols and commas
            cleaned_amt = re.sub(r"[^\d.]", "", raw_amt)
            try:
                data["amount"] = float(cleaned_amt) if cleaned_amt else 0.0
            except ValueError:
                data["amount"] = 0.0

        # Match 'Date: ...' (YYYY-MM-DD or standard date format)
        date_match = re.match(r"^Date(?:\s*\(YYYY-MM-DD\))?\s*:\s*(\d{4}-\d{2}-\d{2})", line, re.IGNORECASE)
        if date_match:
            data["invoice_date"] = date_match.group(1).strip()
        elif re.match(r"^Date\s*:\s*(.+)$", line, re.IGNORECASE):
            data["invoice_date"] = re.match(r"^Date\s*:\s*(.+)$", line, re.IGNORECASE).group(1).strip()

        # Match 'PO No: ...' or 'PO Number: ...'
        po_match = re.match(r"^PO\s*No(?:\.|umber)?\s*:\s*(.+)$", line, re.IGNORECASE)
        if po_match:
            data["po_no"] = po_match.group(1).strip()

        # Match 'Quantity: ...'
        qty_match = re.match(r"^Quantity\s*:\s*(\d+)", line, re.IGNORECASE)
        if qty_match:
            try:
                data["quantity"] = int(qty_match.group(1).strip())
            except ValueError:
                data["quantity"] = 0

    return data


if __name__ == "__main__":
    import os
    print("Testing backend/extractor.py...")
    sample_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_data", "case1")
    inv_path = os.path.join(sample_dir, "invoice.pdf")
    if os.path.exists(inv_path):
        with open(inv_path, "rb") as f:
            res = extract(f.read(), "invoice")
        print("Case 1 Invoice Extracted:", res)
    else:
        print(f"Sample file not found at {inv_path}. Run sample_data/generate.py first.")
