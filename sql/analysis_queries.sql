-- 1. Row counts and date range per series (data check)
SELECT
  series_key,
  COUNT(*)     AS hours,
  MIN(ts_utc)  AS first_hour,
  MAX(ts_utc)  AS last_hour
FROM `smard-energy-pipeline.smard_raw.energy_hourly`
GROUP BY series_key
ORDER BY series_key;

-- 2. Average price and negative-price hours per month
SELECT
  FORMAT_TIMESTAMP('%Y-%m', ts_utc, 'Europe/Berlin') AS month,
  ROUND(AVG(value), 1)  AS avg_price_eur_mwh,
  COUNTIF(value < 0)    AS negative_price_hours
FROM `smard-energy-pipeline.smard_raw.energy_hourly`
WHERE series_key = 'day_ahead_price'
GROUP BY month
ORDER BY month;