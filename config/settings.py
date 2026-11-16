from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data" / "raw" / "olist"
OUTPUT_DIR = PROJECT_ROOT / "data" / "outputs"

SNAPSHOT_DIR = OUTPUT_DIR / "snapshots"
REPORT_DIR = OUTPUT_DIR / "reports"

SELLERS_FILE = DATA_DIR / "olist_sellers_dataset.csv"
ORDERS_FILE = DATA_DIR / "olist_orders_dataset.csv"
ORDER_ITEMS_FILE = DATA_DIR / "olist_order_items_dataset.csv"

CURRENCY = "BRL"
SIMULATION_FREQUENCY = "M"
HISTORICAL_DATA_IMMUTABLE = True

for directory in [OUTPUT_DIR, SNAPSHOT_DIR, REPORT_DIR]:
    directory.mkdir(parents=True, exist_ok=True)