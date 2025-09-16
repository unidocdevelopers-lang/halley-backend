# app.py — Render deploy–ready (Flask)
# -----------------------------------
# Features:
# - /api/health        -> health check for Render
# - /api/process-billing (POST file=.xlsx/.xls) -> Excel read using pandas
# - /api/process-insurance (POST file=.zip)     -> Try to parse CSV/JSON inside ZIP; else fallback
# - /api/run-tests     -> If pytest exists, runs tests; else returns friendly message
# - CORS enabled for /api/*
# - PORT env supported (Render sets $PORT)

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path
import os
import io
import zipfile
import traceback
import tempfile
import pandas as pd

APP_ROOT = Path(__file__).resolve().parent

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB uploads (tweak if needed)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# -----------------------------
# Helpers
# -----------------------------
def ok(data=None, message="success"):
    return jsonify({"status": "success", "message": message, "data": data or {}}), 200

def fail(message="Something went wrong", code=400, error=None):
    payload = {"status": "error", "message": message}
    if error:
        payload["error"] = str(error)
    return jsonify(payload), code

def _read_excel_to_df(file_storage):
    # Reads .xlsx/.xls into pandas DataFrame
    stream = io.BytesIO(file_storage.read())
    stream.seek(0)
    try:
        df = pd.read_excel(stream, engine="openpyxl")
    except Exception:
        # try fallback engine (older xls)
        stream.seek(0)
        df = pd.read_excel(stream)
    return df

