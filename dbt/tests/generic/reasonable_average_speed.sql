{% test reasonable_average_speed(model, column_name, maximum_mph=100) %}
select *
from {{ model }}
where {{ column_name }} is not null
  and ({{ column_name }} < 0 or {{ column_name }} > {{ maximum_mph }})
{% endtest %}
