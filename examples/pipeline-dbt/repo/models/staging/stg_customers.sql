-- The customers as exported. Known defects the staging layer should
-- handle: a customer exported twice (the later row is the current one),
-- an empty country.
select
    customer_id,
    name,
    country,
    cast(signup_date as date) as signup_date
from {{ source('raw', 'customers') }}
