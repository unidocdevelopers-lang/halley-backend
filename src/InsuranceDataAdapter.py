import pandas as pd

class InsuranceDataAdapter:
    def __init__(self, file_path):
        self.file_path = file_path
        self.partA = None  # Patient & Hospital info
        self.partB = None  # Diagnosis info
        self.partC = None  # Itemized bill summary
        self.partD = None  # Claim summary

    def read_data(self):
        """Reads all 4 sheets into pandas DataFrames"""
        try:
            self.partA = pd.read_excel(self.file_path, sheet_name="PartA_PatientHospital")
            self.partB = pd.read_excel(self.file_path, sheet_name="PartB_Diagnosis")
            self.partC = pd.read_excel(self.file_path, sheet_name="PartC_BillSummary")
            self.partD = pd.read_excel(self.file_path, sheet_name="PartD_Claim")

            #  Normalize UHID across all sheets
            for df in [self.partA, self.partB, self.partC, self.partD]:
                df["UHID"] = df["UHID"].astype(str).str.strip()

            print(" All sheets loaded successfully.")

        except Exception as e:
            print(f" Error loading sheets: {e}")
            raise

    def get_patient_info(self, uhid):
        """Return patient info dict from PartA"""
        patient = self.partA[self.partA['UHID'] == uhid]
        if patient.empty:
            return None
        return patient.to_dict(orient='records')[0]

    def get_diagnosis_info(self, uhid):
        """Return diagnosis/treatment list for patient"""
        diag = self.partB[self.partB['UHID'] == uhid]
        return diag.to_dict(orient='records')

    def get_bill_summary(self, uhid):
        """Return itemized bill for patient"""
        bills = self.partC[self.partC['UHID'] == uhid]
        return bills.to_dict(orient='records')

    def get_claim_summary(self, uhid):
        """Return claim summary for patient"""
        claim = self.partD[self.partD['UHID'] == uhid]
        if claim.empty:
            return None
        return claim.to_dict(orient='records')[0]
