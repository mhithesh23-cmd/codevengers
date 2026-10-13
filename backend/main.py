"""
main.py - FastAPI application entry point for InvoiceTrust.

Handles server initialization, CORS configuration, and baseline endpoints.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.db import get_all_invoices

# Initialize the FastAPI application
app = FastAPI(
    title="InvoiceTrust API",
    description="Invoice-financing verification platform for lenders",
    version="0.1.0",
)

# Enable Cross-Origin Resource Sharing (CORS) for all origins (hackathon development only)
# This allows the frontend (built with HTML, Tailwind, vanilla JS) to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """
    Health check endpoint to verify that the backend server is running.
    Returns: {"status": "ok"}
    """
    return {"status": "ok"}


@app.get("/test-db")
def test_db():
    """
    Test endpoint to verify database connectivity.
    Reads the 'invoices' table in Supabase and returns the row count.
    """
    result = get_all_invoices()

    # If the database query failed or credentials are not set, return HTTP 500 error
    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=f"Database connection failed: {result.get('error')}"
        )

    invoices = result.get("data", [])
    return {
        "status": "connected",
        "table": "invoices",
        "row_count": len(invoices),
        "message": "Supabase connection is working successfully!"
    }
