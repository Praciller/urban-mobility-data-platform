{% test valid_trip_duration(model, column_name, maximum_minutes=1440) %}
select *
from {{ model }}
where {{ column_name }} is null or {{ column_name }} < 0 or {{ column_name }} > {{ maximum_minutes }}
{% endtest %}
