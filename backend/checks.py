"""
checks.py - Invoice financing risk assessment and document cross-checking engine.

Implements make_fingerprint and run_checks according to InvoiceTrust verification rules:
1. Already Financed / Duplicate Detection (weight: 40)
2. Purchase Order Match (weight: 25)
3. Delivery Verification (weight: 20)
4. Buyer Payment History (weight: 15)
5. Contract Validation (weight: 10)
6. Seller Exposure Limit (weight: 10)
7. GSTIN Format Verification (weight: 10)
8. Invoice Date Freshness (weight: 5)
"""

import hashlib
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from rapidfuzz import fuzz


def make_fingerprint(invoice: Dict[str, Any]) -> str:
    """
    Creates a deterministic SHA-256 fingerprint from invoice core attributes:
    lowercase, stripped seller_name + buyer_name + invoice_no + amount + invoice_date.
    """
    s_name = str(invoice.get("seller_name", "")).strip().lower()
    b_name = str(invoice.get("buyer_name", "")).strip().lower()
    inv_no = str(invoice.get("invoice_no", "")).strip().lower()
    
    try:
        amt_val = float(invoice.get("amount", 0.0))
        amt_str = f"{amt_val:.2f}"
    except (ValueError, TypeError):
        amt_str = str(invoice.get("amount", "")).strip().lower()
        
    inv_date = str(invoice.get("invoice_date", "")).strip().lower()

    raw_string = f"{s_name}{b_name}{inv_no}{amt_str}{inv_date}"
    return hashlib.sha256(raw_string.encode("utf-8")).hexdigest()


