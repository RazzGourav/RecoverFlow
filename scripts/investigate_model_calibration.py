#!/usr/bin/env python3
"""
Model Calibration & RETRY-Dominance Investigation Script

READ-ONLY analysis — no models, thresholds, or data are modified.

This script addresses three questions:
  1. What is the full probability distribution (min/max/mean/median/percentiles)
     of the recoverability score and the intervention confidence (best_prob)
     that the benchmark actually produces? How does this compare to the 0.80
     confidence_threshold in the live policy?
  2. WHY does RETRY dominate 100/100 argmax picks? Is this a training-data
     property (the ground truth never rewards non-RETRY actions for any segment)?
  3. Does RecoverFlow differentiate meaningfully in a "retry-exhausted" scenario
     where prior retries exceed the policy retry_limit?
"""

import json
import sys
from pathlib import Path

# Windows consoles default to a legacy codepage that cannot encode arrows/symbols.
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd

root_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root_dir))

from ai.features.engineer import build_features, ACTION_TYPES
from ai.inference import predict


def pct_stats(arr: np.ndarray, label: str) -> dict:
    """Compute full distribution stats for a 1-D array of probabilities."""
    return {
        "label": label,
        "n": len(arr),
        "min": float(np.min(arr)),
        "p5": float(np.percentile(arr, 5)),
        "p10": float(np.percentile(arr, 10)),
        "p25": float(np.percentile(arr, 25)),
        "median": float(np.median(arr)),
        "mean": float(np.mean(arr)),
        "p75": float(np.percentile(arr, 75)),
        "p90": float(np.percentile(arr, 90)),
        "p95": float(np.percentile(arr, 95)),
        "max": float(np.max(arr)),
        "std": float(np.std(arr)),
        "above_080": int(np.sum(arr >= 0.80)),
        "pct_above_080": float(np.mean(arr >= 0.80) * 100),
    }


def print_stats(stats: dict) -> None:
    """Pretty-print distribution stats."""
    print(f"\n{'='*60}")
    print(f"  {stats['label']}  (n={stats['n']})")
    print(f"{'='*60}")
    print(f"  min    = {stats['min']:.6f}")
    print(f"  p5     = {stats['p5']:.6f}")
    print(f"  p10    = {stats['p10']:.6f}")
    print(f"  p25    = {stats['p25']:.6f}")
    print(f"  median = {stats['median']:.6f}")
    print(f"  mean   = {stats['mean']:.6f}")
    print(f"  p75    = {stats['p75']:.6f}")
    print(f"  p90    = {stats['p90']:.6f}")
    print(f"  p95    = {stats['p95']:.6f}")
    print(f"  max    = {stats['max']:.6f}")
    print(f"  std    = {stats['std']:.6f}")
    print(f"  >= 0.80 threshold: {stats['above_080']} / {stats['n']}  "
          f"({stats['pct_above_080']:.1f}%)")


# ---------------------------------------------------------------------------
# TASK 1: Full probability distribution of recoverability + confidence
# ---------------------------------------------------------------------------
def task1_probability_distributions(test_df: pd.DataFrame) -> tuple[dict, dict]:
    """Extract the exact recoverability and confidence distributions from test set."""
    print("\n" + "#" * 70)
    print("# TASK 1: Probability Distributions (recoverability & confidence)")
    print("#" * 70)

    recoverability_scores: list[float] = []
    confidence_scores: list[float] = []  # = best_prob (argmax intervention prob)
    all_action_probs: list[dict[str, float]] = []

    for _, row in test_df.iterrows():
        case_data = {
            "amount_paise": int(row["amount_paise"]),
            "failure_type": str(row["failure_type"]),
            "segment": str(row["segment"]),
            "tenure_days": int(row["tenure_days"]),
            "high_frequency_contact": str(row.get("high_frequency_contact", "False")) == "True",
            "requires_human_review": str(row.get("requires_human_review", "False")) == "True",
        }

        df_single = pd.DataFrame([case_data])
        X_base = build_features(df_single)

        # Recovery model (XGBoost) — same path as predict.py line 82
        recov_prob = float(predict._recovery_model.predict_proba(X_base)[0, 1])
        recoverability_scores.append(recov_prob)

        # Intervention model — scan all actions, record argmax
        action_probs: dict[str, float] = {}
        for action in ACTION_TYPES:
            X_action = X_base.copy()
            for a in ACTION_TYPES:
                X_action[f"action_{a}"] = 1 if a == action else 0
            prob = float(predict._intervention_model.predict_proba(X_action)[0, 1])
            action_probs[action] = prob

        best_prob = max(action_probs.values())
        confidence_scores.append(best_prob)
        all_action_probs.append(action_probs)

    recov_arr = np.array(recoverability_scores)
    conf_arr = np.array(confidence_scores)

    recov_stats = pct_stats(recov_arr, "Recoverability P(success) — Recovery XGBoost model")
    conf_stats = pct_stats(conf_arr, "Confidence (best_prob) — Intervention Logistic model argmax")

    print_stats(recov_stats)
    print_stats(conf_stats)

    # Show confidence gap
    print(f"\n  ** Gap to 0.80 threshold: "
          f"max confidence is {conf_stats['max']:.6f}, "
          f"which is {'ABOVE' if conf_stats['max'] >= 0.80 else 'BELOW'} 0.80 **")
    if conf_stats['max'] < 0.80:
        print("  ** Every single case falls BELOW the 0.80 threshold — "
              "0.80 was NEVER achievable with this model. **")

    return recov_stats, conf_stats