def _normalize_cols(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    # also create a lowercase map if needed
    lower_map = {c.lower(): c for c in df.columns}
    return df, lower_map

def _get_col(lower_map, *cands):
    # returns real column name if any candidate matches (case-insensitive)
    for c in cands:
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None

# -----------------------------
# Routes
# -----------------------------
@app.get("/")
def root():
    # Optional: serve a tiny info page (you can remove if not needed)
    return jsonify({"app": "Halley Backend", "status": "ok"})

@app.get("/api/health")
def health():
    return jsonify({"status": "healthy"})

@app.post("/api/process-billing")
def process_billing():
    """
    Expects form-data with 'file' (Excel: .xlsx/.xls)
    Returns a dict keyed by UHID with totals (if columns present), else returns rows
    """
    try:
        if "file" not in request.files:
            return fail("No file part 'file' found", 400)
        f = request.files["file"]
        if not f or not f.filename:
            return fail("No file selected", 400)

        # Read Excel
        df = _read_excel_to_df(f)
        df, lower_map = _normalize_cols(df)

        # Try to map well-known columns if available
        col_uhid     = _get_col(lower_map, "UHID", "uhid", "patient_id", "MRN")
        col_name     = _get_col(lower_map, "Patient Name", "patient_name", "Name")
        col_subtotal = _get_col(lower_map, "Subtotal", "subtotal")
        col_gst      = _get_col(lower_map, "GST", "gst", "Tax", "tax")
        col_discount = _get_col(lower_map, "Discount", "discount")
        col_grand    = _get_col(lower_map, "Grand Total", "grand_total", "Total", "total")
        col_balance  = _get_col(lower_map, "Balance Due", "balance_due", "Due", "due")

        result = {}

        if col_uhid:
            # group by UHID and aggregate known fields if present
            grouped = df.groupby(col_uhid, dropna=False)

            for uhid, g in grouped:
                rec = {}
                # Patient name (first non-null)
                if col_name and col_name in g.columns:
                    name_val = g[col_name].dropna().astype(str)
                    rec["Patient Name"] = name_val.iloc[0] if len(name_val) else ""

                # numeric sums (if columns present)
                def _sum(col):
                    if col and col in g.columns:
                        try:
                            return float(pd.to_numeric(g[col], errors="coerce").fillna(0).sum())
                        except Exception:
                            return 0.0
                    return 0.0

                rec["Subtotal"]     = _sum(col_subtotal)
                rec["GST"]          = _sum(col_gst)
                rec["Discount"]     = _sum(col_discount)
                rec["Grand Total"]  = _sum(col_grand)
                rec["Balance Due"]  = _sum(col_balance)

                result[str(uhid)] = rec

            return ok(result, "Billing processed")
        else:
            # No UHID column: return limited preview to prove parse worked
            # (UI still shows success; you can adjust to your schema)
            preview_cols = df.columns[:10].tolist()
            preview_rows = df[preview_cols].head(25).fillna("").astype(str).to_dict(orient="records")
            return ok({"rows": preview_rows, "columns": preview_cols}, "Billing parsed (no UHID column found)")

    except Exception as e:
        return fail("Billing processing failed", 500, traceback.format_exc())

@app.post("/api/process-insurance")
def process_insurance():
    """
    Expects form-data with 'file' (ZIP).
    Tries to parse CSV or JSON files inside the zip.
    Returns list[claims] with common fields if discovered; else a fallback item per file.
    """
    try:
        if "file" not in request.files:
            return fail("No file part 'file' found", 400)
        f = request.files["file"]
        if not f or not f.filename:
            return fail("No file selected", 400)

        # Read zip in-memory
        zbuf = io.BytesIO(f.read())
        with zipfile.ZipFile(zbuf) as z:
            names = z.namelist()

            claims = []
            parsed_any = False

            for name in names:
                if name.endswith("/") or "__MACOSX" in name:
                    continue
                with z.open(name) as fh:
                    # Try CSV via pandas
                    try:
                        if name.lower().endswith(".csv"):
                            df = pd.read_csv(fh)
                            df, lower_map = _normalize_cols(df)

                            col_name    = _get_col(lower_map, "Patient Name", "patient_name", "Name")
                            col_uhid    = _get_col(lower_map, "UHID", "uhid", "patient_id", "MRN")
                            col_policy  = _get_col(lower_map, "Policy No", "policy_no", "Policy")
                            col_insurer = _get_col(lower_map, "Insurer", "insurer", "TPA")
                            col_total   = _get_col(lower_map, "Total Claimed", "total_claimed", "Claimed", "Total")
                            col_paid    = _get_col(lower_map, "Amount Paid by Patient", "patient_paid", "Paid")
                            col_claim   = _get_col(lower_map, "Amount Claimed from Insurer", "insurer_claim", "Claim From Insurer")

                            for _, r in df.iterrows():
                                claims.append({
                                    "Patient Name": str(r.get(col_name, "")) if col_name else "",
                                    "UHID":         str(r.get(col_uhid, "")) if col_uhid else "",
                                    "Policy No":    str(r.get(col_policy, "")) if col_policy else "",
                                    "Insurer":      str(r.get(col_insurer, "")) if col_insurer else "",
                                    "Total Claimed": float(pd.to_numeric([r.get(col_total, 0)], errors="coerce")[0]) if col_total else 0.0,
                                    "Amount Paid by Patient": float(pd.to_numeric([r.get(col_paid, 0)], errors="coerce")[0]) if col_paid else 0.0,
                                    "Amount Claimed from Insurer": float(pd.to_numeric([r.get(col_claim, 0)], errors="coerce")[0]) if col_claim else 0.0,
                                })
                            parsed_any = True
                            continue
                    except Exception:
                        pass

                    # Try JSON list of dicts
                    try:
                        import json
                        if name.lower().endswith(".json"):
                            data = json.load(fh)
                            if isinstance(data, list):
                                for item in data:
                                    claims.append({
                                        "Patient Name": str(item.get("Patient Name", item.get("patient_name", ""))),
                                        "UHID": str(item.get("UHID", item.get("uhid", ""))),
                                        "Policy No": str(item.get("Policy No", item.get("policy_no", ""))),
                                        "Insurer": str(item.get("Insurer", item.get("insurer", ""))),
                                        "Total Claimed": float(item.get("Total Claimed", item.get("total_claimed", 0)) or 0),
                                        "Amount Paid by Patient": float(item.get("Amount Paid by Patient", item.get("patient_paid", 0)) or 0),
                                        "Amount Claimed from Insurer": float(item.get("Amount Claimed from Insurer", item.get("insurer_claim", 0)) or 0),
                                    })
                                parsed_any = True
                                continue
                    except Exception:
                        pass

                    # Fallback: if unknown file, add a placeholder claim record so UI shows something
                    claims.append({
                        "Patient Name": name,
                        "UHID": "",
                        "Policy No": "",
                        "Insurer": "",
                        "Total Claimed": 0.0,
                        "Amount Paid by Patient": 0.0,
                        "Amount Claimed from Insurer": 0.0,
                    })

            if not claims and not parsed_any:
                return ok([], "No parsable CSV/JSON found in ZIP (added 0 claims)")

            return ok(claims, "Insurance processed")

    except Exception as e:
        return fail("Insurance processing failed", 500, traceback.format_exc())

@app.get("/api/run-tests")
def run_tests():
    """
    If pytest is installed and tests exist, run them.
    Otherwise returns a friendly message.
    """
    try:
        import subprocess, sys, shutil
        if not shutil.which("pytest"):
            return ok({"output": ""}, "pytest not installed on server")
        # run quietly; 60s timeout to be safe
        res = subprocess.run(
            ["pytest", "-q"],
            capture_output=True,
            text=True,
            timeout=60
        )
        status = "success" if res.returncode == 0 else "error"
        return jsonify({
            "status": status,
            "message": "Tests finished",
            "output": (res.stdout or "") + "\n" + (res.stderr or "")
        }), 200
    except Exception as e:
        return fail("Could not run tests", 500, traceback.format_exc())

# -----------------------------
# Entrypoint
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render sets $PORT
    app.run(host="0.0.0.0", port=port)
