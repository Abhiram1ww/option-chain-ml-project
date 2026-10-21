# Airflow DAGs

This directory contains Apache Airflow DAG definitions
for orchestrating the option-chain analytics pipeline.

## Available DAGs

- `market_pipeline_dag.py`: Main market-data processing workflow.

## Configuration

Configure Airflow connections, environment variables,
and other credentials outside the public repository.

Never commit passwords, API secrets, or access tokens.
