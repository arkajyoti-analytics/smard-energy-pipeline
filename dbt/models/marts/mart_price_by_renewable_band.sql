-- Business question 1: how does renewable share move wholesale prices?
select
    cast(floor(renewable_share * 10) * 10 as int64) as renewable_share_band_pct,
    count(*)                                        as hours,
    round(avg(price_eur_mwh), 2)                    as avg_price_eur_mwh,
    round(approx_quantiles(price_eur_mwh, 100)[offset(50)], 2) as median_price_eur_mwh,
    countif(is_negative_price)                      as negative_price_hours
from {{ ref('fct_energy_hourly') }}
where price_eur_mwh is not null and renewable_share is not null
group by 1
order by 1
