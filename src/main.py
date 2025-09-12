import os
from pathlib import Path
from billing_adapter import BillingDataAdapter
import logging

# Set up logging (will append to audit_log.csv)
logging.basicConfig(
    filename="audit_log.csv",
    level=logging.INFO,
    format="%(asctime)s,%(levelname)s,%(message)s"
)

# Base directory = project root (Halley/)
BASE = Path(__file__).resolve().parents[1]
DATA_DIR = BASE / "data"

# Excel file (use env var if set, else default location)
excel_path = Path(os.getenv("BILL_EXCEL", DATA_DIR / "Hospital_Bill_MRD_SYNTHETIC_v2.xlsx"))

if not excel_path.exists():
    raise FileNotFoundError(f"Excel file not found at path: {excel_path}")

# Initialize adapter
adapter = BillingDataAdapter(
    source_type='excel',
    source=excel_path
)

# Read and normalize
adapter.read_data()
adapter.normalize_data()

# Generate billing
billing_results = adapter.generate_billing()

# Print
for uhid, bill in billing_results.items():
    print(f"\n--- Billing for Patient: {bill['Patient Name']} (UHID: {uhid}) ---")
    print(f"Subtotal: {bill['Subtotal']}")
    print(f"GST (5%): {bill['GST']}")
    print(f"Discount: {bill['Discount']}")
    print(f"Advance Paid: {bill['Advance Paid']}")
    print(f"Grand Total: {bill['Grand Total']}")
    print(f"Total Paid: {bill['Total Paid']}")
    print(f"Balance Due: {bill['Balance Due']}\n")

    print("Itemized Charges :")
    print(bill['Charges'].to_string(index=False))

    if bill['Errors']:
        print("\n Billing Errors Detected:")
        for err in bill['Errors']:
            print(f" - {err}")
    else:
        print("\n Info: Patient billing is clean.")
