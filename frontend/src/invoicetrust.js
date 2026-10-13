/**
 * invoicetrust.js - Client API bridge and utilities for InvoiceTrust
 */

const API_BASE = window.location.origin;

// ----------------------------------------------------------------------------
// Utilities: Format Currency, Toasts, Hashing
// ----------------------------------------------------------------------------
window.formatINR = function (val) {
  if (val === undefined || val === null || isNaN(val)) return "₹0";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(val);
};

window.showToast = function (message, type = "info") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast-msg ${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
};

window.computeSHA256 = async function (file) {
  if (!file || typeof file.arrayBuffer !== "function") {
    return "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
  }
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest("SHA-256", buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
};

window.checkBackendHealth = async function () {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (res.ok) {
      const data = await res.json();
      return { connected: true, status: data.status };
    }
  } catch (err) {
    console.warn("Backend health check failed:", err);
  }
  return { connected: false };
};

// ----------------------------------------------------------------------------
// Real REST API Client
// ----------------------------------------------------------------------------
window.InvoiceTrustAPI = {
  async upload(formData) {
    const response = await fetch(`${API_BASE}/upload`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(err.detail || err.error || "Upload failed");
    }
    return await response.json();
  },

  async getInvoices() {
    const response = await fetch(`${API_BASE}/invoices`);
    if (!response.ok) throw new Error("Failed to fetch invoices");
    return await response.json();
  },

  async getInvoice(id) {
    const response = await fetch(`${API_BASE}/invoice/${id}`);
    if (!response.ok) throw new Error(`Failed to fetch invoice #${id}`);
    return await response.json();
  },

  async approve(id) {
    const response = await fetch(`${API_BASE}/invoice/${id}/approve`, { method: "POST" });
    if (!response.ok) throw new Error(`Failed to approve invoice #${id}`);
    return await response.json();
  },

  async markPaid(id) {
    const response = await fetch(`${API_BASE}/invoice/${id}/paid`, { method: "POST" });
    if (!response.ok) throw new Error(`Failed to mark invoice #${id} as paid`);
    return await response.json();
  },

  async getAudit(id) {
    const response = await fetch(`${API_BASE}/audit/${id}`);
    if (!response.ok) throw new Error(`Failed to fetch audit for invoice #${id}`);
    return await response.json();
  },

  async verifyIntegrity() {
    const response = await fetch(`${API_BASE}/verify`);
    if (!response.ok) throw new Error("Integrity verification check failed");
    return await response.json();
  },

  async demoTamper(id) {
    const response = await fetch(`${API_BASE}/demo/tamper/${id}`, { method: "POST" });
    if (!response.ok) throw new Error(`Demo tamper failed on invoice #${id}`);
    return await response.json();
  },

  async demoReset() {
    const response = await fetch(`${API_BASE}/demo/reset`, { method: "POST" });
    if (!response.ok) throw new Error("Demo reset failed");
    return await response.json();
  },
};

// ----------------------------------------------------------------------------
// Adapter Bridge for Template Pages (InvoiceTrustDB)
// ----------------------------------------------------------------------------
window.InvoiceTrustDB = {
  async getAll() {
    try {
      const serverInvoices = await window.InvoiceTrustAPI.getInvoices();
      if (Array.isArray(serverInvoices) && serverInvoices.length > 0) {
        return serverInvoices.map(mapServerInvoiceToClient);
      }
    } catch (e) {
      console.warn("API getInvoices error, falling back to local mock data:", e);
    }
    return getLocalMockInvoices();
  },

  async getById(id) {
    try {
      const inv = await window.InvoiceTrustAPI.getInvoice(id);
      if (inv) return mapServerInvoiceToClient(inv);
    } catch (e) {
      console.warn(`API getInvoice(${id}) error, checking local store:`, e);
    }
    const mocks = getLocalMockInvoices();
    return mocks.find(i => String(i.id) === String(id) || i.invoiceNumber === id) || null;
  },

  async save(record) {
    console.log("Local mock save called:", record);
    return record;
  },
};

