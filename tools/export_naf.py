#!/usr/bin/env python3
"""Convert NAF XLS file to CSV format."""

import sys
from pathlib import Path

try:
    import openpyxl
except ImportError:
    print("Error: openpyxl is required. Install with: pip install openpyxl")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
XLS_FILE = SCRIPT_DIR / "int_courts_naf_rev_2.xls"
CSV_FILE = SCRIPT_DIR / "naf_codes.csv"


def export_naf_to_csv():
    """Load XLS file and export to CSV."""
    if not XLS_FILE.exists():
        print(f"Error: {XLS_FILE} not found")
        sys.exit(1)

    try:
        wb = openpyxl.load_workbook(XLS_FILE)
        ws = wb.active

        print(f"Reading {XLS_FILE}...")
        print(f"Active sheet: {ws.title}")

        # Write to CSV
        with open(CSV_FILE, "w", encoding="utf-8") as f:
            for row in ws.iter_rows(values_only=True):
                # Skip empty rows
                if not any(row):
                    continue

                # Write as CSV
                csv_line = ",".join(str(cell) if cell is not None else "" for cell in row)
                f.write(csv_line + "\n")

        print(f"✓ Exported to {CSV_FILE}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    export_naf_to_csv()
