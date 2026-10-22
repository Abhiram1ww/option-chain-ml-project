import logging
import pandas as pd
import mysql.connector

from sqlalchemy import create_engine
from sqlalchemy.engine import URL

# ==========================================================
# CONFIGURATION
# ==========================================================

TARGET_HORIZONS = [5, 15, 30]

UP_THRESHOLD = 20
DOWN_THRESHOLD = -20

PIPELINE_VERSION = "v2"

# ==========================================================
# LOGGING
# ==========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ==========================================================
# MYSQL CONNECTION
# ==========================================================

conn = mysql.connector.connect(
    host="",
    user="",
    password="",
    database=""
)

# ==========================================================
# SQLALCHEMY ENGINE
# ==========================================================

url = URL.create(
    drivername="",
    username="",
    password="",
    host="",
    database=""
)

engine = create_engine(url)

# ==========================================================
# GET FUTURE SPOT
# ==========================================================

def get_future_spot(engine, current_timestamp, horizon):


    # Convert timestamp to pandas datetime
    current_timestamp = pd.Timestamp(current_timestamp)


    # Remove seconds and microseconds
    current_minute = current_timestamp.replace(
        second=0,
        microsecond=0
    )


    # Calculate target minute
    target_minute = current_minute + pd.Timedelta(
        minutes=horizon
    )


    # End of that target minute
    target_minute_end = target_minute + pd.Timedelta(
        minutes=1
    )


    query = """
    SELECT
        timestamp,
        spot
    FROM option_chain_raw_1
    WHERE timestamp >= %s
      AND timestamp < %s
    ORDER BY timestamp
    LIMIT 1;
    """

    future_df = pd.read_sql(
        query,
        engine,
        params=(
            target_minute,
            target_minute_end
        )
    )

    # If no snapshot exists in that minute
    if future_df.empty:
        return None, None

    return (
        future_df.iloc[0]["timestamp"],
        future_df.iloc[0]["spot"]
    )


#    query = f"""
 #   SELECT
  #      timestamp,
   #     spot

    #FROM option_chain_raw_1

    #WHERE timestamp >=
    #    DATE_ADD('{current_timestamp}', INTERVAL {horizon} MINUTE)

    #ORDER BY timestamp

    #LIMIT 1;
    #"""

    #future_df = pd.read_sql(query, engine)

    #if future_df.empty:
     #   return None, None

    #return (
     #   future_df.iloc[0]["timestamp"],
      #  future_df.iloc[0]["spot"]
    #)

# ==========================================================
# GET PENDING TIMESTAMPS
# ==========================================================

#query = """
#SELECT
#   f.timestamp

#FROM option_features_1 f

#LEFT JOIN ml_dataset m
#ON f.timestamp = m.timestamp

#WHERE m.timestamp IS NULL

#ORDER BY f.timestamp;
#"""


query = """
SELECT
    f.timestamp
FROM option_features_1 f
LEFT JOIN ml_dataset m
ON f.timestamp = m.timestamp
WHERE m.timestamp IS NULL
  AND f.timestamp <= DATE_SUB(NOW(), INTERVAL 30 MINUTE)
ORDER BY f.timestamp;
"""
pending_df = pd.read_sql(query, engine)

logging.info(f"Pending Snapshots : {len(pending_df)}")
# ==========================================================
# PROCESS EACH SNAPSHOT
# ==========================================================

for _, row in pending_df.iterrows():

    current_timestamp = row["timestamp"]

    try:

        logging.info("=" * 70)
        logging.info(f"Processing Snapshot : {current_timestamp}")

        # ======================================================
        # READ FEATURE ROW
        # ======================================================

        feature_query = f"""
        SELECT *
        FROM option_features_1
        WHERE timestamp = '{current_timestamp}';
        """

        feature_df = pd.read_sql(feature_query, engine)

        if feature_df.empty:

            logging.warning("Feature row not found.")
            continue

        feature = feature_df.iloc[0]

        # ======================================================
        # READ CURRENT SPOT
        # ======================================================

        current_query = f"""
        SELECT
            spot

        FROM option_chain_raw_1

        WHERE timestamp = '{current_timestamp}'

        LIMIT 1;
        """

        current_spot_df = pd.read_sql(current_query, engine)

        if current_spot_df.empty:

            logging.warning("Current Spot not found.")
            continue

        current_spot = current_spot_df.iloc[0]["spot"]

        logging.info(f"Current Spot : {current_spot}")

        # ======================================================
        # FUTURE SPOTS
        # ======================================================

        future_data = {}

        for horizon in TARGET_HORIZONS:

            future_timestamp, future_spot = get_future_spot(
                engine,
                current_timestamp,
                horizon
            )

            future_data[horizon] = {
                "timestamp": future_timestamp,
                "spot": future_spot
            }

            logging.info(
                f"{horizon}m -> {future_timestamp} | {future_spot}"
            )

        # ======================================================
        # TARGET CALCULATION
        # ======================================================

        target_results = {}

        for horizon in TARGET_HORIZONS:

            future_spot = future_data[horizon]["spot"]

            if future_spot is None:

                target_results[horizon] = {

                    "future_spot": None,

                    "move": None,

                    "target": None

                }

                continue

            move = future_spot - current_spot

            if move >= UP_THRESHOLD:

                target = 1

            elif move <= DOWN_THRESHOLD:

                target = -1

            else:

                target = 0

            target_results[horizon] = {

                "future_spot": future_spot,

                "move": move,

                "target": target

            }

            logging.info(
                f"{horizon}m | Move : {move:.2f} | Target : {target}"
            )

        # ======================================================
        # BUILD ML ROW
        # ======================================================

        ml_row = pd.DataFrame([{

            "timestamp": current_timestamp,

            "oi_change_pcr": feature["oi_change_pcr"],

            "net_delta_exposure": feature["net_delta_exposure"],

            "gamma_exposure": feature["gamma_exposure"],

            "iv_skew": feature["iv_skew"],

            "order_book_imbalance": feature["order_book_imbalance"],

            "put_call_volume_ratio": feature["put_call_volume_ratio"],

            "current_spot": current_spot,

            "future_spot_5m": target_results[5]["future_spot"],
            "move_5m": target_results[5]["move"],
            "target_5m": target_results[5]["target"],

            "future_spot_15m": target_results[15]["future_spot"],
            "move_15m": target_results[15]["move"],
            "target_15m": target_results[15]["target"],

            "future_spot_30m": target_results[30]["future_spot"],
            "move_30m": target_results[30]["move"],
            "target_30m": target_results[30]["target"],

            "pipeline_version": PIPELINE_VERSION

        }])

        # ======================================================
        # INSERT INTO MYSQL
        # ======================================================

        ml_row.to_sql(

            "ml_dataset",

            con=engine,

            if_exists="append",

            index=False

        )

        logging.info(
            f"Inserted : {current_timestamp}"
        )

    except Exception as e:

        logging.exception(
            f"Error while processing {current_timestamp}"
        )

        continue
# ==========================================================
# CLEANUP
# ==========================================================
conn.close()

logging.info("MySQL Connection Closed.")

logging.info("=" * 70)
logging.info("Target Creation Pipeline Completed Successfully")
logging.info("=" * 70)

