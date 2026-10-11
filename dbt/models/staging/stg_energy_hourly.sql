-- One row per series per hour; the latest load wins (raw table is append-only).
with ranked as (
    select
        series_key,
        category,
        unit,
        ts_utc,
        value,
        row_number() over (
            partition by series_key, ts_utc
            order by loaded_at desc
        ) as rn
    from {{ source('smard_raw', 'energy_hourly') }}
)
select
    series_key,
    category,
    unit,
    ts_utc,
    datetime(ts_utc, 'Europe/Berlin') as ts_local,
    value
from ranked
where rn = 1
