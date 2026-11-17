
from pathlib import Path

import pandas as pd
import streamlit as st

from config.settings import DATA_DIR

from scripts.test_monthly_state_alignment_integration import (
    load_datasets,
    build_monthly_states,
    build_specifications,
)

from src.components.seller_component import SellerComponent
from src.components.customer_component import CustomerComponent
from src.components.product_component import ProductComponent
from src.components.order_sales_component import OrderSalesComponent
from src.components.payment_component import PaymentComponent
from src.components.delivery_component import DeliveryComponent

from src.relationships import DependencyManager

from src.simulation import (
    SimulationEngine,
    StateManager,
    TimeManager,
)

from src.simulation.monthly_state_aligner import MonthlyStateAligner
from src.simulation.monthly_state_payload_builder import (
    MonthlyStatePayloadBuilder,
)

from src.dashboard.overview_page import render_overview
from src.dashboard.theme import apply_theme
from src.scenarios.scenario_page import render_scenario_page


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Commercial & Sales Digital Twin",
    page_icon="📊",
    layout="wide",
)

REPORT_DIR = Path("data/outputs/reports")


# --------------------------------------------------
# STYLING
# --------------------------------------------------

apply_theme()


# --------------------------------------------------
# DATA LOADING AND HISTORICAL SIMULATION
# --------------------------------------------------

@st.cache_resource(show_spinner="Loading Olist data and running historical simulation...")
def initialize_digital_twin():

    data = load_datasets()

    # Build all seven monthly states
    monthly_states = build_monthly_states(data)

    orders = data["orders"]

    purchase_dates = pd.to_datetime(
        orders["order_purchase_timestamp"],
        errors="raise",
    )

    timeline = pd.period_range(
        start=purchase_dates.min().to_period("M"),
        end=purchase_dates.max().to_period("M"),
        freq="M",
    )

    specifications = build_specifications(monthly_states)

    aligner = MonthlyStateAligner(
        timeline=timeline,
        specifications=specifications,
    )

    aligned_states = aligner.align(monthly_states)

    payload_builder = MonthlyStatePayloadBuilder(aligned_states)

    # Initialize the six existing components
    components = {
        "seller_management": SellerComponent(
            data["sellers"],
            data["items"],
            data["orders"],
        ),

        "customer_management": CustomerComponent(
            data["customers"],
            data["orders"],
            data["items"],
        ),

        "product_management": ProductComponent(
            data["products"],
            data["items"],
            data["translation"],
        ),

        "order_sales_management": OrderSalesComponent(
            data["orders"],
            data["items"],
            data["customers"],
            data["products"],
            data["sellers"],
        ),

        "payment_revenue_management": PaymentComponent(
            data["orders"],
            data["payments"],
        ),

        "delivery_customer_experience": DeliveryComponent(
            data["orders"],
            data["items"],
            data["reviews"],
            data["customers"],
            data["sellers"],
        ),
    }

    dependency_manager = DependencyManager()
    time_manager = TimeManager(orders)
    state_manager = StateManager()

    engine = SimulationEngine(
        components=components,
        dependency_manager=dependency_manager,
        time_manager=time_manager,
        state_manager=state_manager,
    )

    # Historical component execution
    historical_report = engine.run_historical_execution()

    if historical_report["status"] != "SUCCESS":
        raise RuntimeError("Historical execution failed.")

    # Full monthly replay
    replay_report = engine.run_monthly_replay(payload_builder)

    if replay_report["status"] != "SUCCESS":
        raise RuntimeError("Monthly replay failed.")

    if replay_report["processed_months"] != 26:
        raise RuntimeError("Expected 26 monthly snapshots.")

    return {
        "data": data,
        "monthly_states": monthly_states,
        "aligned_states": aligned_states,
        "state_manager": state_manager,
        "replay_report": replay_report,
    }


# --------------------------------------------------
# INITIALIZE APPLICATION
# --------------------------------------------------

try:
    twin = initialize_digital_twin()

except Exception as error:
    st.error(f"Digital Twin initialization failed: {error}")
    st.stop()


data = twin["data"]
aligned = twin["aligned_states"]
state_manager = twin["state_manager"]
replay_report = twin["replay_report"]


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

st.sidebar.markdown(
    '<div class="brand">Biz<span>Twin</span></div>'
    '<div class="brand-sub">Commercial &amp; Sales Digital Twin</div>',
    unsafe_allow_html=True,
)

page = st.sidebar.radio(
    "Navigation",
    ["Business Overview", "Scenario Analysis"],
    label_visibility="collapsed",
)



# --------------------------------------------------
# PAGES
# --------------------------------------------------

if page == "Business Overview":
    render_overview(data, replay_report)
else:
    render_scenario_page(data, REPORT_DIR)
