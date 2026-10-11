# German Electricity Market Pipeline (SMARD)

End-to-end analytics pipeline on official German power-market data from
[SMARD.de](https://www.smard.de) (Bundesnetzagentur): hourly day-ahead prices,
generation by source and consumption, refreshed daily.

**Stack:** Python → BigQuery → dbt (staging → marts, tests) → Power BI · scheduled with GitHub Actions

## Business questions
1. **How does the renewable share move wholesale prices?** (merit-order effect)
2. **When are the peak-cost hours**, by season and weekday/weekend?
3. **How often do prices go negative**, and what is the generation mix in those hours?

## Key findings
> _Fill in after the first full load. Example format:_
> - In hours with ≥ 70% renewables, the average price was €__/MWh vs €__/MWh below 30%.
> - Evening peak (18–20h) is __% more expensive than the midday solar dip in summer.
> - __ negative-price hours in 2025, __% of them on weekends.

![Dashboard](docs/dashboard.png)

## Architecture
```
SMARD API ──► ingest/smard_ingest.py ──► BigQuery smard_raw.energy_hourly (append, partitioned)
                                              │
                                     dbt  stg_energy_hourly   (dedup, Berlin local time, tests)
                                              │
                         fct_energy_hourly · dim_date · mart_price_by_renewable_band · mart_hourly_price_profile
                                              │
                                         Power BI dashboard
GitHub Actions: daily 06:17 UTC → ingest last 3 days → dbt build
```

## Data
15 SMARD series (filter IDs in `ingest/smard_ingest.py`): day-ahead price (4169),
total load (410), residual load (4359), and generation by source (solar, wind
on/offshore, biomass, hydro, lignite, hard coal, gas, pumped storage, nuclear, other).

## Run it
```bash
pip install -r requirements.txt
python ingest/smard_ingest.py --start 2023-01-01          # local Parquet
export GCP_PROJECT_ID=... GOOGLE_APPLICATION_CREDENTIALS=key.json
python ingest/smard_ingest.py --start 2023-01-01 --bigquery
cd dbt && dbt deps && dbt build --profiles-dir .
```

## Design decisions
- **Long-format raw table, append-only.** Re-runs never lose data; dedup lives in dbt
  (`row_number()` on `loaded_at`), so ingestion stays dumb and idempotent.
- **3-day rolling window** on daily runs catches SMARD's late corrections.
- **Time zones:** stored in UTC, reported in Europe/Berlin, so DST days don't break hourly profiles.
- **Tests:** uniqueness of (series, hour), not-null values.

---

