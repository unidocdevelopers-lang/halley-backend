import pandas as pd
import zipfile
import os
from pathlib import Path
import random

# CONFIG
BASE = Path(__file__).resolve().parents[1]   # project root (Halley/)
DATA_DIR = BASE / "data"
OUTPUT_DIR = BASE / "Insurance_Reports"

# Use env var if set, else fallback to default
ZIP_FILE = Path(os.getenv("INS_ZIP", DATA_DIR / "Insurance_Claims_50patients.zip"))
MASTER_CSV = OUTPUT_DIR / "Insurance_Claims_Summary.csv"


# Pre-auth rules (for simulation)
PRE_AUTH_RULES = {
    "ICU": "Partial",             # max 80%
    "OT/Cath Lab": "Required",    # full approval simulated
    "Surgery/Procedure": "Required",
    "Anesthesia": "Required",
    "Room Rent": "Partial",       # 80%
    "Pharmacy & Consumables": "Approved",
    "Investigations": "Approved",
    "Miscellaneous": "Approved",
    "Nursing": "Approved",
    "Procedure/Treatment": "Required"
}

PARTIAL_PERCENT = 0.8  # 80% for partial approval


# UTILITIES

def pre_auth_simulation(head, amount):
    rule = PRE_AUTH_RULES.get(head, "Approved")
    if rule == "Approved":
        return "Approved", amount
    elif rule == "Partial":
        return "Partial", round(amount * PARTIAL_PERCENT, 2)
    elif rule == "Required":
        # Randomly approve full or partial for simulation
        approved_amount = amount if random.random() > 0.2 else round(amount * PARTIAL_PERCENT, 2)
        status = "Approved" if approved_amount == amount else "Partial"
        return status, approved_amount
    else:
        return "Rejected", 0.0

def format_currency(amount):
    return f"{amount:,.2f}"


# MAIN PROCESSING

