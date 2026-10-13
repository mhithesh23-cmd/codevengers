"""
audit.py - Cryptographic SHA-256 hash-chain audit logging and file verification.

Maintains a tamper-evident sequence of state events for every invoice in Supabase:
1. add_event(invoice_id, event, file_hash): adds next block to the hash-chain
2. get_events(invoice_id): retrieves ordered audit trail
3. verify_chain(): recomputes SHA-256 hashes sequentially to detect chain tampering
4. verify_files(): downloads stored invoice PDFs from Supabase Storage and compares hashes
5. verify_all(): returns full verification status and list of issues
"""

import hashlib
from typing import Any, Dict, List, Tuple
from backend.db import get_client


def add_event(invoice_id: Any, event: str, file_hash: str) -> Dict[str, Any]:
    """
    Appends an immutable event to the audit_chain table using SHA-256 hash chaining.
    prev_hash = latest block's hash or 'GENESIS'.
    hash = sha256(f"{prev_hash}|{invoice_id}|{event}|{file_hash}").
    """
    client = get_client()

    # Retrieve the latest block's hash to maintain link integrity
    latest_block = (
        client.table("audit_chain")
        .select("hash")
        .order("id", desc=True)
        .limit(1)
        .execute()
    )

    if latest_block.data and len(latest_block.data) > 0:
        prev_hash = latest_block.data[0].get("hash") or "GENESIS"
    else:
        prev_hash = "GENESIS"

    raw_payload = f"{prev_hash}|{invoice_id}|{event}|{file_hash}"
    current_hash = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

    record = {
        "invoice_id": invoice_id,
        "event": event,
        "file_hash": file_hash,
        "prev_hash": prev_hash,
        "hash": current_hash,
    }

    response = client.table("audit_chain").insert(record).execute()
    return response.data[0] if response.data else record


def get_events(invoice_id: Any) -> List[Dict[str, Any]]:
    """
    Returns all audit events for a specific invoice ordered chronologically by id.
    """
    client = get_client()
    response = (
        client.table("audit_chain")
        .select("*")
        .eq("invoice_id", invoice_id)
        .order("id", desc=False)
        .execute()
    )
    return response.data or []


def verify_chain() -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Recomputes every block in audit_chain in id order.
    Returns (chain_ok, problems).
    """
    client = get_client()
    rows = (
        client.table("audit_chain")
        .select("*")
        .order("id", desc=False)
        .execute()
        .data or []
    )

    problems: List[Dict[str, Any]] = []
    expected_prev = "GENESIS"

    for row in rows:
        stored_prev = row.get("prev_hash")
        stored_hash = row.get("hash")
        inv_id = row.get("invoice_id")
        event = row.get("event")
        f_hash = row.get("file_hash")

        if stored_prev != expected_prev:
            problems.append({
                "invoice_id": inv_id,
                "issue": f"Chain broken at Block #{row.get('id')}: prev_hash '{stored_prev}' does not match expected '{expected_prev}'",
            })

        recomputed = hashlib.sha256(f"{stored_prev}|{inv_id}|{event}|{f_hash}".encode("utf-8")).hexdigest()
        if stored_hash != recomputed:
            problems.append({
                "invoice_id": inv_id,
                "issue": f"Tampered hash detected at Block #{row.get('id')}: stored '{stored_hash}' vs recomputed '{recomputed}'",
            })

        expected_prev = stored_hash

    return (len(problems) == 0, problems)


def verify_files() -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Downloads every invoice PDF from Supabase Storage and recalculates its SHA-256 hash.
    Compares against the database file_hash to detect off-chain file tampering.
    Returns (files_ok, problems).
    """
    client = get_client()
    invoices = client.table("invoices").select("id, invoice_no, file_path, file_hash").execute().data or []
    problems: List[Dict[str, Any]] = []

    for inv in invoices:
        f_path = inv.get("file_path")
        stored_fhash = inv.get("file_hash")
        inv_id = inv.get("id")

        if not f_path or not stored_fhash:
            continue

        try:
            # Download file bytes from private storage bucket "invoices"
            file_bytes = client.storage.from_("invoices").download(f_path)
            computed_hash = hashlib.sha256(file_bytes).hexdigest()

            if computed_hash != stored_fhash:
                problems.append({
                    "invoice_id": inv_id,
                    "issue": f"File content tampered for invoice #{inv.get('invoice_no')}: Expected hash {stored_fhash[:12]}... but storage file hash is {computed_hash[:12]}...",
                })
        except Exception as e:
            problems.append({
                "invoice_id": inv_id,
                "issue": f"Could not download file for invoice #{inv.get('invoice_no')}: {str(e)}",
            })

    return (len(problems) == 0, problems)


def verify_all() -> Dict[str, Any]:
    """
    Full cryptographic health check across the audit hash-chain and physical Storage bucket files.
    """
    chain_ok, chain_problems = verify_chain()
    files_ok, file_problems = verify_files()
    all_problems = chain_problems + file_problems

    return {
        "chain_ok": chain_ok,
        "files_ok": files_ok,
        "problems": all_problems,
    }
