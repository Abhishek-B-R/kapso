"""`kapso doctor`: check this machine can run what the active config asks for."""

import sys

from kapso.kapso import DEFAULT_CONFIG_PATH
from kapso.core.config import load_config
from kapso.core.preflight import (
    VERBS,
    configured_bank_home,
    dedupe,
    live_model_requirements,
    requirements_for,
)

NAME = "doctor"


def cmd_doctor(args) -> None:
    """Report what the active config actually needs, and exit 1 when a
    required item is missing. With no verb this is the union across all
    five verbs; naming one narrows it to that verb's own requirements.
    --models adds the live tier (a one-token probe per {cli, model} pair).

    Same resolver the verbs themselves run at call time, so the doctor can
    never disagree with what a run will do (core/preflight.py)."""
    config = load_config(args.config or DEFAULT_CONFIG_PATH)
    verb = args.verb
    # The only context a doctor can supply is what the config declares —
    # a live call's own arguments (skip_merge, strategy) are not knowable
    # here, so those verbs report their fullest requirement set.
    context = (
        {"bank_home": configured_bank_home(config)}
        if verb in ("evolve", "learn") else {}
    )

    requirements = requirements_for(verb, config, **context)
    if args.models:
        requirements = dedupe(
            requirements + live_model_requirements(verb, config, **context)
        )

    scope = f"kapso doctor {verb}" if verb else "kapso doctor"
    print(scope + "\n" + "=" * 68)
    for item in requirements:
        mark = "OK " if item.ok else ("FAIL" if item.required else "-- ")
        print(f"  [{mark}] {item.label}")
        if item.ok:
            continue
        if item.detail:
            print(f"         reason     {item.detail}")
        print(f"         needed by  {item.origin}")
        if item.fix:
            print(f"         fix        {item.fix}")

    failures = [i for i in requirements if not i.ok and i.required]
    advisories = [i for i in requirements if not i.ok and not i.required]
    print("=" * 68)
    if failures:
        print(f"{len(failures)} required check(s) failed — fix the items "
              f"above, then rerun `{scope}`.")
        sys.exit(1)
    summary = f"Required checks passed ({len(requirements)} checked)."
    if advisories:
        summary += (f" {len(advisories)} optional item(s) marked [-- ] "
                    "only limit features you may not need.")
    print(summary)


def add_parser(subparsers):
    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Check this machine can run what your config asks for",
        description=(
            "Reports the requirements the ACTIVE CONFIG implies — an "
            "all-codex config is never asked for claude, and a local "
            "codify target is never asked for gcloud. With no argument "
            "this is the union across all five verbs; name one "
            f"({', '.join(VERBS)}) to see just that verb's requirements, "
            "which are exactly the checks it runs at call time. Every "
            "missing item names the config key that wants it and one fix. "
            "Exits non-zero when a required item is missing. With "
            "--models, additionally fires a one-token live probe per "
            "{cli, model} pair — a revoked login or a model the plan does "
            "not include surfaces here in seconds instead of hours into a "
            "run (a usage cap on a model it can serve does not)."
        ),
    )
    doctor_parser.add_argument(
        "verb", nargs="?", choices=list(VERBS), default=None,
        help="Narrow the report to one verb's requirements",
    )
    doctor_parser.add_argument(
        "--models", action="store_true",
        help="Live-probe each configured {cli, model} pair (spends a few "
             "one-token calls)",
    )
    doctor_parser.add_argument(
        "--config", type=str, default=None,
        help="Config to check (default: packaged config.yaml)",
    )
    return cmd_doctor
