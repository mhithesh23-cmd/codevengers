# InvoiceTrust

An invoice-financing verification platform for lenders to detect fraud, verify invoices, and streamline risk assessment.

---

## Team Setup Guide

Follow these steps to set up your local development environment:

### 1. Clone the repository
```bash
git clone https://github.com/mhithesh23-cmd/codevengers.git
cd codevengers
```

### 2. Create and activate a virtual environment
- **Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **macOS / Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Copy the `.env.example` file to create your local `.env`:
- **Windows (PowerShell):**
  ```powershell
  Copy-Item .env.example .env
  ```
- **macOS / Linux:**
  ```bash
  cp .env.example .env
  ```

Open `.env` and fill in your Supabase credentials:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-or-service-key
```

---

## Running the Server

Start the FastAPI development server with live reload:

```bash
uvicorn backend.main:app --reload
```

Once running, the API will be available at: `http://127.0.0.1:8000`

---

## Testing Endpoints

1. **Health Check:**
   - URL: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
   - Expected Response:
     ```json
     {
       "status": "ok"
     }
     ```

2. **Supabase Database Test:**
   - URL: [http://127.0.0.1:8000/test-db](http://127.0.0.1:8000/test-db)
   - Expected Response:
     ```json
     {
       "status": "connected",
       "table": "invoices",
       "row_count": 0,
       "message": "Supabase connection is working successfully!"
     }
     ```

3. **Interactive Swagger Docs:**
   - Visit [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
