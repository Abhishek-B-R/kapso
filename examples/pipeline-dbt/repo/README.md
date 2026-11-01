# retail: the warehouse pipeline

A dbt project on DuckDB: three nightly exports (`customers`, `orders`,
`payments`, CSV files under `data/`) read in place as sources, three
staging views, two marts the dashboards read (`fct_orders`,
`dim_customers`), tests in `models/schema.yml` and `tests/`.

```bash
pip install dbt-core dbt-duckdb
dbt build --profiles-dir .            # builds dev.duckdb and runs every test
dbt test --profiles-dir .             # the tests alone
dbt build --profiles-dir . --vars '{data_dir: kapso_datasets}'   # the sources elsewhere
```

The staging models pass the exports through untouched, and the tests say
what that costs: repeated customers and orders, orders without a customer
or with one the customer export never had, a status outside the list,
negative amounts, a lower-case currency, payments captured twice. The
marts' columns are a contract: fix the defects where they enter, in the
staging layer.
