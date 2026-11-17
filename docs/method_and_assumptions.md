# BizTwin: method, assumptions and limits

## Purpose
A what-if tool for commercial decisions on a marketplace product. It shows how a
change in price, discount, freight, commission or seller cost moves customer
spend, platform commission, seller payout and orders. It is not a forecast.

## Data (Olist, Sep 2016 to Oct 2018)
- Orders, order items, payments, products, sellers, customers, reviews.
- No quantity, discount, commission or seller-cost field exists. "Orders" are
  counted from order lines; baseline discount is 0 (payments equal items plus
  freight in 99.6% of orders).
- Product scope: a product's **single-product orders**, because payments are
  recorded per order and can be attributed exactly only then. 99.6% of orders
  with items reconcile to their payments.

## What is observed, external, assumed
| Item | Status | Source |
|---|---|---|
| Prices, freight, orders, sellers, payments, delivery, reviews | Observed | Olist tables |
| Commission 20% (19% to 21% by plan) on product value, freight excluded | External | Olist pricing as reported by Exame and Olist's blog (2019 to 2020, after the data period) |
| Seller cost 72.67% of price | External proxy | IBGE PAC 2018 retail margin 37.6% (cost = 1 / 1.376); economy-wide, not Olist |
| Price elasticity | User assumption | Not estimable from Olist |

## Calculations
For each order line: discounted price = price x (1 + price change) x (1 - discount);
freight = freight x (1 + freight change).
- Net merchandise value (NMV) = discounted price.
- Commission = NMV x commission rate.
- Seller payout = NMV - commission.
- Seller margin (proxy) = payout - historical price x seller cost rate.
- Customer order value = NMV + freight.
- Customer payments = recorded payment + change in order value (recorded gaps kept).

## Demand response (optional, off by default)
Customer outlay factor f = (scenario NMV + freight) / (baseline NMV + freight).
Volume multiplier m = f ^ elasticity. Elasticity is set by the user, applies to
price plus freight, and is the same for the whole scope. Every scenario value
(value, commission, payout, orders) is multiplied by m. Orders shown under a
non-zero elasticity are expected values, not counts.

## Break-even
For a metric with constant-volume ratio r (scenario / baseline), the elasticity
at which it returns to baseline is -ln(r) / ln(f). It is arithmetic on the
figures shown. It states how elastic demand can be before a decision stops
paying off, without claiming to know the true elasticity.

## Not modelled
Competitor or seller reactions, delivery changes, repeat purchases (only 3.1% of
customers order twice), product substitution, seasonality, taxes and other
seller costs. Delivery and customer experience are shown as historical context
and carry no scenario effect. Seller margin depends on the cost proxy and is
indicative only. Totals cover the whole period of the scoped orders, not a year.

## Validation
- Engine: 126 independent reconciliation checks per run, neutral baseline equals
  scenario, source data unchanged.
- Propagation: 8 checks per run (values reconcile to the engine, payments
  reconcile to recorded payments, counts scale with the multiplier).
- Product analysis: seller and monthly impacts sum to the scenario totals.
