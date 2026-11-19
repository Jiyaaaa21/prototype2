
from pathlib import Path
import pandas as pd

# ============================================================
# CONFIGURATION
# ============================================================

DATA_DIR = Path("data/raw/olist")

FILES = {
    "customers": "olist_customers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "category_translation":
        "product_category_name_translation.csv"
}

# Candidate primary keys to investigate
PRIMARY_KEYS = {
    "customers": ["customer_id"],
    "orders": ["order_id"],
    "order_items": ["order_id", "order_item_id"],
    "products": ["product_id"],
    "sellers": ["seller_id"],
    "order_payments": ["order_id", "payment_sequential"],
    "order_reviews": ["review_id", "order_id"],
    "category_translation": ["product_category_name"]
}

# Parent table, child table, parent key, child foreign key
RELATIONSHIPS = [
    ("customers", "orders", "customer_id", "customer_id"),
    ("orders", "order_items", "order_id", "order_id"),
    ("products", "order_items", "product_id", "product_id"),
    ("sellers", "order_items", "seller_id", "seller_id"),
    ("orders", "order_payments", "order_id", "order_id"),
    ("orders", "order_reviews", "order_id", "order_id"),
    (
        "category_translation",
        "products",
        "product_category_name",
        "product_category_name"
    )
]

# ============================================================
# LOAD DATA
# ============================================================

def load_datasets():
    datasets = {}

    print("\n" + "=" * 65)
    print("LOADING DATASETS")
    print("=" * 65)

    for table, filename in FILES.items():
        path = DATA_DIR / filename

        if not path.exists():
            print(f"[MISSING] {filename}")
            continue

        df = pd.read_csv(path)
        datasets[table] = df

        print(f"{table:25} Rows: {len(df):>10,} | Columns: {len(df.columns)}")

    return datasets


# ============================================================
# 1. ENTITY / TABLE STRUCTURE
# ============================================================

def inspect_entities(datasets):
    print("\n" + "=" * 65)
    print("1. ENTITY STRUCTURE")
    print("=" * 65)

    for table, df in datasets.items():
        print(f"\nENTITY: {table.upper()}")
        print("-" * 50)

        print("Rows:", len(df))
        print("Columns:", len(df.columns))

        for col in df.columns:
            print(f"  - {col:40} {df[col].dtype}")


# ============================================================
# 2. DATA QUALITY PROFILE
# ============================================================

def inspect_data_quality(datasets):
    print("\n" + "=" * 65)
    print("2. DATA QUALITY PROFILE")
    print("=" * 65)

    for table, df in datasets.items():
        print(f"\nTABLE: {table.upper()}")

        print("Duplicate rows:", df.duplicated().sum())

        nulls = df.isnull().sum()
        nulls = nulls[nulls > 0]

        if nulls.empty:
            print("Null values: None")
        else:
            print("Null values:")
            print(nulls.to_string())

        print("\nUnique values:")
        print(df.nunique().to_string())


# ============================================================
# 3. PRIMARY KEY VALIDATION
# ============================================================

def validate_primary_keys(datasets):
    print("\n" + "=" * 65)
    print("3. PRIMARY KEY VALIDATION")
    print("=" * 65)

    for table, columns in PRIMARY_KEYS.items():

        if table not in datasets:
            continue

        df = datasets[table]

        if not all(col in df.columns for col in columns):
            print(f"\n{table}: Missing candidate key columns")
            continue

        duplicate_count = df.duplicated(
            subset=columns
        ).sum()

        null_count = df[columns].isnull().any(axis=1).sum()

        is_unique = duplicate_count == 0
        has_nulls = null_count > 0

        print(f"\nTABLE: {table.upper()}")
        print("Candidate key:", columns)
        print("Duplicate key combinations:", duplicate_count)
        print("Rows with null key values:", null_count)
        print("Unique:", is_unique)
        print("Null-free:", not has_nulls)

        if is_unique and not has_nulls:
            print("RESULT: Valid candidate primary key")
        else:
            print("RESULT: Requires investigation")


# ============================================================
# 4. FOREIGN KEY / RELATIONSHIP VALIDATION
# ============================================================

