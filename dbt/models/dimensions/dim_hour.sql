select
    hour::integer as hour,
    lpad(cast(hour as varchar), 2, '0') || ':00' as hour_label,
    case
        when hour between 5 and 11 then 'morning'
        when hour between 12 and 16 then 'afternoon'
        when hour between 17 and 20 then 'evening'
        else 'overnight'
    end as day_part
from range(24) as hours(hour)
