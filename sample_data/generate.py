"""
generate.py - Synthetic document generator for InvoiceTrust test cases.

Generates sample PDF documents (invoice, po, delivery, contract) for Cases 1 through 6
using ReportLab with clean, single-line "Label: Value" formatting for robust extraction.
"""

import os
import shutil
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def create_pdf(file_path: str, doc_title: str, fields: list):
    """Draws a clean, single-page PDF with 'Label: value' on distinct lines."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    c = canvas.Canvas(file_path, pagesize=letter)
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 730, doc_title.upper())
    
    c.setLineWidth(1)
    c.line(72, 720, 540, 720)
    
    # Key-value lines
    c.setFont("Helvetica", 12)
    y = 690
    for label, val in fields:
        c.drawString(72, y, f"{label}: {val}")
        y -= 28
    
    c.showPage()
    c.save()


def generate_all_cases():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    today = datetime.now()
    inv_date = (today - timedelta(days=5)).strftime("%Y-%m-%d")
    po_date = (today - timedelta(days=12)).strftime("%Y-%m-%d")
    delivery_date = (today - timedelta(days=4)).strftime("%Y-%m-%d")
    contract_date = (today - timedelta(days=25)).strftime("%Y-%m-%d")

    seller = "Bharat Electronics Ltd"
    buyer = "Reliance Industries Ltd"
    gstin = "27AABCU9603R1ZM"
    
    # ==========================================
    # Case 1: Perfect Match
    # ==========================================
    case1_dir = os.path.join(base_dir, "case1")
    os.makedirs(case1_dir, exist_ok=True)
    
    c1_inv = [
        ("Invoice No", "INV-2026-001"),
        ("Seller", seller),
        ("Buyer", buyer),
        ("GSTIN", gstin),
        ("Amount", "150000"),
        ("Date (YYYY-MM-DD)", inv_date),
        ("PO No", "PO-89012"),
        ("Quantity", "100"),
    ]
    create_pdf(os.path.join(case1_dir, "invoice.pdf"), "Tax Invoice", c1_inv)
    
    c1_po = [
        ("PO No", "PO-89012"),
        ("Seller", seller),
        ("Buyer", buyer),
        ("Amount", "150000"),
        ("Date (YYYY-MM-DD)", po_date),
        ("Quantity", "100"),
    ]
    create_pdf(os.path.join(case1_dir, "po.pdf"), "Purchase Order", c1_po)
    
    c1_del = [
        ("PO No", "PO-89012"),
        ("Seller", seller),
        ("Buyer", buyer),
        ("Date (YYYY-MM-DD)", delivery_date),
        ("Quantity", "100"),
    ]
    create_pdf(os.path.join(case1_dir, "delivery.pdf"), "Delivery Receipt", c1_del)
    
    c1_con = [
        ("Seller", seller),
        ("Buyer", buyer),
        ("Date (YYYY-MM-DD)", contract_date),
    ]
    create_pdf(os.path.join(case1_dir, "contract.pdf"), "Master Services Agreement", c1_con)
    print("Generated Case 1 (Perfect Match)")

    # ==========================================
    # Case 2: Exact duplicate of Case 1 (same file bytes)
    # ==========================================
    case2_dir = os.path.join(base_dir, "case2")
    os.makedirs(case2_dir, exist_ok=True)
    for fname in ["invoice.pdf", "po.pdf", "delivery.pdf", "contract.pdf"]:
        shutil.copyfile(os.path.join(case1_dir, fname), os.path.join(case2_dir, fname))
    print("Generated Case 2 (Exact Duplicate of Case 1)")

    # ==========================================
    # Case 3: Invoice Amount 20% higher than PO (PO 150000, Invoice 180000)
    # ==========================================
    case3_dir = os.path.join(base_dir, "case3")
    os.makedirs(case3_dir, exist_ok=True)
    
    c3_inv = [
        ("Invoice No", "INV-2026-003"),
        ("Seller", seller),
        ("Buyer", buyer),
        ("GSTIN", gstin),
        ("Amount", "180000"),  # 20% higher than 150000
        ("Date (YYYY-MM-DD)", inv_date),
        ("PO No", "PO-89013"),
        ("Quantity", "100"),
    ]
    create_pdf(os.path.join(case3_dir, "invoice.pdf"), "Tax Invoice", c3_inv)
    
    c3_po = [
        ("PO No", "PO-89013"),
        ("Seller", seller),
        ("Buyer", buyer),
        ("Amount", "150000"),
        ("Date (YYYY-MM-DD)", po_date),
        ("Quantity", "100"),
    ]
    create_pdf(os.path.join(case3_dir, "po.pdf"), "Purchase Order", c3_po)
    
    c3_del = [
        ("PO No", "PO-89013"),
        ("Seller", seller),
        ("Buyer", buyer),
        ("Date (YYYY-MM-DD)", delivery_date),
        ("Quantity", "100"),
    ]
    create_pdf(os.path.join(case3_dir, "delivery.pdf"), "Delivery Receipt", c3_del)
    create_pdf(os.path.join(case3_dir, "contract.pdf"), "Master Services Agreement", c1_con)
    print("Generated Case 3 (Amount Mismatch 20% higher)")

    # ==========================================
    # Case 4: No delivery.pdf
    # ==========================================
    case4_dir = os.path.join(base_dir, "case4")
    os.makedirs(case4_dir, exist_ok=True)
    
    c4_inv = [
        ("Invoice No", "INV-2026-004"),
        ("Seller", seller),
        ("Buyer", buyer),
        ("GSTIN", gstin),
        ("Amount", "150000"),
        ("Date (YYYY-MM-DD)", inv_date),
        ("PO No", "PO-89014"),
        ("Quantity", "100"),
    ]
    create_pdf(os.path.join(case4_dir, "invoice.pdf"), "Tax Invoice", c4_inv)
    
    c4_po = [
        ("PO No", "PO-89014"),
        ("Seller", seller),
        ("Buyer", buyer),
        ("Amount", "150000"),
        ("Date (YYYY-MM-DD)", po_date),
        ("Quantity", "100"),
    ]
    create_pdf(os.path.join(case4_dir, "po.pdf"), "Purchase Order", c4_po)
    create_pdf(os.path.join(case4_dir, "contract.pdf"), "Master Services Agreement", c1_con)
    # Notice: NO delivery.pdf is created for Case 4!
    print("Generated Case 4 (Missing Delivery)")

    # ==========================================
    # Case 5: Buyer 'Slowpay Retail Pvt Ltd', everything else matches
    # ==========================================
    case5_dir = os.path.join(base_dir, "case5")
    os.makedirs(case5_dir, exist_ok=True)
    slow_buyer = "Slowpay Retail Pvt Ltd"
    
    c5_inv = [
        ("Invoice No", "INV-2026-005"),
        ("Seller", seller),
        ("Buyer", slow_buyer),
        ("GSTIN", gstin),
        ("Amount", "150000"),
        ("Date (YYYY-MM-DD)", inv_date),
        ("PO No", "PO-89015"),
        ("Quantity", "100"),
    ]
    create_pdf(os.path.join(case5_dir, "invoice.pdf"), "Tax Invoice", c5_inv)
    
    c5_po = [
        ("PO No", "PO-89015"),
        ("Seller", seller),
        ("Buyer", slow_buyer),
        ("Amount", "150000"),
        ("Date (YYYY-MM-DD)", po_date),
        ("Quantity", "100"),
    ]
    create_pdf(os.path.join(case5_dir, "po.pdf"), "Purchase Order", c5_po)
    
    c5_del = [
        ("PO No", "PO-89015"),
        ("Seller", seller),
        ("Buyer", slow_buyer),
        ("Date (YYYY-MM-DD)", delivery_date),
        ("Quantity", "100"),
    ]
    create_pdf(os.path.join(case5_dir, "delivery.pdf"), "Delivery Receipt", c5_del)
    
    c5_con = [
        ("Seller", seller),
        ("Buyer", slow_buyer),
        ("Date (YYYY-MM-DD)", contract_date),
    ]
    create_pdf(os.path.join(case5_dir, "contract.pdf"), "Master Services Agreement", c5_con)
    print("Generated Case 5 (Slowpay Retail Pvt Ltd)")

    # ==========================================
    # Case 6: Copy of Case 1 with a different invoice number (used for tamper demo)
    # ==========================================
    case6_dir = os.path.join(base_dir, "case6")
    os.makedirs(case6_dir, exist_ok=True)
    
    c6_inv = [
        ("Invoice No", "INV-2026-006"),
        ("Seller", seller),
        ("Buyer", buyer),
        ("GSTIN", gstin),
        ("Amount", "150000"),
        ("Date (YYYY-MM-DD)", inv_date),
        ("PO No", "PO-89016"),
        ("Quantity", "100"),
    ]
    create_pdf(os.path.join(case6_dir, "invoice.pdf"), "Tax Invoice", c6_inv)
    
    c6_po = [
        ("PO No", "PO-89016"),
        ("Seller", seller),
        ("Buyer", buyer),
        ("Amount", "150000"),
        ("Date (YYYY-MM-DD)", po_date),
        ("Quantity", "100"),
    ]
    create_pdf(os.path.join(case6_dir, "po.pdf"), "Purchase Order", c6_po)
    
    c6_del = [
        ("PO No", "PO-89016"),
        ("Seller", seller),
        ("Buyer", buyer),
        ("Date (YYYY-MM-DD)", delivery_date),
        ("Quantity", "100"),
    ]
    create_pdf(os.path.join(case6_dir, "delivery.pdf"), "Delivery Receipt", c6_del)
    create_pdf(os.path.join(case6_dir, "contract.pdf"), "Master Services Agreement", c1_con)
    print("Generated Case 6 (Copy of Case 1 for tamper demo)")


if __name__ == "__main__":
    generate_all_cases()
