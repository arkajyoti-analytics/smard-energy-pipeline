-- Wide fact table: one row per hour, all series as columns, plus derived KPIs.
with pivoted as (
    select
        ts_utc,
        any_value(ts_local) as ts_local,
        max(if(series_key = 'day_ahead_price', value, null)) as price_eur_mwh,
        max(if(series_key = 'total_load',      value, null)) as load_mwh,
        max(if(series_key = 'residual_load',   value, null)) as residual_load_mwh,
        sum(if(category = 'generation_renewable',    value, 0)) as gen_renewable_mwh,
        sum(if(category = 'generation_conventional', value, 0)) as gen_conventional_mwh,
        max(if(series_key = 'solar',         value, null)) as gen_solar_mwh,
        max(if(series_key = 'wind_onshore',  value, null)) as gen_wind_onshore_mwh,
        max(if(series_key = 'wind_offshore', value, null)) as gen_wind_offshore_mwh,
        max(if(series_key = 'natural_gas',   value, null)) as gen_gas_mwh,
        max(if(series_key = 'lignite',       value, null)) as gen_lignite_mwh,
        max(if(series_key = 'hard_coal',     value, null)) as gen_hard_coal_mwh
    from {{ ref('stg_energy_hourly') }}
    group by ts_utc
)
select
    *,
    date(ts_local)                                   as date_local,
    extract(hour from ts_local)                      as hour_local,
    safe_divide(gen_renewable_mwh,
                gen_renewable_mwh + gen_conventional_mwh) as renewable_share,
    price_eur_mwh < 0                                as is_negative_price,
    price_eur_mwh * load_mwh                         as est_wholesale_cost_eur
from pivoted
