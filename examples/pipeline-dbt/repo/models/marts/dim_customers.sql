-- One row per customer with their order history. The columns are the
-- contract the dashboards read; keep them.
with history as (
    select customer_id, count(*) as order_count, sum(amount) as lifetime_amount, min(order_date) as first_order_date
    from {{ ref('stg_orders') }}
    group by customer_id
)
select
    c.customer_id,
    c.name,
    c.country,
    c.signup_date,
    coalesce(h.order_count, 0) as order_count,
    coalesce(h.lifetime_amount, 0.0) as lifetime_amount,
    h.first_order_date
from {{ ref('stg_customers') }} as c
left join history as h using (customer_id)
