"""
SMARD.de ingestion: German electricity prices, generation and consumption.

Pulls hourly series from the public SMARD chart-data API (Bundesnetzagentur)
and writes them in long format: one row per (series, hour).

Usage:
    python ingest/smard_ingest.py --start 2023-01-01            # local Parquet only
    python ingest/smard_ingest.py --start 2023-01-01 --bigquery # also load to BigQuery

API pattern (no key needed):
    index:  https://www.smard.de/app/chart_data/{id}/{region}/index_hour.json
    chunk:  https://www.smard.de/app/chart_data/{id}/{region}/{id}_{region}_hour_{ts}.json
Each chunk holds one week of hourly values; future hours come back as null.
"""

from __future__ import annotations

import argparse
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://www.smard.de/app/chart_data"
REGION = "DE"
RESOLUTION = "hour"

# SMARD filter IDs -> (series_key, category, unit)
SERIES = {
    4169: ("day_ahead_price", "price", "EUR/MWh"),
    410: ("total_load", "consumption", "MWh"),
    4359: ("residual_load", "consumption", "MWh"),
    4068: ("solar", "generation_renewable", "MWh"),
    4067: ("wind_onshore", "generation_renewable", "MWh"),
    1225: ("wind_offshore", "generation_renewable", "MWh"),
    4066: ("biomass", "generation_renewable", "MWh"),
    1226: ("hydro", "generation_renewable", "MWh"),
    1228: ("other_renewable", "generation_renewable", "MWh"),
    1223: ("lignite", "generation_conventional", "MWh"),
    4069: ("hard_coal", "generation_conventional", "MWh"),
    4071: ("natural_gas", "generation_conventional", "MWh"),
    4070: ("pumped_storage", "generation_conventional", "MWh"),
    1227: ("other_conventional", "generation_conventional", "MWh"),
    1224: ("nuclear", "generation_conventional", "MWh"),
}

log = logging.getLogger("smard")
session = requests.Session()
session.headers.update({"User-Agent": "smard-energy-pipeline (portfolio project)"})


def get_json(url: str, retries: int = 3) -> dict:
    for attempt in range(1, retries + 1):
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as exc:
            if attempt == retries:
                raise
            wait = 2 ** attempt
            log.warning("Request failed (%s), retrying in %ss: %s", exc, wait, url)
            time.sleep(wait)
    raise RuntimeError("unreachable")


def chunk_timestamps(filter_id: int, start_ms: int) -> list[int]:
    """Weekly chunk start timestamps that can contain data on/after start_ms."""
    idx = get_json(f"{BASE_URL}/{filter_id}/{REGION}/index_{RESOLUTION}.json")
    ts = sorted(idx["timestamps"])
    week_ms = 7 * 24 * 3600 * 1000
    # keep the chunk that *contains* start_ms, plus everything after it
    return [t for t in ts if t + week_ms > start_ms]


def fetch_series(filter_id: int, start_ms: int) -> pd.DataFrame:
    key, category, unit = SERIES[filter_id]
    rows: list[tuple[int, float]] = []
    for ts in chunk_timestamps(filter_id, start_ms):
        url = f"{BASE_URL}/{filter_id}/{REGION}/{filter_id}_{REGION}_{RESOLUTION}_{ts}.json"
        rows.extend(get_json(url)["series"])
        time.sleep(0.2)  # be polite to a public government API

    df = pd.DataFrame(rows, columns=["ts_ms", "value"])
    df = df.dropna(subset=["value"])          # drop not-yet-published hours
    df = df[df["ts_ms"] >= start_ms]
    df["ts_utc"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True)
    df["series_id"] = filter_id
    df["series_key"] = key
    df["category"] = category
    df["unit"] = unit
    df["region"] = REGION
    df["loaded_at"] = datetime.now(timezone.utc)
    log.info("%-20s %6d rows", key, len(df))
    return df[["series_id", "series_key", "category", "unit", "region",
               "ts_utc", "value", "loaded_at"]]


def load_to_bigquery(df: pd.DataFrame) -> None:
    """Append to raw table; dedup happens in the dbt staging model."""
    from google.cloud import bigquery  # imported lazily so local runs need no GCP

    project = os.environ["GCP_PROJECT_ID"]
    table_id = f"{project}.{os.environ.get('BQ_DATASET', 'smard_raw')}.energy_hourly"
    client = bigquery.Client(project=project)
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_APPEND",
        clustering_fields=["series_key"],
    )
    client.load_table_from_dataframe(df, table_id, job_config=job_config).result()
    log.info("Loaded %d rows into %s", len(df), table_id)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--start", default=None,
                   help="YYYY-MM-DD (UTC). Default: 3 days ago (incremental mode).")
    p.add_argument("--out", default="data/raw/energy_hourly.parquet")
    p.add_argument("--bigquery", action="store_true", help="Also load to BigQuery")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.start:
        start = pd.Timestamp(args.start, tz="UTC")
    else:
        start = pd.Timestamp.now(tz="UTC").normalize() - pd.Timedelta(days=3)
    start_ms = int(start.timestamp() * 1000)
    log.info("Fetching %d series from %s", len(SERIES), start.date())

    frames = []
    for fid in SERIES:
        try:
            df_one = fetch_series(fid, start_ms)
            if not df_one.empty:
                frames.append(df_one)
        except Exception as exc:  # one broken series shouldn't kill the run
            log.error("Series %s failed: %s", fid, exc)
    if not frames:
        raise SystemExit("No data fetched.")
    df = pd.concat(frames, ignore_index=True)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    log.info("Wrote %d rows to %s", len(df), out)

    if args.bigquery:
        load_to_bigquery(df)


if __name__ == "__main__":
    main()
