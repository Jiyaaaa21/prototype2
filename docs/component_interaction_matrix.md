# Component Interaction Matrix
## Commercial & Sales Digital Twin

**Project:** Commercial & Sales Digital Twin  
**Dataset:** Olist Brazilian E-Commerce Dataset  
**Architecture:** Hybrid Component-Based Architecture with Central Simulation Engine  
**Simulation Approach:** Integrated Scenario Simulation  
**Historical Replay Frequency:** Monthly

---

## 1. Purpose

This document defines the interactions, dependencies, inputs, and outputs of the six business components in the Commercial & Sales Digital Twin.

The objective is to establish a structured interaction framework before implementing the Central Simulation Engine.

Each component maintains its own business state and performs component-specific analysis. The Central Simulation Engine coordinates communication between components and manages integrated scenario execution.

## 2. Component Overview

| ID | Component | Primary Responsibility |
|---|---|---|
| C01 | Customer Management | Analyse customer behaviour, purchasing patterns, and customer activity. |
| C02 | Product Management | Maintain product information and analyse product-level sales performance. |
| C03 | Seller Management | Analyse seller performance, sales contribution, and seller-related metrics. |
| C04 | Order & Sales Management | Manage order-level activity, sales quantities, and transaction relationships. |
| C05 | Payment & Revenue Management | Analyse payment methods, payment values, installments, and revenue-related metrics. |
| C06 | Delivery & Customer Experience | Analyse shipping activity, delivery performance, and customer experience indicators. |

## 3. Component Inputs and Outputs

### C01 — Customer Management

**Inputs**
- Customer master records
- Customer-to-order relationships
- Order purchase timestamps
- Order status
- Customer location information

**Outputs**
- Customer-level purchase history
- Customer order frequency
- Customer activity metrics
- Customer location distribution
- Customer-related performance indicators

**Dependencies**
- Receives order information from Order & Sales Management.
- Provides customer-related information to Delivery & Customer Experience.

### C02 — Product Management

**Inputs**
- Product master records
- Product category information
- Product dimensions and attributes
- Order-item records
- Product sales quantities

**Outputs**
- Product-level sales performance
- Product demand indicators
- Product category performance
- Product-level merchandise value
- Product availability assumptions for scenario modelling

**Dependencies**
- Provides product information to Order & Sales Management.
- Uses order-item information to calculate historical product performance.
- Interacts with Seller Management through product-order-item relationships.

### C03 — Seller Management

**Inputs**
- Seller master records
- Order-item records
- Order status
- Order purchase timestamps
- Product and seller relationships

**Outputs**
- Seller-level historical state
- Seller order-item metrics
- Seller sales contribution
- Seller delivery-related performance
- Seller scenario results
- Seller business-rule validation results

**Dependencies**
- Receives order-item activity from Order & Sales Management.
- Uses product-related information from Product Management where required.
- Provides seller performance information to the Central Simulation Engine.

**Implementation Status:** Seller Component implemented and integrity tests passed.

**Important modelling limitation:** Olist does not provide actual seller procurement costs, operating expenses, or platform commission rates. These must remain explicitly identified as hypothetical scenario inputs.

### C04 — Order & Sales Management

**Inputs**
- Customer identifiers
- Product identifiers
- Seller identifiers
- Order timestamps
- Order status
- Order-item quantities
- Item prices
- Freight values

**Outputs**
- Order-level historical state
- Sales volume metrics
- Order-item metrics
- Order status distribution
- Merchandise sales value
- Order-level scenario changes

**Dependencies**
- Receives customer information from Customer Management.
- Uses product information from Product Management.
- Uses seller information from Seller Management.
- Provides transaction information to Payment & Revenue Management.
- Provides shipment-related order information to Delivery & Customer Experience.

### C05 — Payment & Revenue Management

**Inputs**
- Order identifiers
- Payment type
- Payment value
- Payment installments
- Order-level transaction information

**Outputs**
- Payment method distribution
- Payment value metrics
- Installment distribution
- Order-level payment summaries
- Revenue-related scenario indicators

**Dependencies**
- Receives order transaction information from Order & Sales Management.
- Provides payment-related metrics to the Central Simulation Engine.

**Important modelling limitation:** Payment value should not automatically be interpreted as platform-recognised revenue or profit. The accounting meaning must be defined separately.

### C06 — Delivery & Customer Experience

**Inputs**
- Order identifiers
- Seller identifiers
- Customer location information
- Order purchase timestamps
- Carrier handover timestamps
- Estimated delivery dates
- Actual delivery dates
- Order status

**Outputs**
- Delivery duration metrics
- Estimated-versus-actual delivery performance
- Late delivery indicators
- Delivery status distribution
- Customer experience indicators
- Delivery-related scenario results

**Dependencies**
- Receives order information from Order & Sales Management.
- Uses seller information from Seller Management.
- Uses customer location information from Customer Management.
- Provides delivery performance indicators to the Central Simulation Engine.

---

## 4. Component Interaction Matrix

The following matrix identifies the proposed interactions between components.