def process_insurance_zip(zip_file):
    OUTPUT_DIR.mkdir(exist_ok=True)
    master_data = []

    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        excel_files = [f for f in zip_ref.namelist() if f.endswith(".xlsx")]
        print(f"Found {len(excel_files)} Excel files in the ZIP.")

        for excel_file in excel_files:
            print(f"\n--- Processing file: {excel_file} ---")
            with zip_ref.open(excel_file) as file:
                xls = pd.ExcelFile(file)
                print(f"Sheets in file: {xls.sheet_names}")

                # Load sheets
                df_partA = pd.read_excel(xls, 'PartA_PatientHospital')
                df_partB = pd.read_excel(xls, 'PartB_Diagnosis')
                df_partC = pd.read_excel(xls, 'PartC_BillSummary')
                df_partD = pd.read_excel(xls, 'PartD_Claim')

                # For simplicity, assume one patient per file
                patient_info = df_partA.iloc[0].to_dict()
                print(f"Patient Info: {patient_info['Patient Name']} (UHID: {patient_info['UHID']})")

                # Diagnosis info
                diagnoses = df_partB.to_dict(orient='records')

                # Itemized bill
                bills = df_partC.to_dict(orient='records')
                for item in bills:
                    status, authorized = pre_auth_simulation(item['Head'], item['Amount'])
                    item['Pre-Auth Status'] = status
                    item['Authorized Amount'] = authorized

                # Adjusted claim totals
                authorized_total = sum(item['Authorized Amount'] for item in bills)
                amount_paid_by_patient = df_partD.iloc[0]['Amount Paid by Patient']
                balance_due = authorized_total - amount_paid_by_patient

                # Determine overall claim status
                statuses = [item['Pre-Auth Status'] for item in bills]
                if all(s == "Approved" for s in statuses):
                    claim_status = "Approved"
                elif any(s == "Rejected" for s in statuses):
                    claim_status = "Partial"
                elif any(s == "Partial" for s in statuses):
                    claim_status = "Partial"
                else:
                    claim_status = "Pending"

                # Generate per-patient .txt report
                txt_lines = []
                txt_lines.append(f"--- Insurance Claim for Patient: {patient_info['Patient Name']} (UHID: {patient_info['UHID']}) ---")
                txt_lines.append(f"Policy No: {patient_info['Policy No']}   Insurer: {patient_info['Insurer/TPA']}   Type: {patient_info['Insurance Type']}")
                txt_lines.append(f"Hospital: {patient_info['Hospital']} (NABH: {patient_info['NABH No']})")
                txt_lines.append(f"Admission: {patient_info['Admission Date']}  |  Discharge: {patient_info['Discharge Date']}")
                txt_lines.append(f"Hospitalization Reason: {patient_info['Hospitalization Reason']}")
                txt_lines.append("\n--- Diagnosis & Procedures ---")
                for diag in diagnoses:
                    txt_lines.append(f"{diag['Primary Diagnosis (ICD-10)']} : {diag['Procedure/Treatment']} by {diag['Surgeon/Physician']} on {diag['Date of Procedure/Key Event']}")
                txt_lines.append("\n--- Itemized Bill (Authorized Amounts) ---")
                for item in bills:
                    txt_lines.append(f"{item['Head']}: {format_currency(item['Amount'])} ({item['Pre-Auth Status']}: {format_currency(item['Authorized Amount'])})")
                txt_lines.append("\n--- Claim Summary ---")
                txt_lines.append(f"Bill Subtotal: {format_currency(df_partD.iloc[0]['Bill Subtotal'])}")
                txt_lines.append(f"GST (5%): {format_currency(df_partD.iloc[0]['GST'])}")
                txt_lines.append(f"Discount: {format_currency(df_partD.iloc[0]['Discount'])}")
                txt_lines.append(f"Total Claimed: {format_currency(df_partD.iloc[0]['Total Claimed'])}")
                txt_lines.append(f"Amount Paid by Patient: {format_currency(amount_paid_by_patient)}")
                txt_lines.append(f"Original Amount Claimed from Insurer: {format_currency(df_partD.iloc[0]['Amount Claimed from Insurer'])}")
                txt_lines.append(f"Authorized Amount Claimed from Insurer: {format_currency(authorized_total)}")
                txt_lines.append(f"Balance Due from Insurer: {format_currency(balance_due)}")
                txt_lines.append(f"Pre-Auth Status: {claim_status}")

                txt_filename = OUTPUT_DIR / f"{patient_info['UHID']}.txt"
                with open(txt_filename, 'w') as f:
                    f.write('\n'.join(txt_lines))
                print(f"Report saved: {txt_filename}")

                # Append to master CSV
                master_data.append({
                    "UHID": patient_info['UHID'],
                    "Patient Name": patient_info['Patient Name'],
                    "Policy No": patient_info['Policy No'],
                    "Insurer": patient_info['Insurer/TPA'],
                    "Bill Subtotal": df_partD.iloc[0]['Bill Subtotal'],
                    "GST": df_partD.iloc[0]['GST'],
                    "Discount": df_partD.iloc[0]['Discount'],
                    "Total Claimed": df_partD.iloc[0]['Total Claimed'],
                    "Amount Paid by Patient": amount_paid_by_patient,
                    "Original Claimed from Insurer": df_partD.iloc[0]['Amount Claimed from Insurer'],
                    "Authorized Claimed from Insurer": authorized_total,
                    "Balance Due from Insurer": balance_due,
                    "Claim Status": claim_status
                })

    # Save master CSV
    df_master = pd.DataFrame(master_data)
    df_master.to_csv(MASTER_CSV, index=False)
    print(f"\nAll reports saved in '{OUTPUT_DIR}'")
    print(f"Master CSV generated: {MASTER_CSV}")


# RUN

if __name__ == "__main__":
    process_insurance_zip(ZIP_FILE)
