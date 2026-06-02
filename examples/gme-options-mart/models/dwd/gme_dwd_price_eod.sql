with src as (
    select
        trading_date,
        open_px,
        high_px,
        low_px,
        close_px,
        volume,
        provider,
        pull_ts_utc
    from {{ ref('gme_ods_price_history') }}
)

select
    trading_date,
    open_px,
    high_px,
    low_px,
    close_px,
    volume,
    ln(close_px / nullif(lag(close_px) over (order by trading_date), 0)) as log_return_1d,
    cast(strftime(trading_date, '%Y%m%d') as integer) as date_sk,
    provider,
    pull_ts_utc
from src
