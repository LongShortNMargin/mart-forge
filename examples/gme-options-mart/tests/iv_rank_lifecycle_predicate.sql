-- TC-26 (Phase D /mart-dqc gap-fill): TDD §T-18 row iv_rank_link_status_active_lifecycle.
-- The schema.yml accepted_values check (TC-11) only proves the badge value
-- is one of {'unsupported', 'proxy'}; it does NOT prove the lifecycle predicate
-- 'proxy' iff iv_rank_lookback_days >= 252. This singular test enforces the
-- bi-conditional so the cold-start → final flip can never drift.

select
    trading_date,
    iv_rank_link_status_active,
    (
        select iv_rank_lookback_days
        from {{ ref('gme_dws_perf_implied_vol') }} v
        where v.trading_date = a.trading_date
    ) as iv_rank_lookback_days
from {{ ref('gme_ads_market_dashboard') }} a
where iv_rank_link_status_active is not null
  and (
        (
            iv_rank_link_status_active = 'proxy'
            and (
                select iv_rank_lookback_days
                from {{ ref('gme_dws_perf_implied_vol') }} v
                where v.trading_date = a.trading_date
            ) < 252
        )
        or
        (
            iv_rank_link_status_active = 'unsupported'
            and (
                select iv_rank_lookback_days
                from {{ ref('gme_dws_perf_implied_vol') }} v
                where v.trading_date = a.trading_date
            ) >= 252
        )
    )
