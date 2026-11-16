
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from config.settings import DATA_DIR, REPORT_DIR

from src.scenarios.product_price_scenario import (
    ProductPriceScenarioEngine
)

from src.scenarios.scenario_report_generator import (
    ScenarioReportGenerator
)


def load_datasets():
    files = {
        "products": "olist_products_dataset.csv",
        "order_items": "olist_order_items_dataset.csv",
        "orders": "olist_orders_dataset.csv",
        "customers": "olist_customers_dataset.csv",
        "category_translation": "product_category_name_translation.csv"
    }

    return {
        name: pd.read_csv(DATA_DIR / filename)
        for name, filename in files.items()
    }


def validate_generated_files(paths):
    print("\nVALIDATING GENERATED FILES")

    excel_path = Path(paths["excel"])
    pdf_path = Path(paths["pdf"])

    assert excel_path.exists(), "Excel report was not generated."
    assert pdf_path.exists(), "PDF report was not generated."

    assert excel_path.stat().st_size > 0
    assert pdf_path.stat().st_size > 0

    print("Excel file exists.")
    print("PDF file exists.")

    # Validate Excel workbook structure.
    print("\nVALIDATING EXCEL WORKBOOK")

    workbook = load_workbook(
        excel_path,
        read_only=True,
        data_only=True
    )

    expected_sheets = {
        "Executive Summary",
        "Scenario Configuration",
        "KPI Comparison",
        "Product Impact",
        "Category Impact",
        "Seller Impact",
        "Customer Impact",
        "Order Impact",
        "Monthly Impact",
        "Limitations"
    }

    actual_sheets = set(workbook.sheetnames)

    missing_sheets = expected_sheets - actual_sheets

    assert not missing_sheets, (
        f"Missing Excel worksheets: {missing_sheets}"
    )

    print("All 10 expected worksheets exist.")

    executive_sheet = workbook["Executive Summary"]

    excel_scenario_id = executive_sheet["B1"].value

    assert excel_scenario_id == "SCN-001"

    print("Scenario ID validated.")

    kpi_sheet = workbook["KPI Comparison"]

    assert kpi_sheet.max_row >= 4

    print("KPI comparison data validated.")

    workbook.close()

    # Validate PDF structure.
    print("\nVALIDATING PDF REPORT")

    with open(pdf_path, "rb") as file:
        pdf_header = file.read(5)

    assert pdf_header == b"%PDF-", (
        "Generated file is not a valid PDF document."
    )

    print("PDF file signature validated.")

    print("\nGENERATED REPORT LOCATIONS")
    print(f"Excel: {excel_path.resolve()}")
    print(f"PDF:   {pdf_path.resolve()}")

    print("\nALL REPORT VALIDATION TESTS PASSED.")


def main():
    print("LOADING OLIST DATASETS")

    data = load_datasets()

    print("Datasets loaded.")

    print("\nINITIALIZING PRODUCT PRICE SCENARIO")

    scenario_engine = ProductPriceScenarioEngine(
        products=data["products"],
        order_items=data["order_items"],
        orders=data["orders"],
        customers=data["customers"],
        category_translation=data["category_translation"],
        adjustment_rate=0.05
    )

    print("Executing scenario.")

    results = scenario_engine.run()

    print("Scenario executed.")

    print("\nGENERATING EXCEL AND PDF REPORTS")

    report_generator = ScenarioReportGenerator(
        output_dir=REPORT_DIR
    )

    generated_paths = report_generator.generate(results)

    print("Both reports generated.")

    validate_generated_files(generated_paths)


if __name__ == "__main__":
    main()
