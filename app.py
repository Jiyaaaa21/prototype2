
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

from src.scenarios.scenario_orchestrator import ScenarioOrchestrator


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

st.markdown(
    """
    <style>
    .main {
        background-color: #0e1117;
    }
    [data-testid="stMetric"] {
        background-color: #1c2333;
        padding: 18px;
        border-radius: 10px;
        border: 1px solid #303846;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


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

st.sidebar.title("COMMERCIAL DIGITAL TWIN")
st.sidebar.caption("Olist Brazilian E-Commerce Dataset")

page = st.sidebar.radio(
    "Navigation",
    [
        "Business Overview",
        "Historical Performance",
        "Simulation Explorer",
        "Scenario Analysis",
        "Reports",
    ],
)

st.sidebar.divider()

st.sidebar.success("Simulation Engine: Active")
st.sidebar.success("Historical Replay: Complete")

st.sidebar.metric("Months Processed", replay_report["processed_months"])


# --------------------------------------------------
# PAGE 1: BUSINESS OVERVIEW
# --------------------------------------------------

if page == "Business Overview":

    st.title("Commercial & Sales Digital Twin")
    st.caption(
        "Historical business intelligence and simulation "
        "using the Olist e-commerce dataset."
    )

    order_state = aligned["order_sales"]
    payment_state = aligned["payment_revenue"]

    total_orders = int(order_state["order_count"].sum())

    merchandise_value = float(
        order_state["merchandise_value"].sum()
    )

    freight_value = float(
        order_state["freight_value"].sum()
    )

    total_customers = data["customers"][
        "customer_unique_id"
    ].nunique()

    total_products = len(data["products"])
    total_sellers = len(data["sellers"])

    total_payment_value = float(
        payment_state["total_payment_value"].sum()
    )

    st.subheader("Business KPIs")

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Orders", f"{total_orders:,}")
    col2.metric("Unique Customers", f"{total_customers:,}")
    col3.metric("Merchandise Value", f"R$ {merchandise_value:,.2f}")

    col4, col5, col6 = st.columns(3)

    col4.metric("Products", f"{total_products:,}")
    col5.metric("Sellers", f"{total_sellers:,}")
    col6.metric("Freight Value", f"R$ {freight_value:,.2f}")

    st.divider()

    st.subheader("Business Summary")

    left, right = st.columns(2)

    with left:
        st.markdown("**Merchandise Value vs Payment Value**")

        comparison = pd.DataFrame(
            {
                "Metric": [
                    "Merchandise Value",
                    "Payment Value",
                ],
                "Value (BRL)": [
                    merchandise_value,
                    total_payment_value,
                ],
            }
        ).set_index("Metric")

        st.bar_chart(comparison)

    with right:
        st.markdown("**Dataset Coverage**")

        st.write("Dataset: Olist Brazilian E-Commerce")
        st.write("Timeline: September 2016 – October 2018")
        st.write("Total timeline months: 26")
        st.write("Business components: 6")
        st.write("Monthly state datasets: 7")

    st.info(
        "Merchandise value represents the value of order items. "
        "It should not be interpreted as business profit."
    )


# --------------------------------------------------
# PAGE 2: HISTORICAL PERFORMANCE
# --------------------------------------------------

elif page == "Historical Performance":

    st.title("Historical Business Performance")

    order_state = aligned["order_sales"].copy()

    order_state["purchase_month"] = (
        order_state["purchase_month"].astype(str)
    )

    st.subheader("Monthly Merchandise Value")

    monthly_value = order_state.set_index("purchase_month")[
        ["merchandise_value"]
    ]

    st.line_chart(monthly_value)

    st.subheader("Monthly Order Volume")

    monthly_orders = order_state.set_index("purchase_month")[
        ["order_count"]
    ]

    st.bar_chart(monthly_orders)

    st.subheader("Monthly Historical Data")

    st.dataframe(
        order_state,
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    st.subheader("Other Business Dimensions")

    dimension = st.selectbox(
        "Select a business dimension",
        [
            "customer",
            "product",
            "category",
            "seller",
            "payment_revenue",
            "delivery_experience",
        ],
    )

    selected_state = aligned[dimension].copy()

    if "purchase_month" in selected_state.columns:
        selected_state["purchase_month"] = (
            selected_state["purchase_month"].astype(str)
        )

    st.dataframe(
        selected_state,
        use_container_width=True,
        hide_index=True,
    )


# --------------------------------------------------
# PAGE 3: SIMULATION EXPLORER
# --------------------------------------------------

elif page == "Simulation Explorer":

    st.title("Historical Simulation Explorer")

    st.write(
        "Explore the six component states stored by the "
        "26-month historical replay."
    )

    periods = state_manager.get_available_periods()

    selected_month = st.selectbox(
        "Select simulation month",
        periods,
    )

    snapshot = state_manager.get_simulation_state(
        selected_month
    )

    st.subheader(f"Simulation Snapshot: {selected_month}")

    st.success("Six component states retrieved successfully.")

    component_states = snapshot["components"]

    component_names = {
        "customer_management": "Customer Management",
        "product_management": "Product Management",
        "seller_management": "Seller Management",
        "order_sales_management": "Order & Sales Management",
        "payment_revenue_management": "Payment & Revenue Management",
        "delivery_customer_experience": "Delivery & Customer Experience",
    }

    for key, display_name in component_names.items():

        with st.expander(display_name):

            component_state = component_states[key]

            if "summary" in component_state:
                st.json(component_state["summary"])

            st.json(component_state)


# --------------------------------------------------
# PAGE 4: SCENARIO ANALYSIS
# --------------------------------------------------

elif page == "Scenario Analysis":

    st.title("Business Scenario Analysis")

    st.write(
        "Evaluate a hypothetical product price adjustment "
        "using the existing scenario engine."
    )

    st.warning(
        "This is a deterministic counterfactual scenario. "
        "It holds historical quantities constant and does not "
        "predict customer demand or price elasticity."
    )

    adjustment = st.slider(
        "Product Price Adjustment (%)",
        min_value=-20.0,
        max_value=20.0,
        value=5.0,
        step=0.5,
    )

    st.write(
        f"Selected price adjustment: **{adjustment:.1f}%**"
    )

    if st.button("Run Scenario", type="primary"):

        try:
            with st.spinner("Executing and validating scenario..."):

                orchestrator = ScenarioOrchestrator(
                    products=data["products"],
                    order_items=data["items"],
                    orders=data["orders"],
                    customers=data["customers"],
                    category_translation=data["translation"],
                    output_dir=REPORT_DIR,
                )

                result = orchestrator.run(
                    adjustment_rate=adjustment / 100,
                )

                st.session_state["scenario_result"] = result

            st.success("Scenario executed and independently validated.")

        except Exception as error:
            st.error(f"Scenario execution failed: {error}")


    if "scenario_result" in st.session_state:

        result = st.session_state["scenario_result"]

        summary = result["execution_summary"]

        st.divider()

        st.subheader("Scenario Results")

        if summary["status"] == "SUCCESS":

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Baseline Merchandise Value",
                f"R$ {summary['baseline_merchandise_value']:,.2f}",
            )

            col2.metric(
                "Scenario Merchandise Value",
                f"R$ {summary['scenario_merchandise_value']:,.2f}",
            )

            col3.metric(
                "Merchandise Value Change",
                f"R$ {summary['merchandise_value_change']:,.2f}",
            )

            st.write(
                f"Scenario ID: **{summary['scenario_id']}**"
            )

            st.write(
                f"Affected item lines: "
                f"**{summary['affected_item_lines']:,}**"
            )

            st.success(
                f"Independent validation: "
                f"{summary['independent_validation']}"
            )

            st.subheader("Six-Dimensional Impact Analysis")

            impacts = result["scenario_results"]["impact"]

            for dimension, frame in impacts.items():

                with st.expander(
                    dimension.replace("_", " ").title()
                ):
                    st.dataframe(
                        frame,
                        use_container_width=True,
                        hide_index=True,
                    )


# --------------------------------------------------
# PAGE 5: REPORTS
# --------------------------------------------------

elif page == "Reports":

    st.title("Scenario Reports")

    st.write(
        "Download the PDF and Excel reports generated "
        "by the scenario engine."
    )

    if "scenario_result" not in st.session_state:

        st.info(
            "Run a scenario first to generate downloadable reports."
        )

    else:

        report_paths = st.session_state[
            "scenario_result"
        ]["report_paths"]

        col1, col2 = st.columns(2)

        with col1:

            pdf_path = Path(report_paths["pdf"])

            if pdf_path.exists():

                with open(pdf_path, "rb") as file:
                    pdf_data = file.read()

                st.download_button(
                    label="Download PDF Report",
                    data=pdf_data,
                    file_name=pdf_path.name,
                    mime="application/pdf",
                    use_container_width=True,
                )

            else:
                st.error("PDF report not found.")

        with col2:

            excel_path = Path(report_paths["excel"])

            if excel_path.exists():

                with open(excel_path, "rb") as file:
                    excel_data = file.read()

                st.download_button(
                    label="Download Excel Report",
                    data=excel_data,
                    file_name=excel_path.name,
                    mime=(
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                    use_container_width=True,
                )

            else:
                st.error("Excel report not found.")


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "Commercial & Sales Digital Twin | "
    "Olist Brazilian E-Commerce Dataset | "
    "Historical Simulation and Scenario Analysis"
)
