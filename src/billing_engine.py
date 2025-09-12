import pandas as pd

class BillingEngine:
    GST_RATE = 0.05

    @staticmethod
    def calculate_totals(charges_df: pd.DataFrame, summary_row: pd.Series):
        """
        charges_df: DataFrame of itemized charges
        summary_row: Series containing 'Advance Paid' and 'Discount'
        """
        errors = []

        # Detect duplicates
        duplicates = charges_df.groupby(['Head', 'Description']).size()
        duplicates = duplicates[duplicates > 1]
        for idx, count in duplicates.items():
            errors.append(
                f"Duplicate charge '{idx[1]}' under head '{idx[0]}'. Kept 1, ignored {count-1} extra."
            )

        #  Remove exact duplicates (keep only the first)
        cleaned_charges = charges_df.drop_duplicates(subset=['Head', 'Description'], keep='first')

        # Subtotal
        subtotal = cleaned_charges['Amount'].sum()

        # GST
        gst = round(subtotal * BillingEngine.GST_RATE, 2)

        # Discount & Advance Paid
        discount = summary_row.get('Discount', 0)
        advance_paid = summary_row.get('Advance Paid', 0)

        # Grand Total
        grand_total = subtotal + gst - discount
        total_paid = advance_paid
        balance_due = grand_total - total_paid

        return {
            'Subtotal': subtotal,
            'GST': gst,
            'Discount': discount,
            'Advance Paid': advance_paid,
            'Grand Total': grand_total,
            'Total Paid': total_paid,
            'Balance Due': balance_due,
            'Errors': errors,
            'Charges': cleaned_charges  # return cleaned version
        }
