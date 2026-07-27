"""Check the world against config/metrics.yaml.

The registry is the human-owned definition of every published number. This script is
the machine half: it recomputes each metric from source, compares to the registered
value, scans content surfaces for retracted numbers, and checks that each derived
artifact still has exactly one writer.

    python scripts/validate_metrics.py            # report; exit 1 on any drift
    python scripts/validate_metrics.py --update   # rewrite `value`/`sample` to truth
    python scripts/validate_metrics.py --quiet    # only failures

Why it exists: a prose rule in CLAUDE.md cannot notice when it stops being true.
Project memory was publishing 68.11% overall and 61.07% close-game months after both
had moved, and weekly_validation.py quietly took over a file it did not own. Both are
the same class of bug, and both are cheap to catch mechanically.

Run it after any pipeline change, before publishing numbers, and in a session's
closing checks. It is deliberately NOT wired into the daily cron: it is a gate for
humans and agents, not a thing that should page a server at 7am.
"""

import argparse
import ast
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "config/metrics.yaml"

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


# --------------------------------------------------------------- computations
# Explicit functions rather than eval'ing the YAML: the registry states intent in
# prose for a human, the code states it in python for the machine, and the two being
# separate is what makes a mismatch visible instead of self-confirming.
def _log() -> pd.DataFrame:
    p = ROOT / "data/exports/prediction_tracking_honest.csv"
    if not p.exists():
        raise FileNotFoundError(p)
    return pd.read_csv(p).dropna(subset=["correct"])


def _bucket(lo: float, hi: float):
    def f():
        d = _log()
        s = d[(d["confidence"] > lo) & (d["confidence"] <= hi)]
        return 100 * s["correct"].mean(), len(s)
    return f


def _flag(col: str):
    def f():
        d = _log()
        s = d[d[col] == True]  # noqa: E712  (pandas mask, not a bool identity test)
        return 100 * s["correct"].mean(), len(s)
    return f


def _accuracy():
    d = _log()
    return 100 * d["correct"].mean(), len(d)


def _correct():
    d = _log()
    return int(d["correct"].sum()), len(d)


def _brier():
    d = _log()
    y = (d["actual_winner"] == "home").astype(int)
    return float(np.mean((d["predicted_home_prob"] - y) ** 2)), len(d)


COMPUTE = {
    "season_accuracy": _accuracy,
    "season_correct": _correct,
    "season_brier": _brier,
    "close_game_accuracy": _flag("is_close_game"),
    "toss_up_accuracy": _flag("is_toss_up"),
    "calibration_80_90": _bucket(0.80, 0.90),
    "calibration_70_80": _bucket(0.70, 0.80),
}


# -------------------------------------------------------------------- checks
def check_metrics(reg: dict, update: bool) -> tuple[list, dict]:
    problems, observed = [], {}
    for key, spec in (reg.get("metrics") or {}).items():
        fn = COMPUTE.get(key)
        if fn is None:
            problems.append(("UNCHECKED", key,
                             "registered but no computation is wired in "
                             "(add one to COMPUTE, or the entry is decorative)"))
            continue
        try:
            value, sample = fn()
        except Exception as e:
            problems.append(("ERROR", key, f"{type(e).__name__}: {e}"))
            continue
        observed[key] = (value, sample)

        tol = float(spec.get("tolerance", 0))
        want = spec.get("value")
        if want is not None and abs(float(want) - value) > tol:
            problems.append(("DRIFT", key,
                             f"registry says {want}, source says {round(value, 4)} "
                             f"(tolerance {tol})"))
        want_n = spec.get("sample")
        if want_n is not None and int(want_n) != sample:
            problems.append(("DRIFT", key,
                             f"sample size {want_n} -> {sample}"))
    return problems, observed


def check_forbidden(reg: dict) -> list:
    problems = []
    for rule in reg.get("forbidden") or []:
        pat, allow = str(rule["pattern"]), rule.get("allow") or []
        surfaces = [f for g in (rule.get("scan") or []) for f in ROOT.glob(g)
                    if f.is_file()]
        for f in surfaces:
            rel = f.relative_to(ROOT).as_posix()
            if rel in allow:
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if pat in text:
                line = next((i for i, l in enumerate(text.splitlines(), 1)
                             if pat in l), "?")
                problems.append(("FORBIDDEN", rel,
                                 f"contains {pat!r} at line {line}"))
    return problems


