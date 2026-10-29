-- One row per order with what was paid against it. The columns are the
-- contract the dashboards read; keep them.
with paid as (
    select order_id, sum(amount) as paid_amount, count(*) as payment_count
    from {{ ref('stg_payments') }}
    group by order_id
)
select
    o.order_id,
    o.customer_id,
    o.order_date,
    o.status,
    o.amount,
    o.currency,
    coalesce(p.paid_amount, 0.0) as paid_amount,
    coalesce(p.payment_count, 0) as payment_count
from {{ ref('stg_orders') }} as o
left join paid as p using (order_id)
