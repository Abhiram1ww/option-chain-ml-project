from datetime import datetime, timedelta
from airflow.timetables.trigger import MultipleCronTriggerTimetable
from airflow import DAG
from airflow.operators.bash import BashOperator

# -----------------------------
# Default Arguments
# -----------------------------
default_args = {
    "owner": "Abhiram",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
}

# -----------------------------
# Project Paths
# -----------------------------
PROJECT_PATH = "your path of file"
VENV_PATH = "your path of files"

# -----------------------------
# DAG Definition
# -----------------------------
with DAG(
    dag_id="market_pipeline",
    description="Option Chain → Greeks → Feature Engineering",
    default_args=default_args,
    start_date=datetime(2026, 6, 25),
    schedule=MultipleCronTriggerTimetable(
    "15-59 9 * * 1-5",
    "* 10-14 * * 1-5",
    "0-30 15 * * 1-5",
    timezone="Asia/Kolkata",
    ),   # Every minute
    catchup=False,
    tags=["kite", "ml", "production"],
) as dag:

    # -----------------------------
    # Task 1 - Collect Option Chain
    # -----------------------------
    collect_option_chain = BashOperator(
        task_id="collect_option_chain",
        bash_command=f"""
        source {VENV_PATH} &&
        python {PROJECT_PATH}/option_chain_collector.py
        """,
    )

    # -----------------------------
    # Task 2 - Calculate Greeks
    # -----------------------------
    calculate_greeks = BashOperator(
        task_id="calculate_greeks",
        bash_command=f"""
        source {VENV_PATH} &&
        python {PROJECT_PATH}/greeks_calculator_v2.py
        """,
    )

    # -----------------------------
    # Task 3 - Feature Engineering
    # -----------------------------
    feature_engineering = BashOperator(
        task_id="feature_engineering",
        bash_command=f"""
        source {VENV_PATH} &&
        python {PROJECT_PATH}/feature_engineering_v2.py
        """,
    )

    # -----------------------------
    # Task 4 - target_creation_v2
    # -----------------------------
    target_creation = BashOperator(
        task_id="target_creation",
        bash_command=f"""
        source {VENV_PATH} &&
        {PROJECT_PATH} &&
        python target_creation_v3.py
        """,
    )
    # -----------------------------
    # Task Dependencies
    # -----------------------------
    collect_option_chain >> calculate_greeks >> feature_engineering >> target_creation