def scheduled_scripts() -> set:
    """Scripts reachable from something that runs on a schedule. A second writer that
    fires on a timer is how player_team_mapping.csv got clobbered every Sunday; one
    sitting in scripts/ that nobody runs is a footgun, not an incident. Separating the
    two is what keeps this check worth reading."""
    entry, out = [], set()
    for g in ("scripts/run_*.bat", "scripts/daily_update.py",
              "scripts/weekly_validation.py", "run_daily_update.sh"):
        entry += list(ROOT.glob(g))
    for e in entry:
        out.add(e.relative_to(ROOT).as_posix())
        try:
            raw = e.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        # Text matching is too blunt here. weekly_validation.py NAMES
        # update_rosters_2025_26.py three times, twice in comments and once in a
        # DOCSTRING ("Mirrors the logic in ..."), while never running it, and that
        # reported a dormant script as a live second writer. For python, parse and
        # look only at real imports and at strings passed to calls; for shell and
        # batch, strip comments and match text.
        if e.suffix == ".py":
            names = set()
            try:
                tree = ast.parse(raw)
            except SyntaxError:
                tree = None
            for node in ast.walk(tree) if tree else []:
                if isinstance(node, ast.Import):
                    names.update(a.name.split(".")[-1] for a in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names.add(node.module.split(".")[-1])
                elif isinstance(node, ast.Call):
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                            names.add(Path(sub.value).name)
                            names.add(Path(sub.value).stem)
            hit = lambda s: s.name in names or s.stem in names  # noqa: E731
        else:
            lines = [ln.split(" #")[0] for ln in raw.splitlines()
                     if not ln.strip().startswith("#")
                     and not ln.strip().lower().startswith(("::", "rem "))]
            text = "\n".join(lines)
            hit = lambda s: s.name in text  # noqa: E731

        for s in list((ROOT / "scripts").glob("*.py")) + list((ROOT / "src").rglob("*.py")):
            if hit(s):
                out.add(s.relative_to(ROOT).as_posix())
    return out


def check_artifacts(reg: dict) -> list:
    """Grep for scripts writing a file they do not own. Static and approximate: it
    looks for a write call naming the path, which catches the real-world case
    (a second script quietly taking over an output) without pretending to be
    dataflow analysis."""
    problems = []
    sched = scheduled_scripts()
    scripts = list((ROOT / "scripts").glob("*.py")) + list((ROOT / "src").rglob("*.py"))
    for path, spec in (reg.get("artifacts") or {}).items():
        owner = spec["owner"]
        stem = Path(path).name
        for s in scripts:
            rel = s.relative_to(ROOT).as_posix()
            if rel == owner:
                continue
            try:
                text = s.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for m in re.finditer(r"^.*\b(to_csv|write_text|to_json|savefig|open)\s*\(.*$",
                                 text, re.M):
                line = m.group(0)
                if stem in line or re.search(rf"\b{re.escape(stem.split('.')[0])}\b.*\)", line):
                    kind = "SECOND WRITER" if rel in sched else "legacy writer"
                    problems.append((kind, rel,
                                     f"appears to write {stem}, owned by {owner}"))
                    break
            else:
                # also catch `VAR = ...path...` then `VAR.write`/`to_csv(VAR)`
                if stem in text and re.search(r"to_csv\(|write_text\(|to_json\(", text):
                    var = re.search(rf"^\s*(\w+)\s*=\s*.*{re.escape(stem)}.*$",
                                    text, re.M)
                    if var and re.search(rf"to_csv\(\s*{var.group(1)}\b|"
                                         rf"{var.group(1)}\.write_text\(", text):
                        kind = "SECOND WRITER" if rel in sched else "legacy writer"
                        problems.append((kind, rel,
                                         f"writes {stem} via {var.group(1)}, "
                                         f"owned by {owner}"))
    return problems


def do_update(reg_text: str, observed: dict, reg: dict) -> str:
    """Rewrite value/sample in place, preserving comments and layout."""
    out = reg_text
    for key, (value, sample) in observed.items():
        spec = reg["metrics"][key]
        block = re.search(rf"^  {re.escape(key)}:\n(?:\s.*\n|\n)*?(?=^  \w|\Z)",
                          out, re.M)
        if not block:
            continue
        body = block.group(0)
        new = body
        dec = 4 if spec.get("unit") == "score" else 2
        if spec.get("value") is not None:
            new = re.sub(r"^(\s*value:\s*).*$", rf"\g<1>{round(value, dec)}",
                         new, count=1, flags=re.M)
        if spec.get("sample") is not None:
            new = re.sub(r"^(\s*sample:\s*).*$", rf"\g<1>{sample}",
                         new, count=1, flags=re.M)
        out = out.replace(body, new)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Validate published metrics")
    ap.add_argument("--update", action="store_true",
                    help="rewrite registry values to observed truth")
    ap.add_argument("--quiet", action="store_true", help="only show failures")
    a = ap.parse_args()

    text = REGISTRY.read_text(encoding="utf-8")
    reg = yaml.safe_load(text)

    problems, observed = check_metrics(reg, a.update)
    problems += check_forbidden(reg)
    problems += check_artifacts(reg)

    if not a.quiet:
        print(f"{DIM}registry: {REGISTRY.relative_to(ROOT)}{RESET}")
        for key, (v, n) in observed.items():
            spec = reg["metrics"][key]
            unit = "" if spec.get("unit") == "count" else \
                   ("%" if spec.get("unit") == "percent" else "")
            dec = 4 if spec.get("unit") == "score" else 2
            print(f"  {GREEN}ok{RESET}  {key:22s} {round(v, dec)}{unit}  (n={n})")

    if a.update:
        REGISTRY.write_text(do_update(text, observed, reg), encoding="utf-8")
        print(f"\n{YELLOW}registry updated to observed values. "
              f"Review and commit the diff.{RESET}")
        return

    advisory = {"UNCHECKED", "legacy writer"}
    drift = [p for p in problems if p[0] not in advisory]
    legacy = [p for p in problems if p[0] == "legacy writer"]
    for kind, where, detail in problems:
        if kind == "legacy writer":
            continue
        colour = YELLOW if kind in advisory else RED
        print(f"  {colour}{kind}{RESET}  {where}: {detail}")
    if legacy and not a.quiet:
        print(f"\n{DIM}{len(legacy)} dormant legacy writer(s), not on any "
              f"schedule (advisory):{RESET}")
        for _, where, detail in legacy:
            print(f"  {DIM}- {where}: {detail}{RESET}")

    if drift:
        print(f"\n{RED}{len(drift)} problem(s).{RESET} If a number legitimately "
              f"changed, run --update and commit the diff so the change is reviewed.")
        sys.exit(1)
    print(f"\n{GREEN}All registered metrics match source.{RESET}")


if __name__ == "__main__":
    main()
