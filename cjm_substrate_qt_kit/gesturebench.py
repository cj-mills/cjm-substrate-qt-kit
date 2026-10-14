"""Run one app's canonical gestures headlessly -- the scale harness's gesture leg.

Design detail 4389a579 (work item 85b0d368). Sessions are Qt-free, so an app's gestures run
against any graph without a window: each app with a graph-reading session carries a DRIVER
(`module:function`, taking the filled params and returning the names of the gestures it ran)
that opens its session on the given db and runs its canonical read ladder; every gesture is
recorded by the session's own seam (`loopthread`). The harness (`bench run`) launches this
module in the app's env under its memory and wall limits, CJM_TIMINGS_PATH naming the lane's
ledger and CJM_BENCH_TIER / CJM_BENCH_LANE tagging each event; which drivers run, in which
env, with which params, is DATA in the lane's bench config.
"""

import argparse
import importlib
import json
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple


def load_driver(
    spec: str,  # "<module>:<function>"
) -> Callable[[Dict[str, Any]], List[str]]:  # The driver
    """Import the driver named `module:function` (a malformed name refuses loudly)."""
    mod, sep, fn = spec.partition(":")
    if not sep or not mod or not fn:
        raise ValueError(f"a driver is '<module>:<function>', got {spec!r}")
    return getattr(importlib.import_module(mod), fn)


def ladder(
    steps: List[Tuple[str, Callable[[], Any]]],  # (gesture name, a blocking call) in order
) -> List[str]:  # Each step's name, a failure suffixed with its error class
    """Run a driver's read ladder step by step: a failing gesture is recorded by the seam (its
    outcome names the error) and the ladder goes on, so one failure never hides the rest. A
    step may return a value later steps read through the driver's own closure."""
    ran: List[str] = []
    for name, step in steps:
        try:
            step()
            ran.append(name)
        except Exception as e:
            print(f"gesture {name} failed: {type(e).__name__}: {e}", file=sys.stderr)
            ran.append(f"{name}: {type(e).__name__}")
    return ran


def main(
    argv: Optional[List[str]] = None,  # Command-line args (default: sys.argv)
) -> int:  # Exit code
    """`python -m cjm_substrate_qt_kit.gesturebench <module:function> --params JSON`: run the
    driver and print the gestures it ran as JSON."""
    ap = argparse.ArgumentParser(prog="gesturebench",
                                 description="Run one app's canonical gestures headlessly.")
    ap.add_argument("driver", help="The app's driver, '<module>:<function>'")
    ap.add_argument("--params", default="{}",
                    help="The driver's params as JSON (db, manifests_dir, journals, placeholders)")
    args = ap.parse_args(argv)
    ran = load_driver(args.driver)(json.loads(args.params))
    print(json.dumps({"driver": args.driver, "gestures": list(ran or [])}))
    return 0


if __name__ == "__main__":  # runtime-order: must trail every def
    sys.exit(main())
