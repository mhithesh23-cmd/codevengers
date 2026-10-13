"""
db.py - Supabase client setup and helper functions for InvoiceTrust.

Provides easy-to-use helpers to interact with Supabase database tables
(invoices, buyer_history, financed_registry, audit_chain) and private storage.
"""

import os
from typing import Any, Dict, Optional
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env file
load_dotenv()

# Read Supabase credentials from environment
SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL")
SUPABASE_KEY: Optional[str] = os.getenv("SUPABASE_KEY")

# Initialize client instance (will be None if .env keys are not yet configured)
supabase: Optional[Client] = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as err:
        print(f"Warning: Could not initialize Supabase client: {err}")


def get_client() -> Client:
    """
    Helper function to get the Supabase client.
    Reloads .env dynamically if credentials were added after launch.
    Raises ValueError with a clear message if credentials are missing.
    """
    global supabase
    if supabase is not None:
        return supabase

    load_dotenv(override=True)
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise ValueError(
            "Supabase credentials missing! Please configure SUPABASE_URL and SUPABASE_KEY in your .env file."
        )

    supabase = create_client(url, key)
    return supabase


def save_invoice(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insert a new invoice record into the 'invoices' table.

    :param data: Dictionary containing invoice columns (e.g., invoice_no, seller_name, buyer_name, amount)
    :return: Dict with 'success' status and 'data' or 'error' message
    """
    try:
        client = get_client()
        response = client.table("invoices").insert(data).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        return {"success": False, "error": f"Error saving invoice: {str(e)}"}


def get_invoice(invoice_id: Any) -> Dict[str, Any]:
    """
    Retrieve an invoice record by its ID.

    :param invoice_id: Primary key ID of the invoice
    :return: Dict with 'success' status and 'data' or 'error' message
    """
    try:
        client = get_client()
        response = client.table("invoices").select("*").eq("id", invoice_id).execute()
        if response.data and len(response.data) > 0:
            return {"success": True, "data": response.data[0]}
        return {"success": False, "error": f"Invoice with ID '{invoice_id}' not found."}
    except Exception as e:
        return {"success": False, "error": f"Error retrieving invoice {invoice_id}: {str(e)}"}


def get_all_invoices() -> Dict[str, Any]:
    """
    Retrieve all invoices from the 'invoices' table.

    :return: Dict with 'success' status and 'data' list or 'error' message
    """
    try:
        client = get_client()
        response = client.table("invoices").select("*").execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        return {"success": False, "error": f"Error fetching invoices: {str(e)}"}


def update_invoice(invoice_id: Any, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update an existing invoice record by ID.

    :param invoice_id: Primary key ID of the invoice
    :param data: Dictionary containing the fields to update (e.g., risk_score, decision, status)
    :return: Dict with 'success' status and 'data' or 'error' message
    """
    try:
        client = get_client()
        response = client.table("invoices").update(data).eq("id", invoice_id).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        return {"success": False, "error": f"Error updating invoice {invoice_id}: {str(e)}"}


def upload_file(path: str, file_bytes: bytes) -> Dict[str, Any]:
    """
    Upload a file (e.g., invoice PDF) to the private 'invoices' storage bucket in Supabase.

    :param path: Destination file path within the 'invoices' bucket (e.g. 'invoices/sample.pdf')
    :param file_bytes: Raw bytes of the file to upload
    :return: Dict with 'success' status and 'data' or 'error' message
    """
    try:
        client = get_client()
        response = client.storage.from_("invoices").upload(path, file_bytes)
        return {"success": True, "data": response}
    except Exception as e:
        return {"success": False, "error": f"Error uploading file to storage bucket: {str(e)}"}
