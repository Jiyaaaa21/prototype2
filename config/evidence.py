"""
Published evidence behind the demand-side assumptions.

Only claims verified against the sources' own abstracts are recorded.
Elasticity values are literature means: reference points for a what-if, not
estimates for Olist.
"""

TELLIS_1988 = -1.76          # mean price elasticity, 367 estimates, ~220 brands/markets
BIJMOLT_2005 = -2.62         # mean price elasticity, 1,851 estimates, 81 studies

LITERATURE_ELASTICITIES = {
    "Tellis 1988": TELLIS_1988,
    "Bijmolt et al. 2005": BIJMOLT_2005,
}

EVIDENCE = [
    {
        "Used for": "Elasticity reference value -1.76",
        "Source": "Tellis (1988), Journal of Marketing Research 25(4), 331-341",
        "Finding": "Mean price elasticity of selective demand -1.76 across 367 "
                   "estimates from about 220 brands or markets.",
        "Limit": "Brand-level, mostly packaged goods. Estimates are biased when "
                 "distribution or quality is omitted, data are cross-sectional only "
                 "or time-aggregated.",
    },
    {
        "Used for": "Elasticity reference value -2.62",
        "Source": "Bijmolt, van Heerde and Pieters (2005), Journal of Marketing "
                  "Research 42(2), 141-156",
        "Finding": "Mean price elasticity -2.62 across 1,851 estimates from 81 "
                   "studies. Accounting for price endogeneity increases the "
                   "magnitude of estimates.",
        "Limit": "Average over many categories and countries. Elasticity varies "
                 "widely by category.",
    },
    {
        "Used for": "Demand responds to price plus freight",
        "Source": "Lewis, Singh and Fay (2006), Marketing Science 25(1), 51-64",
        "Finding": "In experiments at an online retailer, consumers were very "
                   "sensitive to shipping charges. Free-shipping promotions raised "
                   "sales but the lost shipping revenue made them unprofitable.",
        "Limit": "One US online retailer. The model weights freight only through "
                 "its share of the total outlay, which is a simplification.",
    },
    {
        "Used for": "Discount response is understated by a single elasticity",
        "Source": "Fok, Horvath, Paap and Franses (2006), Journal of Marketing "
                  "Research 43(3), 443-461; Fibich, Gavious and Lowengart (2005), "
                  "Journal of the Academy of Marketing Science",
        "Finding": "Immediate response to promotional prices differs from the "
                   "response to regular prices, and immediate elasticity exceeds "
                   "long-term regular-price elasticity.",
        "Limit": "The model uses one elasticity for price and discount, so "
                 "temporary-promotion response is likely understated.",
    },
]
