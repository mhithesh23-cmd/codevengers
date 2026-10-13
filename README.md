# InvoiceTrust

An enterprise invoice-financing verification platform for lenders to detect fraudulent invoices, uncover cross-document inconsistencies, prevent double-pledging, and maintain a tamper-evident SHA-256 hash-chain audit log.

---

## Architecture Overview

- **Backend:** Python FastAPI with CORS enabled for rapid hackathon testing.
- **Database & Storage:** Supabase PostgreSQL (`invoices`, `buyer_history`, `financed_registry`, `audit_chain`) + Private Supabase Storage bucket (`invoices`).
- **Cryptographic Audit Chain:** Sequential SHA-256 hash chaining of all transaction events (`UPLOADED`, `VERIFIED`, `APPROVED`, `FUNDED`, `PAID`).
- **Document Field Extraction:** Automated metadata extraction from PDF documents using `pdfplumber` and regular expressions.
- **Cross-Checking Engine:** 8 deterministic risk rules scoring 0–100 (`APPROVE < 30`, `REVIEW 30–60`, `REJECT > 60`).
- **Frontend:** Vanilla HTML5, Tailwind CSS, and liquid glass styling hosted directly through FastAPI's StaticFiles.

---

## Quick Setup & Running Locally

### 1. Clone & Setup Virtual Environment
```powershell
git clone https://github.com/mhithesh23-cmd/codevengers.git
cd codevengers

python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure Environment (`.env`)
Copy `.env.example` to `.env` and fill in your Supabase credentials:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key
```

### 3. Generate Sample PDFs & Seed Database
```powershell
# Generate test cases 1 through 6
python sample_data/generate.py

# Seed buyer payment history records
python backend/seed.py
```

### 4. Run the Server
```powershell
uvicorn backend.main:app --reload
```
Open your browser at: **`http://127.0.0.1:8000`**

---

## Demo Flow for Judges (Step-by-Step)

The repository includes a ready-to-use end-to-end verification test: `python test_flow.py` which runs all 9 steps automatically. For live judging:

1. **Step 1 — Clean State:**
   - In Dashboard or via API, click **Reset Demo** (`POST /demo/reset`) to ensure clean starting state.
2. **Step 2 — Perfect Clean Invoice (Case 1):**
   - Upload `sample_data/case1/invoice.pdf`, `po.pdf`, `delivery.pdf`, `contract.pdf`.
   - Result: **0/100 Risk Score → APPROVE**.
   - Click **Approve (Fund)** on the result or dashboard to fund the loan. Fingerprint is added to the central registry.
3. **Step 3 — Double-Pledging / Duplicate Detection (Case 2):**
   - Upload `sample_data/case2/invoice.pdf`.
   - Result: **70/100 Risk Score → REJECT** with `"Critical: Invoice or identical file hash has already been financed or registered."`
4. **Step 4 — 20% Amount Variance (Case 3):**
   - Upload `sample_data/case3/invoice.pdf` and `po.pdf`.
   - Result: **35/100 Risk Score → REVIEW** with `"Invoice amount ₹1,80,000 does not match PO amount ₹1,50,000"`.
5. **Step 5 — Missing Delivery Receipt (Case 4):**
   - Upload `sample_data/case4/invoice.pdf` without a delivery receipt.
   - Result: Flags `"Delivery receipt document is missing."`
6. **Step 6 — Risky Buyer History (Case 5):**
   - Upload `sample_data/case5/invoice.pdf` (Buyer: *Slowpay Retail Pvt Ltd*).
   - Result: Flags buyer on-time rate as only **40.0%** (under 70% threshold with 45-day delay).
7. **Step 7 — Cryptographic Audit Trail & Integrity Check:**
   - Open **Audit Trail** page (`/audit.html`).
   - Click **Verify Integrity** (`GET /verify`) → Green Banner: **"All records intact"** (all SHA-256 hash blocks continuous and storage file checksums match).
8. **Step 8 — Off-Chain File Tamper Detection Demo:**
   - On the Audit page, click **Demo: Tamper** (`POST /demo/tamper/{id}`) which simulates modifying the stored PDF file in Supabase Storage.
   - Click **Verify Integrity** → Red Alert: **"TAMPERED"** showing exact file hash mismatch!
9. **Step 9 — Reset Demo:**
   - Click **Reset Demo** to restore a clean state.

---

## API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Server health check (`{"status": "ok"}`) |
| `GET` | `/test-db` | Verify connection to Supabase database |
| `POST` | `/upload` | Multipart upload (invoice, po, delivery, contract) & risk evaluation |
| `GET` | `/invoices` | List all verified invoices (newest first, without private paths) |
| `GET` | `/invoice/{id}` | Invoice details + full audit event timeline |
| `POST` | `/invoice/{id}/approve` | Mark invoice as `Funded` and log fingerprint in registry |
| `POST` | `/invoice/{id}/paid` | Mark invoice as `Paid` |
| `GET` | `/audit/{id}` | Chronological SHA-256 audit blocks for an invoice |
| `GET` | `/verify` | Validates hash-chain integrity & checks storage file hashes |
| `POST` | `/demo/tamper/{id}` | Demo only: Corrupts an invoice PDF in storage |
| `POST` | `/demo/reset` | Demo only: Resets invoices, registry, and audit chain |
