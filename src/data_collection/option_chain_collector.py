from kiteconnect import KiteConnect
import pandas as pd
from datetime import datetime
import os


# =========================================
# KITE CREDENTIALS
# =========================================

api_key = ""
access_token = ""
kite = KiteConnect(api_key=api_key)
kite.set_access_token(access_token)

# =========================================
# GET NIFTY SPOT
# =========================================

spot_quote = kite.quote(["NSE:NIFTY 50"])

spot = spot_quote["NSE:NIFTY 50"]["last_price"]
# ==========================================
# NEAREST NIFTY FUTURE
# ==========================================
instruments = kite.instruments("NFO")

nifty_futures = []

for ins in instruments:

    if (
        ins["name"] == "NIFTY"
        and ins["segment"] == "NFO-FUT"
    ):
        nifty_futures.append(ins)

nearest_future = min(
    nifty_futures,
    key=lambda x: pd.to_datetime(x["expiry"])
)

future_symbol = f"NFO:{nearest_future['tradingsymbol']}"

print("Future Symbol:", future_symbol)
# =========================================
# FUTURE PRICE
# =========================================

future_quote = kite.quote([future_symbol])

future_price = future_quote[
    future_symbol
]["last_price"]

print("Future Price:", future_price)
# =========================================
# BASIS
# =========================================

basis = future_price - spot

print("Basis:", round(basis, 2))


# =========================================
# ATM SPOT
# =========================================
atm = round(spot / 50) * 50

print(f"\nSpot = {spot}")
print(f"ATM  = {atm}")

# =========================================
# ATM ± 10 STRIKES
# =========================================

strikes = list(range(atm - 500, atm + 501, 50))

# =========================================
# FIND NEAREST NIFTY OPTION EXPIRY
# =========================================

option_expiries = sorted({
    ins["expiry"]
    for ins in instruments
    if ins["name"] == "NIFTY"
    and ins["segment"] == "NFO-OPT"
})

nearest_expiry = option_expiries[0]

print("Nearest Option Expiry:", nearest_expiry)

# =========================================
# BUILD SYMBOLS FROM INSTRUMENT MASTER
# =========================================

symbols = []

for ins in instruments:

    if (
        ins["name"] == "NIFTY"
        and ins["segment"] == "NFO-OPT"
        and ins["expiry"] == nearest_expiry
        and ins["strike"] in strikes
    ):

        symbols.append("NFO:" + ins["tradingsymbol"])

print("Contracts =", len(symbols))
# =========================================
# FETCH QUOTES
# =========================================

quotes = kite.quote(symbols)

rows = []

# =========================================
# PROCESS CONTRACTS
# =========================================

