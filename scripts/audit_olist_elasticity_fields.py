"""
Olist source-data audit for price elasticity feasibility.

Run from the digitalTwin project root:
    python scripts/audit_olist_elasticity_fields.py

Scans CSV files under data/raw/olist and exports:
    data/outputs/reports/elasticity_data_audit/Olist_Elasticity_Data_Audit.xlsx

This script only audits available source fields. It does not modify source data,
create synthetic zero-sales months, or estimate elasticity.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


ROOT = Path.cwd()
RAW_DIR = ROOT / "data" / "raw" / "olist"
OUT_DIR = ROOT / "data" / "outputs" / "reports" / "elasticity_data_audit"
OUT_FILE = OUT_DIR / "Olist_Elasticity_Data_Audit.xlsx"

# Terms are used to flag potentially relevant columns, not to assert their meaning.
KEYWORD_GROUPS = {
    "price_or_revenue": [
        "price", "value", "freight", "payment", "revenue", "amount", "total"
    ],
    "discount_or_promotion": [
        "discount", "promo", "coupon", "campaign", "promotion", "sale"
    ],
    "inventory_or_availability": [
        "stock", "inventory", "available", "availability", "quantity",
        "warehouse", "fulfillment"
    ],
    "product_attributes": [
        "product", "category", "weight", "length", "height", "width"
    ],
    "time_or_date": [
        "date", "time", "timestamp", "created", "approved", "delivered"
    ],
    "seller_or_customer": [
        "seller", "customer", "buyer"
    ],
}


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def read_csv_safely(path: Path) -> tuple[pd.DataFrame | None, str | None]:
    encodings = ["utf-8", "utf-8-sig", "latin1"]
    last_error = None
    for encoding in encodings:
        try:
            return pd.read_csv(path, encoding=encoding, low_memory=False), None
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
    return None, last_error


def classify_column(column: str) -> list[str]:
    name = normalize(column)
    matches = []
    for group, terms in KEYWORD_GROUPS.items():
        if any(term in name for term in terms):
            matches.append(group)
    return matches


def main() -> None:
    if not RAW_DIR.exists():
        raise FileNotFoundError(
            f"Raw data folder not found: {RAW_DIR}\n"
            "Run this script from the digitalTwin project root or update RAW_DIR."
        )

    files = sorted(RAW_DIR.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found directly inside: {RAW_DIR}")

    file_rows = []
    column_rows = []
    candidate_rows = []
    date_rows = []
    errors = []

    for path in files:
        df, error = read_csv_safely(path)
        if error:
            errors.append({"file": path.name, "error": error})
            continue

        file_rows.append(
            {
                "file": path.name,
                "rows": len(df),
                "columns": len(df.columns),
                "duplicate_rows": int(df.duplicated().sum()),
                "memory_mb_approx": round(
                    df.memory_usage(index=True, deep=True).sum() / (1024**2), 2
                ),
            }
        )

        for col in df.columns:
            series = df[col]
            non_null = series.dropna()
            sample_values = " | ".join(
                str(x)[:70] for x in non_null.astype(str).head(3).tolist()
            )
            matches = classify_column(col)

            row = {
                "file": path.name,
                "column": col,
                "dtype": str(series.dtype),
                "non_null_count": int(series.notna().sum()),
                "null_count": int(series.isna().sum()),
                "null_pct": round(float(series.isna().mean() * 100), 2),
                "unique_non_null": int(series.nunique(dropna=True)),
                "sample_values_first_3": sample_values,
                "keyword_flags": ", ".join(matches),
            }
            column_rows.append(row)

            if matches:
                candidate_rows.append(row.copy())

            # Inspect parseable date-like columns without assuming their semantics.
            col_name = normalize(col)
            if any(term in col_name for term in ["date", "time", "timestamp", "created"]):
                parsed = pd.to_datetime(series, errors="coerce")
                valid = parsed.dropna()
                date_rows.append(
                    {
                        "file": path.name,
                        "column": col,
                        "parseable_date_count": int(len(valid)),
                        "parseable_date_pct": round(
                            float(len(valid) / max(len(series), 1) * 100), 2
                        ),
                        "minimum_date": str(valid.min()) if len(valid) else "",
                        "maximum_date": str(valid.max()) if len(valid) else "",
                    }
                )

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(OUT_FILE, engine="openpyxl") as writer:
        pd.DataFrame(file_rows).to_excel(writer, sheet_name="File Summary", index=False)
        pd.DataFrame(column_rows).to_excel(writer, sheet_name="All Columns", index=False)
        pd.DataFrame(candidate_rows).to_excel(
            writer, sheet_name="Candidate Fields", index=False
        )
        pd.DataFrame(date_rows).to_excel(
            writer, sheet_name="Date Coverage", index=False
        )
        pd.DataFrame(errors, columns=["file", "error"]).to_excel(
            writer, sheet_name="Read Errors", index=False
        )

        notes = pd.DataFrame(
            [
                ("Purpose", "Identify source fields relevant to price, promotions, inventory, availability and time."),
                ("Keyword flags", "Flags are search aids only; inspect source definitions before assigning business meaning."),
                ("Inventory", "A product weight, dimensions, or order quantity field is not evidence of stock availability."),
                ("Discount", "A payment difference or freight value is not automatically a product discount."),
                ("Zero sales", "This audit does not establish whether a product was available in months with no observed orders."),
                ("Causality", "Finding candidate columns does not by itself identify causal price elasticity."),
            ],
            columns=["item", "interpretation"],
        )
        notes.to_excel(writer, sheet_name="Read Me", index=False)

    print(f"CSV files found: {len(files)}")
    print(f"Files successfully read: {len(file_rows)}")
    print(f"Read errors: {len(errors)}")
    print("\nFILE SUMMARY")
    if file_rows:
        print(pd.DataFrame(file_rows).to_string(index=False))
    print("\nCANDIDATE FIELDS")
    if candidate_rows:
        print(
            pd.DataFrame(candidate_rows)[
                ["file", "column", "dtype", "null_pct", "unique_non_null", "keyword_flags"]
            ].to_string(index=False)
        )
    else:
        print("No candidate fields matched the keyword audit.")
    print(f"\nAudit workbook saved to:\n{OUT_FILE}")


if __name__ == "__main__":
    main()
