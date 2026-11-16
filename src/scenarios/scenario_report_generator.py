from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
import pandas as pd

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from config.settings import REPORT_DIR


class ScenarioReportGenerator:
    """
    Generates Excel and PDF reports for MultiParameterScenarioEngine.

    Expected input is the dictionary returned by:
        MultiParameterScenarioEngine.run()

    The generator only formats supplied results. It does not rerun
    calculations or modify historical data.
    """

    DIMENSIONS = (
        "product",
        "category",
        "seller",
        "customer",
        "order",
        "monthly",
    )

    DIMENSION_KEYS = {
        "product": ["product_id"],
        "category": ["category_english"],
        "seller": ["seller_id"],
        "customer": ["customer_unique_id"],
        "order": ["order_id"],
        "monthly": ["purchase_month"],
    }

    METRICS = (
        "gross_merchandise_value",
        "discount_amount",
        "net_merchandise_value",
        "freight_value",
        "commission",
        "seller_cost",
        "seller_payout",
        "seller_contribution",
        "item_line_count",
    )

    CURRENCY_METRICS = {
        "gross_merchandise_value",
        "discount_amount",
        "net_merchandise_value",
        "freight_value",
        "commission",
        "seller_cost",
        "seller_payout",
        "seller_contribution",
    }

    PARAMETER_LABELS = {
        "product_price_adjustment": "Product price adjustment",
        "discount_rate": "Discount rate",
        "seller_cost_rate": "Seller cost rate",
        "commission_rate": "Commission rate",
        "freight_adjustment": "Freight adjustment",
    }

    CURRENCY_FORMAT = '"R$" #,##0.00;[Red]-"R$" #,##0.00'
    NUMBER_FORMAT = '#,##0'
    PERCENTAGE_FORMAT = '0.00"%"'

    def __init__(self, output_dir=None):
        self.output_dir = Path(
            output_dir if output_dir is not None else REPORT_DIR
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------
    # VALIDATION
    # ---------------------------------------------------------

    def _validate_results(self, results):
        if not isinstance(results, dict):
            raise TypeError("Scenario results must be a dictionary.")

        required = {
            "status",
            "parameters",
            "baseline",
            "scenario",
            "impact",
            "validation",
        }
        missing = required - set(results)
        if missing:
            raise ValueError(
                f"Scenario results missing keys: {sorted(missing)}"
            )

        for section in ("baseline", "scenario"):
            if not isinstance(results[section], dict):
                raise TypeError(f"{section} must be a dictionary.")

            for key in ("summary", "transactions", "dimensions"):
                if key not in results[section]:
                    raise ValueError(
                        f"{section} results missing '{key}'."
                    )

            if not isinstance(results[section]["summary"], dict):
                raise TypeError(f"{section} summary must be a dictionary.")

            if not isinstance(results[section]["dimensions"], dict):
                raise TypeError(
                    f"{section} dimensions must be a dictionary."
                )

        if not isinstance(results["parameters"], dict):
            raise TypeError("Parameters must be a dictionary.")

        for config_name in ("baseline", "scenario"):
            if config_name not in results["parameters"]:
                raise ValueError(
                    f"Missing {config_name} parameter configuration."
                )

        if not isinstance(results["impact"], dict):
            raise TypeError("Impact results must be a dictionary.")

        if "overall" not in results["impact"]:
            raise ValueError("Impact results missing 'overall'.")

        if "dimensions" not in results["impact"]:
            raise ValueError("Impact results missing 'dimensions'.")

        for dimension in self.DIMENSIONS:
            if dimension not in results["impact"]["dimensions"]:
                raise ValueError(
                    f"Missing impact dimension: {dimension}"
                )

            frame = results["impact"]["dimensions"][dimension]
            if not isinstance(frame, pd.DataFrame):
                raise TypeError(
                    f"Impact for {dimension} must be a DataFrame."
                )

            required_columns = (
                set(self.DIMENSION_KEYS[dimension])
                | {
                    f"{metric}_{suffix}"
                    for metric in self.METRICS
                    for suffix in ("baseline", "scenario", "impact")
                }
            )
            missing_columns = required_columns - set(frame.columns)
            if missing_columns:
                raise ValueError(
                    f"{dimension} impact is missing columns: "
                    f"{sorted(missing_columns)}"
                )

        if not isinstance(results["validation"], dict):
            raise TypeError("Validation results must be a dictionary.")

        return True

    # ---------------------------------------------------------
    # FORMATTING HELPERS
    # ---------------------------------------------------------

    @staticmethod
    def _safe_value(value):
        if value is None:
            return None

        if pd.isna(value):
            return None

        if isinstance(value, (np.integer,)):
            return int(value)

        if isinstance(value, (np.floating,)):
            return float(value)

        if isinstance(value, (np.bool_,)):
            return bool(value)

        if isinstance(value, pd.Timestamp):
            return value.isoformat()

        if isinstance(value, (dict, list, tuple, set)):
            return str(value)

        return value

    @staticmethod
    def _currency(value):
        return f"R$ {float(value):,.2f}"

    @staticmethod
    def _percentage(value):
        if value is None or pd.isna(value):
            return "N/A"
        return f"{float(value):,.2f}%"

    @staticmethod
    def _parameter_as_percentage(value):
        return f"{float(value) * 100:,.2f}%"

    def _build_kpi_rows(self, results):
        baseline = results["baseline"]["summary"]
        scenario = results["scenario"]["summary"]
        overall_impact = results["impact"]["overall"]

        rows = []
        for metric in self.METRICS:
            rows.append({
                "KPI": metric.replace("_", " ").title(),
                "Baseline": baseline[metric],
                "Scenario": scenario[metric],
                "Change": overall_impact[metric]["impact"],
                "Change (%)": overall_impact[metric]["impact_pct"],
            })
        return rows

    # ---------------------------------------------------------
    # REPORT ENTRY POINT
    # ---------------------------------------------------------

    def generate(self, results):
        """
        Generate Excel and PDF reports from validated engine results.

        Returns a dictionary containing generated file paths.
        """
        self._validate_results(results)

        if not results["validation"].get("passed", False):
            raise ValueError(
                "Reports cannot be generated because scenario "
                "validation did not pass."
            )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"Multi_Parameter_Scenario_{timestamp}"

        excel_path = self.output_dir / f"{base_name}.xlsx"
        pdf_path = self.output_dir / f"{base_name}.pdf"

        self._generate_excel(results, excel_path)
        self._generate_pdf(results, pdf_path)

        return {
            "excel": excel_path,
            "pdf": pdf_path,
        }

    # ---------------------------------------------------------
    # EXCEL REPORT
    # ---------------------------------------------------------

    def _generate_excel(self, results, output_path):
        workbook = Workbook()

        baseline = results["baseline"]["summary"]
        scenario = results["scenario"]["summary"]
        overall = results["impact"]["overall"]
        validation = results["validation"]

        # 1. Executive summary
        sheet = workbook.active
        sheet.title = "Executive Summary"

        executive_rows = [
            ["Metric", "Value"],
            ["Execution Status", results["status"]],
            ["Validation Status", "PASSED" if validation["passed"] else "FAILED"],
            ["Historical Transactions Unchanged",
             validation["historical_transactions_unchanged"]],
            ["Transaction / Item Lines", scenario["item_line_count"]],
        ]

        for metric in self.METRICS:
            executive_rows.append([
                f"{metric.replace('_', ' ').title()} - Baseline",
                baseline[metric],
            ])
            executive_rows.append([
                f"{metric.replace('_', ' ').title()} - Scenario",
                scenario[metric],
            ])
            executive_rows.append([
                f"{metric.replace('_', ' ').title()} - Impact",
                overall[metric]["impact"],
            ])
            executive_rows.append([
                f"{metric.replace('_', ' ').title()} - Impact (%)",
                overall[metric]["impact_pct"],
            ])

        for row in executive_rows:
            sheet.append(row)

        # 2. Scenario configuration
        config_sheet = workbook.create_sheet("Scenario Configuration")
        config_sheet.append(["Parameter", "Baseline", "Scenario", "Unit"])

        baseline_parameters = results["parameters"]["baseline"]
        scenario_parameters = results["parameters"]["scenario"]

        for key, label in self.PARAMETER_LABELS.items():
            config_sheet.append([
                label,
                baseline_parameters[key],
                scenario_parameters[key],
                "Rate / adjustment (decimal; e.g. 0.10 = 10%)",
            ])

        # 3. KPI comparison
        kpi_sheet = workbook.create_sheet("KPI Comparison")
        kpi_sheet.append([
            "KPI", "Baseline", "Scenario", "Change", "Change (%)"
        ])

        for row in self._build_kpi_rows(results):
            kpi_sheet.append([
                row["KPI"],
                row["Baseline"],
                row["Scenario"],
                row["Change"],
                row["Change (%)"],
            ])

        # 4. Six dimensional impact sheets
        for dimension in self.DIMENSIONS:
            frame = results["impact"]["dimensions"][dimension]
            output_sheet = workbook.create_sheet(
                f"{dimension.title()} Impact"
            )
            output_sheet.append(list(frame.columns))

            for record in frame.itertuples(index=False, name=None):
                output_sheet.append([
                    self._safe_value(value) for value in record
                ])

        # 5. Validation report
        validation_sheet = workbook.create_sheet("Validation")
        validation_sheet.append(["Validation", "Result"])

        validation_sheet.append([
            "Overall validation",
            validation["passed"],
        ])
        validation_sheet.append([
            "Historical transactions unchanged",
            validation["historical_transactions_unchanged"],
        ])

        for config_name in ("baseline", "scenario"):
            report = validation[config_name]
            validation_sheet.append([
                f"{config_name.title()} checks passed",
                f"{report['passed_checks']} / {report['total_checks']}",
            ])
            validation_sheet.append([
                f"{config_name.title()} reconciliation status",
                report["passed"],
            ])
            for failed_check in report["failed_checks"]:
                validation_sheet.append([
                    f"{config_name.title()} failed check",
                    failed_check,
                ])

        # 6. Methodology and limitations
        limitations = workbook.create_sheet("Methodology & Limits")
        limitations.append(["Area", "Treatment"])
        limitations.append([
            "Historical source data",
            "Copied before calculations; original input files are not modified.",
        ])
        limitations.append([
            "Product price adjustment",
            "Applied to historical item-line price.",
        ])
        limitations.append([
            "Discount",
            "Applied to adjusted gross merchandise value.",
        ])
        limitations.append([
            "Seller cost",
            "User-configured rate applied to historical item price; "
            "not an observed Olist procurement cost.",
        ])
        limitations.append([
            "Commission",
            "User-configured rate applied to net merchandise value plus adjusted freight. "
            "The 20% baseline benchmark is sourced from Olist's documented 2017 fee model; "
            "it is a historical benchmark, not a measured rate for every seller/order.",
        ])
        limitations.append([
            "Commission source",
            "Olist 2017 documented commission model: 20% of the order value including product price and freight. Applied here as a historical benchmark; source period and seller-specific terms may differ.",
        ])
        limitations.append([
            "Seller cost source",
            "IBGE Annual Trade Survey 2018: retail trade margin rate 37.6%, defined relative to cost of goods sold. Derived cost-to-sales proxy = 1 / (1 + 0.376) = 72.6744%. This is not an Olist-specific cost observation.",
        ])
        limitations.append([
            "Seller payout",
            "Net merchandise value less commission calculated on net merchandise value plus adjusted freight. "
            "Freight is not added as seller payout revenue.",
        ])
        limitations.append([
            "Seller contribution",
            "Calculated seller payout less estimated seller cost.",
        ])
        limitations.append([
            "Freight",
            "Adjusted separately and excluded from seller payout and contribution.",
        ])
        limitations.append([
            "Demand and order volume",
            "Held at historical item-line records; no demand response is inferred.",
        ])
        limitations.append([
            "Customer behaviour",
            "No behavioural response or causal elasticity is estimated.",
        ])
        limitations.append([
            "Delivery experience",
            "Not recalculated by financial parameter changes.",
        ])
        limitations.append([
            "Inventory and stockouts",
            "Not modelled.",
        ])
        limitations.append([
            "Payment records",
            "Actual payment transaction outcomes are not recalculated.",
        ])
        limitations.append([
            "Monthly dimension",
            "Contains months with item-line activity in the input transactions.",
        ])
        limitations.append([
            "Item line count",
            "Each Olist order_items row is treated as one item line; "
            "this is not a unit quantity field.",
        ])

        self._format_workbook(workbook)
        self._apply_number_formats(workbook)
        workbook.save(output_path)

    @staticmethod
    def _format_workbook(workbook):
        header_fill = PatternFill(
            fill_type="solid",
            fgColor="1F4E78",
        )
        header_font = Font(bold=True, color="FFFFFF")
        thin_border = Border(
            bottom=Side(style="thin", color="D9E2F3")
        )

        for sheet in workbook.worksheets:
            sheet.freeze_panes = "A2"
            sheet.sheet_view.showGridLines = False

            if sheet.max_row:
                for cell in sheet[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(
                        horizontal="center",
                        vertical="center",
                        wrap_text=True,
                    )

            for row in sheet.iter_rows():
                for cell in row:
                    cell.border = thin_border
                    cell.alignment = Alignment(
                        vertical="center",
                        wrap_text=True,
                    )

            for column_cells in sheet.columns:
                column_letter = get_column_letter(
                    column_cells[0].column
                )
                max_length = max(
                    (
                        len(str(cell.value))
                        for cell in column_cells
                        if cell.value is not None
                    ),
                    default=10,
                )
                sheet.column_dimensions[column_letter].width = min(
                    max(max_length + 3, 14),
                    48,
                )

            if sheet.max_row > 1:
                sheet.auto_filter.ref = sheet.dimensions

    def _apply_number_formats(self, workbook):
        for sheet in workbook.worksheets:
            headers = {
                cell.value: cell.column
                for cell in sheet[1]
                if cell.value is not None
            }

            for header, column_index in headers.items():
                header_text = str(header).lower()

                if (
                    header in self.CURRENCY_METRICS
                    or any(
                        header_text == f"{metric}_{suffix}"
                        for metric in self.CURRENCY_METRICS
                        for suffix in ("baseline", "scenario", "impact")
                    )
                    or header_text.endswith(" - baseline")
                    or header_text.endswith(" - scenario")
                    or header_text.endswith(" - impact")
                ):
                    number_format = self.CURRENCY_FORMAT
                elif (
                    header_text.endswith("_impact_pct")
                    or header_text == "change (%)"
                    or header_text.endswith(" - impact (%)")
                ):
                    number_format = self.PERCENTAGE_FORMAT
                elif (
                    header_text == "item_line_count"
                    or header_text.endswith("_item_line_count")
                ):
                    number_format = self.NUMBER_FORMAT
                else:
                    continue

                for row in range(2, sheet.max_row + 1):
                    sheet.cell(
                        row=row,
                        column=column_index,
                    ).number_format = number_format

        # Executive summary values use labels in column A.
        sheet = workbook["Executive Summary"]
        for row in range(2, sheet.max_row + 1):
            label = str(sheet.cell(row, 1).value or "")
            metric_name = label.rsplit(" - ", 1)[0].lower().replace(" ", "_")
            suffix = label.rsplit(" - ", 1)[-1].lower()

            if metric_name in self.CURRENCY_METRICS and suffix != "impact (%)":
                sheet.cell(row, 2).number_format = self.CURRENCY_FORMAT
            elif suffix == "impact (%)":
                sheet.cell(row, 2).number_format = self.PERCENTAGE_FORMAT
            elif metric_name == "item_line_count":
                sheet.cell(row, 2).number_format = self.NUMBER_FORMAT

        # KPI comparison
        sheet = workbook["KPI Comparison"]
        for row in range(2, sheet.max_row + 1):
            label = str(sheet.cell(row, 1).value or "").lower()
            fmt = (
                self.NUMBER_FORMAT
                if label == "item line count"
                else self.CURRENCY_FORMAT
            )
            for col in (2, 3, 4):
                sheet.cell(row, col).number_format = fmt
            sheet.cell(row, 5).number_format = self.PERCENTAGE_FORMAT

        # Scenario configuration values are decimal rates.
        sheet = workbook["Scenario Configuration"]
        for row in range(2, sheet.max_row + 1):
            for col in (2, 3):
                sheet.cell(row, col).number_format = self.PERCENTAGE_FORMAT

    # ---------------------------------------------------------
    # PDF REPORT
    # ---------------------------------------------------------

    def _generate_pdf(self, results, output_path):
        baseline = results["baseline"]["summary"]
        scenario = results["scenario"]["summary"]
        overall = results["impact"]["overall"]
        validation = results["validation"]
        parameters = results["parameters"]

        document = SimpleDocTemplate(
            str(output_path),
            pagesize=landscape(A4),
            rightMargin=13 * mm,
            leftMargin=13 * mm,
            topMargin=13 * mm,
            bottomMargin=13 * mm,
        )

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name="TwinReportTitle",
            parent=styles["Title"],
            fontSize=19,
            leading=23,
            alignment=TA_CENTER,
            spaceAfter=10,
        ))
        styles.add(ParagraphStyle(
            name="TwinSectionHeading",
            parent=styles["Heading2"],
            fontSize=12,
            leading=15,
            spaceBefore=10,
            spaceAfter=6,
        ))
        styles.add(ParagraphStyle(
            name="TwinSmall",
            parent=styles["BodyText"],
            fontSize=8,
            leading=10,
        ))

        story = []

        def heading(text):
            story.append(Paragraph(
                escape(str(text)),
                styles["TwinSectionHeading"],
            ))

        def paragraph(text):
            story.append(Paragraph(
                escape(str(text)),
                styles["TwinSmall"],
            ))
            story.append(Spacer(1, 4))

        def make_table(data, widths=None, font_size=7):
            table = Table(
                data,
                colWidths=widths,
                repeatRows=1,
                hAlign="LEFT",
            )
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), font_size),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B7C9D6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                    colors.white,
                    colors.HexColor("#EDF3F8"),
                ]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            return table

        # Cover and executive summary
        story.append(Paragraph(
            "COMMERCIAL &amp; SALES DIGITAL TWIN",
            styles["TwinReportTitle"],
        ))
        story.append(Paragraph(
            "Multi-Parameter Scenario Impact Report",
            styles["Heading2"],
        ))
        paragraph(
            f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}"
        )
        paragraph(f"Execution status: {results['status']}")
        paragraph(
            "Validation: PASSED"
            if validation["passed"]
            else "Validation: FAILED"
        )

        heading("1. Executive KPI Comparison")
        kpi_data = [[
            "KPI", "Baseline", "Scenario", "Impact", "Impact (%)"
        ]]

        for metric in self.METRICS:
            if metric in self.CURRENCY_METRICS:
                formatter = self._currency
            else:
                formatter = lambda value: f"{value:,.0f}"

            kpi_data.append([
                metric.replace("_", " ").title(),
                formatter(baseline[metric]),
                formatter(scenario[metric]),
                formatter(overall[metric]["impact"]),
                self._percentage(overall[metric]["impact_pct"]),
            ])

        story.append(make_table(kpi_data))

        # Configuration
        heading("2. Scenario Configuration")
        config_data = [[
            "Parameter", "Baseline", "Scenario"
        ]]
        for key, label in self.PARAMETER_LABELS.items():
            config_data.append([
                label,
                self._parameter_as_percentage(parameters["baseline"][key]),
                self._parameter_as_percentage(parameters["scenario"][key]),
            ])
        story.append(make_table(config_data))

        # Methodology
        heading("3. Calculation Methodology")
        methodology = [
            "Adjusted item price = historical item price × (1 + price adjustment).",
            "Gross merchandise value = sum of adjusted item-line prices.",
            "Discount amount = gross merchandise value × discount rate.",
            "Net merchandise value = gross merchandise value − discount amount.",
            "Freight = historical freight × (1 + freight adjustment).",
            "Seller cost = historical item price × user-configured seller cost rate.",
            "Commission base = net merchandise value + adjusted freight.",
            "Commission = commission base × user-configured commission rate; the 20% baseline is an Olist 2017 historical benchmark.",
            "Seller payout = net merchandise value − commission (freight is not added to payout).",
            "Seller contribution = seller payout − estimated seller cost.",
        ]
        for item in methodology:
            paragraph(f"• {item}")

        # Six dimensions
        story.append(PageBreak())
        heading("4. Six-Dimensional Impact Analysis")

        for index, dimension in enumerate(self.DIMENSIONS, start=1):
            frame = results["impact"]["dimensions"][dimension].copy()
            metric = "net_merchandise_value"

            frame["_sort"] = frame[f"{metric}_impact"].abs()
            top_rows = frame.sort_values(
                "_sort",
                ascending=False,
            ).head(10)

            heading(f"4.{index} {dimension.title()} Impact")

            table_data = [[
                "Group",
                "Baseline NMV",
                "Scenario NMV",
                "NMV Impact",
                "Commission Impact",
                "Seller Contribution Impact",
            ]]

            for _, record in top_rows.iterrows():
                group_label = " | ".join(
                    str(record[key])
                    for key in self.DIMENSION_KEYS[dimension]
                )
                table_data.append([
                    group_label[:42],
                    self._currency(record["net_merchandise_value_baseline"]),
                    self._currency(record["net_merchandise_value_scenario"]),
                    self._currency(record["net_merchandise_value_impact"]),
                    self._currency(record["commission_impact"]),
                    self._currency(record["seller_contribution_impact"]),
                ])

            story.append(make_table(table_data, font_size=6.5))

        # Validation and limitations
        story.append(PageBreak())
        heading("5. Validation and Reconciliation")

        validation_data = [
            ["Check", "Result"],
            ["Overall validation", "PASSED" if validation["passed"] else "FAILED"],
            [
                "Historical transactions unchanged",
                str(validation["historical_transactions_unchanged"]),
            ],
        ]

        for config_name in ("baseline", "scenario"):
            report = validation[config_name]
            validation_data.append([
                f"{config_name.title()} reconciliation",
                f"{report['passed_checks']} / {report['total_checks']} passed",
            ])

        story.append(make_table(validation_data))

        heading("6. Assumptions and Model Limitations")
        limitations = [
            "Seller cost rate is a proxy derived from IBGE's 2018 retail trade margin rate of 37.6%; cost-to-sales = 1 / (1 + 0.376) = 72.6744%. This is an industry-level proxy, not Olist seller procurement data.",
            "Baseline commission rate of 20% is based on Olist's documented 2017 fee model. It is applied to net merchandise value plus adjusted freight. It should not be treated as an exact fee for every historical order or seller.",
            "Seller cost is calculated on historical item price, not adjusted price. The IBGE-derived proxy is not an observed seller cost.",
            "Freight is calculated separately. Adjusted freight is included in the commission base but is not added to seller payout or seller contribution.",
            "Historical item lines and order volume are held constant.",
            "No demand response, causal price elasticity, or customer behavioural response is estimated.",
            "Delivery outcomes and inventory or stockout effects are not recalculated.",
            "Actual payment transaction outcomes are not recalculated.",
            "Each order_items row is treated as one item line, not as a unit quantity.",
            "Monthly impact contains months with transaction activity; zero-activity calendar months are not generated by this engine.",
        ]
        for item in limitations:
            paragraph(f"• {item}")

        heading("7. Interpretation")
        paragraph(
            "This report presents a deterministic financial counterfactual "
            "on historical Olist item lines. Results depend on the explicitly "
            "entered baseline and scenario parameters. Estimated seller cost "
            "and commission must not be interpreted as observed historical "
            "business values. Changes in demand, order volume, delivery, or "
            "customer behaviour are not inferred."
        )

        document.build(story)
