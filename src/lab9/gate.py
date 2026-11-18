"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item


def _looser(spec_th: dict, base_th: dict) -> str | None:
    """First way spec_th is looser than base_th, or None when equal/stricter."""
    # A bound present in base must survive and may only get stricter: a deleted key is the loosest change.
    for key, lower_is_looser in (("min", True), ("max", False), ("max_increase", False)):
        if key not in base_th:
            continue
        if key not in spec_th:
            return f"{key} {base_th[key]} removed"
        if (spec_th[key] < base_th[key]) if lower_is_looser else (spec_th[key] > base_th[key]):
            return f"{key} {base_th[key]} -> {spec_th[key]}"
    if base_th.get("no_significant_drop") and not spec_th.get("no_significant_drop"):
        return "no_significant_drop dropped"
    if base_th.get("blocking") and not spec_th.get("blocking"):
        return "blocking -> non-blocking"
    return None


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate."""
    problems: list[str] = []
    # NaN / inf anywhere in the reported metrics.
    for mid, val in pr["metrics"].items():
        if isinstance(val, float) and not math.isfinite(val):
            problems.append(f"metric {mid} is {val}")
    # Row count and (item, seed) set must match the manifest exactly.
    # Trust the baseline's manifest, not the PR's own claim (a gamed report edits both rows and manifest).
    items, seeds = base["manifest"]["items"], base["manifest"]["seeds"]
    if len(pr["rows"]) != items * len(seeds):
        problems.append(f"rows {len(pr['rows'])} != baseline items {items} x seeds {len(seeds)}")
    pr_keys = {(r["item_id"], r["seed"]) for r in pr["rows"]}
    if len(pr_keys) != len(pr["rows"]):
        problems.append("duplicate (item_id, seed) rows")
    base_keys = {(r["item_id"], r["seed"]) for r in base["rows"]}
    if pr_keys != base_keys:
        dropped, added = base_keys - pr_keys, pr_keys - base_keys
        problems.append(f"(item, seed) set differs from baseline: dropped {sorted(dropped)[:3]}, added {sorted(added)[:3]}")
    # A crashed grader must not silently drop out of the mean.
    if "evaluator_failures" not in pr:
        problems.append("evaluator_failures key missing from report")
    elif pr["evaluator_failures"]:
        problems.append(f"evaluator_failures non-empty ({len(pr['evaluator_failures'])})")
    # Only row-level (grader) metrics live in rows; aggregates like pass_hat_5 do not.
    row_metrics = [k for k in (pr["rows"][0] if pr["rows"] else {}) if k not in ("item_id", "seed", "slices", "cost")]
    for r in pr["rows"]:
        missing = [m for m in row_metrics if r.get(m) is None]
        if missing:
            problems.append(f"{r['item_id']}@{r['seed']}: value None for {','.join(missing)}")
            break
    # Slice tags may not be relabelled between PR and baseline.
    base_slices = {r["item_id"]: r.get("slices") or [] for r in base["rows"]}
    relabelled = sorted({r["item_id"] for r in pr["rows"] if (r.get("slices") or []) != base_slices.get(r["item_id"])})
    if relabelled:
        problems.append(f"slice tags differ from baseline for {relabelled[:3]}")
    # Ratchet: on the same eval-set version a threshold may only get stricter.
    if base_spec is not None:
        if spec.get("eval_set_version") == base_spec.get("eval_set_version"):
            spec_by_id = {m["id"]: m for m in spec["metrics"]}
            for b in base_spec["metrics"]:
                m = spec_by_id.get(b["id"])
                if m is None:
                    problems.append(f"metric {b['id']} dropped from spec")
                    continue
                if b.get("blocking") and not m.get("blocking"):
                    problems.append(f"metric {b['id']}: blocking -> non-blocking")
                looser = _looser(m.get("threshold") or {}, b.get("threshold") or {})
                if looser:
                    problems.append(f"metric {b['id']} threshold loosened: {looser}")
            base_names = {(s["name"], s["metric"]) for s in base_spec.get("slices") or []}
            have = {(s["name"], s["metric"]) for s in spec.get("slices") or []}
            for name, metric in sorted(base_names - have):
                problems.append(f"slice {name}/{metric} dropped from spec")
            base_by_pair = {(s["name"], s["metric"]): s for s in base_spec.get("slices") or []}
            for s in spec.get("slices") or []:
                b = base_by_pair.get((s["name"], s["metric"]))
                if b is None:
                    continue
                looser = _looser(s, b)  # slice entries carry min/max/no_significant_drop/blocking inline
                if looser:
                    problems.append(f"slice {s['name']}/{s['metric']} loosened: {looser}")
    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "max"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min" / above "max", or if no_significant_drop and the paired CI over the
        slice's items lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked: list[str] = []
    lines: list[str] = []
    bs = spec.get("bootstrap", {})
    for s in spec.get("slices") or []:
        name, mid = s["name"], s["metric"]
        a = per_item(pr, mid, slice_name=name)
        if not a:
            lines.append(f"  slice {name}/{mid:<22} no items carry this slice")
            continue
        value = sum(a.values()) / len(a)
        verdict, note = "ok", f"({len(a)} items)"
        if s.get("no_significant_drop"):
            b = per_item(base, mid, slice_name=name)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"({len(a)} items) Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if "min" in s and value < s["min"]:
            verdict = "fail"
        if "max" in s and value > s["max"]:
            verdict = "fail"
        if verdict == "fail" and s.get("blocking"):
            blocked.append(f"slice:{name}/{mid}")
        label = "BLOCK" if (verdict == "fail" and s.get("blocking")) else ("warn" if verdict == "fail" else "ok")
        lines.append(f"  slice {name}/{mid:<22} {value:<8.3f} {json.dumps({k: v for k, v in s.items() if k in ('min', 'max', 'no_significant_drop')}):<46} {note:<28} {label}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
