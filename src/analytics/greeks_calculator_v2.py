import numpy as np
import pandas as pd
# from datetime import datetime
import mysql.connector

from py_vollib.black_scholes_merton.implied_volatility import implied_volatility
from py_vollib.black_scholes_merton.greeks.analytical import (
    delta,
    gamma,
    theta,
    vega,
    rho
)
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
# ==========================================
# MYSQL CONNECTION
# ==========================================

conn = mysql.connector.connect(
    host="",
    user="",
    password="",
    database=""
)

# ==========================================
# READ UNPROCESSED ROWS
# ==========================================

query = """
SELECT *
FROM option_chain_raw_1 r
WHERE NOT EXISTS
(
    SELECT 1
    FROM option_enriched e
    WHERE e.timestamp = r.timestamp
    AND e.strike_price = r.strike_price
    AND e.option_type = r.option_type
)
"""

df = pd.read_sql(query, conn)

# print(f"Rows Found = {len(df)}")
logging.info(f"Rows Found : {len(df)}")

if len(df) == 0:
    # print("No new rows found.")
    logging.info("No new rows found.")
    conn.close()
    exit()

# =====================================
# SETTINGS
# =====================================

RISK_FREE_RATE = 0.00
DIVIDEND_YIELD = 0.00

# current_time = datetime.now()
# expiry_time = datetime(2026, 7, 21, 15, 30)

# T = max(
#     (expiry_time - current_time).total_seconds() / (365 * 24 * 60 * 60),
#     1e-8
# )

# =====================================
# IV + GREEKS FUNCTION
# =====================================

def calculate_iv_and_greeks(row):
    try:
        price = float(row["ltp"])
        spot = float(row["spot"])
        strike = float(row["strike_price"])
        current_time = pd.to_datetime(row["timestamp"])

        expiry_time = (
            pd.to_datetime(row["expiry_date"])
            + pd.Timedelta(hours=15, minutes=30)
        )

        T = max(
            (expiry_time - current_time).total_seconds()
            / (365 * 24 * 60 * 60),
            1e-8
        )

        option_type = str(row["option_type"]).strip().upper()

        if option_type == "CE":
            flag = "c"
            intrinsic = max(spot - strike, 0)
        elif option_type == "PE":
            flag = "p"
            intrinsic = max(strike - spot, 0)
        else:
            return pd.Series([np.nan, np.nan, np.nan, np.nan, np.nan, np.nan])

        if price <= 0 or spot <= 0 or strike <= 0:
            return pd.Series([np.nan, np.nan, np.nan, np.nan, np.nan, np.nan])

        # if price < intrinsic:
        #     return pd.Series([np.nan, np.nan, np.nan, np.nan, np.nan, np.nan])

        iv = implied_volatility(
            price,
            spot,
            strike,
            T,
            RISK_FREE_RATE,
            DIVIDEND_YIELD,
            flag
        )

        d = delta(
            flag,
            spot,
            strike,
            T,
            RISK_FREE_RATE,
            iv,
            DIVIDEND_YIELD
        )

        g = gamma(
            flag,
            spot,
            strike,
            T,
            RISK_FREE_RATE,
            iv,
            DIVIDEND_YIELD
        )

        th = theta(
            flag,
            spot,
            strike,
            T,
            RISK_FREE_RATE,
            iv,
            DIVIDEND_YIELD
        )

        vg = vega(
            flag,
            spot,
            strike,
            T,
            RISK_FREE_RATE,
            iv,
            DIVIDEND_YIELD
        )

        rh = rho(
            flag,
            spot,
            strike,
            T,
            RISK_FREE_RATE,
            iv,
            DIVIDEND_YIELD
        )

        return pd.Series([
            round(iv * 100, 2),  # IV in percentage
            round(d, 4),
            round(g, 6),
            round(th, 4),
            round(vg, 4),
            round(rh, 4)
        ])

    # except Exception:
    #     return pd.Series([np.nan, np.nan, np.nan, np.nan, np.nan, np.nan])
    except Exception as e:

        logging.debug(
            f"Greek calculation failed for strike "
            f"{row['strike_price']} "
            f"{row['option_type']} : {e}"
        )

        return pd.Series([
            np.nan,
            np.nan,
            np.nan,
            np.nan,
            np.nan,
            np.nan
        ])
# =====================================
# CALCULATE
# =====================================

df[
    [
        "iv",
        "delta",
        "gamma",
        "theta",
        "vega",
        "rho"
    ]
] = df.apply(
    calculate_iv_and_greeks,
    axis=1
)

# =====================================
# OUTPUT
# =====================================

# print(
#     df[
#         [
#             "option_type",
#             "strike_price",
#             "ltp",
#             "spot",
#             "iv",
#             "delta",
#             "gamma",
#             "theta",
#             "vega",
#             "rho"
#         ]
#     ].head()
# )
logging.info("Sample Greeks:")

logging.info(
    "\n%s",
    df[
        [
            "option_type",
            "strike_price",
            "ltp",
            "spot",
            "iv",
            "delta",
            "gamma",
            "theta",
            "vega",
            "rho"
        ]
    ].head()
)

# ==========================================
# WRITE TO MYSQL
# ==========================================

from sqlalchemy import create_engine
from sqlalchemy.engine import URL

url = URL.create(
    drivername="",
    username="",
    password="",
    host="",
    database=""
)

engine = create_engine(url)

df.to_sql(
    "option_enriched",
    con=engine,
    if_exists="append",
    index=False
)

# print(
#     f"Rows Inserted = {len(df)}"
# )
logging.info(f"Rows Inserted : {len(df)}")

conn.close()
