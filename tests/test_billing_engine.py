import unittest
import pandas as pd
from src.billing_engine import BillingEngine

class TestBillingEngine(unittest.TestCase):
    def test_totals_calculation(self):
        # Sample charges with Head + Description (important!)
        charges = pd.DataFrame([
            {"Head": "Room Rent", "Description": "Single AC", "Amount": 1000},
            {"Head": "Pharmacy", "Description": "Medicines", "Amount": 500},
            {"Head": "Pharmacy", "Description": "Medicines", "Amount": 500},  # duplicate
        ])
        summary = pd.Series({"Discount": 100, "Advance Paid": 500})

        totals = BillingEngine.calculate_totals(charges, summary)

        # Subtotal = 1000 + 500 = 1500
        # GST = 5% of 1500 = 75
        # Discount = 100
        # Advance = 500
        # Grand Total = 1500 + 75 - 100 = 1475
        # Balance Due = 1475 - 500 = 975

        self.assertEqual(totals["Subtotal"], 1500)
        self.assertEqual(totals["GST"], 75)
        self.assertEqual(totals["Discount"], 100)
        self.assertEqual(totals["Advance Paid"], 500)
        self.assertEqual(totals["Grand Total"], 1475)
        self.assertEqual(totals["Balance Due"], 975)

if __name__ == '__main__':
    unittest.main()
