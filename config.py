"""Constants for the FIRE Retirement Tracker application."""

# Equity sub-fund splits (must sum to 100)
EQUITY_SUB_SPLITS = {
    "UTI Nifty 50": 35,
    "UTI Nifty Next 50": 20,
    "Oswal Midcap 150": 20,
    "Nippon Smallcap 250": 10,
    "Nippon Momentum 50": 15,
}

# Debt sub-fund splits (must sum to 100)
DEBT_SUB_SPLITS = {
    "ICICI Short Term": 40,
    "Invesco Arbitrage": 30,
    "ICICI Liquid": 30,
}

# 3-Bucket strategy percentages (must sum to 1.0)
BUCKET_PERCENTAGES = {
    "Safety": 0.08,
    "Income": 0.27,
    "Growth": 0.65,
}

# SWR scenarios for comparison table
SWR_SCENARIOS = [0.02, 0.025, 0.03, 0.035, 0.04]

SWR_VERDICTS = {
    0.02: "Ultra Safe",
    0.025: "Very Safe",
    0.03: "Recommended",
    0.035: "Moderate Risk",
    0.04: "Risky (45yr)",
}

# Idle session timeout in minutes
IDLE_TIMEOUT_MINUTES = 30

# Fund definitions: (name, category, parent_pct_key, sub_pct, account)
# category "equity"/"debt" use sub-splits; "gold"/"cash" use 100% of parent allocation.
FUNDS = [
    ("UTI Nifty 50 Index Fund",                       "equity", "equity_pct", 35,  "Your"),
    ("UTI Nifty Next 50 Index Fund",                  "equity", "equity_pct", 20,  "Your"),
    ("Oswal Nifty Midcap 150 Index Fund",             "equity", "equity_pct", 20,  "Your"),
    ("Nippon India Nifty Smallcap 250",               "equity", "equity_pct", 10,  "Your"),
    ("Nippon India Nifty 500 Momentum 50 Index Fund", "equity", "equity_pct", 15,  "Your"),
    ("ICICI Prudential Short Term Fund",              "debt",   "debt_pct",   40,  "Your"),
    ("Invesco India Arbitrage Fund",                  "debt",   "debt_pct",   30,  "Your"),
    ("ICICI Prudential Liquid Fund",                  "debt",   "debt_pct",   30,  "Your"),
    ("Precious Metals",                                "gold",   "precious_metals_pct", 100, "Zerodha"),
    ("Emergency / Cash Reserve",                      "cash",   "cash_pct",   100, "Liquid Fund"),
]
