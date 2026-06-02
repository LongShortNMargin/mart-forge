-- TC-16: asymmetric synthetic chain — 1,000 calls @ K_under=20, 1,000 puts @ K_under=30,
-- nothing else. Assert max_pain_strike ∈ [20, 30]. Closes Phase B.5 finding 1 (the round-1
-- swapped-terms formula would tie {20, 25, 30} at pain=0 and pick 20, FAILING this test).

with chain as (
    select 20.0 as strike, 'call' as option_type, 1000 as oi
    union all select 30.0 as strike, 'put'  as option_type, 1000 as oi
),
universe as (
    select distinct strike as candidate_k from chain
),
pain as (
    select
        u.candidate_k,
        sum(case when c.option_type = 'call' then c.oi * greatest(0, u.candidate_k - c.strike) else 0 end)
          + sum(case when c.option_type = 'put'  then c.oi * greatest(0, c.strike - u.candidate_k) else 0 end) as pain_value
    from universe u
    cross join chain c
    group by 1
),
argmin as (
    select candidate_k as max_pain_strike
    from pain
    where pain_value = (select min(pain_value) from pain)
    order by candidate_k asc
    limit 1
)

-- Fail if max_pain_strike is outside the closed interval [20, 30].
select max_pain_strike
from argmin
where max_pain_strike < 20.0 or max_pain_strike > 30.0
