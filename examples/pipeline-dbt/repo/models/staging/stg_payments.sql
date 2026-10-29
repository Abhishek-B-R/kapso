-- The payments as exported. Known defect the staging layer should
-- handle: a capture retried is exported twice under the same payment id.
select
    payment_id,
    order_id,
    cast(amount as double) as amount,
    method,
    cast(paid_at as date) as paid_at
from {{ source('raw', 'payments') }}
