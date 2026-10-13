"""
main.py - FastAPI application entry point for InvoiceTrust.

Provides endpoints for document upload, automated verification checks,
audit hash-chain tracking, lender approval workflow, and integrity verification.
"""

import hashlib
import os
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.audit import add_event, get_events, verify_all
from backend.checks import make_fingerprint, run_checks
from backend.db import get_all_invoices, get_client
from backend.extractor import extract

app = FastAPI(
    title="InvoiceTrust API",
    description="Invoice-financing verification platform for lenders",
    version="1.0.0",
)

# Enable CORS for all origins (hackathon development only)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Health check endpoint to verify that backend is running."""
    return {"status": "ok"}


@app.get("/test-db")
def test_db():
    """Test endpoint that reads the invoices table in Supabase and returns the row count."""
    result = get_all_invoices()
    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=f"Database connection failed: {result.get('error')}",
        )
    invoices = result.get("data", [])
    return {
        "status": "connected",
        "table": "invoices",
        "row_count": len(invoices),
        "message": "Supabase connection is working successfully!",
    }


@app.post("/upload")
async def upload_documents(
    invoice: UploadFile = File(...),
    po: Optional[UploadFile] = File(None),
    delivery: Optional[UploadFile] = File(None),
    contract: Optional[UploadFile] = File(None),
):
    """
    Upload invoice and supporting documents for automated verification.
    Extracts fields, cross-checks against PO/delivery/contract, performs risk scoring,
    persists records, and creates cryptographic hash-chain audit events.
    """
    try:
        client = get_client()
        session_id = str(uuid.uuid4())

        # 1. Read bytes and compute SHA-256 for each document
        inv_bytes = await invoice.read()
        inv_hash = hashlib.sha256(inv_bytes).hexdigest()

        po_bytes = await po.read() if po and po.filename else None
        del_bytes = await delivery.read() if delivery and delivery.filename else None
        con_bytes = await contract.read() if contract and contract.filename else None

        # 2. Upload files to private Supabase Storage bucket 'invoices'
        inv_storage_path = f"{session_id}/invoice.pdf"
        try:
            client.storage.from_("invoices").upload(inv_storage_path, inv_bytes, file_options={"upsert": "true"})
        except Exception:
            try:
                client.storage.create_bucket("invoices", options={"public": False})
                client.storage.from_("invoices").upload(inv_storage_path, inv_bytes, file_options={"upsert": "true"})
            except Exception as e_upload:
                print(f"Warning: Storage upload notice: {e_upload}")

        if po_bytes:
            try:
                client.storage.from_("invoices").upload(f"{session_id}/po.pdf", po_bytes, file_options={"upsert": "true"})
            except Exception:
                pass

        if del_bytes:
            try:
                client.storage.from_("invoices").upload(f"{session_id}/delivery.pdf", del_bytes, file_options={"upsert": "true"})
            except Exception:
                pass

        if con_bytes:
            try:
                client.storage.from_("invoices").upload(f"{session_id}/contract.pdf", con_bytes, file_options={"upsert": "true"})
            except Exception:
                pass

        # 3. Extract metadata from documents
        ext_inv = extract(inv_bytes, "invoice")
        ext_po = extract(po_bytes, "po") if po_bytes else None
        ext_del = extract(del_bytes, "delivery") if del_bytes else None
        ext_con = extract(con_bytes, "contract") if con_bytes else None

        # 4. Look up buyer_history by buyer_name (case-insensitive)
        buyer_name = ext_inv.get("buyer_name", "").strip()
        buyer_hist = None
        if buyer_name:
            bh_res = client.table("buyer_history").select("*").ilike("buyer_name", buyer_name).execute()
            if bh_res.data and len(bh_res.data) > 0:
                buyer_hist = bh_res.data[0]

        # 5. Calculate seller exposure
        seller_name = ext_inv.get("seller_name", "").strip()
        seller_invs = []
        if seller_name:
            s_res = client.table("invoices").select("amount, status").ilike("seller_name", seller_name).execute()
            seller_invs = s_res.data or []

        seller_financed_total = sum(
            float(i.get("amount") or 0.0) for i in seller_invs if i.get("status") == "Funded"
        )
        current_amount = float(ext_inv.get("amount") or 0.0)
        seller_unpaid_total = sum(
            float(i.get("amount") or 0.0) for i in seller_invs if i.get("status") != "Paid"
        ) + current_amount

        # 6. Generate fingerprint and check if already financed / duplicate
        fingerprint = make_fingerprint(ext_inv)

        fin_reg = client.table("financed_registry").select("fingerprint").eq("fingerprint", fingerprint).execute().data or []
        hash_matches = client.table("invoices").select("id").eq("file_hash", inv_hash).execute().data or []

        already_financed = (len(fin_reg) > 0) or (len(hash_matches) > 0)

        # 7. Run risk checks
        check_res = run_checks(
            invoice=ext_inv,
            po=ext_po,
            delivery=ext_del,
            contract=ext_con,
            buyer_history=buyer_hist,
            seller_financed_total=seller_financed_total,
            seller_unpaid_total=seller_unpaid_total,
            already_financed=already_financed,
        )

        risk_score = check_res["risk_score"]
        decision = check_res["decision"]
        reasons = check_res["reasons"]

        status_map = {"APPROVE": "Approved", "REVIEW": "Review", "REJECT": "Rejected"}
        inv_status = status_map.get(decision, "Review")

        # 8. Insert record into invoices table
        record = {
            "invoice_no": ext_inv.get("invoice_no") or f"INV-{session_id[:8].upper()}",
            "seller_name": ext_inv.get("seller_name") or "Unknown Seller",
            "buyer_name": ext_inv.get("buyer_name") or "Unknown Buyer",
            "gstin": ext_inv.get("gstin") or "",
            "amount": ext_inv.get("amount") or 0.0,
            "invoice_date": ext_inv.get("invoice_date") or datetime.now().strftime("%Y-%m-%d"),
            "po_no": ext_inv.get("po_no") or "",
            "quantity": ext_inv.get("quantity") or 0,
            "file_path": inv_storage_path,
            "file_hash": inv_hash,
            "risk_score": risk_score,
            "decision": decision,
            "reasons": reasons,
            "status": inv_status,
        }

        insert_res = client.table("invoices").insert(record).execute()
        if not insert_res.data:
            raise HTTPException(status_code=500, detail="Failed to insert invoice into database.")
        
        saved_inv = insert_res.data[0]
        invoice_id = saved_inv["id"]

        # 9. Append immutable hash-chain audit events
        add_event(invoice_id, "UPLOADED", inv_hash)
        add_event(invoice_id, "VERIFIED", inv_hash)
        decision_event = "APPROVED" if decision == "APPROVE" else ("REJECTED" if decision == "REJECT" else "REVIEW")
        add_event(invoice_id, decision_event, inv_hash)

        # 10. Return verified response
        return {
            "invoice_id": invoice_id,
            "extracted": ext_inv,
            "risk_score": risk_score,
            "decision": decision,
            "reasons": reasons,
            "status": inv_status,
            "fingerprint": fingerprint,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in /upload: {e}")
        return {"error": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR


@app.get("/invoices")
def get_invoices():
    """Retrieve all invoices, newest first, without internal file_path."""
    try:
        client = get_client()
        res = client.table("invoices").select("*").order("created_at", desc=True).execute()
        rows = res.data or []
        for row in rows:
            row.pop("file_path", None)
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch invoices: {str(e)}")


@app.get("/invoice/{invoice_id}")
def get_invoice_detail(invoice_id: Any):
    """Retrieve an invoice without file_path, including its chronological audit events."""
    try:
        client = get_client()
        res = client.table("invoices").select("*").eq("id", invoice_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail=f"Invoice #{invoice_id} not found.")

        invoice_data = res.data[0]
        invoice_data.pop("file_path", None)
        invoice_data["events"] = get_events(invoice_id)
        return invoice_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving invoice: {str(e)}")


@app.post("/invoice/{invoice_id}/approve")
def approve_and_fund_invoice(invoice_id: Any):
    """
    Marks an invoice as 'Funded', inserts its fingerprint into financed_registry,
    and appends a FUNDED event to the audit hash chain.
    """
    try:
        client = get_client()
        res = client.table("invoices").select("*").eq("id", invoice_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail=f"Invoice #{invoice_id} not found.")

        inv = res.data[0]

        # Update status to Funded
        client.table("invoices").update({"status": "Funded"}).eq("id", invoice_id).execute()

        # Insert fingerprint into financed_registry
        fp = make_fingerprint(inv)
        client.table("financed_registry").insert({
            "fingerprint": fp,
            "invoice_id": invoice_id,
            "lender": "DemoLender",
            "financed_at": datetime.now().isoformat(),
        }).execute()

        # Add audit hash chain block
        add_event(invoice_id, "FUNDED", inv.get("file_hash", ""))

        return {"status": "ok", "message": f"Invoice #{invoice_id} approved and funded successfully.", "invoice_id": invoice_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Approval failed: {str(e)}")


@app.post("/invoice/{invoice_id}/paid")
def mark_invoice_paid(invoice_id: Any):
    """Marks an invoice as 'Paid' and appends a PAID event to the audit hash chain."""
    try:
        client = get_client()
        res = client.table("invoices").select("*").eq("id", invoice_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail=f"Invoice #{invoice_id} not found.")

        inv = res.data[0]
        client.table("invoices").update({"status": "Paid"}).eq("id", invoice_id).execute()
        add_event(invoice_id, "PAID", inv.get("file_hash", ""))

        return {"status": "ok", "message": f"Invoice #{invoice_id} marked as Paid.", "invoice_id": invoice_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mark paid failed: {str(e)}")


@app.get("/audit/{invoice_id}")
def get_audit_trail(invoice_id: Any):
    """Retrieve chronological audit hash-chain events for a given invoice."""
    try:
        return get_events(invoice_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch audit events: {str(e)}")


@app.get("/verify")
def verify_system_integrity():
    """Validates the audit hash-chain links and checks storage files against stored hashes."""
    try:
        return verify_all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification check failed: {str(e)}")


# -----------------------------------------------------------------------------
# DEMO UTILITIES
# -----------------------------------------------------------------------------
@app.post("/demo/tamper/{invoice_id}")
def demo_tamper_file(invoice_id: Any):
    """
    DEMO ONLY: Simulates off-chain file tampering by modifying the stored PDF in Storage.
    Appends extra bytes to invalidate the SHA-256 hash, causing /verify to report corruption.
    """
    try:
        client = get_client()
        res = client.table("invoices").select("file_path, invoice_no").eq("id", invoice_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail=f"Invoice #{invoice_id} not found.")

        inv = res.data[0]
        f_path = inv.get("file_path")
        if not f_path:
            raise HTTPException(status_code=400, detail="No file_path recorded for this invoice.")

        # Download original PDF from Supabase Storage
        file_bytes = client.storage.from_("invoices").download(f_path)
        # Corrupt file by appending arbitrary bytes
        tampered_bytes = file_bytes + b"\n% TAMPERED INVOICE DEMO DATA"

        # Overwrite file in storage
        client.storage.from_("invoices").upload(f_path, tampered_bytes, file_options={"upsert": "true"})

        return {
            "status": "ok",
            "message": f"Tampered file for invoice #{inv.get('invoice_no')} in Supabase Storage. Run /verify to see detection.",
            "invoice_id": invoice_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tamper demo failed: {str(e)}")


@app.post("/demo/reset")
def demo_reset_data():
    """
    DEMO ONLY: Cleans up demo data by deleting all rows from invoices,
    financed_registry, and audit_chain tables (preserves buyer_history).
    """
    try:
        client = get_client()
        # Delete from audit_chain, financed_registry, and invoices
        try:
            client.table("audit_chain").delete().neq("id", -999999).execute()
        except Exception as e1:
            print(f"Reset audit_chain notice: {e1}")

        try:
            client.table("financed_registry").delete().neq("lender", "__NON_EXISTENT__").execute()
        except Exception as e2:
            print(f"Reset financed_registry notice: {e2}")

        try:
            client.table("invoices").delete().neq("id", -999999).execute()
        except Exception as e3:
            print(f"Reset invoices notice: {e3}")

        return {"status": "ok", "message": "Demo data reset successfully (buyer_history preserved)."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Demo reset failed: {str(e)}")


# -----------------------------------------------------------------------------
# Frontend Static Files Mount
# -----------------------------------------------------------------------------
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