| Source Component | Target Component | Interaction | Relationship Type |
|---|---|---|---|
| Customer Management | Order & Sales Management | Customer information supports order analysis. | Direct |
| Product Management | Order & Sales Management | Product information supports order-item analysis. | Direct |
| Seller Management | Order & Sales Management | Seller information supports seller-related order analysis. | Direct |
| Order & Sales Management | Payment & Revenue Management | Order transactions are linked to payment records. | Direct |
| Order & Sales Management | Delivery & Customer Experience | Order timestamps and status support delivery analysis. | Direct |
| Seller Management | Delivery & Customer Experience | Seller identifiers support seller-related delivery analysis. | Direct |
| Customer Management | Delivery & Customer Experience | Customer location supports delivery analysis. | Direct |
| Product Management | Seller Management | Product and seller relationships are analysed through order items. | Indirect |
| Customer Management | Payment & Revenue Management | Customer payment behaviour is derived through customer-order-payment relationships. | Indirect |
| Product Management | Payment & Revenue Management | Product sales value can be related to payments through order transactions. | Indirect |

**Note:** Direct and indirect relationships describe the proposed business/data flow. They do not imply that every interaction has already been implemented in code.

## 5. Central Simulation Engine

The Central Simulation Engine will coordinate all six components.

Its responsibilities will include:

1. Initialising the component instances.
2. Receiving historical states and component outputs.
3. Maintaining a consistent simulation timeline.
4. Accepting scenario parameters.
5. Determining the execution order of dependent components.
6. Passing relevant scenario changes between components.
7. Collecting component-level scenario results.
8. Consolidating system-wide business metrics.
9. Recording scenario assumptions and execution results.
10. Ensuring historical datasets remain unchanged during simulation.

### Proposed Architecture

```text
                    CENTRAL SIMULATION ENGINE
                              |
             +----------------+----------------+
             |                |                |
       Historical State  Scenario Manager  Result Collector
             |                |                |
     +-------+-------+--------+--------+-------+
     |       |       |        |        |       |
    C01     C02     C03      C04      C05     C06
     |       |       |        |        |       |
 Customer Product Seller   Order &  Payment  Delivery &
 Mgmt.    Mgmt.   Mgmt.    Sales    & Revenue Customer
                           Mgmt.              Experience
```

The diagram represents logical coordination. Actual execution order and data-transfer mechanisms will be defined during implementation.

## 6. Integrated Scenario Flow

**Example Scenario: Increase in Product Demand**

1. Product Management identifies the affected products.
2. Order & Sales Management receives the increased demand assumption and calculates the resulting order activity.
3. Seller Management evaluates the additional seller workload and its effect on seller-level metrics.
4. Payment & Revenue Management evaluates the corresponding payment and revenue-related changes.
5. Delivery & Customer Experience evaluates the additional delivery workload and potential delivery delays.
6. Customer Management evaluates the potential impact on customer-level indicators.
7. The Central Simulation Engine consolidates the outputs and generates an overall scenario report.

**Scenario assumptions:** Any unavailable variables, such as seller capacity, stock availability, or delivery capacity, must be introduced as explicitly documented parameters rather than treated as observed historical facts.

## 7. Historical Data and Scenario Separation

The system will maintain a clear distinction between historical observations and simulated values.

| Data Category | Purpose |
|---|---|
| Historical Data | Original Olist dataset records used for analysis. |
| Component State | Derived business metrics and component-level historical state. |
| Scenario Inputs | User-defined hypothetical business parameters. |
| Scenario Outputs | Simulated changes and calculated business indicators. |

Historical datasets must remain immutable during scenario execution.

Scenario calculations must operate on separate state representations or copies.

## 8. Design Principles

The following principles will guide implementation:

- **Modularity:** Each component has a clearly defined business responsibility.
- **Loose Coupling:** Components communicate through defined interfaces rather than accessing each other's internal implementation.
- **High Cohesion:** Each component performs operations related to its own business domain.
- **Traceability:** Each output should be traceable to its source data or scenario assumptions.
- **Data Integrity:** Historical data must remain unchanged during simulation.
- **Reproducibility:** Identical historical inputs and scenario parameters should produce consistent results.
- **Transparency:** Hypothetical assumptions must be distinguished from actual dataset observations.
- **Scalability:** New business components and scenario types should be addable without redesigning the entire system.

## 9. Current Implementation Status

| Component | Implementation Status |
|---|---|
| Customer Management | Pending |
| Product Management | Pending |
| Seller Management | Implemented; integrity tests passed |
| Order & Sales Management | Pending |
| Payment & Revenue Management | Pending |
| Delivery & Customer Experience | Pending |
| Central Simulation Engine | Pending |

The interaction matrix is a design specification. It does not indicate that all listed component interactions have already been implemented or validated.

## 10. Next Development Steps

1. Finalise the component interaction matrix.
2. Standardise the component interface and output schema.
3. Implement the remaining five business components.
4. Validate each component independently.
5. Implement the Central Simulation Engine.
6. Integrate component dependencies.
7. Execute integrated business scenarios.
8. Validate system-level outputs and historical data integrity.
