# billing_adapter.py
import pandas as pd
from src.billing_engine import BillingEngine
import logging

def log_error(message):
    logging.error(message)

def log_info(message):
    logging.info(message)


def validate_schema(charges_df):
    required_columns = {"UHID", "Head", "Description", "Qty", "Rate", "Amount", "Date"}
    missing_cols = required_columns - set(charges_df.columns)
    if missing_cols:
        raise ValueError(f" Missing columns in charges data: {', '.join(missing_cols)}")


class BillingDataAdapter:
    def __init__(self, source_type, source):
        """
        source_type: 'excel', 'json', 'api', etc.
        source: file path / URL / dict / DataFrame
        """
        self.source_type = source_type
        self.source = source
        self.charges_df = None
        self.summary_df = None
        self.patient_df = None

    def read_data(self):
        """Reads all relevant sheets or data from the source."""
        if self.source_type == 'excel':
            xls = pd.ExcelFile(self.source)
            # Read itemized charges
            self.charges_df = pd.read_excel(xls, sheet_name="Charges_Itemized")
            validate_schema(self.charges_df)
            # Read summary (for Discount & Advance Paid)
            self.summary_df = pd.read_excel(xls, sheet_name="Summary")
            # Read patient names
            self.patient_df = pd.read_excel(xls, sheet_name="Patient")
        else:
            raise NotImplementedError(f"{self.source_type} not supported yet.")

    def normalize_data(self):
        """Basic cleanup: remove duplicates, strip strings."""
        if self.charges_df is not None:
            self.charges_df['Head'] = self.charges_df['Head'].astype(str).str.strip()
            self.charges_df['Description'] = self.charges_df['Description'].astype(str).str.strip()
        if self.patient_df is not None:
            self.patient_df['Patient Name'] = self.patient_df['Patient Name'].astype(str).str.strip()
        if self.summary_df is not None:
            self.summary_df['UHID'] = self.summary_df['UHID'].astype(str).str.strip()

    def generate_billing(self):
        """
        Returns dict keyed by UHID, each value contains
        charges, totals, patient name, errors, etc.
        """
        billing_results = {}
        for uhid, group in self.charges_df.groupby('UHID'):
            # Patient name lookup
            patient_name = self.patient_df.loc[self.patient_df['UHID'] == uhid, 'Patient Name']
            patient_name = patient_name.values[0] if not patient_name.empty else "Unknown"

            # Summary row
            summary_row = self.summary_df.loc[self.summary_df['UHID'] == uhid]
            summary_row = summary_row.iloc[0] if not summary_row.empty else pd.Series({'Discount': 0, 'Advance Paid': 0})

            # Calculate totals
            totals = BillingEngine.calculate_totals(group, summary_row)
            totals['Patient Name'] = patient_name
            totals['Charges'] = totals['Charges']   # keep the cleaned charges

            # Logging step
            errors = totals.get("Errors", [])
            if errors:
                for err in errors:
                    log_error(f"Billing error for UHID {uhid}: {err}")
            else:
                log_info(f"Billing processed successfully for UHID {uhid}")


            billing_results[uhid] = totals
        return billing_results
