select
    row_number() over (order by event_date, event_type) as event_sk,
    event_date,
    event_type,
    event_label
from {{ ref('dim_macro_events_seed') }}
