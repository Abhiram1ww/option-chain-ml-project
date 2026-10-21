import logging
# import mysql.connector
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

# ==========================================
# LOGGING
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ==========================================
# MYSQL CONNECTION
# ==========================================

MYSQL_CONFIG = {
    "host": "localhost",
    "user": "kite_user",
    "password": "KiteML@2026",
    "database": "option_chain_db"
}


# def connect_mysql():

#     conn = mysql.connector.connect(**MYSQL_CONFIG)

#     logging.info("Connected to MySQL")

#     return conn


# ==========================================
# SQLALCHEMY ENGINE
# ==========================================

def create_mysql_engine():

    url = URL.create(
        drivername="mysql+pymysql",
        username=MYSQL_CONFIG["user"],
        password=MYSQL_CONFIG["password"],
        host=MYSQL_CONFIG["host"],
        database=MYSQL_CONFIG["database"]
    )

    return create_engine(url)


# ==========================================
# GET PENDING TIMESTAMPS
# ==========================================

def get_pending_timestamps(engine):

    query = """
    SELECT DISTINCT e.timestamp

    FROM option_enriched e

    LEFT JOIN option_features_1 f

    ON e.timestamp = f.timestamp

    WHERE f.timestamp IS NULL

    ORDER BY e.timestamp;
    """

    pending = pd.read_sql(query, engine)

    logging.info(f"Pending Snapshots : {len(pending)}")

    return pending


# ==========================================
# GET PREVIOUS TIMESTAMP
# ==========================================

def get_previous_timestamp(engine, current_timestamp):

    query = f"""
    SELECT MAX(timestamp) AS previous_timestamp

    FROM option_enriched

    WHERE timestamp < '{current_timestamp}'
    """

    previous = pd.read_sql(query, engine)

    return previous.iloc[0]["previous_timestamp"]


# ==========================================
# LOAD SNAPSHOT
# ==========================================

def load_snapshot(engine, timestamp):

    query = f"""
    SELECT *

    FROM option_enriched

    WHERE timestamp = '{timestamp}'
    """

    df = pd.read_sql(query, engine)

    return df


# ==========================================
# MAIN
# ==========================================

def main():

    # engine = connect_mysql()
    engine=create_mysql_engine()
    pending = get_pending_timestamps(engine)

    if pending.empty:

        logging.info("No Pending Snapshots.")

        engine.dispose()

        return

    for ts in pending["timestamp"]:

        logging.info(f"Processing Snapshot : {ts}")

        previous_ts = get_previous_timestamp(engine, ts)

        if pd.isna(previous_ts):

            logging.warning("Previous snapshot not found. Skipping.")

            continue

        current_df = load_snapshot(engine, ts)

        previous_df = load_snapshot(engine, previous_ts)

        logging.info(
            f"Current Rows : {len(current_df)} | Previous Rows : {len(previous_df)}"
        )

        # -----------------------------------
        # Feature Calculation
        # (Part 2)
        # -----------------------------------
        merged = current_df.merge(
            previous_df,
            on=["strike_price", "option_type"],
            suffixes=("_cur", "_prev")
        )

        merged["oi_change"] = (
            merged["oi_cur"] -
            merged["oi_prev"]
        )

        # ==========================================
        # FEATURE 1
        # OI CHANGE PCR
        # ==========================================

        pe_change = merged.loc[
            merged["option_type"] == "PE",
            "oi_change"
        ].sum()

        ce_change = merged.loc[
            merged["option_type"] == "CE",
            "oi_change"
        ].sum()

        if abs(ce_change) < 100:
            oi_change_pcr = np.nan
        else:
            oi_change_pcr = pe_change / ce_change

        # ==========================================
        # FEATURE 2
        # NET DELTA EXPOSURE
        # ==========================================

        net_delta_exposure = (
            current_df["delta"] *
            current_df["oi"]
        ).sum()

        # ==========================================
        # FEATURE 3
        # GAMMA EXPOSURE
        # ==========================================

        gamma_exposure = (
            current_df["gamma"] *
            current_df["oi"]
        ).sum()

        # ==========================================
        # FEATURE 4
        # IV SKEW
        # ==========================================

        atm = current_df["atm"].iloc[0]

        atm_df = current_df[
            current_df["strike_price"] == atm
        ]

        #ce_iv = atm_df.loc[
            #atm_df["option_type"] == "CE",
            #"iv"
        #].iloc[0]

        #pe_iv = atm_df.loc[
            #atm_df["option_type"] == "PE",
            #"iv"
        #].iloc[0]
        
        ce_data = atm_df.loc[
            atm_df["option_type"] == "CE",
            "iv"
        ]

        pe_data = atm_df.loc[
            atm_df["option_type"] == "PE",
            "iv"
        ]

        if ce_data.empty or pe_data.empty:
            logging.warning(f"Missing CE or PE IV data for timestamp {ts}. Skipping.")
            continue

        ce_iv = ce_data.iloc[0]
        pe_iv = pe_data.iloc[0]


        

        iv_skew = pe_iv - ce_iv

        # ==========================================
        # FEATURE 5
        # ORDER BOOK IMBALANCE
        # ==========================================

        bid_total = (
            current_df["bid1_qty"] +
            current_df["bid2_qty"] +
            current_df["bid3_qty"] +
            current_df["bid4_qty"] +
            current_df["bid5_qty"]
        )

        ask_total = (
            current_df["ask1_qty"] +
            current_df["ask2_qty"] +
            current_df["ask3_qty"] +
            current_df["ask4_qty"] +
            current_df["ask5_qty"]
        )

        order_book_imbalance = (
            (
                bid_total - ask_total
            ) /
            (
                bid_total + ask_total
            )
        ).mean()

        # ==========================================
        # FEATURE 6
        # PUT CALL VOLUME RATIO
        # ==========================================

        put_volume = current_df.loc[
            current_df["option_type"] == "PE",
            "volume"
        ].sum()

        call_volume = current_df.loc[
            current_df["option_type"] == "CE",
            "volume"
        ].sum()

        if call_volume == 0:
            put_call_volume_ratio = np.nan
        else:
            put_call_volume_ratio = put_volume / call_volume

        # ==========================================
        # CREATE FEATURE ROW
        # ==========================================

        feature_row = pd.DataFrame([{

            "timestamp": ts,

            "oi_change_pcr": oi_change_pcr,

            "net_delta_exposure": net_delta_exposure,

            "gamma_exposure": gamma_exposure,

            "iv_skew": iv_skew,

            "order_book_imbalance": order_book_imbalance,

            "put_call_volume_ratio": put_call_volume_ratio,

            "pipeline_version": "v2"

        }])

        # ==========================================
        # INSERT INTO MYSQL
        # ==========================================

        feature_row.to_sql(
            "option_features_1",
            con=engine,
            if_exists="append",
            index=False
        )
        logging.info(f"Inserted Feature : {ts}")

    # -----------------------------------------
    # CLOSE CONNECTIONS
    # -----------------------------------------

    # engine.close()
    engine.dispose()                  # Close engine
    logging.info("Feature Engineering Finished")


if __name__ == "__main__":

    main()

