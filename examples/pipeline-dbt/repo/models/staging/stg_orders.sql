-- The orders as exported. Known defects the staging layer should handle:
-- an order exported twice, an order without a customer or with one the
-- customer export never had, a status outside the list, a negative
-- amount, the currency in lower case.
select
    order_id,
    customer_id,
    cast(order_date as date) as order_date,
    status,
    cast(amount as double) as amount,
    currency
from {{ source('raw', 'orders') }}
