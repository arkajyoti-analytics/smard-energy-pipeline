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

## Build plan (for Arka — delete this section before publishing)

Budget: ~6–8 h/week. Target: done by mid-November.

### Week 1 — Data in (≈ 7 h)
- [ ] Create GitHub repo `smard-energy-pipeline`, push this skeleton.
- [ ] Run `smard_ingest.py --start 2023-01-01` locally; open the Parquet in a notebook,
      sanity-check: load ≈ 40–70 GWh/h, prices mostly €0–300, some negative hours.
- [ ] Create a GCP project, BigQuery dataset `smard_raw` (location **EU**), a service account
      with *BigQuery Data Editor* + *Job User*. Sandbox/free tier is plenty (data is ~1M rows).
- [ ] Load to BigQuery with `--bigquery`.

### Week 2 — Model it (≈ 7 h)
- [ ] `dbt build`; fix anything that breaks (it's normal; note what you fixed for interviews).
- [ ] Add one test of your own (e.g. `accepted_range` on renewable_share 0–1).
- [ ] Run `dbt docs generate` and screenshot the lineage graph for the README.
- [ ] Add GitHub secrets `GCP_PROJECT_ID`, `GCP_SA_KEY`; trigger the workflow manually once.

### Week 3 — Dashboard (≈ 8 h)
Power BI, import mode, connect to `smard_analytics`. Three pages:
1. **Overview:** KPI cards (avg price, renewable share, negative-price hours, MoM change), monthly trend.
2. **Price drivers:** price vs renewable-share band (column), scatter price vs residual load.
3. **When is power expensive:** hour × season heatmap (matrix + conditional formatting), weekday/weekend toggle.
Use DAX measures, not implicit sums. At least: `Avg Price`, `Renewable Share %`,
`Negative Hours`, `Price MoM %` (with `DATEADD`), and a date table marked as such.

### Week 4 — Ship it (≈ 5 h)
- [ ] Fill in the Key findings with real numbers.
- [ ] Publish the dashboard (see note below), add screenshot + link.
- [ ] LinkedIn post: one chart + one finding + repo link. In German if you can, or bilingual.
- [ ] Add to CV (energy/BI version).

**Publishing note:** Power BI "Publish to web" needs a work/school account and can be
disabled by the tenant. Try your university account first; if blocked, publish a
screenshot + `.pbix` in the repo, or mirror the 3 pages in Looker Studio (free, shareable link).

### CV line (fill in numbers)
> **German Electricity Market Pipeline** | Python, BigQuery, dbt, Power BI, GitHub Actions
> - Built an automated daily pipeline ingesting __k hourly records across 15 SMARD series into BigQuery, modelled with dbt (staging → star schema, data tests)
> - Power BI dashboard quantifying the merit-order effect: prices __% lower in high-renewable hours; identified peak-cost windows
