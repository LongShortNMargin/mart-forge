{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key=['pull_date', 'option_symbol']
    )
}}

{% set fixture_path = 'fixtures/gme_options_chain.parquet' %}
{% set staging_path = 'staging/gme_options_chain.parquet' %}
{% set src = fixture_path if var('use_fixture', true) else staging_path %}

SELECT
    pull_date,
    ticker,
    option_symbol,
    expiry,
    strike,
    option_type,
    last_trade_price,
    bid,
    ask,
    volume,
    open_interest,
    iv,
    in_the_money,
    underlying_close,
    provider,
    pull_ts_utc,
    quote_ts_utc,
    run_id
FROM read_parquet('{{ src }}')

{% if is_incremental() %}
WHERE pull_date >= (SELECT MAX(pull_date) FROM {{ this }})
{% endif %}
