select
    cast(strftime(holiday_date, '%Y%m%d') as integer) as holiday_sk,
    holiday_date,
    holiday_name
from {{ ref('dim_holidays_seed') }}
