Objective    Make the retail warehouse's data contract hold: every assertion
             of kapso_evaluation/evaluate.py passes (a share of 1.0) without
             changing the marts' columns. The shipped staging models pass the
             exports through untouched and two of thirteen assertions hold.
Measured by  kapso_evaluation/evaluate.py: the share of its thirteen
             assertions that pass after `dbt run` builds the project into the
             evaluator's own DuckDB file (unique keys, present customers and
             countries, the status list, non-negative amounts, upper-case
             currencies, every order's customer in dim_customers, payments
             within the order's amount and reconciled within half a percent,
             the marts' columns kept, 95% of the exported orders kept)
Baseline     0.15 (two of thirteen: the marts' columns and the row count)
Target       1.0
Rules
  - the evaluator is never modified
  - fct_orders and dim_customers keep their columns, in order and in type: dashboards read them
  - a defect is handled where it enters, in the staging layer (dedupe, normalise, quarantine), not by filtering the marts
  - the exports under the data directory are read as they are; no edit to them
Budget       minutes=30 experiments=2
