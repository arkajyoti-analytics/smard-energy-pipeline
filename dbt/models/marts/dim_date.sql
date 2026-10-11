select
    d as date_local,
    extract(year from d)       as year,
    extract(quarter from d)    as quarter,
    extract(month from d)      as month,
    format_date('%Y-%m', d)    as year_month,
    extract(isoweek from d)    as iso_week,
    extract(dayofweek from d) in (1, 7) as is_weekend,
    case when extract(month from d) in (12, 1, 2) then 'Winter'
         when extract(month from d) in (3, 4, 5)  then 'Spring'
         when extract(month from d) in (6, 7, 8)  then 'Summer'
         else 'Autumn' end      as season
from unnest(generate_date_array('2015-01-01', date_add(current_date(), interval 1 year))) as d
