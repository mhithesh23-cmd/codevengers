"""
test_flow.py - End-to-end verification script for InvoiceTrust 9-step flow.
"""

import os
import sys

# Ensure UTF-8 output encoding for Windows shells
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
base_sample_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_data")


def run_9_step_test():
    print("=" * 70)
    print("STARTING INVOICETRUST 9-STEP VERIFICATION FLOW")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # STEP 1: POST /demo/reset
    # -------------------------------------------------------------------------
    print("\n[STEP 1] Resetting demo data...")
    res = client.post("/demo/reset")
    assert res.status_code == 200, f"Reset failed: {res.text}"
    print("Result:", res.json())

    # -------------------------------------------------------------------------
    # STEP 2: Upload Case 1 -> expect APPROVE -> POST approve -> status Funded
    # -------------------------------------------------------------------------
    print("\n[STEP 2] Uploading Case 1 (Perfect Match)...")
    c1_dir = os.path.join(base_sample_dir, "case1")
    with open(os.path.join(c1_dir, "invoice.pdf"), "rb") as f_inv, \
         open(os.path.join(c1_dir, "po.pdf"), "rb") as f_po, \
         open(os.path.join(c1_dir, "delivery.pdf"), "rb") as f_del, \
         open(os.path.join(c1_dir, "contract.pdf"), "rb") as f_con:
        
        files = {
            "invoice": ("invoice.pdf", f_inv, "application/pdf"),
            "po": ("po.pdf", f_po, "application/pdf"),
            "delivery": ("delivery.pdf", f_del, "application/pdf"),
            "contract": ("contract.pdf", f_con, "application/pdf"),
        }
        res2 = client.post("/upload", files=files)

    assert res2.status_code == 200, f"Upload Case 1 failed: {res2.text}"
    case1_data = res2.json()
    case1_id = case1_data["invoice_id"]
    print(f"Case 1 Uploaded: ID={case1_id}, RiskScore={case1_data['risk_score']}, Decision={case1_data['decision']}")
    assert case1_data["decision"] == "APPROVE", f"Expected APPROVE, got {case1_data['decision']}"

    # Now approve Case 1
    print(f"Approving Case 1 (ID={case1_id})...")
    res_app = client.post(f"/invoice/{case1_id}/approve")
    assert res_app.status_code == 200, f"Approve failed: {res_app.text}"
    inv1_detail = client.get(f"/invoice/{case1_id}").json()
    print("Case 1 Detail after approval:", inv1_detail.get("status"))
    assert inv1_detail["status"] == "Funded", f"Expected Funded, got {inv1_detail['status']}"

    # -------------------------------------------------------------------------
    # STEP 3: Upload Case 2 (exact duplicate of case 1) -> expect REJECT with "already financed"
    # -------------------------------------------------------------------------
    print("\n[STEP 3] Uploading Case 2 (Duplicate of Case 1)...")
    c2_dir = os.path.join(base_sample_dir, "case2")
    with open(os.path.join(c2_dir, "invoice.pdf"), "rb") as f_inv, \
         open(os.path.join(c2_dir, "po.pdf"), "rb") as f_po, \
         open(os.path.join(c2_dir, "delivery.pdf"), "rb") as f_del, \
         open(os.path.join(c2_dir, "contract.pdf"), "rb") as f_con:
        
        files = {
            "invoice": ("invoice.pdf", f_inv, "application/pdf"),
            "po": ("po.pdf", f_po, "application/pdf"),
            "delivery": ("delivery.pdf", f_del, "application/pdf"),
            "contract": ("contract.pdf", f_con, "application/pdf"),
        }
        res3 = client.post("/upload", files=files)

    assert res3.status_code == 200, f"Upload Case 2 failed: {res3.text}"
    case2_data = res3.json()
    print(f"Case 2 Uploaded: ID={case2_data['invoice_id']}, RiskScore={case2_data['risk_score']}, Decision={case2_data['decision']}")
    dup_reason = next((r for r in case2_data["reasons"] if r["check"] == "Duplicate & Prior Financing"), None)
    print("Duplicate Check Reason:", dup_reason["message"])
    assert case2_data["decision"] == "REJECT", f"Expected REJECT, got {case2_data['decision']}"
    assert dup_reason and not dup_reason["passed"], "Duplicate check should have failed"

    # -------------------------------------------------------------------------
    # STEP 4: Upload Case 3 -> expect amount mismatch -> REVIEW or REJECT
    # -------------------------------------------------------------------------
    print("\n[STEP 4] Uploading Case 3 (20% Amount Mismatch: PO 150k vs Invoice 180k)...")
    c3_dir = os.path.join(base_sample_dir, "case3")
    with open(os.path.join(c3_dir, "invoice.pdf"), "rb") as f_inv, \
         open(os.path.join(c3_dir, "po.pdf"), "rb") as f_po, \
         open(os.path.join(c3_dir, "delivery.pdf"), "rb") as f_del, \
         open(os.path.join(c3_dir, "contract.pdf"), "rb") as f_con:
        
        files = {
            "invoice": ("invoice.pdf", f_inv, "application/pdf"),
            "po": ("po.pdf", f_po, "application/pdf"),
            "delivery": ("delivery.pdf", f_del, "application/pdf"),
            "contract": ("contract.pdf", f_con, "application/pdf"),
        }
        res4 = client.post("/upload", files=files)

    assert res4.status_code == 200, f"Upload Case 3 failed: {res4.text}"
    case3_data = res4.json()
    print(f"Case 3 Uploaded: ID={case3_data['invoice_id']}, RiskScore={case3_data['risk_score']}, Decision={case3_data['decision']}")
    po_reason = next((r for r in case3_data["reasons"] if r["check"] == "Purchase Order Match"), None)
    print("PO Match Reason:", po_reason["message"])
    assert case3_data["decision"] in ["REVIEW", "REJECT"], f"Expected REVIEW or REJECT, got {case3_data['decision']}"
    assert po_reason and not po_reason["passed"], "PO match check should have failed"

    # -------------------------------------------------------------------------
    # STEP 5: Upload Case 4 -> expect missing delivery check to fail
    # -------------------------------------------------------------------------
    print("\n[STEP 5] Uploading Case 4 (No Delivery Receipt)...")
    c4_dir = os.path.join(base_sample_dir, "case4")
    with open(os.path.join(c4_dir, "invoice.pdf"), "rb") as f_inv, \
         open(os.path.join(c4_dir, "po.pdf"), "rb") as f_po, \
         open(os.path.join(c4_dir, "contract.pdf"), "rb") as f_con:
        
        files = {
            "invoice": ("invoice.pdf", f_inv, "application/pdf"),
            "po": ("po.pdf", f_po, "application/pdf"),
            "contract": ("contract.pdf", f_con, "application/pdf"),
        }
        res5 = client.post("/upload", files=files)

    assert res5.status_code == 200, f"Upload Case 4 failed: {res5.text}"
    case4_data = res5.json()
    print(f"Case 4 Uploaded: ID={case4_data['invoice_id']}, RiskScore={case4_data['risk_score']}, Decision={case4_data['decision']}")
    del_reason = next((r for r in case4_data["reasons"] if r["check"] == "Delivery Receipt Verification"), None)
    print("Delivery Check Reason:", del_reason["message"])
    assert del_reason and not del_reason["passed"], "Delivery check should have failed"

    # -------------------------------------------------------------------------
    # STEP 6: Upload Case 5 -> expect risky buyer check to fail
    # -------------------------------------------------------------------------
    print("\n[STEP 6] Uploading Case 5 (Risky Buyer 'Slowpay Retail Pvt Ltd')...")
    c5_dir = os.path.join(base_sample_dir, "case5")
    with open(os.path.join(c5_dir, "invoice.pdf"), "rb") as f_inv, \
         open(os.path.join(c5_dir, "po.pdf"), "rb") as f_po, \
         open(os.path.join(c5_dir, "delivery.pdf"), "rb") as f_del, \
         open(os.path.join(c5_dir, "contract.pdf"), "rb") as f_con:
        
        files = {
            "invoice": ("invoice.pdf", f_inv, "application/pdf"),
            "po": ("po.pdf", f_po, "application/pdf"),
            "delivery": ("delivery.pdf", f_del, "application/pdf"),
            "contract": ("contract.pdf", f_con, "application/pdf"),
        }
        res6 = client.post("/upload", files=files)

    assert res6.status_code == 200, f"Upload Case 5 failed: {res6.text}"
    case5_data = res6.json()
    print(f"Case 5 Uploaded: ID={case5_data['invoice_id']}, RiskScore={case5_data['risk_score']}, Decision={case5_data['decision']}")
    buyer_reason = next((r for r in case5_data["reasons"] if r["check"] == "Buyer Payment History"), None)
    print("Buyer History Check Reason:", buyer_reason["message"])
    assert buyer_reason and not buyer_reason["passed"], "Buyer history check should have failed"

    # -------------------------------------------------------------------------
    # STEP 7: GET /verify -> all OK
    # -------------------------------------------------------------------------
    print("\n[STEP 7] Verifying integrity of audit hash-chain and storage files...")
    res7 = client.get("/verify")
    assert res7.status_code == 200, f"Verify failed: {res7.text}"
    v_data = res7.json()
    print("Verify Result:", v_data)
    assert v_data["chain_ok"] is True, f"Audit chain should be OK: {v_data['problems']}"
    assert v_data["files_ok"] is True, f"Storage files should be OK: {v_data['problems']}"

    # -------------------------------------------------------------------------
    # STEP 8: POST /demo/tamper/{case1 id} -> GET /verify -> files_ok false
    # -------------------------------------------------------------------------
    print(f"\n[STEP 8] Simulating tamper on Case 1 (ID={case1_id})...")
    res8_tamper = client.post(f"/demo/tamper/{case1_id}")
    assert res8_tamper.status_code == 200, f"Tamper demo failed: {res8_tamper.text}"
    print("Tamper Response:", res8_tamper.json())

    res8_verify = client.get("/verify")
    assert res8_verify.status_code == 200
    v8_data = res8_verify.json()
    print("Verify Result after Tampering:", v8_data)
    assert v8_data["files_ok"] is False, "Expected files_ok to be False after tampering!"
    print("SUCCESS: Cryptographic file tamper detected correctly by /verify!")

    # -------------------------------------------------------------------------
    # STEP 9: POST /demo/reset again so it's clean for live demo
    # -------------------------------------------------------------------------
    print("\n[STEP 9] Resetting demo data for clean state...")
    res9 = client.post("/demo/reset")
    assert res9.status_code == 200
    print("Reset Result:", res9.json())

    print("\n" + "=" * 70)
    print("ALL 9 STEPS PASSED PERFECTLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_9_step_test()