# ---------------------------------------------------------------------------
# TASK 2: Investigate RETRY dominance at the training-data level
# ---------------------------------------------------------------------------
def task2_retry_dominance_in_training_data() -> None:
    """Analyze the synthetic training labels to see if RETRY is actually the
    best-rewarded action in ground truth across all segment × failure_type combos."""
    print("\n" + "#" * 70)
    print("# TASK 2: RETRY Dominance in Training Data (Ground Truth Analysis)")
    print("#" * 70)

    train_df = pd.read_csv(root_dir / "data" / "processed" / "train.csv")

    # Parse boolean
    if train_df["actually_recovered"].dtype == object:
        train_df["recovered"] = train_df["actually_recovered"] == "True"
    else:
        train_df["recovered"] = train_df["actually_recovered"].astype(bool)

    # Overall action distribution in training data
    print("\n--- Overall action_taken distribution (training set) ---")
    action_counts = train_df["action_taken"].value_counts()
    print(action_counts.to_string())
    print(f"Total rows: {len(train_df)}")

    # Recovery rate per action
    print("\n--- Recovery rate by action_taken (training set) ---")
    action_recovery = train_df.groupby("action_taken")["recovered"].agg(["mean", "sum", "count"])
    action_recovery.columns = ["recovery_rate", "n_recovered", "n_total"]
    action_recovery = action_recovery.sort_values("recovery_rate", ascending=False)
    print(action_recovery.to_string())

    # Now the critical question: for each (segment, failure_type) pair,
    # which action has the HIGHEST recovery rate?
    print("\n--- Best action per (segment, failure_type) by ground-truth recovery rate ---")
    print("    (This is what the model SHOULD learn to prefer)")

    combos = train_df.groupby(["segment", "failure_type", "action_taken"])["recovered"].agg(
        ["mean", "sum", "count"]
    ).reset_index()
    combos.columns = ["segment", "failure_type", "action_taken", "recovery_rate", "n_recovered", "n_total"]

    # For each (segment, failure_type), find the action with the highest recovery rate
    # (only among actions with at least 2 samples to avoid noise)
    best_actions = []
    for (seg, ft), group in combos.groupby(["segment", "failure_type"]):
        # Filter to actions with enough data
        reliable = group[group["n_total"] >= 2]
        if reliable.empty:
            reliable = group  # fallback if no action has >= 2 samples

        best_row = reliable.loc[reliable["recovery_rate"].idxmax()]
        best_actions.append({
            "segment": seg,
            "failure_type": ft,
            "best_action": best_row["action_taken"],
            "best_recovery_rate": best_row["recovery_rate"],
            "n_total": best_row["n_total"],
            "all_actions": group[["action_taken", "recovery_rate", "n_total"]].to_dict("records"),
        })

    for ba in best_actions:
        is_retry = "✓ RETRY" if ba["best_action"] == "RETRY" else f"✗ {ba['best_action']}"
        print(f"  {ba['segment']:>14} × {ba['failure_type']:<18} → "
              f"{is_retry}  (rate={ba['best_recovery_rate']:.2f}, n={int(ba['n_total'])})")

    n_retry_best = sum(1 for ba in best_actions if ba["best_action"] == "RETRY")
    n_total = len(best_actions)
    print(f"\n  Summary: RETRY is the best action in {n_retry_best}/{n_total} "
          f"segment×failure_type combinations")

    # Check what determine_recovery() in generate.py actually rewards
    print("\n--- Analyzing determine_recovery() logic from generate.py ---")
    print("  failure_type=TEMPORARY: +0.20 for RETRY, +0.00 for everything else")
    print("  failure_type=PAYMENT_METHOD: +0.30 for PAYMENT_METHOD_UPDATE, -0.10 otherwise")
    print("  failure_type=CUSTOMER_ACTION: +0.20 for PAYMENT_LINK, -0.10 otherwise")
    print("  failure_type=PERSISTENT: always False (0% recovery)")
    print("  failure_type=UNKNOWN: no action modifier (base prob only)")
    print("  HIGH_VALUE + HUMAN_ESCALATION: +0.25")

    # Verify: for PAYMENT_METHOD failures, does PAYMENT_METHOD_UPDATE actually
    # show a higher recovery rate than RETRY in training data?
    print("\n--- Cross-check: PAYMENT_METHOD failures —")
    print("    Does PAYMENT_METHOD_UPDATE actually beat RETRY in training data? ---")
    pm_data = train_df[train_df["failure_type"] == "PAYMENT_METHOD"]
    pm_by_action = pm_data.groupby("action_taken")["recovered"].agg(["mean", "count"]).sort_values("mean", ascending=False)
    pm_by_action.columns = ["recovery_rate", "n"]
    print(pm_by_action.to_string())

    print("\n--- Cross-check: CUSTOMER_ACTION failures —")
    print("    Does PAYMENT_LINK actually beat RETRY in training data? ---")
    ca_data = train_df[train_df["failure_type"] == "CUSTOMER_ACTION"]
    ca_by_action = ca_data.groupby("action_taken")["recovered"].agg(["mean", "count"]).sort_values("mean", ascending=False)
    ca_by_action.columns = ["recovery_rate", "n"]
    print(ca_by_action.to_string())

    # NOW: the key — action_taken is assigned randomly (line 88 of generate.py),
    # so each (segment, failure_type) pair gets a RANDOM action,
    # and recovery depends on matching action to failure_type.
    # The model sees which action was taken and whether it succeeded.
    # So the model SHOULD learn the pattern — unless the training set is too small
    # or the logistic regression can't capture the interaction.
    print("\n--- Root cause analysis ---")
    print("  action_taken is assigned via random.choice(ACTION_TYPES) — uniform random.")
    print(f"  With {len(ACTION_TYPES)} actions and {len(train_df)} training rows,")
    print(f"  each (segment, failure_type, action) triple has ~"
          f"{len(train_df) / (len(set(train_df['segment'])) * len(set(train_df['failure_type'])) * len(ACTION_TYPES)):.1f} samples on average.")
    print("  This IS enough for logistic regression to learn the interaction IF the")
    print("  one-hot encoding captures it. Let's check what the model actually learned.")

    # Check model coefficients for action features
    model = predict._intervention_model
    feature_names = list(build_features(train_df.head(1)).columns) + [f"action_{a}" for a in ACTION_TYPES]
    coefs = dict(zip(feature_names, model.coef_[0]))
    action_coefs = {k: v for k, v in coefs.items() if k.startswith("action_")}

    print("\n--- Intervention model (LogisticRegression) coefficients for action features ---")
    for fname, coef in sorted(action_coefs.items(), key=lambda x: -x[1]):
        print(f"  {fname:<35} = {coef:+.6f}")

    print("\n--- Intervention model coefficients for ALL features ---")
    for fname, coef in sorted(coefs.items(), key=lambda x: -abs(x[1])):
        print(f"  {fname:<35} = {coef:+.6f}")

    # Check the intercept
    print(f"\n  Model intercept = {model.intercept_[0]:+.6f}")