def run_checks(
    invoice: Dict[str, Any],
    po: Optional[Dict[str, Any]],
    delivery: Optional[Dict[str, Any]],
    contract: Optional[Dict[str, Any]],
    buyer_history: Optional[Dict[str, Any]],
    seller_financed_total: float,
    seller_unpaid_total: float,
    already_financed: bool,
) -> Dict[str, Any]:
    """
    Executes all cross-document and risk checks on the submitted invoice.

    :return: Dict containing risk_score (0-100), decision ('APPROVE'/'REVIEW'/'REJECT'), and reasons list.
    """
    reasons: List[Dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # a) Already financed / duplicate (Weight: 40)
    # -------------------------------------------------------------------------
    if already_financed:
        reasons.append({
            "check": "Duplicate & Prior Financing",
            "passed": False,
            "message": "Critical: Invoice or identical file hash has already been financed or registered.",
            "weight": 40,
        })
    else:
        reasons.append({
            "check": "Duplicate & Prior Financing",
            "passed": True,
            "message": "No duplicate record found. Invoice is unique.",
            "weight": 40,
        })

    # -------------------------------------------------------------------------
    # b) PO match: amount within 1%, po_no and quantity equal (Weight: 25)
    # -------------------------------------------------------------------------
    inv_amt = float(invoice.get("amount", 0.0) or 0.0)
    inv_po = str(invoice.get("po_no", "")).strip()
    inv_qty = int(invoice.get("quantity", 0) or 0)

    if not po or not any(po.values()):
        reasons.append({
            "check": "Purchase Order Match",
            "passed": False,
            "message": "Purchase Order (PO) document is missing.",
            "weight": 25,
        })
    else:
        po_amt = float(po.get("amount", 0.0) or 0.0)
        po_num = str(po.get("po_no", "")).strip()
        po_qty = int(po.get("quantity", 0) or 0)

        # Check amount within 1%
        amt_match = False
        if po_amt > 0:
            diff_ratio = abs(inv_amt - po_amt) / po_amt
            amt_match = diff_ratio <= 0.01

        po_num_match = (inv_po.lower() == po_num.lower()) if inv_po and po_num else True
        qty_match = (inv_qty == po_qty) if inv_qty > 0 and po_qty > 0 else True

        if amt_match and po_num_match and qty_match:
            reasons.append({
                "check": "Purchase Order Match",
                "passed": True,
                "message": f"PO matched: Amount (₹{inv_amt:,.2f}), PO No '{po_num}', and quantity ({inv_qty}) match.",
                "weight": 25,
            })
        else:
            mismatches = []
            if not amt_match:
                mismatches.append(f"Invoice amount ₹{inv_amt:,.2f} does not match PO amount ₹{po_amt:,.2f}")
            if not po_num_match:
                mismatches.append(f"Invoice PO No '{inv_po}' does not match PO '{po_num}'")
            if not qty_match:
                mismatches.append(f"Invoice quantity {inv_qty} does not match PO quantity {po_qty}")
            
            reasons.append({
                "check": "Purchase Order Match",
                "passed": False,
                "message": "; ".join(mismatches) if mismatches else "Purchase order details do not match invoice.",
                "weight": 25,
            })

    # -------------------------------------------------------------------------
    # c) Delivery: exists and quantity matches the invoice (Weight: 20)
    # -------------------------------------------------------------------------
    if not delivery or not any(delivery.values()):
        reasons.append({
            "check": "Delivery Receipt Verification",
            "passed": False,
            "message": "Delivery receipt document is missing.",
            "weight": 20,
        })
    else:
        del_qty = int(delivery.get("quantity", 0) or 0)
        if inv_qty > 0 and del_qty == inv_qty:
            reasons.append({
                "check": "Delivery Receipt Verification",
                "passed": True,
                "message": f"Delivery verified: Delivered quantity ({del_qty}) matches invoice ({inv_qty}).",
                "weight": 20,
            })
        else:
            reasons.append({
                "check": "Delivery Receipt Verification",
                "passed": False,
                "message": f"Delivery quantity ({del_qty}) does not match invoice quantity ({inv_qty}).",
                "weight": 20,
            })

    # -------------------------------------------------------------------------
    # d) Buyer payment history: on-time rate >= 70% (Weight: 15); missing = fail
    # -------------------------------------------------------------------------
    if not buyer_history:
        reasons.append({
            "check": "Buyer Payment History",
            "passed": False,
            "message": f"No payment history found for buyer '{invoice.get('buyer_name')}'.",
            "weight": 15,
        })
    else:
        total_bills = float(buyer_history.get("total_bills", 0) or 0)
        paid_on_time = float(buyer_history.get("paid_on_time", 0) or 0)
        avg_delay = buyer_history.get("avg_delay_days", 0)

        on_time_rate = (paid_on_time / total_bills) if total_bills > 0 else 0.0
        if on_time_rate >= 0.70:
            reasons.append({
                "check": "Buyer Payment History",
                "passed": True,
                "message": f"Strong buyer history: {on_time_rate * 100:.1f}% on-time payment rate ({int(paid_on_time)}/{int(total_bills)} bills, avg delay {avg_delay} days).",
                "weight": 15,
            })
        else:
            reasons.append({
                "check": "Buyer Payment History",
                "passed": False,
                "message": f"Risky buyer history: On-time rate is only {on_time_rate * 100:.1f}% (below 70% threshold, avg delay {avg_delay} days).",
                "weight": 15,
            })

    # -------------------------------------------------------------------------
    # e) Contract: exists and seller/buyer names match with rapidfuzz >= 85 (Weight: 10)
    # -------------------------------------------------------------------------
    if not contract or not any(contract.values()):
        reasons.append({
            "check": "Contract Validation",
            "passed": False,
            "message": "Master contract / agreement document is missing.",
            "weight": 10,
        })
    else:
        c_seller = str(contract.get("seller_name", "")).strip()
        c_buyer = str(contract.get("buyer_name", "")).strip()
        inv_seller = str(invoice.get("seller_name", "")).strip()
        inv_buyer = str(invoice.get("buyer_name", "")).strip()

        seller_score = fuzz.token_sort_ratio(inv_seller, c_seller) if inv_seller and c_seller else 0.0
        buyer_score = fuzz.token_sort_ratio(inv_buyer, c_buyer) if inv_buyer and c_buyer else 0.0

        if seller_score >= 85 and buyer_score >= 85:
            reasons.append({
                "check": "Contract Validation",
                "passed": True,
                "message": f"Contract verified: Seller match ({seller_score:.0f}%), Buyer match ({buyer_score:.0f}%).",
                "weight": 10,
            })
        else:
            reasons.append({
                "check": "Contract Validation",
                "passed": False,
                "message": f"Contract entity mismatch: Seller match score {seller_score:.0f}%, Buyer match score {buyer_score:.0f}% (threshold 85%).",
                "weight": 10,
            })

    # -------------------------------------------------------------------------
    # f) Seller exposure: (financed + this amount) / unpaid <= 80% (Weight: 10)
    # -------------------------------------------------------------------------
    if seller_financed_total == 0:
        reasons.append({
            "check": "Seller Credit Exposure",
            "passed": True,
            "message": "Seller exposure is healthy (no outstanding funded invoices).",
            "weight": 10,
        })
    else:
        denom = max(seller_unpaid_total, inv_amt)
        exposure_ratio = (seller_financed_total + inv_amt) / denom if denom > 0 else 1.0
        if exposure_ratio <= 0.80:
            reasons.append({
                "check": "Seller Credit Exposure",
                "passed": True,
                "message": f"Seller exposure is {exposure_ratio * 100:.1f}%, within the 80% safety limit.",
                "weight": 10,
            })
        else:
            reasons.append({
                "check": "Seller Credit Exposure",
                "passed": False,
                "message": f"High seller exposure: {exposure_ratio * 100:.1f}% exceeds the 80% threshold.",
                "weight": 10,
            })

    # -------------------------------------------------------------------------
    # g) GSTIN valid 15-char Indian format (Weight: 10)
    # -------------------------------------------------------------------------
    gstin = str(invoice.get("gstin", "")).strip().upper()
    gstin_regex = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    if gstin and re.match(gstin_regex, gstin):
        reasons.append({
            "check": "GSTIN Format Verification",
            "passed": True,
            "message": f"Valid 15-character Indian GSTIN format ({gstin}).",
            "weight": 10,
        })
    else:
        reasons.append({
            "check": "GSTIN Format Verification",
            "passed": False,
            "message": f"Invalid GSTIN '{gstin}'. Must be a valid 15-character Indian format.",
            "weight": 10,
        })

    # -------------------------------------------------------------------------
    # h) Date not in future and not older than 180 days (Weight: 5)
    # -------------------------------------------------------------------------
    inv_date_str = str(invoice.get("invoice_date", "")).strip()
    date_passed = False
    date_msg = ""
    try:
        inv_dt = datetime.strptime(inv_date_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        if inv_dt > today:
            date_passed = False
            date_msg = f"Invoice date ({inv_date_str}) is in the future."
        elif (today - inv_dt).days > 180:
            date_passed = False
            date_msg = f"Invoice date ({inv_date_str}) is older than 180 days ({(today - inv_dt).days} days old)."
        else:
            date_passed = True
            date_msg = f"Invoice date ({inv_date_str}) is fresh (within 180 days)."
    except Exception:
        date_passed = False
        date_msg = f"Invalid or unparseable invoice date format: '{inv_date_str}'."

    reasons.append({
        "check": "Invoice Date Freshness",
        "passed": date_passed,
        "message": date_msg,
        "weight": 5,
    })

    # -------------------------------------------------------------------------
    # Scoring & Final Decision
    # <30 APPROVE, 30–60 REVIEW, >60 REJECT
    # -------------------------------------------------------------------------
    failed_weight = sum(r["weight"] for r in reasons if not r["passed"])
    risk_score = min(100, failed_weight)

    po_check = next((r for r in reasons if r["check"] == "Purchase Order Match"), None)
    if po_check and not po_check["passed"]:
        # An unverified PO must trigger human review
        risk_score = max(risk_score, 35)

    if already_financed:
        decision = "REJECT"
        risk_score = max(risk_score, 70)
    elif risk_score < 30:
        decision = "APPROVE"
    elif risk_score <= 60:
        decision = "REVIEW"
    else:
        decision = "REJECT"

    return {
        "risk_score": risk_score,
        "decision": decision,
        "reasons": reasons,
    }