for symbol, q in quotes.items():

    # =====================================
    # STRIKE + OPTION TYPE
    # =====================================

    # Extract strike from generated symbol
     # Extract strike from generated symbol

    instrument = next(
    ins for ins in instruments
    if "NFO:" + ins["tradingsymbol"] == symbol
    )

    strike = instrument["strike"]
    option_type = instrument["instrument_type"]

    # =====================================
    # SAFE MARKET DEPTH
    # =====================================

    buy_depth = q.get("depth", {}).get("buy", [])
    sell_depth = q.get("depth", {}).get("sell", [])

    bid1_price = buy_depth[0]["price"] if len(buy_depth) > 0 else 0
    bid1_qty   = buy_depth[0]["quantity"] if len(buy_depth) > 0 else 0

    bid2_price = buy_depth[1]["price"] if len(buy_depth) > 1 else 0
    bid2_qty   = buy_depth[1]["quantity"] if len(buy_depth) > 1 else 0

    bid3_price = buy_depth[2]["price"] if len(buy_depth) > 2 else 0
    bid3_qty   = buy_depth[2]["quantity"] if len(buy_depth) > 2 else 0

    bid4_price = buy_depth[3]["price"] if len(buy_depth) > 3 else 0
    bid4_qty   = buy_depth[3]["quantity"] if len(buy_depth) > 3 else 0

    bid5_price = buy_depth[4]["price"] if len(buy_depth) > 4 else 0
    bid5_qty   = buy_depth[4]["quantity"] if len(buy_depth) > 4 else 0

    ask1_price = sell_depth[0]["price"] if len(sell_depth) > 0 else 0
    ask1_qty   = sell_depth[0]["quantity"] if len(sell_depth) > 0 else 0

    ask2_price = sell_depth[1]["price"] if len(sell_depth) > 1 else 0
    ask2_qty   = sell_depth[1]["quantity"] if len(sell_depth) > 1 else 0

    ask3_price = sell_depth[2]["price"] if len(sell_depth) > 2 else 0
    ask3_qty   = sell_depth[2]["quantity"] if len(sell_depth) > 2 else 0

    ask4_price = sell_depth[3]["price"] if len(sell_depth) > 3 else 0
    ask4_qty   = sell_depth[3]["quantity"] if len(sell_depth) > 3 else 0

    ask5_price = sell_depth[4]["price"] if len(sell_depth) > 4 else 0
    ask5_qty   = sell_depth[4]["quantity"] if len(sell_depth) > 4 else 0

    # =====================================
    # CREATE ROW
    # =====================================

    row = {

        "timestamp": datetime.now(),

        "symbol": symbol,
        "spot": spot,
        "future_price": future_price,
        "future_symbol": future_symbol,
        "basis": basis,
        "atm": atm,

        "strike_price": strike,
        "option_type": option_type,

        "expiry_date": instrument["expiry"],
   
        "ltp": q.get("last_price", 0),
        "average_price": q.get("average_price", 0),

        "open_price": q.get("ohlc", {}).get("open", 0),
        "high_price": q.get("ohlc", {}).get("high", 0),
        "low_price": q.get("ohlc", {}).get("low", 0),
        "close_price": q.get("ohlc", {}).get("close", 0),

        "volume": q.get("volume", 0),
        "last_quantity": q.get("last_quantity", 0),

        "oi": q.get("oi", 0),
        "oi_day_high": q.get("oi_day_high", 0),
        "oi_day_low": q.get("oi_day_low", 0),

        "buy_quantity": q.get("buy_quantity", 0),
        "sell_quantity": q.get("sell_quantity", 0),

        "bid1_price": bid1_price,
        "bid1_qty": bid1_qty,

        "bid2_price": bid2_price,
        "bid2_qty": bid2_qty,

        "bid3_price": bid3_price,
        "bid3_qty": bid3_qty,

        "bid4_price": bid4_price,
        "bid4_qty": bid4_qty,

        "bid5_price": bid5_price,
        "bid5_qty": bid5_qty,

        "ask1_price": ask1_price,
        "ask1_qty": ask1_qty,

        "ask2_price": ask2_price,
        "ask2_qty": ask2_qty,

        "ask3_price": ask3_price,
        "ask3_qty": ask3_qty,

        "ask4_price": ask4_price,
        "ask4_qty": ask4_qty,

        "ask5_price": ask5_price,
        "ask5_qty": ask5_qty
    }

    rows.append(row)


# =========================================
# DATAFRAME
# =========================================

df = pd.DataFrame(rows)

# =========================================
# SAVE RAW DATA
# =========================================

#filename = "option_chain_raw.csv"
BASE_DIR = "/home/abhivardhan/kite_ml_project/data"

os.makedirs(BASE_DIR, exist_ok=True)

filename = os.path.join(BASE_DIR, "option_chain_raw_1.csv")


if not os.path.exists(filename):
    df.to_csv(filename, index=False)
else:
    df.to_csv(
        filename,
        mode="a",
        header=False,
        index=False
    )

# =========================================
# OUTPUT
# =========================================

print(df.head())

print(f"\nContracts Collected = {len(df)}")
print(f"Rows Written = {len(df)}")

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
    "option_chain_raw_1",
    con=engine,
    if_exists="append",
    index=False
)

print("Data inserted into MySQL")

