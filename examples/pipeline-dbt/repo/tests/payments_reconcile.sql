-- What the orders say was paid must match what the payments say was
-- captured, within half a percent. A row returned is a failure.
with totals as (
    select
        (select sum(paid_amount) from {{ ref('fct_orders') }}) as from_orders,
        (select sum(amount) from {{ ref('stg_payments') }}) as from_payments
)
select *
from totals
where abs(from_orders - from_payments) > 0.005 * from_payments
