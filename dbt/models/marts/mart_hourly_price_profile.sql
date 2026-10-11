-- Business question 2: when are the peak-cost hours, by season and day type?
select
    d.season,
    d.is_weekend,
    f.hour_local,
    round(avg(f.price_eur_mwh), 2)  as avg_price_eur_mwh,
    round(avg(f.renewable_share), 3) as avg_renewable_share
from {{ ref('fct_energy_hourly') }} f
join {{ ref('dim_date') }} d using (date_local)
where f.price_eur_mwh is not null
group by 1, 2, 3
