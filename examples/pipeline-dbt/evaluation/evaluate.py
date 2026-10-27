"""The evaluation Kapso protects for the pipeline example.

    python kapso_evaluation/evaluate.py [--fast]

Run from the workspace root, where dbt_project.yml is. It builds the
project with the evaluator's own profile into warehouse.duckdb beside this
script (the sources read from kapso_datasets/ when that directory exists,
else data/), then runs its thirteen assertions against the built tables
with DuckDB directly (the project's own tests are the engineer's; these
are the contract's), writes result.json beside this script and prints the
count then the metric as its last line:

    assertions: 2/13
    tests_passing: 0.1538

Higher is better. Exit codes: 0 scored; 2 the project did not build (dbt's
last lines are printed); 3 dbt_project.yml is missing. `--fast` builds the
staging layer alone and runs its eight assertions: a smoke check whose
number is not comparable with a full score.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import duckdb

SCRIPT_PATH = "kapso_evaluation/evaluate.py"
STATUSES = "('placed', 'shipped', 'delivered', 'returned', 'cancelled')"
FCT_COLUMNS = ["order_id", "customer_id", "order_date", "status", "amount", "currency", "paid_amount", "payment_count"]
DIM_COLUMNS = ["customer_id", "name", "country", "signup_date", "order_count", "lifetime_amount", "first_order_date"]
# Each assertion is a query returning one number: the violations. Zero passes.
STAGING_ASSERTIONS = [
    ("stg_orders: order_id unique", "select count(*) - count(distinct order_id) from stg_orders"),
    ("stg_orders: customer_id present", "select count(*) from stg_orders where customer_id is null or customer_id = ''"),
    ("stg_orders: status in the list", f"select count(*) from stg_orders where status not in {STATUSES}"),
    ("stg_orders: amount not negative", "select count(*) from stg_orders where amount < 0"),
    ("stg_orders: currency in upper case", "select count(*) from stg_orders where currency <> upper(currency)"),
    ("stg_customers: customer_id unique", "select count(*) - count(distinct customer_id) from stg_customers"),
    ("stg_customers: country present", "select count(*) from stg_customers where country is null or country = ''"),
    ("stg_payments: payment_id unique", "select count(*) - count(distinct payment_id) from stg_payments"),
]
MART_ASSERTIONS = [
    ("fct_orders: every customer in dim_customers",
     "select count(*) from fct_orders as o left join dim_customers as c using (customer_id) where c.customer_id is null"),
    ("fct_orders: paid_amount within the order's amount", "select count(*) from fct_orders where paid_amount > amount + 0.01"),
    ("payments reconcile within half a percent",
     "select case when abs(o - p) > 0.005 * p then 1 else 0 end from "
     "(select (select sum(paid_amount) from fct_orders) as o, (select sum(amount) from stg_payments) as p)"),
    ("fct_orders keeps 95% of the distinct orders exported",
     "select case when (select count(*) from fct_orders) < 0.95 * (select count(distinct order_id) from read_csv_auto('{orders}')) then 1 else 0 end"),
]


def fail(code: int, reason: str) -> None:
    print(f"evaluation failed: {reason}")
    sys.exit(code)


def build(workspace: Path, here: Path, data_dir: Path, fast: bool) -> None:
    warehouse = here / "warehouse.duckdb"
    if warehouse.exists():
        warehouse.unlink()
    command = [
        "dbt", "run", "--project-dir", str(workspace), "--profiles-dir", str(here), "--target", "eval",
        "--vars", json.dumps({"data_dir": str(data_dir)}), "--quiet",
    ]
    if fast:
        command += ["--select", "staging"]
    # dbt resolves the profile's relative path against its working directory:
    # run from here, so the warehouse lands beside this script.
    run = subprocess.run(command, cwd=here, capture_output=True, text=True)
    if run.returncode != 0:
        tail = "\n".join((run.stdout + run.stderr).strip().splitlines()[-12:])
        fail(2, f"the project did not build (dbt exit {run.returncode}):\n{tail}")


def columns_of(connection, table: str) -> list:
    return [row[0] for row in connection.execute(f"describe {table}").fetchall()]


def assertions(connection, data_dir: Path, fast: bool) -> list:
    results = []
    queries = list(STAGING_ASSERTIONS) if fast else STAGING_ASSERTIONS + MART_ASSERTIONS
    for name, query in queries:
        violations = connection.execute(query.format(orders=str(data_dir / "orders.csv"))).fetchone()[0]
        results.append({"assertion": name, "violations": int(violations), "passed": int(violations) == 0})
    if not fast:
        kept = columns_of(connection, "fct_orders") == FCT_COLUMNS and columns_of(connection, "dim_customers") == DIM_COLUMNS
        results.append({"assertion": "the marts keep their columns", "violations": 0 if kept else 1, "passed": kept})
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fast", action="store_true", help="the staging layer and its eight assertions, not comparable with a full score")
    args = parser.parse_args()
    workspace = Path.cwd()
    here = Path(__file__).resolve().parent
    if not (workspace / "dbt_project.yml").is_file():
        fail(3, "dbt_project.yml is missing from the workspace root")
    if shutil.which("dbt") is None:
        fail(2, "dbt is not on PATH (pip install dbt-core dbt-duckdb)")
    data_dir = (workspace / "kapso_datasets") if (workspace / "kapso_datasets").is_dir() else (workspace / "data")
    build(workspace, here, data_dir, args.fast)
    connection = duckdb.connect(str(here / "warehouse.duckdb"), read_only=True)
    results = assertions(connection, data_dir, args.fast)
    connection.close()
    passed = sum(1 for result in results if result["passed"])
    score = round(passed / len(results), 4)
    for result in results:
        mark = "ok" if result["passed"] else f"{result['violations']} violation(s)"
        print(f"  {result['assertion']}: {mark}")
    if args.fast:
        print("fast: the staging layer alone; not comparable with a full score")
    (here / "result.json").write_text(json.dumps({
        "evaluation_script_path": SCRIPT_PATH,
        "evaluation_output": f"assertions: {passed}/{len(results)}\ntests_passing: {score}",
        "score": score,
        "assertions": results,
        "fast": args.fast,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"assertions: {passed}/{len(results)}")
    print(f"tests_passing: {score}")


if __name__ == "__main__":
    main()