def validate_relationships(datasets):
    print("\n" + "=" * 65)
    print("4. RELATIONSHIP VALIDATION")
    print("=" * 65)

    for parent, child, parent_key, child_key in RELATIONSHIPS:

        if parent not in datasets or child not in datasets:
            continue

        parent_df = datasets[parent]
        child_df = datasets[child]

        if parent_key not in parent_df.columns:
            continue

        if child_key not in child_df.columns:
            continue

        parent_values = set(
            parent_df[parent_key].dropna().unique()
        )

        child_values = child_df[child_key].dropna()

        matched = child_values.isin(parent_values)

        unmatched_count = (~matched).sum()

        non_null_count = len(child_values)

        match_rate = (
            matched.mean() * 100
            if non_null_count > 0 else 0
        )

        # Count child records associated with each parent key
        child_counts = child_df[child_key].value_counts()

        max_children = (
            int(child_counts.max())
            if not child_counts.empty else 0
        )

        avg_children = (
            child_counts.mean()
            if not child_counts.empty else 0
        )

        parent_unique = parent_df[parent_key].nunique()

        child_unique = child_df[child_key].nunique()

        print(f"\n{parent.upper()} -> {child.upper()}")
        print("-" * 50)

        print(f"Parent key: {parent_key}")
        print(f"Child foreign key: {child_key}")
        print(f"Parent unique values: {parent_unique:,}")
        print(f"Child unique values: {child_unique:,}")
        print(f"Matched child records: {matched.sum():,}")
        print(f"Unmatched child records: {unmatched_count:,}")
        print(f"Match rate: {match_rate:.2f}%")
        print(f"Maximum children per parent: {max_children}")
        print(f"Average children per referenced parent: {avg_children:.2f}")

        if parent_unique == child_unique and max_children <= 1:
            print("Observed pattern: 1:1 (verify optional participation)")
        elif max_children > 1:
            print("Observed pattern: 1:N")
        else:
            print("Observed pattern: Requires further validation")


# ============================================================
# 5. SPECIAL CUSTOMER IDENTITY ANALYSIS
# ============================================================

def inspect_customer_identity(datasets):
    if "customers" not in datasets:
        return

    df = datasets["customers"]

    print("\n" + "=" * 65)
    print("5. CUSTOMER IDENTITY ANALYSIS")
    print("=" * 65)

    print("Customer records:", len(df))
    print(
        "Unique customer_id:",
        df["customer_id"].nunique()
    )
    print(
        "Unique customer_unique_id:",
        df["customer_unique_id"].nunique()
    )

    repeated = df["customer_unique_id"].value_counts()

    print(
        "Unique customers with multiple customer records:",
        (repeated > 1).sum()
    )

    print(
        "Maximum records per unique customer:",
        repeated.max()
    )


# ============================================================
# 6. SPECIAL GEOGRAPHIC JOIN ANALYSIS
# ============================================================

def inspect_geolocation(datasets):
    if "geolocation" not in datasets:
        return

    geo = datasets["geolocation"]

    print("\n" + "=" * 65)
    print("6. GEOGRAPHIC JOIN ANALYSIS")
    print("=" * 65)

    key = "geolocation_zip_code_prefix"

    print("Geolocation records:", len(geo))
    print("Unique ZIP prefixes:", geo[key].nunique())
    print("Duplicate ZIP prefix records:", geo.duplicated(
        subset=[key]
    ).sum())

    for table in ["customers", "sellers"]:
        if table not in datasets:
            continue

        df = datasets[table]
        column = (
            "customer_zip_code_prefix"
            if table == "customers"
            else "seller_zip_code_prefix"
        )

        if column not in df.columns:
            continue

        geo_prefixes = set(geo[key].dropna().unique())
        business_prefixes = set(df[column].dropna().unique())

        print(f"\n{table.upper()} ZIP prefix match:")
        print(
            "Matched unique prefixes:",
            len(geo_prefixes & business_prefixes)
        )
        print(
            "Unmatched unique prefixes:",
            len(business_prefixes - geo_prefixes)
        )

    print(
        "\nNOTE: ZIP prefix is a non-unique analytical join, "
        "not a conventional enforced foreign key."
    )


# ============================================================
# 7. EXPORT SUMMARY
# ============================================================

def export_entity_summary(datasets):
    rows = []

    for table, df in datasets.items():
        rows.append({
            "entity": table,
            "row_count": len(df),
            "column_count": len(df.columns),
            "duplicate_rows": int(df.duplicated().sum()),
            "columns": ", ".join(df.columns)
        })

    output = pd.DataFrame(rows)

    output.to_csv(
        "entity_summary.csv",
        index=False
    )

    print("\nEntity summary exported to entity_summary.csv")


# ============================================================
# MAIN
# ============================================================

def main():
    datasets = load_datasets()

    if not datasets:
        print("No datasets loaded. Check DATA_DIR and filenames.")
        return

    inspect_entities(datasets)
    inspect_data_quality(datasets)
    validate_primary_keys(datasets)
    validate_relationships(datasets)
    inspect_customer_identity(datasets)
    inspect_geolocation(datasets)
    export_entity_summary(datasets)

    print("\n" + "=" * 65)
    print("ENTITY AND RELATIONSHIP EXPLORATION COMPLETED")
    print("=" * 65)


if __name__ == "__main__":
    main()