# ---------------------------------------------------------------------------
# TASK 3: Retry-exhausted scenario
# ---------------------------------------------------------------------------
def task3_retry_exhausted_comparison(test_df: pd.DataFrame) -> dict:
    """Simulate the retry-exhausted scenario: filter/construct cases where
    prior retry count exceeds policy's retry_limit (2). Compare:
      A) RecoverFlow's best non-RETRY action selection
      B) "Give up" baseline (NO_ACTION, ₹0 recovery)
      C) For reference: what RETRY would have scored (not executable)
    """
    print("\n" + "#" * 70)
    print("# TASK 3: Retry-Exhausted Scenario Comparison")
    print("#" * 70)

    POLICY_RETRY_LIMIT = 2  # from live policy defaults

    # We construct the scenario: all test cases are treated as if they've already
    # exhausted their retry budget (retry_count >= retry_limit).
    # In this scenario, RETRY is no longer a valid action.
    # We compare RecoverFlow's best PAID/non-retry action vs. give-up.

    non_retry_actions = [a for a in ACTION_TYPES if a not in ("RETRY", "NO_ACTION")]

    results = []

    for _, row in test_df.iterrows():
        case_data = {
            "amount_paise": int(row["amount_paise"]),
            "failure_type": str(row["failure_type"]),
            "segment": str(row["segment"]),
            "tenure_days": int(row["tenure_days"]),
            "high_frequency_contact": str(row.get("high_frequency_contact", "False")) == "True",
            "requires_human_review": str(row.get("requires_human_review", "False")) == "True",
        }

        df_single = pd.DataFrame([case_data])
        X_base = build_features(df_single)

        # Score all actions
        action_probs: dict[str, float] = {}
        for action in ACTION_TYPES:
            X_action = X_base.copy()
            for a in ACTION_TYPES:
                X_action[f"action_{a}"] = 1 if a == action else 0
            prob = float(predict._intervention_model.predict_proba(X_action)[0, 1])
            action_probs[action] = prob

        # RETRY score (for reference — not selectable in retry-exhausted scenario)
        retry_prob = action_probs["RETRY"]
        retry_ev = retry_prob * case_data["amount_paise"]

        # Best non-retry, non-no_action action
        best_alt_action = max(non_retry_actions, key=lambda a: action_probs[a])
        best_alt_prob = action_probs[best_alt_action]
        best_alt_ev = best_alt_prob * case_data["amount_paise"]

        # Give-up baseline
        give_up_ev = 0.0

        results.append({
            "case_id": str(row.get("case_id", "unknown")),
            "segment": case_data["segment"],
            "failure_type": case_data["failure_type"],
            "amount_paise": case_data["amount_paise"],
            "retry_prob": retry_prob,
            "retry_ev": retry_ev,
            "best_alt_action": best_alt_action,
            "best_alt_prob": best_alt_prob,
            "best_alt_ev": best_alt_ev,
            "give_up_ev": give_up_ev,
            "alt_beats_giveup": best_alt_ev > 0,
            "all_probs": action_probs,
        })

    results_df = pd.DataFrame(results)

    # Summary stats
    total_value = results_df["amount_paise"].sum()
    total_retry_ev = results_df["retry_ev"].sum()
    total_alt_ev = results_df["best_alt_ev"].sum()
    total_giveup_ev = 0

    print(f"\n  Scenario: All {len(results_df)} test cases treated as retry-exhausted")
    print(f"  (retry_count >= {POLICY_RETRY_LIMIT}, RETRY action NOT selectable)")
    print(f"  Total value at risk: ₹{total_value / 100:,.2f}")

    print("\n  Strategy comparison (retry-exhausted cases):")
    print(f"  {'Strategy':<35} {'Expected Recovery (₹)':>22} {'vs Give-Up':>12}")
    print(f"  {'-'*35} {'-'*22} {'-'*12}")
    print(f"  {'Give Up (NO_ACTION)':<35} {'₹0.00':>22} {'—':>12}")
    print(f"  {'RecoverFlow Best Non-RETRY':<35} ₹{total_alt_ev / 100:>20,.2f} "
          f"+₹{(total_alt_ev - total_giveup_ev) / 100:>10,.2f}")
    print(f"  {'(Reference: RETRY if allowed)':<35} ₹{total_retry_ev / 100:>20,.2f} "
          f"+₹{(total_retry_ev - total_giveup_ev) / 100:>10,.2f}")

    # Show distribution of alternative action selections
    print("\n  Action distribution in retry-exhausted scenario:")
    alt_action_dist = results_df["best_alt_action"].value_counts()
    for action, count in alt_action_dist.items():
        print(f"    {action:<30} {count:>4} cases")

    # Break down by failure_type
    print("\n  Expected recovery by failure_type (retry-exhausted):")
    for ft in sorted(results_df["failure_type"].unique()):
        subset = results_df[results_df["failure_type"] == ft]
        alt_ev = subset["best_alt_ev"].sum()
        retry_ev = subset["retry_ev"].sum()
        n = len(subset)
        print(f"    {ft:<20} n={n:>3}  "
              f"Alt EV=₹{alt_ev / 100:>12,.2f}  "
              f"RETRY EV=₹{retry_ev / 100:>12,.2f}  "
              f"Alt/RETRY={alt_ev / retry_ev * 100 if retry_ev > 0 else 0:.1f}%")

    # Detailed probability comparison: RETRY vs best alternative
    print("\n  Probability comparison: RETRY vs best non-RETRY action")
    retry_probs = np.array(results_df["retry_prob"])
    alt_probs = np.array(results_df["best_alt_prob"])
    gap = retry_probs - alt_probs

    print(f"    RETRY prob:    mean={retry_probs.mean():.6f}, "
          f"median={np.median(retry_probs):.6f}")
    print(f"    Alt prob:      mean={alt_probs.mean():.6f}, "
          f"median={np.median(alt_probs):.6f}")
    print(f"    Gap (R - Alt): mean={gap.mean():.6f}, "
          f"median={np.median(gap):.6f}, "
          f"max={gap.max():.6f}")
    print(f"    Cases where alt > RETRY: {(alt_probs > retry_probs).sum()} / {len(results_df)}")
    print(f"    Cases where alt == RETRY: {(np.isclose(alt_probs, retry_probs)).sum()} / {len(results_df)}")

    # The honest answer
    print("\n  ** HONEST ASSESSMENT **")
    if total_alt_ev > 0:
        print("  RecoverFlow's non-RETRY actions DO produce non-zero expected recovery")
        print(f"  (₹{total_alt_ev / 100:,.2f}) in the retry-exhausted scenario,")
        print("  meaningfully outperforming the 'give up' baseline (₹0.00).")
        pct_of_retry = (total_alt_ev / total_retry_ev * 100) if total_retry_ev > 0 else 0
        print(f"  However, alt actions recover only {pct_of_retry:.1f}% of what RETRY would,")
        print("  reflecting the model's learned RETRY preference from training data.")
    else:
        print("  RecoverFlow's non-RETRY actions produce ZERO expected recovery — ")
        print("  no meaningful differentiation from the 'give up' baseline.")

    summary = {
        "n_cases": len(results_df),
        "total_value_paise": int(total_value),
        "give_up_ev_paise": 0,
        "alt_ev_paise": int(total_alt_ev),
        "retry_ev_paise": int(total_retry_ev),
        "alt_pct_of_retry": float(total_alt_ev / total_retry_ev * 100) if total_retry_ev > 0 else 0.0,
        "action_distribution": alt_action_dist.to_dict(),
    }
    return summary


def main() -> None:
    # Load models
    predict.load_models()

    # Load test set (same as benchmark: first 100 rows)
    test_df = pd.read_csv(root_dir / "data" / "processed" / "test.csv")
    test_df = test_df.head(100)
    print(f"Loaded {len(test_df)} test cases (matching benchmark N=100)")

    # Run all three tasks
    recov_stats, conf_stats = task1_probability_distributions(test_df)
    task2_retry_dominance_in_training_data()
    task3_summary = task3_retry_exhausted_comparison(test_df)

    # Save full results to JSON for reference
    output = {
        "recoverability_distribution": recov_stats,
        "confidence_distribution": conf_stats,
        "retry_exhausted_summary": task3_summary,
    }
    output_path = root_dir / "evaluation" / "reports" / "model-calibration-investigation.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\n\nFull results saved to {output_path}")


if __name__ == "__main__":
    main()