function mapServerInvoiceToClient(item) {
  const amount = parseFloat(item.amount || 0);
  const reasons = item.reasons || [];

  return {
    id: item.id,
    invoiceNumber: item.invoice_no || `INV-${item.id}`,
    sellerName: item.seller_name || "Unknown Seller",
    sellerGstin: item.gstin || "",
    buyerName: item.buyer_name || "Unknown Buyer",
    buyerGstin: "",
    invoiceAmount: amount,
    requestedAmount: Math.round(amount * 0.8),
    dueDate: item.invoice_date || "",
    createdAt: item.created_at || new Date().toISOString(),
    riskScore: item.risk_score !== undefined ? item.risk_score : 20,
    decision: item.decision || (item.status === "Approved" ? "APPROVE" : "REVIEW"),
    status: item.status || "Review",
    fileHash: item.file_hash || "",
    fingerprint: item.fingerprint || "",
    documents: {
      invoice: {
        name: `${item.invoice_no || 'invoice'}.pdf`,
        size: "1.2 MB",
        sha256: item.file_hash || "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      },
      po: { name: "purchase_order.pdf", size: "850 KB", sha256: "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08" },
      delivery: { name: "delivery_receipt.pdf", size: "1.1 MB", sha256: "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8" },
      contract: { name: "agreement.pdf", size: "2.4 MB", sha256: "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a" },
    },
    checklist: reasons.map((r, idx) => ({
      id: idx + 1,
      name: r.check,
      status: r.passed ? "passed" : "failed",
      reason: r.message,
      weight: r.weight,
      evidence: r.passed ? "Verified" : "Discrepancy",
      action: r.passed ? "Passed" : `+${r.weight} Risk`,
    })),
    auditEvents: (item.events || []).map(ev => ({
      timestamp: ev.created_at || new Date().toISOString(),
      actor: "InvoiceTrust Engine",
      action: ev.event,
      details: `Block #${ev.id} | Hash: ${ev.hash ? ev.hash.substring(0, 16) : 'N/A'}...`,
      hash: ev.hash,
      prevHash: ev.prev_hash,
    })),
  };
}

function getLocalMockInvoices() {
  return [
    {
      id: "INV-2024-9120",
      invoiceNumber: "INV-2024-9120",
      sellerName: "Tata Steel Ltd",
      sellerGstin: "27AAACT2727Q1ZW",
      buyerName: "Reliance Industries Ltd",
      buyerGstin: "27AABCR0001R1Z8",
      invoiceAmount: 1850000,
      requestedAmount: 1480000,
      dueDate: "2024-06-30",
      createdAt: "2024-04-12T10:30:00Z",
      riskScore: 12,
      decision: "APPROVE",
      status: "Approved",
      documents: {
        invoice: { name: "Tax_Invoice_9120.pdf", size: "1.4 MB", sha256: "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0" },
        po: { name: "PO_Reliance_4001.pdf", size: "890 KB", sha256: "b2c3d4e5f6a17890123456789abcdef0123456789abcdef0123456789abcdef0" },
        delivery: { name: "POD_Signed_9120.pdf", size: "1.1 MB", sha256: "c3d4e5f6a1b27890123456789abcdef0123456789abcdef0123456789abcdef0" },
        contract: { name: "Master_Agreement_TCS.pdf", size: "2.8 MB", sha256: "d4e5f6a1b2c37890123456789abcdef0123456789abcdef0123456789abcdef0" },
      },
      checklist: [
        { id: 1, name: "Purchase Order Match", status: "passed", reason: "Amount and PO match exactly.", evidence: "PO Verified", action: "Passed" },
        { id: 2, name: "Delivery Verification", status: "passed", reason: "Quantity match verified.", evidence: "POD", action: "Passed" },
      ],
      auditEvents: [
        { timestamp: "2024-04-12T10:30:00Z", actor: "Upload Desk", action: "UPLOADED", details: "Initial documents ingested." },
        { timestamp: "2024-04-12T10:30:05Z", actor: "Risk Engine", action: "VERIFIED", details: "All cross-checks passed." },
        { timestamp: "2024-04-12T10:30:06Z", actor: "Risk Engine", action: "APPROVED", details: "Risk score 12/100." },
      ],
    },
  ];
}
